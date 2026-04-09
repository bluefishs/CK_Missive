"""
桃園派工系統 - 收發文對照確認與重建 API

包含端點：
- /dispatch/{dispatch_id}/confirm-correspondence - 確認收發文對應並寫入知識圖譜
- /dispatch/{dispatch_id}/rebuild-correspondence - 重建派工單的公文對照矩陣
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, tuple_
from sqlalchemy.orm import selectinload
from .common import (
    get_async_db, require_auth,
    TaoyuanDispatchOrder, TaoyuanDispatchDocumentLink,
)
from app.schemas.taoyuan.links import ConfirmCorrespondenceRequest

router = APIRouter()


@router.post(
    "/dispatch/{dispatch_id}/confirm-correspondence",
    summary="確認收發文對應並寫入知識圖譜",
)
async def confirm_correspondence(
    dispatch_id: int,
    request: ConfirmCorrespondenceRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_auth()),
):
    """
    確認收發文對應配對，將關係寫入知識圖譜。

    對每組 incoming↔outgoing 配對：
    1. 查找兩份公文共享的 CanonicalEntity（透過 DocumentEntityMention）
    2. 為共享實體建立或更新 EntityRelationship (relation_type='correspondence')
    3. 失效圖譜快取
    """
    logger = logging.getLogger(__name__)

    try:
        from app.extended.models import (
            CanonicalEntity, DocumentEntityMention, EntityRelationship,
        )
        from app.services.ai.graph.graph_helpers import invalidate_graph_cache

        if not request.pairs:
            return {
                "success": True,
                "confirmed_count": 0,
                "relationships_created": 0,
                "relationships_updated": 0,
            }

        # ----------------------------------------------------------------
        # Phase 1: 批次預載所有相關公文的 canonical_entity_id
        # 將 O(2N) 查詢合併為 1 次
        # ----------------------------------------------------------------
        valid_pairs = []
        all_doc_ids = set()
        for pair in request.pairs:
            incoming_doc_id = pair.get("incoming_doc_id")
            outgoing_doc_id = pair.get("outgoing_doc_id")
            if not incoming_doc_id or not outgoing_doc_id:
                logger.warning("跳過無效配對: incoming=%s, outgoing=%s", incoming_doc_id, outgoing_doc_id)
                continue
            valid_pairs.append((incoming_doc_id, outgoing_doc_id))
            all_doc_ids.update([incoming_doc_id, outgoing_doc_id])

        if not valid_pairs:
            return {"success": True, "confirmed_count": 0, "relationships_created": 0, "relationships_updated": 0}

        # 一次查詢所有 document → canonical_entity_id 映射
        mentions_result = await db.execute(
            select(
                DocumentEntityMention.document_id,
                DocumentEntityMention.canonical_entity_id,
            ).where(
                DocumentEntityMention.document_id.in_(all_doc_ids),
                DocumentEntityMention.canonical_entity_id.isnot(None),
            )
        )
        doc_entity_map: dict[int, set[int]] = {}
        for doc_id, entity_id in mentions_result.all():
            doc_entity_map.setdefault(doc_id, set()).add(entity_id)

        # ----------------------------------------------------------------
        # Phase 2: 收集所有需要的 (source, target) 對
        # ----------------------------------------------------------------
        needed_pairs: list[tuple[int, int, int]] = []  # (source_id, target_id, incoming_doc_id)
        pair_plan: list[tuple[set[int], set[int], int, int]] = []  # (shared, fallback, in_id, out_id)

        for incoming_doc_id, outgoing_doc_id in valid_pairs:
            in_ents = doc_entity_map.get(incoming_doc_id, set())
            out_ents = doc_entity_map.get(outgoing_doc_id, set())
            shared = in_ents & out_ents

            if not shared:
                if in_ents and out_ents:
                    src = next(iter(in_ents))
                    tgt = next(iter(out_ents))
                    needed_pairs.append((src, tgt, incoming_doc_id))
            else:
                for eid in shared:
                    needed_pairs.append((eid, eid, incoming_doc_id))
                shared_list = list(shared)
                if len(shared_list) >= 2:
                    needed_pairs.append((shared_list[0], shared_list[1], incoming_doc_id))

            pair_plan.append((shared, in_ents | out_ents, incoming_doc_id, outgoing_doc_id))

        # ----------------------------------------------------------------
        # Phase 3: 批次查詢既有 correspondence 關係 → O(1) 查詢
        # ----------------------------------------------------------------
        existing_rels_map: dict[tuple[int, int], EntityRelationship] = {}
        if needed_pairs:
            st_pairs = [(s, t) for s, t, _ in needed_pairs]
            unique_pairs = list(set(st_pairs))
            # 批次查詢：所有相關的 correspondence 關係
            existing_result = await db.execute(
                select(EntityRelationship).where(
                    EntityRelationship.relation_type == "correspondence",
                    tuple_(
                        EntityRelationship.source_entity_id,
                        EntityRelationship.target_entity_id,
                    ).in_(unique_pairs),
                )
            )
            for rel in existing_result.scalars().all():
                existing_rels_map[(rel.source_entity_id, rel.target_entity_id)] = rel

        # ----------------------------------------------------------------
        # Phase 4: 批次建立/更新關係 (純記憶體操作，最後一次 commit)
        # ----------------------------------------------------------------
        relationships_created = 0
        relationships_updated = 0
        confirmed_count = 0

        for incoming_doc_id, outgoing_doc_id in valid_pairs:
            in_ents = doc_entity_map.get(incoming_doc_id, set())
            out_ents = doc_entity_map.get(outgoing_doc_id, set())
            shared = in_ents & out_ents

            def _upsert_rel(source_id: int, target_id: int, doc_id: int) -> None:
                nonlocal relationships_created, relationships_updated
                key = (source_id, target_id)
                existing = existing_rels_map.get(key)
                if existing:
                    existing.document_count = (existing.document_count or 1) + 1
                    existing.weight = (existing.weight or 1.0) + 1.0
                    relationships_updated += 1
                else:
                    rel = EntityRelationship(
                        source_entity_id=source_id,
                        target_entity_id=target_id,
                        relation_type="correspondence",
                        relation_label="收發文對應",
                        weight=1.0,
                        document_count=1,
                        first_document_id=doc_id,
                    )
                    db.add(rel)
                    existing_rels_map[key] = rel
                    relationships_created += 1

            if not shared:
                if in_ents and out_ents:
                    _upsert_rel(next(iter(in_ents)), next(iter(out_ents)), incoming_doc_id)
                confirmed_count += 1
                continue

            for eid in shared:
                _upsert_rel(eid, eid, incoming_doc_id)

            shared_list = list(shared)
            if len(shared_list) >= 2:
                _upsert_rel(shared_list[0], shared_list[1], incoming_doc_id)

            confirmed_count += 1

        await db.commit()

        # 失效圖譜快取
        await invalidate_graph_cache()

        logger.info(
            "收發文對應確認完成: dispatch=%d, confirmed=%d, created=%d, updated=%d",
            dispatch_id, confirmed_count, relationships_created, relationships_updated,
        )

        return {
            "success": True,
            "confirmed_count": confirmed_count,
            "relationships_created": relationships_created,
            "relationships_updated": relationships_updated,
        }

    except Exception as e:
        logger.error("收發文對應確認失敗: %s", e)
        return {
            "success": False,
            "confirmed_count": 0,
            "relationships_created": 0,
            "relationships_updated": 0,
        }


@router.post(
    "/dispatch/{dispatch_id}/rebuild-correspondence",
    summary="重建派工單的公文對照矩陣",
)
async def rebuild_correspondence(
    dispatch_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_auth()),
):
    """
    重建派工單的公文對照矩陣：

    1. 取得該派工單所有已關聯的公文
    2. 對每份公文重新執行自動關聯邏輯
    3. 回傳更新後的關聯統計
    """
    logger = logging.getLogger(__name__)

    try:
        from app.services.document_dispatch_linker_service import DocumentDispatchLinkerService

        # 1. 確認派工單存在
        order_result = await db.execute(
            select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.id == dispatch_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="派工紀錄不存在")

        # 2. 取得目前所有關聯公文 ID
        existing_links_result = await db.execute(
            select(TaoyuanDispatchDocumentLink)
            .options(selectinload(TaoyuanDispatchDocumentLink.document))
            .where(TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id)
        )
        existing_links = existing_links_result.scalars().all()
        existing_doc_ids = {link.document_id for link in existing_links}

        # 3. 對每份已關聯的公文重新執行自動關聯
        linker = DocumentDispatchLinkerService(db)
        new_links_count = 0
        for link in existing_links:
            if link.document:
                await linker.auto_link_to_dispatch_orders(link.document)

        # 4. 統計新增的關聯
        updated_links_result = await db.execute(
            select(TaoyuanDispatchDocumentLink).where(
                TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id
            )
        )
        updated_links = updated_links_result.scalars().all()
        updated_doc_ids = {link.document_id for link in updated_links}
        new_links_count = len(updated_doc_ids - existing_doc_ids)

        await db.commit()

        logger.info(
            "重建公文對照矩陣完成: dispatch_id=%d, 既有=%d, 新增=%d, 總計=%d",
            dispatch_id, len(existing_doc_ids), new_links_count, len(updated_doc_ids),
        )

        return {
            "success": True,
            "dispatch_id": dispatch_id,
            "existing_count": len(existing_doc_ids),
            "new_links_count": new_links_count,
            "total_count": len(updated_doc_ids),
            "message": f"重建完成：既有 {len(existing_doc_ids)} 筆，新增 {new_links_count} 筆",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("重建公文對照矩陣失敗: dispatch_id=%d, error=%s", dispatch_id, e)
        return {
            "success": False,
            "message": f"重建失敗: {str(e)}",
        }

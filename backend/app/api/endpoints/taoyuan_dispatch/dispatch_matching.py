"""
桃園派工系統 - 實體匹配與公文對照建議 API

從 dispatch_document_links.py 拆分 (1057L → ~740L + 320L)

包含端點:
- /dispatch/{dispatch_id}/entity-similarity - 知識圖譜實體配對建議
- /dispatch/{dispatch_id}/correspondence-suggestions - NER 驅動公文對照建議

Version: 1.0.0
Created: 2026-03-29 (拆分自 dispatch_document_links.py)
"""
import logging
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from .common import (
    get_async_db, require_auth,
    TaoyuanDispatchDocumentLink,
)

router = APIRouter()


@router.post(
    "/dispatch/{dispatch_id}/entity-similarity",
    summary="知識圖譜實體配對建議",
)
async def get_entity_similarity(
    dispatch_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_auth()),
):
    """
    利用知識圖譜實體共現分析，計算派工單關聯公文間的語意相似度。

    回傳來文/發文兩兩間共享的 canonical entity 數量及詳情，
    供前端 buildCorrespondenceMatrix Phase 2 加權使用。
    """
    logger = logging.getLogger(__name__)

    try:
        from app.extended.models import DocumentEntityMention

        result = await db.execute(
            select(TaoyuanDispatchDocumentLink)
            .options(selectinload(TaoyuanDispatchDocumentLink.document))
            .where(TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id)
        )
        links = result.scalars().all()

        if not links:
            return {"success": True, "pairs": [], "total_entities": 0}

        incoming_ids: list[int] = []
        outgoing_ids: list[int] = []
        for link in links:
            if link.link_type == "company_outgoing":
                outgoing_ids.append(link.document_id)
            else:
                incoming_ids.append(link.document_id)

        all_doc_ids = incoming_ids + outgoing_ids
        if not all_doc_ids:
            return {"success": True, "pairs": [], "total_entities": 0}

        mentions_result = await db.execute(
            select(DocumentEntityMention).where(
                DocumentEntityMention.document_id.in_(all_doc_ids)
            )
        )
        mentions = mentions_result.scalars().all()

        doc_entities: dict[int, set] = defaultdict(set)
        entity_names: dict[int, str] = {}
        for m in mentions:
            doc_entities[m.document_id].add(m.canonical_entity_id)
            entity_names[m.canonical_entity_id] = m.mention_text

        pairs = []
        for in_id in incoming_ids:
            in_ents = doc_entities.get(in_id, set())
            if not in_ents:
                continue
            for out_id in outgoing_ids:
                out_ents = doc_entities.get(out_id, set())
                if not out_ents:
                    continue
                shared = in_ents & out_ents
                if shared:
                    union_size = len(in_ents | out_ents)
                    pairs.append({
                        "incoming_doc_id": in_id,
                        "outgoing_doc_id": out_id,
                        "shared_entity_count": len(shared),
                        "jaccard": round(len(shared) / union_size, 3) if union_size else 0,
                        "shared_entities": [
                            entity_names.get(eid, f"entity#{eid}")
                            for eid in list(shared)[:10]
                        ],
                    })

        pairs.sort(key=lambda p: p["shared_entity_count"], reverse=True)
        total_entities = len({eid for ents in doc_entities.values() for eid in ents})

        return {
            "success": True,
            "pairs": pairs,
            "total_entities": total_entities,
            "incoming_count": len(incoming_ids),
            "outgoing_count": len(outgoing_ids),
        }

    except Exception as e:
        logger.error("實體相似度計算失敗: %s", e)
        return {"success": False, "pairs": [], "total_entities": 0}


@router.post(
    "/dispatch/{dispatch_id}/correspondence-suggestions",
    summary="NER 驅動公文對照建議",
)
async def get_correspondence_suggestions(
    dispatch_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_auth()),
):
    """
    利用派工單實體連結和公文實體提及做 NER 驅動的來文/發文配對建議。
    回傳分級信心度 (confirmed/high/medium/low) 和具體實體名稱。
    """
    logger = logging.getLogger(__name__)

    try:
        from app.extended.models import (
            TaoyuanDispatchEntityLink, DocumentEntityMention,
            CanonicalEntity, TaoyuanWorkRecord, EntityRelationship,
        )

        # 1. 取得派工單的正規化實體集合
        dispatch_entities_result = await db.execute(
            select(
                TaoyuanDispatchEntityLink.canonical_entity_id,
                CanonicalEntity.canonical_name,
                CanonicalEntity.entity_type,
            )
            .join(CanonicalEntity, CanonicalEntity.id == TaoyuanDispatchEntityLink.canonical_entity_id)
            .where(TaoyuanDispatchEntityLink.dispatch_order_id == dispatch_id)
        )
        dispatch_entity_rows = dispatch_entities_result.all()
        dispatch_entity_ids = {r[0] for r in dispatch_entity_rows}
        dispatch_entity_names = {r[0]: (r[1], r[2]) for r in dispatch_entity_rows}

        if not dispatch_entity_ids:
            return {"success": True, "suggestions": [], "dispatch_entities": [], "message": "此派工單尚未建立實體連結"}

        # 2. 取得關聯公文及其分類
        links_result = await db.execute(
            select(TaoyuanDispatchDocumentLink)
            .options(selectinload(TaoyuanDispatchDocumentLink.document))
            .where(TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id)
        )
        links = links_result.scalars().all()

        incoming_ids: list[int] = []
        outgoing_ids: list[int] = []
        doc_info: dict[int, dict] = {}
        for link in links:
            doc = link.document
            info = {"doc_id": link.document_id, "link_type": link.link_type, "doc_number": doc.doc_number if doc else None, "subject": doc.subject if doc else None, "doc_date": str(doc.doc_date) if doc and doc.doc_date else None}
            doc_info[link.document_id] = info
            if link.link_type == "company_outgoing":
                outgoing_ids.append(link.document_id)
            else:
                incoming_ids.append(link.document_id)

        all_doc_ids = incoming_ids + outgoing_ids
        if not all_doc_ids:
            return {"success": True, "suggestions": [], "dispatch_entities": [{"id": eid, "name": name, "type": etype} for eid, (name, etype) in dispatch_entity_names.items()]}

        # 3. 查詢關聯公文的實體提及（只看派工單有的實體）
        mentions_result = await db.execute(
            select(DocumentEntityMention).where(DocumentEntityMention.document_id.in_(all_doc_ids), DocumentEntityMention.canonical_entity_id.in_(dispatch_entity_ids))
        )
        mentions = mentions_result.scalars().all()

        doc_entities: dict[int, set[int]] = defaultdict(set)
        for m in mentions:
            doc_entities[m.document_id].add(m.canonical_entity_id)

        # 4. 查詢已確認的配對
        work_records_result = await db.execute(
            select(TaoyuanWorkRecord).where(TaoyuanWorkRecord.dispatch_order_id == dispatch_id, TaoyuanWorkRecord.parent_record_id.isnot(None))
        )
        confirmed_chains = work_records_result.scalars().all()
        confirmed_pairs: set[tuple[int, int]] = set()
        for wr in confirmed_chains:
            if wr.document_id and wr.parent_record_id:
                parent_result = await db.execute(select(TaoyuanWorkRecord.document_id).where(TaoyuanWorkRecord.id == wr.parent_record_id))
                parent_doc_id = parent_result.scalar()
                if parent_doc_id:
                    confirmed_pairs.add((parent_doc_id, wr.document_id))
                    confirmed_pairs.add((wr.document_id, parent_doc_id))

        # 4.5 圖譜 correspondence 邊加分
        graph_boosted_pairs: set[tuple[int, int]] = set()
        all_entity_ids = set()
        for eid_set in doc_entities.values():
            all_entity_ids.update(eid_set)
        if all_entity_ids:
            corr_rels_result = await db.execute(
                select(EntityRelationship.source_entity_id, EntityRelationship.target_entity_id).where(EntityRelationship.relation_type == "correspondence", EntityRelationship.source_entity_id.in_(all_entity_ids), EntityRelationship.target_entity_id.in_(all_entity_ids))
            )
            for src, tgt in corr_rels_result.all():
                graph_boosted_pairs.add((src, tgt))
                graph_boosted_pairs.add((tgt, src))

        # 5. 建立配對建議
        suggestions = []
        for in_id in incoming_ids:
            in_ents = doc_entities.get(in_id, set())
            for out_id in outgoing_ids:
                out_ents = doc_entities.get(out_id, set())
                shared = in_ents & out_ents

                if (in_id, out_id) in confirmed_pairs:
                    confidence, score = "confirmed", 1.0
                elif shared:
                    location_count = sum(1 for eid in shared if dispatch_entity_names.get(eid, ('', ''))[1] == 'location')
                    base_score = len(shared) / max(len(in_ents | out_ents), 1)
                    score = min(base_score + location_count * 0.1, 1.0)
                    has_graph_link = any((a, b) in graph_boosted_pairs for a in in_ents for b in out_ents)
                    if has_graph_link:
                        score = min(score + 0.15, 1.0)
                    confidence = "high" if score >= 0.3 else "medium"
                else:
                    score, confidence = 0.0, "low"

                if confidence == "low" and not shared:
                    continue

                suggestions.append({
                    "incoming_doc_id": in_id, "outgoing_doc_id": out_id,
                    "confidence": confidence, "score": round(score, 3),
                    "shared_entity_count": len(shared),
                    "shared_entities": [dispatch_entity_names.get(eid, (f"entity#{eid}", ''))[0] for eid in list(shared)[:10]],
                    "incoming_doc": doc_info.get(in_id), "outgoing_doc": doc_info.get(out_id),
                })

        suggestions.sort(key=lambda s: s["score"], reverse=True)

        return {
            "success": True,
            "suggestions": suggestions,
            "dispatch_entities": [{"id": eid, "name": name, "type": etype} for eid, (name, etype) in dispatch_entity_names.items()],
            "stats": {"incoming_count": len(incoming_ids), "outgoing_count": len(outgoing_ids), "total_suggestions": len(suggestions), "confirmed": sum(1 for s in suggestions if s["confidence"] == "confirmed"), "high": sum(1 for s in suggestions if s["confidence"] == "high"), "medium": sum(1 for s in suggestions if s["confidence"] == "medium")},
        }

    except Exception as e:
        logger.error("公文對照建議計算失敗: %s", e)
        return {"success": False, "suggestions": [], "dispatch_entities": []}

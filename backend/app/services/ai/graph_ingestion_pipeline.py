"""
知識圖譜入圖管線

將公文的 NER 提取結果（Phase 1 的 DocumentEntity/EntityRelation）
正規化並寫入 Phase 2 的 CanonicalEntity/EntityRelationship 架構。

流程: 提取 → 正規化解析 → 關係連結 → 事件紀錄

Version: 1.1.0
Created: 2026-02-24
"""

import logging
import time
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    OfficialDocument,
    DocumentEntity,
    EntityRelation,
    EntityRelationship,
    GraphIngestionEvent,
)
from .ai_config import get_ai_config
from .canonical_entity_service import CanonicalEntityService

logger = logging.getLogger(__name__)


class GraphIngestionPipeline:
    """知識圖譜入圖管線"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._entity_service = CanonicalEntityService(db)
        self._min_confidence = get_ai_config().ner_min_confidence

    async def ingest_document(
        self,
        document_id: int,
        force: bool = False,
    ) -> dict:
        """
        將單篇公文的提取實體/關係正規化入圖。

        Args:
            document_id: 公文 ID
            force: 是否強制重新入圖

        Returns:
            入圖統計 dict
        """
        start_time = time.monotonic()

        # 檢查是否已入圖
        if not force:
            existing = await self.db.scalar(
                select(sa_func.count())
                .select_from(GraphIngestionEvent)
                .where(GraphIngestionEvent.document_id == document_id)
                .where(GraphIngestionEvent.status == "completed")
            )
            if existing and existing > 0:
                return {
                    "status": "skipped",
                    "reason": "already_ingested",
                    "document_id": document_id,
                }

        # 查詢 Phase 1 提取的實體
        entity_result = await self.db.execute(
            select(DocumentEntity)
            .where(DocumentEntity.document_id == document_id)
            .where(DocumentEntity.confidence >= self._min_confidence)
        )
        raw_entities = entity_result.scalars().all()

        if not raw_entities:
            # 記錄跳過事件
            event = GraphIngestionEvent(
                document_id=document_id,
                event_type="extract" if not force else "re-extract",
                status="skipped",
                error_message="no_entities_found",
                processing_ms=int((time.monotonic() - start_time) * 1000),
            )
            self.db.add(event)
            await self.db.flush()
            return {
                "status": "skipped",
                "reason": "no_entities",
                "document_id": document_id,
            }

        # ── 批次正規化解析所有實體（v1.1.0: 取代 per-entity loop）──
        seen_keys: set[str] = set()
        entity_inputs: list[tuple[str, str]] = []
        for ent in raw_entities:
            key = f"{ent.entity_type}:{ent.entity_name}"
            if key not in seen_keys:
                seen_keys.add(key)
                entity_inputs.append((ent.entity_name, ent.entity_type))

        canonical_map = await self._entity_service.resolve_entities_batch(
            entity_inputs,
        )

        # 統計新建 vs 合併（mention_count == 0 表示剛建立）
        entities_new = 0
        entities_merged = 0
        for canonical in canonical_map.values():
            if (canonical.mention_count or 0) == 0:
                entities_new += 1
            else:
                entities_merged += 1

        # 記錄提及（每個 unique entity 僅一筆，與原邏輯一致）
        for ent_name, ent_type in entity_inputs:
            key = f"{ent_type}:{ent_name}"
            canonical = canonical_map.get(key)
            if not canonical:
                continue
            # 取第一筆原始實體的 confidence/context
            raw_ent = next(
                (e for e in raw_entities
                 if e.entity_name == ent_name and e.entity_type == ent_type),
                None,
            )
            if raw_ent:
                await self._entity_service.add_mention(
                    document_id=document_id,
                    canonical_entity=canonical,
                    mention_text=ent_name,
                    confidence=raw_ent.confidence,
                    context=raw_ent.context,
                )

        # ── 正規化關係（v1.1.0: 預載 + 批次查詢）──────────────
        relation_result = await self.db.execute(
            select(EntityRelation)
            .where(EntityRelation.document_id == document_id)
            .where(EntityRelation.confidence >= self._min_confidence)
        )
        raw_relations = relation_result.scalars().all()

        # Pre-load existing relationships（1 次查詢取代 N 次）
        canonical_ids = {c.id for c in canonical_map.values()}
        rel_lookup: dict[tuple[int, int, str], EntityRelationship] = {}
        if canonical_ids:
            existing_rels_result = await self.db.execute(
                select(EntityRelationship)
                .where(EntityRelationship.source_entity_id.in_(canonical_ids))
                .where(EntityRelationship.target_entity_id.in_(canonical_ids))
                .where(EntityRelationship.invalidated_at.is_(None))
            )
            for rel_obj in existing_rels_result.scalars().all():
                rel_lookup[
                    (rel_obj.source_entity_id, rel_obj.target_entity_id, rel_obj.relation_type)
                ] = rel_obj

        # Pre-compute valid_from（1 次查詢取代 per-relation 查詢）
        doc = await self.db.get(OfficialDocument, document_id)
        valid_from = None
        if doc and doc.doc_date:
            if isinstance(doc.doc_date, str):
                try:
                    valid_from = datetime.strptime(doc.doc_date, "%Y-%m-%d")
                except ValueError:
                    pass
            else:
                valid_from = (
                    datetime.combine(doc.doc_date, datetime.min.time())
                    if doc.doc_date else None
                )

        relations_found = 0
        for rel in raw_relations:
            src_key = f"{rel.source_entity_type}:{rel.source_entity_name}"
            tgt_key = f"{rel.target_entity_type}:{rel.target_entity_name}"
            src_canonical = canonical_map.get(src_key)
            tgt_canonical = canonical_map.get(tgt_key)

            if not src_canonical or not tgt_canonical:
                continue

            lookup_key = (src_canonical.id, tgt_canonical.id, rel.relation_type)
            existing = rel_lookup.get(lookup_key)

            if existing:
                # 已存在：增加權重和佐證公文數
                existing.weight = (existing.weight or 1.0) + 1.0
                existing.document_count = (existing.document_count or 1) + 1
            else:
                new_rel = EntityRelationship(
                    source_entity_id=src_canonical.id,
                    target_entity_id=tgt_canonical.id,
                    relation_type=rel.relation_type,
                    relation_label=rel.relation_label,
                    weight=1.0,
                    valid_from=valid_from,
                    first_document_id=document_id,
                    document_count=1,
                )
                self.db.add(new_rel)
                # 加入 lookup 處理同批次重複關係
                rel_lookup[lookup_key] = new_rel

            relations_found += 1

        # 記錄入圖事件
        processing_ms = int((time.monotonic() - start_time) * 1000)
        event = GraphIngestionEvent(
            document_id=document_id,
            event_type="extract" if not force else "re-extract",
            entities_found=len(raw_entities),
            entities_new=entities_new,
            entities_merged=entities_merged,
            relations_found=relations_found,
            processing_ms=processing_ms,
            status="completed",
        )
        self.db.add(event)
        await self.db.flush()

        logger.info(
            f"入圖完成: doc#{document_id} → "
            f"{len(raw_entities)} 實體 ({entities_new} 新建, {entities_merged} 合併), "
            f"{relations_found} 關係, {processing_ms}ms"
        )

        return {
            "status": "completed",
            "document_id": document_id,
            "entities_found": len(raw_entities),
            "entities_new": entities_new,
            "entities_merged": entities_merged,
            "relations_found": relations_found,
            "processing_ms": processing_ms,
        }

    async def batch_ingest(
        self,
        limit: int = 50,
        force: bool = False,
    ) -> dict:
        """
        批次入圖：將已提取但未入圖的公文正規化。

        Args:
            limit: 最大處理筆數
            force: 是否強制重新入圖

        Returns:
            批次處理統計
        """
        # 查詢已有提取實體但未入圖的公文
        if force:
            doc_query = (
                select(DocumentEntity.document_id)
                .distinct()
                .limit(limit)
            )
        else:
            ingested_subq = (
                select(GraphIngestionEvent.document_id)
                .where(GraphIngestionEvent.status == "completed")
                .distinct()
            )
            doc_query = (
                select(DocumentEntity.document_id)
                .where(DocumentEntity.document_id.notin_(ingested_subq))
                .distinct()
                .limit(limit)
            )

        result = await self.db.execute(doc_query)
        doc_ids = [row[0] for row in result.all()]

        if not doc_ids:
            return {
                "status": "completed",
                "total_processed": 0,
                "success_count": 0,
                "skip_count": 0,
                "error_count": 0,
                "message": "無待入圖公文",
            }

        success_count = 0
        skip_count = 0
        error_count = 0

        for i, doc_id in enumerate(doc_ids):
            try:
                async with self.db.begin_nested():
                    result = await self.ingest_document(doc_id, force=force)
                    if result["status"] == "completed":
                        success_count += 1
                    else:
                        skip_count += 1
            except Exception as e:
                logger.error(f"入圖失敗 doc#{doc_id}: {e}")
                error_count += 1

            # 每 10 筆 commit（savepoint 自動釋放，不影響 session）
            if (i + 1) % 10 == 0:
                try:
                    await self.db.commit()
                except Exception as e:
                    logger.error(f"批次 commit 失敗: {e}")

        # 最後 commit
        try:
            await self.db.commit()
        except Exception as e:
            logger.error(f"最終 commit 失敗: {e}")

        return {
            "status": "completed",
            "total_processed": len(doc_ids),
            "success_count": success_count,
            "skip_count": skip_count,
            "error_count": error_count,
            "message": f"入圖完成: {success_count} 成功, {skip_count} 跳過, {error_count} 錯誤",
        }

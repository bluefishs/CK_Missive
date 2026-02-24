"""
知識圖譜入圖管線

將公文的 NER 提取結果（Phase 1 的 DocumentEntity/EntityRelation）
正規化並寫入 Phase 2 的 CanonicalEntity/EntityRelationship 架構。

流程: 提取 → 正規化解析 → 關係連結 → 事件紀錄

Version: 1.0.0
Created: 2026-02-24
"""

import logging
import time
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
from .canonical_entity_service import CanonicalEntityService

logger = logging.getLogger(__name__)


class GraphIngestionPipeline:
    """知識圖譜入圖管線"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._entity_service = CanonicalEntityService(db)

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
            .where(DocumentEntity.confidence >= 0.6)
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

        # 正規化解析每個實體
        entities_new = 0
        entities_merged = 0
        canonical_map = {}  # entity_key → CanonicalEntity

        for ent in raw_entities:
            entity_key = f"{ent.entity_type}:{ent.entity_name}"
            if entity_key in canonical_map:
                continue

            canonical = await self._entity_service.resolve_entity(
                entity_name=ent.entity_name,
                entity_type=ent.entity_type,
            )
            canonical_map[entity_key] = canonical

            # 判斷是新建還是合併
            if canonical.mention_count <= 1:
                entities_new += 1
            else:
                entities_merged += 1

            # 記錄提及
            await self._entity_service.add_mention(
                document_id=document_id,
                canonical_entity=canonical,
                mention_text=ent.entity_name,
                confidence=ent.confidence,
                context=ent.context,
            )

        # 正規化關係
        relation_result = await self.db.execute(
            select(EntityRelation)
            .where(EntityRelation.document_id == document_id)
            .where(EntityRelation.confidence >= 0.6)
        )
        raw_relations = relation_result.scalars().all()

        relations_found = 0
        for rel in raw_relations:
            src_key = f"{rel.source_entity_type}:{rel.source_entity_name}"
            tgt_key = f"{rel.target_entity_type}:{rel.target_entity_name}"
            src_canonical = canonical_map.get(src_key)
            tgt_canonical = canonical_map.get(tgt_key)

            if not src_canonical or not tgt_canonical:
                continue

            # 查找已存在的同類型關係
            existing_rel = await self.db.execute(
                select(EntityRelationship)
                .where(EntityRelationship.source_entity_id == src_canonical.id)
                .where(EntityRelationship.target_entity_id == tgt_canonical.id)
                .where(EntityRelationship.relation_type == rel.relation_type)
                .where(EntityRelationship.invalidated_at.is_(None))
                .limit(1)
            )
            existing = existing_rel.scalar_one_or_none()

            if existing:
                # 已存在：增加權重和佐證公文數
                existing.weight = (existing.weight or 1.0) + 1.0
                existing.document_count = (existing.document_count or 1) + 1
            else:
                # 新建關係
                # 嘗試從公文取得日期作為 valid_from
                doc = await self.db.get(OfficialDocument, document_id)
                valid_from = None
                if doc and doc.doc_date:
                    from datetime import datetime
                    if isinstance(doc.doc_date, str):
                        try:
                            valid_from = datetime.strptime(doc.doc_date, "%Y-%m-%d")
                        except ValueError:
                            pass
                    else:
                        valid_from = datetime.combine(doc.doc_date, datetime.min.time()) if doc.doc_date else None

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

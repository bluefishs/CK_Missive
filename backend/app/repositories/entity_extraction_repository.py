"""
EntityExtractionRepository - NER 實體提取資料存取層

將 entity_extraction_service.py 中的 raw db.execute 查詢
集中到 Repository 層，符合 Service → Repository 架構規範。

版本: 1.0.0
建立日期: 2026-04-05
"""

import logging
from typing import Dict, Set

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import DocumentEntity, EntityRelation, OfficialDocument

logger = logging.getLogger(__name__)


class EntityExtractionRepository:
    """NER 實體提取相關的資料存取"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 查詢方法
    # ------------------------------------------------------------------

    async def get_extracted_document_ids(self) -> Set[int]:
        """取得所有已提取實體的公文 ID 集合"""
        result = await self.db.execute(
            select(func.distinct(DocumentEntity.document_id))
        )
        return {row[0] for row in result.all()}

    async def count_document_entities(self, doc_id: int) -> int:
        """計算指定公文的實體數量"""
        result = await self.db.execute(
            select(func.count(DocumentEntity.id))
            .where(DocumentEntity.document_id == doc_id)
        )
        return result.scalar() or 0

    async def get_document_by_id(self, doc_id: int) -> OfficialDocument | None:
        """取得指定公文"""
        result = await self.db.execute(
            select(OfficialDocument).where(OfficialDocument.id == doc_id)
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # 刪除方法
    # ------------------------------------------------------------------

    async def delete_document_entities(self, doc_id: int) -> None:
        """刪除指定公文的所有實體"""
        await self.db.execute(
            delete(DocumentEntity).where(DocumentEntity.document_id == doc_id)
        )

    async def delete_document_relations(self, doc_id: int) -> None:
        """刪除指定公文的所有實體關係"""
        await self.db.execute(
            delete(EntityRelation).where(EntityRelation.document_id == doc_id)
        )

    # ------------------------------------------------------------------
    # 統計方法
    # ------------------------------------------------------------------

    async def count_all_documents(self) -> int:
        """計算總公文數"""
        result = await self.db.execute(
            select(func.count(OfficialDocument.id))
        )
        return result.scalar() or 0

    async def count_documents_without_extraction(self) -> int:
        """計算尚未提取實體的公文數"""
        extracted_subq = (
            select(func.distinct(DocumentEntity.document_id))
            .scalar_subquery()
        )
        result = await self.db.execute(
            select(func.count(OfficialDocument.id))
            .where(OfficialDocument.id.notin_(extracted_subq))
        )
        return result.scalar() or 0

    async def count_documents_with_entities(self) -> int:
        """計算已提取實體的公文數 (distinct document_id)"""
        result = await self.db.execute(
            select(func.count(func.distinct(DocumentEntity.document_id)))
        )
        return result.scalar() or 0

    async def count_total_entities(self) -> int:
        """計算總實體數"""
        result = await self.db.execute(
            select(func.count(DocumentEntity.id))
        )
        return result.scalar() or 0

    async def count_total_relations(self) -> int:
        """計算總關係數"""
        result = await self.db.execute(
            select(func.count(EntityRelation.id))
        )
        return result.scalar() or 0

    async def get_entity_count_by_type(self) -> Dict[str, int]:
        """取得各類型實體的數量"""
        result = await self.db.execute(
            select(DocumentEntity.entity_type, func.count(DocumentEntity.id))
            .group_by(DocumentEntity.entity_type)
        )
        return {row[0]: row[1] for row in result.all()}

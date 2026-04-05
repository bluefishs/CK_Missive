"""
RelationGraphRepository - 關聯圖譜資料存取層

將 relation_graph_service.py 中的 raw db.execute 查詢
集中到 Repository 層，符合 Service -> Repository 架構規範。

版本: 1.0.0
建立日期: 2026-04-05
"""

import logging
from typing import List, Optional, Set

from sqlalchemy import or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    ContractProject,
    DocumentEntity,
    EntityRelation,
    OfficialDocument,
    TaoyuanDispatchDocumentLink,
    TaoyuanDispatchOrder,
    TaoyuanDispatchProjectLink,
    TaoyuanProject,
)

logger = logging.getLogger(__name__)


class RelationGraphRepository:
    """關聯圖譜相關的資料存取"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Phase 0: 預設公文 ID 載入
    # ------------------------------------------------------------------

    async def get_ner_document_ids(self, limit: int = 2000) -> Set[int]:
        """取得有 NER 實體提取的公文 ID"""
        result = await self.db.execute(
            select(DocumentEntity.document_id).distinct().limit(limit)
        )
        return {row[0] for row in result.all()}

    async def get_dispatch_linked_document_ids(self, limit: int = 2000) -> Set[int]:
        """取得有派工關聯的公文 ID"""
        result = await self.db.execute(
            select(TaoyuanDispatchDocumentLink.document_id).distinct().limit(limit)
        )
        return {row[0] for row in result.all()}

    async def get_dispatch_fk_document_ids(self, limit: int = 4000) -> Set[int]:
        """取得派工單 FK 關聯的公文 ID (agency_doc_id / company_doc_id)"""
        fk_union = union_all(
            select(TaoyuanDispatchOrder.agency_doc_id.label('doc_id'))
            .where(TaoyuanDispatchOrder.agency_doc_id.isnot(None)),
            select(TaoyuanDispatchOrder.company_doc_id.label('doc_id'))
            .where(TaoyuanDispatchOrder.company_doc_id.isnot(None)),
        ).subquery()
        result = await self.db.execute(
            select(fk_union.c.doc_id).distinct().limit(limit)
        )
        return {row[0] for row in result.all()}

    # ------------------------------------------------------------------
    # Phase 1: 公文與專案
    # ------------------------------------------------------------------

    async def fetch_documents(self, doc_ids: List[int]) -> List[OfficialDocument]:
        """根據 ID 列表取得公文"""
        result = await self.db.execute(
            select(OfficialDocument).where(OfficialDocument.id.in_(doc_ids))
        )
        return list(result.scalars().all())

    async def fetch_projects(self, project_ids: Set[int]) -> List[ContractProject]:
        """根據 ID 集合取得承攬案件"""
        result = await self.db.execute(
            select(ContractProject).where(ContractProject.id.in_(list(project_ids)))
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Phase 3: 同專案其他公文
    # ------------------------------------------------------------------

    async def fetch_related_documents(
        self,
        project_ids: Set[int],
        exclude_doc_ids: List[int],
        limit: int = 20,
    ) -> List[OfficialDocument]:
        """取得同專案但不在 exclude_doc_ids 中的公文"""
        result = await self.db.execute(
            select(OfficialDocument)
            .where(OfficialDocument.contract_project_id.in_(list(project_ids)))
            .where(OfficialDocument.id.notin_(exclude_doc_ids))
            .order_by(OfficialDocument.doc_date.desc().nullslast())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Phase 5: NER 實體 & 關係
    # ------------------------------------------------------------------

    async def fetch_entities_for_docs(
        self, doc_ids: List[int], min_confidence: float
    ) -> List[DocumentEntity]:
        """取得指定公文的 NER 實體 (filtered by confidence)"""
        result = await self.db.execute(
            select(DocumentEntity)
            .where(DocumentEntity.document_id.in_(doc_ids))
            .where(DocumentEntity.confidence >= min_confidence)
        )
        return list(result.scalars().all())

    async def fetch_relations_for_docs(
        self, doc_ids: List[int], min_confidence: float
    ) -> List[EntityRelation]:
        """取得指定公文的 NER 關係 (filtered by confidence)"""
        result = await self.db.execute(
            select(EntityRelation)
            .where(EntityRelation.document_id.in_(doc_ids))
            .where(EntityRelation.confidence >= min_confidence)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Phase 6: 派工單
    # ------------------------------------------------------------------

    async def fetch_dispatch_doc_links(
        self, doc_ids: List[int]
    ) -> List[TaoyuanDispatchDocumentLink]:
        """取得公文的派工關聯記錄"""
        result = await self.db.execute(
            select(TaoyuanDispatchDocumentLink)
            .where(TaoyuanDispatchDocumentLink.document_id.in_(doc_ids))
        )
        return list(result.scalars().all())

    async def fetch_dispatch_orders_by_docs(
        self, doc_ids: List[int]
    ) -> List[TaoyuanDispatchOrder]:
        """取得與指定公文相關的派工單 (link + FK 路徑合併)"""
        link_subquery = (
            select(TaoyuanDispatchDocumentLink.dispatch_order_id)
            .where(TaoyuanDispatchDocumentLink.document_id.in_(doc_ids))
        ).subquery()
        result = await self.db.execute(
            select(TaoyuanDispatchOrder)
            .where(or_(
                TaoyuanDispatchOrder.id.in_(select(link_subquery)),
                TaoyuanDispatchOrder.agency_doc_id.in_(doc_ids),
                TaoyuanDispatchOrder.company_doc_id.in_(doc_ids),
            ))
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Phase 7: 桃園工程
    # ------------------------------------------------------------------

    async def fetch_dispatch_project_links(
        self, dispatch_ids: Set[int]
    ) -> List[TaoyuanDispatchProjectLink]:
        """取得派工單對應的桃園工程關聯"""
        result = await self.db.execute(
            select(TaoyuanDispatchProjectLink)
            .where(TaoyuanDispatchProjectLink.dispatch_order_id.in_(list(dispatch_ids)))
        )
        return list(result.scalars().all())

    async def fetch_taoyuan_projects(
        self, project_ids: Set[int]
    ) -> List[TaoyuanProject]:
        """取得桃園工程專案"""
        result = await self.db.execute(
            select(TaoyuanProject)
            .where(TaoyuanProject.id.in_(list(project_ids)))
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # 語意相似 (pgvector)
    # ------------------------------------------------------------------

    async def get_document_embedding(
        self, doc_id: int
    ) -> Optional[tuple]:
        """取得公文的 embedding 向量，回傳 (id, embedding) 或 None"""
        result = await self.db.execute(
            select(
                OfficialDocument.id,
                OfficialDocument.embedding,
            ).where(OfficialDocument.id == doc_id)
        )
        return result.first()

    async def find_similar_documents(
        self, doc_id: int, source_embedding: list, limit: int = 10
    ) -> list:
        """使用 cosine_distance 查詢相似公文"""
        distance_expr = OfficialDocument.embedding.cosine_distance(source_embedding)
        similarity_expr = (1 - distance_expr).label("similarity")

        result = await self.db.execute(
            select(
                OfficialDocument.id,
                OfficialDocument.doc_number,
                OfficialDocument.subject,
                OfficialDocument.category,
                OfficialDocument.sender,
                OfficialDocument.doc_date,
                similarity_expr,
            )
            .where(OfficialDocument.id != doc_id)
            .where(OfficialDocument.embedding.isnot(None))
            .order_by(distance_expr)
            .limit(limit)
        )
        return list(result.all())

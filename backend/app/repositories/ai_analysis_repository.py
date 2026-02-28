"""
AIAnalysisRepository - AI 分析結果資料存取

繼承 BaseRepository，提供 DocumentAIAnalysis 特定查詢方法。

版本: 1.0.0
建立日期: 2026-02-28
"""

import logging
from typing import Dict, List, Optional, Any

from sqlalchemy import select, update, func, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base_repository import BaseRepository
from app.extended.models import DocumentAIAnalysis

logger = logging.getLogger(__name__)


class AIAnalysisRepository(BaseRepository[DocumentAIAnalysis]):
    """AI 分析結果 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, DocumentAIAnalysis)

    async def get_by_document_id(self, document_id: int) -> Optional[DocumentAIAnalysis]:
        """取得單一公文的分析結果"""
        result = await self.db.execute(
            select(DocumentAIAnalysis)
            .where(DocumentAIAnalysis.document_id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_by_document_ids(
        self, document_ids: List[int]
    ) -> Dict[int, DocumentAIAnalysis]:
        """批次取得多筆公文的分析結果（列表頁用）"""
        if not document_ids:
            return {}
        result = await self.db.execute(
            select(DocumentAIAnalysis)
            .where(DocumentAIAnalysis.document_id.in_(document_ids))
        )
        rows = result.scalars().all()
        return {row.document_id: row for row in rows}

    async def upsert(self, document_id: int, **kwargs) -> DocumentAIAnalysis:
        """建立或更新分析結果（ON CONFLICT UPDATE）"""
        stmt = pg_insert(DocumentAIAnalysis).values(
            document_id=document_id, **kwargs
        )
        update_cols = {k: v for k, v in kwargs.items()}
        update_cols["updated_at"] = func.now()
        stmt = stmt.on_conflict_do_update(
            index_elements=["document_id"],
            set_=update_cols,
        )
        await self.db.execute(stmt)
        await self.db.flush()

        return await self.get_by_document_id(document_id)

    async def mark_stale(self, document_id: int) -> None:
        """標記單一公文分析為過期"""
        await self.db.execute(
            update(DocumentAIAnalysis)
            .where(DocumentAIAnalysis.document_id == document_id)
            .values(is_stale=True)
        )
        await self.db.flush()

    async def mark_stale_batch(self, document_ids: List[int]) -> int:
        """批次標記分析為過期"""
        if not document_ids:
            return 0
        result = await self.db.execute(
            update(DocumentAIAnalysis)
            .where(DocumentAIAnalysis.document_id.in_(document_ids))
            .values(is_stale=True)
        )
        await self.db.flush()
        return result.rowcount

    async def get_pending_documents(self, limit: int = 50) -> List[int]:
        """取得無分析或已過期的公文 ID（批次分析用）"""
        from app.extended.models import OfficialDocument

        subquery = (
            select(DocumentAIAnalysis.document_id)
            .where(
                and_(
                    DocumentAIAnalysis.is_stale == False,  # noqa: E712
                    DocumentAIAnalysis.status == "completed",
                )
            )
        )
        result = await self.db.execute(
            select(OfficialDocument.id)
            .where(OfficialDocument.id.notin_(subquery))
            .order_by(OfficialDocument.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_stats(self) -> Dict[str, Any]:
        """分析覆蓋率統計"""
        from app.extended.models import OfficialDocument

        total_docs = await self.db.execute(
            select(func.count(OfficialDocument.id))
        )
        total = total_docs.scalar() or 0

        analysis_stats = await self.db.execute(
            select(
                func.count(DocumentAIAnalysis.id).label("analyzed"),
                func.count(
                    func.nullif(DocumentAIAnalysis.is_stale, False)
                ).label("stale"),
                func.avg(DocumentAIAnalysis.processing_ms).label("avg_ms"),
            )
        )
        row = analysis_stats.one()
        analyzed = row.analyzed or 0
        stale = row.stale or 0

        return {
            "total_documents": total,
            "analyzed_documents": analyzed,
            "stale_documents": stale,
            "without_analysis": total - analyzed,
            "coverage_percent": round(analyzed / total * 100, 1) if total > 0 else 0.0,
            "avg_processing_ms": round(row.avg_ms or 0, 1),
        }

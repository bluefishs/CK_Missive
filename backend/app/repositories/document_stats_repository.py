"""
DocumentStatsRepository - 公文統計資料存取層

從 DocumentRepository 提取，專注於統計查詢操作。

版本: 1.0.0
建立日期: 2026-03-10
提取自: document_repository.py
"""

from typing import Dict, Any
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, extract

from app.repositories.base_repository import BaseRepository
from app.extended.models import OfficialDocument


class DocumentStatsRepository(BaseRepository[OfficialDocument]):
    """公文統計專用 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, OfficialDocument)

    async def get_statistics(self) -> Dict[str, Any]:
        """
        取得公文統計資料

        Returns:
            統計資料字典，包含：
            - total: 總數
            - by_type: 依類型統計
            - by_status: 依狀態統計
            - by_month: 依月份統計（當年度）
        """
        total = await self.count()
        type_stats = await self._get_grouped_count('doc_type')
        status_stats = await self._get_grouped_count('status')
        current_year = date.today().year
        month_stats = await self._get_monthly_count(current_year)

        return {
            "total": total,
            "by_type": type_stats,
            "by_status": status_stats,
            "by_month": month_stats,
            "year": current_year,
        }

    async def get_type_statistics(self) -> Dict[str, int]:
        """取得依類型統計"""
        return await self._get_grouped_count('doc_type')

    async def get_status_statistics(self) -> Dict[str, int]:
        """取得依狀態統計"""
        return await self._get_grouped_count('status')

    async def get_yearly_statistics(self, year: int) -> Dict[str, Any]:
        """取得年度統計"""
        query = select(func.count(OfficialDocument.id)).where(
            or_(
                extract('year', OfficialDocument.doc_date) == year,
                extract('year', OfficialDocument.receive_date) == year
            )
        )
        total = (await self.db.execute(query)).scalar() or 0
        month_stats = await self._get_monthly_count(year)
        type_stats = await self._get_grouped_count_with_year('doc_type', year)

        return {
            "year": year,
            "total": total,
            "by_month": month_stats,
            "by_type": type_stats,
        }

    async def get_pending_count(self) -> int:
        """取得待處理公文數量"""
        return await self.count_by(status='待處理')

    async def get_unlinked_count(self) -> int:
        """取得未關聯專案的公文數量"""
        query = select(func.count(OfficialDocument.id)).where(
            OfficialDocument.contract_project_id.is_(None)
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _get_grouped_count(self, field_name: str) -> Dict[str, int]:
        """取得依欄位分組的計數"""
        field = getattr(OfficialDocument, field_name)
        query = (
            select(field, func.count(OfficialDocument.id))
            .group_by(field)
        )
        result = await self.db.execute(query)

        stats = {}
        for value, count in result.fetchall():
            key = value if value else '(未設定)'
            stats[key] = count
        return stats

    async def _get_grouped_count_with_year(
        self,
        field_name: str,
        year: int
    ) -> Dict[str, int]:
        """取得指定年度依欄位分組的計數"""
        field = getattr(OfficialDocument, field_name)
        query = (
            select(field, func.count(OfficialDocument.id))
            .where(
                or_(
                    extract('year', OfficialDocument.doc_date) == year,
                    extract('year', OfficialDocument.receive_date) == year
                )
            )
            .group_by(field)
        )
        result = await self.db.execute(query)

        stats = {}
        for value, count in result.fetchall():
            key = value if value else '(未設定)'
            stats[key] = count
        return stats

    async def _get_monthly_count(self, year: int) -> Dict[int, int]:
        """取得指定年度的月份統計"""
        query = (
            select(
                extract('month', OfficialDocument.doc_date).label('month'),
                func.count(OfficialDocument.id)
            )
            .where(extract('year', OfficialDocument.doc_date) == year)
            .group_by(extract('month', OfficialDocument.doc_date))
        )
        result = await self.db.execute(query)

        stats = {i: 0 for i in range(1, 13)}
        for month, count in result.fetchall():
            if month:
                stats[int(month)] = count
        return stats

"""PM 里程碑 Repository"""
import logging
from typing import Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.pm import PMMilestone
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class PMMilestoneRepository(BaseRepository[PMMilestone]):
    """里程碑資料存取"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, PMMilestone)

    async def get_by_case_id(self, pm_case_id: int) -> List[PMMilestone]:
        """取得案件所有里程碑 (依排序)"""
        query = (
            select(PMMilestone)
            .where(PMMilestone.pm_case_id == pm_case_id)
            .order_by(PMMilestone.sort_order.asc(), PMMilestone.id.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_counts_batch(self, case_ids: List[int]) -> Dict[int, int]:
        """批次取得多筆案件的里程碑數量 (消除 N+1)"""
        if not case_ids:
            return {}
        query = (
            select(
                PMMilestone.pm_case_id,
                func.count(PMMilestone.id).label("cnt"),
            )
            .where(PMMilestone.pm_case_id.in_(case_ids))
            .group_by(PMMilestone.pm_case_id)
        )
        result = await self.db.execute(query)
        return {row.pm_case_id: row.cnt for row in result.all()}

    async def get_overdue(self, pm_case_id: int) -> List[PMMilestone]:
        """取得逾期里程碑"""
        from datetime import date
        query = (
            select(PMMilestone)
            .where(
                PMMilestone.pm_case_id == pm_case_id,
                PMMilestone.status.in_(["pending", "in_progress"]),
                PMMilestone.planned_date < date.today(),
            )
            .order_by(PMMilestone.planned_date.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

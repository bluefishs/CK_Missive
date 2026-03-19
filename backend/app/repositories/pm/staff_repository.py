"""PM 案件人員 Repository"""
import logging
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.pm import PMCaseStaff
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class PMCaseStaffRepository(BaseRepository[PMCaseStaff]):
    """案件人員資料存取"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, PMCaseStaff)

    async def get_by_case_id(self, pm_case_id: int) -> List[PMCaseStaff]:
        """取得案件所有人員"""
        query = (
            select(PMCaseStaff)
            .where(PMCaseStaff.pm_case_id == pm_case_id)
            .order_by(PMCaseStaff.is_primary.desc(), PMCaseStaff.id.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_counts_batch(self, case_ids: List[int]) -> Dict[int, int]:
        """批次取得多筆案件的人員數量 (消除 N+1)"""
        if not case_ids:
            return {}
        query = (
            select(
                PMCaseStaff.pm_case_id,
                func.count(PMCaseStaff.id).label("cnt"),
            )
            .where(PMCaseStaff.pm_case_id.in_(case_ids))
            .group_by(PMCaseStaff.pm_case_id)
        )
        result = await self.db.execute(query)
        return {row.pm_case_id: row.cnt for row in result.all()}

    async def get_primary_staff(self, pm_case_id: int) -> Optional[PMCaseStaff]:
        """取得案件主要負責人"""
        query = (
            select(PMCaseStaff)
            .where(
                PMCaseStaff.pm_case_id == pm_case_id,
                PMCaseStaff.is_primary.is_(True),
            )
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

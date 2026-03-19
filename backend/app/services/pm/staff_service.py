"""PM 案件人員服務

Version: 1.0.0
"""
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.pm import PMCaseStaff
from app.repositories.pm import PMCaseStaffRepository
from app.schemas.pm import PMCaseStaffCreate, PMCaseStaffUpdate, PMCaseStaffResponse

logger = logging.getLogger(__name__)


class PMCaseStaffService:
    """案件人員管理服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PMCaseStaffRepository(db)

    async def create(self, data: PMCaseStaffCreate) -> PMCaseStaffResponse:
        """建立案件人員"""
        staff = PMCaseStaff(**data.model_dump())
        self.db.add(staff)
        await self.db.flush()
        await self.db.refresh(staff)
        await self.db.commit()
        return PMCaseStaffResponse.model_validate(staff)

    async def get_by_case(self, pm_case_id: int) -> List[PMCaseStaffResponse]:
        """取得案件所有人員"""
        items = await self.repo.get_by_case_id(pm_case_id)
        return [PMCaseStaffResponse.model_validate(s) for s in items]

    async def update(self, staff_id: int, data: PMCaseStaffUpdate) -> Optional[PMCaseStaffResponse]:
        """更新案件人員"""
        staff = await self.repo.get_by_id(staff_id)
        if not staff:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(staff, key, value)

        await self.db.flush()
        await self.db.refresh(staff)
        await self.db.commit()
        return PMCaseStaffResponse.model_validate(staff)

    async def delete(self, staff_id: int) -> bool:
        """刪除案件人員"""
        staff = await self.repo.get_by_id(staff_id)
        if not staff:
            return False
        await self.db.delete(staff)
        await self.db.commit()
        return True

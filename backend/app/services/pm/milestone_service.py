"""PM 里程碑服務

Version: 1.0.0
"""
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.pm import PMMilestone
from app.repositories.pm import PMMilestoneRepository
from app.schemas.pm import PMMilestoneCreate, PMMilestoneUpdate, PMMilestoneResponse

logger = logging.getLogger(__name__)


class PMMilestoneService:
    """里程碑管理服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PMMilestoneRepository(db)

    async def create(self, data: PMMilestoneCreate) -> PMMilestoneResponse:
        """建立里程碑"""
        milestone = PMMilestone(**data.model_dump())
        self.db.add(milestone)
        await self.db.flush()
        await self.db.refresh(milestone)
        await self.db.commit()
        return PMMilestoneResponse.model_validate(milestone)

    async def get_by_case(self, pm_case_id: int) -> List[PMMilestoneResponse]:
        """取得案件所有里程碑"""
        items = await self.repo.get_by_case_id(pm_case_id)
        return [PMMilestoneResponse.model_validate(m) for m in items]

    async def update(self, milestone_id: int, data: PMMilestoneUpdate) -> Optional[PMMilestoneResponse]:
        """更新里程碑"""
        milestone = await self.repo.get_by_id(milestone_id)
        if not milestone:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(milestone, key, value)

        await self.db.flush()
        await self.db.refresh(milestone)
        await self.db.commit()
        return PMMilestoneResponse.model_validate(milestone)

    async def delete(self, milestone_id: int) -> bool:
        """刪除里程碑"""
        milestone = await self.repo.get_by_id(milestone_id)
        if not milestone:
            return False
        await self.db.delete(milestone)
        await self.db.commit()
        return True

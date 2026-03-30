"""作業性質代碼 Repository"""
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.extended.models.system import CaseNatureCode


class CaseNatureRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, include_inactive: bool = False) -> List[CaseNatureCode]:
        query = select(CaseNatureCode).order_by(CaseNatureCode.sort_order, CaseNatureCode.code)
        if not include_inactive:
            query = query.where(CaseNatureCode.is_active == True)  # noqa: E712
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, id: int) -> Optional[CaseNatureCode]:
        result = await self.db.execute(select(CaseNatureCode).where(CaseNatureCode.id == id))
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[CaseNatureCode]:
        result = await self.db.execute(select(CaseNatureCode).where(CaseNatureCode.code == code))
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> CaseNatureCode:
        item = CaseNatureCode(**data)
        self.db.add(item)
        await self.db.flush()
        return item

    async def update(self, id: int, data: dict) -> Optional[CaseNatureCode]:
        item = await self.get_by_id(id)
        if not item:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(item, key, value)
        await self.db.flush()
        return item

    async def soft_delete(self, id: int) -> bool:
        item = await self.get_by_id(id)
        if not item:
            return False
        item.is_active = False
        await self.db.flush()
        return True

    async def get_next_code(self) -> str:
        result = await self.db.execute(
            select(CaseNatureCode.code).order_by(CaseNatureCode.code.desc()).limit(1)
        )
        last_code = result.scalar()
        if last_code:
            next_num = int(last_code) + 1
            return str(next_num).zfill(2)
        return "01"

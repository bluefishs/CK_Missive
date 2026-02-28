"""
ProjectStaffRepository - 專案人員關聯資料存取

操作 project_user_assignment 關聯表（SQLAlchemy Table，非 ORM Model）。

版本: 1.0.0
建立日期: 2026-02-28
"""

import logging
from typing import Optional

from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import ContractProject, User, project_user_assignment

logger = logging.getLogger(__name__)


class ProjectStaffRepository:
    """專案人員關聯 Repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_project_exists(self, project_id: int) -> Optional[ContractProject]:
        result = await self.db.execute(
            select(ContractProject).where(ContractProject.id == project_id)
        )
        return result.scalar_one_or_none()

    async def check_user_exists(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def check_assignment_exists(self, project_id: int, user_id: int):
        result = await self.db.execute(
            select(project_user_assignment).where(
                (project_user_assignment.c.project_id == project_id) &
                (project_user_assignment.c.user_id == user_id)
            )
        )
        return result.fetchone()

    async def create_assignment(
        self,
        project_id: int,
        user_id: int,
        role: str = 'member',
        is_primary: bool = False,
        start_date=None,
        end_date=None,
        status: str = 'active',
        notes: Optional[str] = None,
    ) -> None:
        stmt = insert(project_user_assignment).values(
            project_id=project_id,
            user_id=user_id,
            role=role,
            is_primary=is_primary,
            start_date=start_date,
            end_date=end_date,
            status=status,
            notes=notes,
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_staff_for_project(self, project_id: int) -> list:
        query = select(
            project_user_assignment.c.id,
            project_user_assignment.c.project_id,
            project_user_assignment.c.user_id,
            project_user_assignment.c.role,
            project_user_assignment.c.is_primary,
            project_user_assignment.c.start_date,
            project_user_assignment.c.end_date,
            project_user_assignment.c.status,
            project_user_assignment.c.notes,
            User.full_name,
            User.email,
            User.username,
        ).select_from(
            project_user_assignment.join(
                User,
                project_user_assignment.c.user_id == User.id,
            )
        ).where(project_user_assignment.c.project_id == project_id)

        result = await self.db.execute(query)
        return result.fetchall()

    async def get_all_assignments(
        self,
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list, int]:
        base = select(
            project_user_assignment.c.id,
            project_user_assignment.c.project_id,
            project_user_assignment.c.user_id,
            project_user_assignment.c.role,
            project_user_assignment.c.is_primary,
            project_user_assignment.c.start_date,
            project_user_assignment.c.end_date,
            project_user_assignment.c.status,
            project_user_assignment.c.notes,
            ContractProject.project_name,
            ContractProject.project_code,
            User.full_name,
            User.email,
            User.username,
        ).select_from(
            project_user_assignment.join(
                ContractProject,
                project_user_assignment.c.project_id == ContractProject.id,
            ).join(
                User,
                project_user_assignment.c.user_id == User.id,
            )
        )

        # 篩選
        conditions = []
        if project_id is not None:
            conditions.append(project_user_assignment.c.project_id == project_id)
        if user_id is not None:
            conditions.append(project_user_assignment.c.user_id == user_id)
        if status is not None:
            conditions.append(project_user_assignment.c.status == status)

        if conditions:
            for cond in conditions:
                base = base.where(cond)

        # 計算總數
        count_query = select(func.count()).select_from(project_user_assignment)
        for cond in conditions:
            count_query = count_query.where(cond)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # 分頁
        offset = (page - 1) * limit
        base = base.offset(offset).limit(limit)

        result = await self.db.execute(base)
        return result.fetchall(), total

    async def update_assignment(
        self, project_id: int, user_id: int, update_data: dict
    ) -> None:
        if not update_data:
            return
        stmt = update(project_user_assignment).where(
            (project_user_assignment.c.project_id == project_id) &
            (project_user_assignment.c.user_id == user_id)
        ).values(**update_data)
        await self.db.execute(stmt)
        await self.db.flush()

    async def delete_assignment(self, project_id: int, user_id: int) -> Optional[int]:
        existing = await self.check_assignment_exists(project_id, user_id)
        if not existing:
            return None
        assignment_id = existing.id if hasattr(existing, 'id') else None

        stmt = delete(project_user_assignment).where(
            (project_user_assignment.c.project_id == project_id) &
            (project_user_assignment.c.user_id == user_id)
        )
        await self.db.execute(stmt)
        await self.db.flush()
        return assignment_id

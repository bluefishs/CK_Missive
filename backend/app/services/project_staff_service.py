"""
ProjectStaffService - 專案人員關聯業務邏輯

處理驗證、衝突偵測、回應格式化，委託 Repository 進行資料存取。

版本: 1.0.0
建立日期: 2026-02-28
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ConflictException
from app.repositories.project_staff_repository import ProjectStaffRepository
from app.schemas.common import DeleteResponse, PaginationMeta
from app.schemas.project_staff import (
    ProjectStaffCreate,
    ProjectStaffUpdate,
    ProjectStaffResponse,
    ProjectStaffListResponse,
    StaffListQuery,
)

logger = logging.getLogger(__name__)


class ProjectStaffService:
    """專案人員關聯 Service"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProjectStaffRepository(db)

    async def create_assignment(self, data: ProjectStaffCreate) -> dict:
        project = await self.repo.check_project_exists(data.project_id)
        if not project:
            raise NotFoundException(resource="承攬案件", resource_id=data.project_id)

        user = await self.repo.check_user_exists(data.user_id)
        if not user:
            raise NotFoundException(resource="使用者", resource_id=data.user_id)

        existing = await self.repo.check_assignment_exists(data.project_id, data.user_id)
        if existing:
            raise ConflictException(message="該同仁已與此案件建立關聯", field="user_id")

        await self.repo.create_assignment(
            project_id=data.project_id,
            user_id=data.user_id,
            role=data.role or 'member',
            is_primary=data.is_primary,
            start_date=data.start_date,
            end_date=data.end_date,
            status=data.status or 'active',
            notes=data.notes,
        )
        await self.db.commit()

        return {
            "message": "案件與承辦同仁關聯建立成功",
            "project_id": data.project_id,
            "user_id": data.user_id,
        }

    async def get_project_staff(self, project_id: int) -> ProjectStaffListResponse:
        project = await self.repo.check_project_exists(project_id)
        if not project:
            raise NotFoundException(resource="承攬案件", resource_id=project_id)

        rows = await self.repo.get_staff_for_project(project_id)

        staff = [
            ProjectStaffResponse(
                id=row.id,
                project_id=row.project_id,
                user_id=row.user_id,
                user_name=row.full_name or row.username,
                user_email=row.email,
                department=None,
                phone=None,
                role=row.role,
                is_primary=row.is_primary or False,
                start_date=row.start_date,
                end_date=row.end_date,
                status=row.status,
                notes=row.notes,
                created_at=None,
                updated_at=None,
            )
            for row in rows
        ]

        return ProjectStaffListResponse(
            project_id=project_id,
            project_name=project.project_name,
            staff=staff,
            total=len(staff),
        )

    async def get_all_assignments(self, query: StaffListQuery) -> dict:
        rows, total = await self.repo.get_all_assignments(
            project_id=query.project_id,
            user_id=query.user_id,
            status=query.status,
            page=query.page,
            limit=query.limit,
        )

        items = [
            {
                "id": row.id,
                "project_id": row.project_id,
                "project_name": row.project_name,
                "project_code": row.project_code,
                "user_id": row.user_id,
                "user_name": row.full_name or row.username,
                "user_email": row.email,
                "role": row.role,
                "is_primary": row.is_primary,
                "start_date": row.start_date,
                "end_date": row.end_date,
                "status": row.status,
                "notes": row.notes,
            }
            for row in rows
        ]

        return {
            "success": True,
            "items": items,
            "pagination": PaginationMeta.create(
                total=total,
                page=query.page,
                limit=query.limit,
            ).model_dump(),
        }

    async def update_assignment(
        self, project_id: int, user_id: int, data: ProjectStaffUpdate
    ) -> dict:
        existing = await self.repo.check_assignment_exists(project_id, user_id)
        if not existing:
            raise NotFoundException(resource="案件與承辦同仁關聯")

        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            await self.repo.update_assignment(project_id, user_id, update_data)
            await self.db.commit()

        return {
            "message": "案件與承辦同仁關聯更新成功",
            "project_id": project_id,
            "user_id": user_id,
        }

    async def delete_assignment(self, project_id: int, user_id: int) -> DeleteResponse:
        existing = await self.repo.check_assignment_exists(project_id, user_id)
        if not existing:
            raise NotFoundException(resource="案件與承辦同仁關聯")

        assignment_id = await self.repo.delete_assignment(project_id, user_id)
        await self.db.commit()

        return DeleteResponse(
            success=True,
            message="案件與承辦同仁關聯已成功刪除",
            deleted_id=assignment_id,
        )

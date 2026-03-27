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
        # 支援 project_id 或 case_code（統一人員表 v2.0）
        if data.project_id:
            project = await self.repo.check_project_exists(data.project_id)
            if not project:
                raise NotFoundException(resource="承攬案件", resource_id=data.project_id)

        if data.user_id:
            user = await self.repo.check_user_exists(data.user_id)
            if not user:
                raise NotFoundException(resource="使用者", resource_id=data.user_id)

            if data.project_id:
                existing = await self.repo.check_assignment_exists(data.project_id, data.user_id)
                if existing:
                    raise ConflictException(message="該同仁已與此案件建立關聯", field="user_id")

        from sqlalchemy import insert
        from app.extended.models.associations import project_user_assignment
        stmt = insert(project_user_assignment).values(
            project_id=data.project_id,
            case_code=data.case_code,
            user_id=data.user_id,
            staff_name=data.staff_name,
            role=data.role or 'member',
            is_primary=data.is_primary,
            start_date=data.start_date,
            end_date=data.end_date,
            status=data.status or 'active',
            notes=data.notes,
        )
        await self.db.execute(stmt)
        await self.db.commit()

        return {
            "message": "承辦同仁關聯建立成功",
            "project_id": data.project_id,
            "case_code": data.case_code,
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

    async def get_staff_by_case_code(self, case_code: str) -> ProjectStaffListResponse:
        """依 case_code 取得承辦同仁（支援未成案 PM 案件）"""
        rows = await self.repo.get_staff_by_case_code(case_code)

        staff = [
            ProjectStaffResponse(
                id=row.id,
                project_id=getattr(row, 'project_id', None),
                case_code=getattr(row, 'case_code', case_code),
                user_id=getattr(row, 'user_id', None),
                staff_name=getattr(row, 'staff_name', None),
                user_name=getattr(row, 'full_name', None) or getattr(row, 'username', None) or getattr(row, 'staff_name', None) or '未知',
                user_email=getattr(row, 'email', None),
                role=row.role,
                is_primary=getattr(row, 'is_primary', False) or False,
                start_date=getattr(row, 'start_date', None),
                end_date=getattr(row, 'end_date', None),
                status=getattr(row, 'status', None),
                notes=getattr(row, 'notes', None),
            )
            for row in rows
        ]

        return ProjectStaffListResponse(
            case_code=case_code,
            project_name=case_code,
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

    async def delete_assignment_by_id(self, assignment_id: int) -> DeleteResponse:
        """依 assignment ID 刪除關聯記錄"""
        existing = await self.repo.get_assignment_by_id(assignment_id)
        if not existing:
            raise NotFoundException(resource="案件與承辦同仁關聯", resource_id=assignment_id)

        await self.repo.delete_assignment_by_id(assignment_id)
        await self.db.commit()

        return DeleteResponse(
            success=True,
            message="案件與承辦同仁關聯已成功刪除",
            deleted_id=assignment_id,
        )

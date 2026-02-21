"""
Service layer for Project Agency Contact operations

v2.0.0 - 2026-02-21
- 遷移至 ContactRepository，移除直接 ORM 操作
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import ContactRepository
from app.extended.models import ProjectAgencyContact
from app.schemas.project_agency_contact import (
    ProjectAgencyContactCreate,
    ProjectAgencyContactUpdate
)

logger = logging.getLogger(__name__)


class ProjectAgencyContactService:
    """專案機關承辦相關的業務邏輯服務"""

    async def get_contact(
        self,
        db: AsyncSession,
        contact_id: int
    ) -> Optional[ProjectAgencyContact]:
        """取得單一機關承辦資料"""
        repo = ContactRepository(db)
        return await repo.get_by_id(contact_id)

    async def get_contacts_by_project(
        self,
        db: AsyncSession,
        project_id: int
    ) -> Dict[str, Any]:
        """取得專案的所有機關承辦資料"""
        repo = ContactRepository(db)
        return await repo.get_by_project_id_with_count(project_id)

    async def create_contact(
        self,
        db: AsyncSession,
        contact: ProjectAgencyContactCreate
    ) -> ProjectAgencyContact:
        """建立機關承辦資料"""
        repo = ContactRepository(db)
        contact_data = contact.model_dump()

        # 如果設為主要承辦人，則取消其他主要承辦人
        if contact_data.get('is_primary'):
            await repo.clear_primary_contact(contact_data['project_id'])

        return await repo.create(contact_data)

    async def update_contact(
        self,
        db: AsyncSession,
        contact_id: int,
        contact_update: ProjectAgencyContactUpdate
    ) -> Optional[ProjectAgencyContact]:
        """更新機關承辦資料"""
        repo = ContactRepository(db)
        db_contact = await repo.get_by_id(contact_id)
        if not db_contact:
            return None

        update_data = contact_update.model_dump(exclude_unset=True)

        # 如果設為主要承辦人，則取消其他主要承辦人
        if update_data.get('is_primary'):
            await repo.clear_primary_contact(db_contact.project_id, exclude_id=contact_id)

        return await repo.update(contact_id, update_data)

    async def delete_contact(
        self,
        db: AsyncSession,
        contact_id: int
    ) -> bool:
        """刪除機關承辦資料"""
        repo = ContactRepository(db)
        return await repo.delete(contact_id)

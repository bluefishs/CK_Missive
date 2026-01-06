"""
Service layer for Project Agency Contact operations
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError

from app.extended.models import ProjectAgencyContact
from app.schemas.project_agency_contact import (
    ProjectAgencyContactCreate,
    ProjectAgencyContactUpdate
)

logger = logging.getLogger(__name__)


class ProjectAgencyContactService:
    """專案機關承辦相關的資料庫操作服務"""

    async def get_contact(
        self,
        db: AsyncSession,
        contact_id: int
    ) -> Optional[ProjectAgencyContact]:
        """取得單一機關承辦資料"""
        result = await db.execute(
            select(ProjectAgencyContact).where(ProjectAgencyContact.id == contact_id)
        )
        return result.scalar_one_or_none()

    async def get_contacts_by_project(
        self,
        db: AsyncSession,
        project_id: int
    ) -> Dict[str, Any]:
        """取得專案的所有機關承辦資料"""
        query = select(ProjectAgencyContact).where(
            ProjectAgencyContact.project_id == project_id
        ).order_by(ProjectAgencyContact.is_primary.desc(), ProjectAgencyContact.id)

        result = await db.execute(query)
        contacts = result.scalars().all()

        return {
            "items": contacts,
            "total": len(contacts)
        }

    async def create_contact(
        self,
        db: AsyncSession,
        contact: ProjectAgencyContactCreate
    ) -> ProjectAgencyContact:
        """建立機關承辦資料"""
        contact_data = contact.model_dump()

        # 如果設為主要承辦人，則取消其他主要承辦人
        if contact_data.get('is_primary'):
            await self._clear_primary_contact(db, contact_data['project_id'])

        db_contact = ProjectAgencyContact(**contact_data)
        db.add(db_contact)
        await db.commit()
        await db.refresh(db_contact)
        return db_contact

    async def update_contact(
        self,
        db: AsyncSession,
        contact_id: int,
        contact_update: ProjectAgencyContactUpdate
    ) -> Optional[ProjectAgencyContact]:
        """更新機關承辦資料"""
        db_contact = await self.get_contact(db, contact_id)
        if not db_contact:
            return None

        update_data = contact_update.model_dump(exclude_unset=True)

        # 如果設為主要承辦人，則取消其他主要承辦人
        if update_data.get('is_primary'):
            await self._clear_primary_contact(db, db_contact.project_id, exclude_id=contact_id)

        for key, value in update_data.items():
            setattr(db_contact, key, value)

        await db.commit()
        await db.refresh(db_contact)
        return db_contact

    async def delete_contact(
        self,
        db: AsyncSession,
        contact_id: int
    ) -> bool:
        """刪除機關承辦資料"""
        db_contact = await self.get_contact(db, contact_id)
        if not db_contact:
            return False

        await db.delete(db_contact)
        await db.commit()
        return True

    async def _clear_primary_contact(
        self,
        db: AsyncSession,
        project_id: int,
        exclude_id: Optional[int] = None
    ) -> None:
        """清除專案中其他主要承辦人標記"""
        stmt = update(ProjectAgencyContact).where(
            ProjectAgencyContact.project_id == project_id,
            ProjectAgencyContact.is_primary == True
        ).values(is_primary=False)

        if exclude_id:
            stmt = stmt.where(ProjectAgencyContact.id != exclude_id)

        await db.execute(stmt)

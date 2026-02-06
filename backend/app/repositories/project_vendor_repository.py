"""
ProjectVendorRepository - 案件廠商關聯資料存取層

處理 project_vendor_association 多對多關聯表的 CRUD 操作。
由於 project_vendor_association 是 SQLAlchemy Table（非 ORM Model），
不繼承 BaseRepository，而是提供獨立的資料存取方法。

版本: 1.0.0
建立日期: 2026-02-06
"""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete

from app.extended.models import (
    project_vendor_association,
    ContractProject,
    PartnerVendor,
)

logger = logging.getLogger(__name__)


class ProjectVendorRepository:
    """
    案件廠商關聯 Repository

    處理 project_vendor_association 關聯表的資料存取。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # 查詢方法
    # =========================================================================

    async def get_association(
        self, project_id: int, vendor_id: int
    ) -> Optional[Any]:
        """取得特定案件-廠商關聯"""
        query = select(project_vendor_association).where(
            (project_vendor_association.c.project_id == project_id)
            & (project_vendor_association.c.vendor_id == vendor_id)
        )
        result = await self.db.execute(query)
        return result.fetchone()

    async def get_project_associations(self, project_id: int) -> List[Any]:
        """
        取得案件的所有廠商關聯（含廠商資訊 JOIN）

        Returns:
            關聯記錄列表，每筆包含關聯欄位 + 廠商名稱/代碼等
        """
        query = (
            select(
                project_vendor_association.c.project_id,
                project_vendor_association.c.vendor_id,
                project_vendor_association.c.role,
                project_vendor_association.c.contract_amount,
                project_vendor_association.c.start_date,
                project_vendor_association.c.end_date,
                project_vendor_association.c.status,
                project_vendor_association.c.created_at,
                project_vendor_association.c.updated_at,
                PartnerVendor.vendor_name,
                PartnerVendor.vendor_code,
                PartnerVendor.contact_person,
                PartnerVendor.phone,
                PartnerVendor.business_type,
            )
            .select_from(
                project_vendor_association.join(
                    PartnerVendor,
                    project_vendor_association.c.vendor_id == PartnerVendor.id,
                )
            )
            .where(project_vendor_association.c.project_id == project_id)
        )
        result = await self.db.execute(query)
        return result.fetchall()

    async def get_vendor_associations(self, vendor_id: int) -> List[Any]:
        """
        取得廠商的所有案件關聯（含案件資訊 JOIN）

        Returns:
            關聯記錄列表，每筆包含關聯欄位 + 案件名稱/代碼等
        """
        query = (
            select(
                project_vendor_association.c.project_id,
                project_vendor_association.c.vendor_id,
                project_vendor_association.c.role,
                project_vendor_association.c.contract_amount,
                project_vendor_association.c.start_date,
                project_vendor_association.c.end_date,
                project_vendor_association.c.status,
                project_vendor_association.c.created_at,
                project_vendor_association.c.updated_at,
                ContractProject.project_name,
                ContractProject.project_code,
                ContractProject.year,
                ContractProject.category,
                ContractProject.status.label("project_status"),
            )
            .select_from(
                project_vendor_association.join(
                    ContractProject,
                    project_vendor_association.c.project_id == ContractProject.id,
                )
            )
            .where(project_vendor_association.c.vendor_id == vendor_id)
        )
        result = await self.db.execute(query)
        return result.fetchall()

    async def list_all(
        self,
        project_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Any]:
        """
        列表查詢所有關聯（含案件與廠商資訊 JOIN）

        Args:
            project_id: 案件 ID 篩選
            vendor_id: 廠商 ID 篩選
            status: 狀態篩選
            skip: 跳過筆數
            limit: 限制筆數
        """
        query = (
            select(
                project_vendor_association.c.project_id,
                project_vendor_association.c.vendor_id,
                project_vendor_association.c.role,
                project_vendor_association.c.contract_amount,
                project_vendor_association.c.start_date,
                project_vendor_association.c.end_date,
                project_vendor_association.c.status,
                project_vendor_association.c.created_at,
                project_vendor_association.c.updated_at,
                ContractProject.project_name,
                ContractProject.project_code,
                PartnerVendor.vendor_name,
                PartnerVendor.vendor_code,
            )
            .select_from(
                project_vendor_association.join(
                    ContractProject,
                    project_vendor_association.c.project_id == ContractProject.id,
                ).join(
                    PartnerVendor,
                    project_vendor_association.c.vendor_id == PartnerVendor.id,
                )
            )
        )

        if project_id is not None:
            query = query.where(
                project_vendor_association.c.project_id == project_id
            )
        if vendor_id is not None:
            query = query.where(
                project_vendor_association.c.vendor_id == vendor_id
            )
        if status is not None:
            query = query.where(
                project_vendor_association.c.status == status
            )

        query = query.order_by(
            project_vendor_association.c.created_at.desc()
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.fetchall()

    # =========================================================================
    # 寫入方法
    # =========================================================================

    async def create_association(self, data: Dict[str, Any]) -> None:
        """建立案件-廠商關聯"""
        stmt = insert(project_vendor_association).values(**data)
        await self.db.execute(stmt)
        await self.db.commit()

    async def update_association(
        self,
        project_id: int,
        vendor_id: int,
        data: Dict[str, Any],
    ) -> None:
        """更新案件-廠商關聯"""
        if not data:
            return
        stmt = (
            update(project_vendor_association)
            .where(
                (project_vendor_association.c.project_id == project_id)
                & (project_vendor_association.c.vendor_id == vendor_id)
            )
            .values(**data)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def delete_association(
        self, project_id: int, vendor_id: int
    ) -> None:
        """刪除案件-廠商關聯"""
        stmt = delete(project_vendor_association).where(
            (project_vendor_association.c.project_id == project_id)
            & (project_vendor_association.c.vendor_id == vendor_id)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    # =========================================================================
    # 輔助方法
    # =========================================================================

    async def exists(self, project_id: int, vendor_id: int) -> bool:
        """檢查關聯是否存在"""
        return await self.get_association(project_id, vendor_id) is not None

    async def project_exists(self, project_id: int) -> Optional[Any]:
        """檢查案件是否存在，回傳案件物件或 None"""
        query = select(ContractProject).where(
            ContractProject.id == project_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def vendor_exists(self, vendor_id: int) -> Optional[Any]:
        """檢查廠商是否存在，回傳廠商物件或 None"""
        query = select(PartnerVendor).where(PartnerVendor.id == vendor_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

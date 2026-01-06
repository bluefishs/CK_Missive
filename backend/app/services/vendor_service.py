"""
廠商服務層 - 繼承 BaseService 實現標準 CRUD

使用泛型基類減少重複代碼，提供統一的資料庫操作介面。
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.services.base_service import BaseService
from app.extended.models import PartnerVendor, project_vendor_association
from app.schemas.vendor import VendorCreate, VendorUpdate

logger = logging.getLogger(__name__)


class VendorService(BaseService[PartnerVendor, VendorCreate, VendorUpdate]):
    """
    協力廠商服務 - 繼承 BaseService

    提供廠商相關的 CRUD 操作和業務邏輯。
    """

    def __init__(self):
        """初始化廠商服務"""
        super().__init__(PartnerVendor, "廠商")

    # =========================================================================
    # 覆寫方法 - 加入業務邏輯
    # =========================================================================

    async def create(
        self,
        db: AsyncSession,
        data: VendorCreate
    ) -> PartnerVendor:
        """
        建立廠商 - 加入統一編號重複檢查

        Args:
            db: 資料庫 session
            data: 建立資料

        Returns:
            新建的廠商

        Raises:
            ValueError: 統一編號已存在
        """
        # 檢查統一編號是否重複
        if data.vendor_code:
            existing = await self.get_by_field(db, "vendor_code", data.vendor_code)
            if existing:
                raise ValueError(f"廠商統一編號 {data.vendor_code} 已存在")

        return await super().create(db, data)

    async def delete(
        self,
        db: AsyncSession,
        vendor_id: int
    ) -> bool:
        """
        刪除廠商 - 檢查是否有關聯專案

        Args:
            db: 資料庫 session
            vendor_id: 廠商 ID

        Returns:
            是否刪除成功

        Raises:
            ValueError: 廠商仍有關聯專案
        """
        # 檢查是否有關聯專案
        usage_query = select(func.count(project_vendor_association.c.project_id)).where(
            project_vendor_association.c.vendor_id == vendor_id
        )
        result = await db.execute(usage_query)
        usage_count = result.scalar_one()

        if usage_count > 0:
            raise ValueError(f"無法刪除，此廠商仍與 {usage_count} 個專案關聯")

        return await super().delete(db, vendor_id)

    # =========================================================================
    # 擴充方法 - 業務特定功能
    # =========================================================================

    async def get_vendors_with_search(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        取得廠商列表（含搜尋）

        Args:
            db: 資料庫 session
            skip: 跳過筆數
            limit: 取得筆數
            search: 搜尋關鍵字

        Returns:
            廠商列表（字典格式）
        """
        query = select(PartnerVendor)

        # 搜尋條件
        if search:
            search_filter = or_(
                PartnerVendor.vendor_name.ilike(f"%{search}%"),
                PartnerVendor.vendor_code.ilike(f"%{search}%")
            )
            query = query.where(search_filter)

        query = query.order_by(PartnerVendor.vendor_name).offset(skip).limit(limit)
        result = await db.execute(query)
        vendors = result.scalars().all()

        # 轉換為字典格式
        return [
            {
                "id": vendor.id,
                "vendor_name": vendor.vendor_name,
                "vendor_code": vendor.vendor_code,
                "contact_person": vendor.contact_person,
                "phone": vendor.phone,
                "address": vendor.address,
                "email": vendor.email,
                "business_type": vendor.business_type,
                "rating": vendor.rating,
                "created_at": vendor.created_at,
                "updated_at": vendor.updated_at
            }
            for vendor in vendors
        ]

    async def get_total_with_search(
        self,
        db: AsyncSession,
        search: Optional[str] = None
    ) -> int:
        """
        取得廠商總數（含搜尋條件）

        Args:
            db: 資料庫 session
            search: 搜尋關鍵字

        Returns:
            符合條件的廠商總數
        """
        query = select(func.count(PartnerVendor.id))

        if search:
            search_filter = or_(
                PartnerVendor.vendor_name.ilike(f"%{search}%"),
                PartnerVendor.vendor_code.ilike(f"%{search}%")
            )
            query = query.where(search_filter)

        result = await db.execute(query)
        return result.scalar() or 0

    async def get_vendor_statistics(
        self,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        取得廠商統計資料

        Args:
            db: 資料庫 session

        Returns:
            統計資料字典
        """
        try:
            # 總數
            total_vendors = await self.get_count(db)

            # 依業務類型統計
            type_result = await db.execute(
                select(PartnerVendor.business_type, func.count(PartnerVendor.id))
                .group_by(PartnerVendor.business_type)
                .order_by(PartnerVendor.business_type)
            )
            type_stats = [
                {"business_type": row[0] or "未分類", "count": row[1]}
                for row in type_result.fetchall()
            ]

            # 平均評等
            rating_result = await db.execute(
                select(func.avg(PartnerVendor.rating)).where(PartnerVendor.rating.isnot(None))
            )
            avg_rating = rating_result.scalar()
            avg_rating = round(float(avg_rating), 2) if avg_rating else 0.0

            return {
                "total_vendors": total_vendors,
                "business_types": type_stats,
                "average_rating": avg_rating
            }
        except Exception as e:
            logger.error(f"取得廠商統計資料失敗: {e}", exc_info=True)
            return {
                "total_vendors": 0,
                "business_types": [],
                "average_rating": 0.0
            }

    # =========================================================================
    # 向後相容方法 (逐步淘汰)
    # =========================================================================

    async def get_vendor(self, db: AsyncSession, vendor_id: int) -> Optional[PartnerVendor]:
        """@deprecated 使用 get_by_id"""
        return await self.get_by_id(db, vendor_id)

    async def get_vendors(self, db: AsyncSession, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> List[dict]:
        """@deprecated 使用 get_vendors_with_search"""
        return await self.get_vendors_with_search(db, skip, limit, search)

    async def get_total_vendors(self, db: AsyncSession, search: Optional[str] = None) -> int:
        """@deprecated 使用 get_total_with_search"""
        return await self.get_total_with_search(db, search)

    async def create_vendor(self, db: AsyncSession, vendor: VendorCreate) -> PartnerVendor:
        """@deprecated 使用 create"""
        return await self.create(db, vendor)

    async def update_vendor(self, db: AsyncSession, vendor_id: int, vendor_update: VendorUpdate) -> Optional[PartnerVendor]:
        """@deprecated 使用 update"""
        return await self.update(db, vendor_id, vendor_update)

    async def delete_vendor(self, db: AsyncSession, vendor_id: int) -> bool:
        """@deprecated 使用 delete"""
        return await self.delete(db, vendor_id)

"""
廠商服務層 - 繼承 BaseService 實現標準 CRUD

使用泛型基類減少重複代碼，提供統一的資料庫操作介面。

.. deprecated:: 1.42.0
   Singleton 模式（db 在每個方法中傳入）將在 v2.0 棄用。
   新開發請使用工廠模式（db 在建構函數注入）。
   參見：docs/SERVICE_ARCHITECTURE_STANDARDS.md

v2.1.0 (2026-01-22): 重構使用 BaseService 新方法
- get_vendors_with_search → 使用 get_list_with_search
- get_total_with_search → 使用 get_count_with_search
- get_vendor_statistics → 使用 @with_stats_error_handling
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.base_service import BaseService, with_stats_error_handling
from app.services.base import DeleteCheckHelper, StatisticsHelper
from app.extended.models import PartnerVendor, project_vendor_association
from app.schemas.vendor import VendorCreate, VendorUpdate

logger = logging.getLogger(__name__)


class VendorService(BaseService[PartnerVendor, VendorCreate, VendorUpdate]):
    """
    協力廠商服務 - 繼承 BaseService

    提供廠商相關的 CRUD 操作和業務邏輯。
    """

    # 類別層級設定
    SEARCH_FIELDS = ['vendor_name', 'vendor_code']
    DEFAULT_SORT_FIELD = 'vendor_name'

    def __init__(self, db: "AsyncSession | None" = None) -> None:
        """初始化廠商服務"""
        super().__init__(PartnerVendor, "廠商", db=db)
        if db:
            from app.repositories import VendorRepository
            self.repository = VendorRepository(db)

    def _to_dict(self, vendor: PartnerVendor) -> Dict[str, Any]:
        """將廠商實體轉換為字典"""
        return {
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
        # 使用 DeleteCheckHelper 檢查關聯專案
        can_delete, usage_count = await DeleteCheckHelper.check_association_usage(
            db,
            project_vendor_association,
            'vendor_id',
            vendor_id,
            'project_id'
        )

        if not can_delete:
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
        search: Optional[str] = None,
        business_type: Optional[str] = None,
        rating: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        取得廠商列表（含搜尋和篩選）

        Args:
            db: 資料庫 session
            skip: 跳過筆數
            limit: 取得筆數
            search: 搜尋關鍵字
            business_type: 營業項目篩選
            rating: 評價篩選 (1-5)

        Returns:
            廠商列表（字典格式）
        """
        from sqlalchemy import select, or_

        query = select(PartnerVendor)

        # 搜尋條件
        if search:
            search_conditions = [
                getattr(PartnerVendor, field).ilike(f"%{search}%")
                for field in self.SEARCH_FIELDS
                if hasattr(PartnerVendor, field)
            ]
            if search_conditions:
                query = query.where(or_(*search_conditions))

        # 營業項目篩選
        if business_type:
            query = query.where(PartnerVendor.business_type == business_type)

        # 評價篩選
        if rating:
            query = query.where(PartnerVendor.rating == rating)

        # 排序和分頁
        query = query.order_by(getattr(PartnerVendor, self.DEFAULT_SORT_FIELD))
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        vendors = result.scalars().all()

        return [self._to_dict(v) for v in vendors]

    async def get_total_with_search(
        self,
        db: AsyncSession,
        search: Optional[str] = None,
        business_type: Optional[str] = None,
        rating: Optional[int] = None
    ) -> int:
        """
        取得廠商總數（含搜尋和篩選條件）

        Args:
            db: 資料庫 session
            search: 搜尋關鍵字
            business_type: 營業項目篩選
            rating: 評價篩選 (1-5)

        Returns:
            符合條件的廠商總數
        """
        from sqlalchemy import select, func, or_

        query = select(func.count()).select_from(PartnerVendor)

        # 搜尋條件
        if search:
            search_conditions = [
                getattr(PartnerVendor, field).ilike(f"%{search}%")
                for field in self.SEARCH_FIELDS
                if hasattr(PartnerVendor, field)
            ]
            if search_conditions:
                query = query.where(or_(*search_conditions))

        # 營業項目篩選
        if business_type:
            query = query.where(PartnerVendor.business_type == business_type)

        # 評價篩選
        if rating:
            query = query.where(PartnerVendor.rating == rating)

        result = await db.execute(query)
        return result.scalar_one()

    @with_stats_error_handling(
        default_return={"total_vendors": 0, "business_types": [], "average_rating": 0.0},
        operation_name="統計資料"
    )
    async def get_vendor_statistics(
        self,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        取得廠商統計資料 - 使用 @with_stats_error_handling 裝飾器

        Args:
            db: 資料庫 session

        Returns:
            統計資料字典
        """
        # 使用 StatisticsHelper 取得基本統計
        basic_stats = await StatisticsHelper.get_basic_stats(db, PartnerVendor)
        total_vendors = basic_stats.get("total", 0)

        # 使用 StatisticsHelper 取得分組統計
        grouped_stats = await StatisticsHelper.get_grouped_stats(
            db, PartnerVendor, 'business_type'
        )
        type_stats = [
            {"business_type": k if k != 'null' else "未分類", "count": v}
            for k, v in sorted(grouped_stats.items())
        ]

        # 使用 StatisticsHelper 取得平均評等
        rating_stats = await StatisticsHelper.get_average_stats(
            db, PartnerVendor, 'rating'
        )
        avg_rating = rating_stats.get("average") or 0.0

        return {
            "total_vendors": total_vendors,
            "business_types": type_stats,
            "average_rating": avg_rating
        }

    # =========================================================================
    # 向後相容方法 (逐步淘汰)
    # =========================================================================

    async def get_vendor(self, db: AsyncSession, vendor_id: int) -> Optional[PartnerVendor]:
        """
        @deprecated v2.0 (2026-01-20) 使用 get_by_id 代替
        移除計畫: v3.0 (2026-03-01)
        """
        return await self.get_by_id(db, vendor_id)

    async def get_vendors(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        business_type: Optional[str] = None,
        rating: Optional[int] = None
    ) -> List[dict]:
        """
        @deprecated v2.0 (2026-01-20) 使用 get_vendors_with_search 代替
        移除計畫: v3.0 (2026-03-01)
        """
        return await self.get_vendors_with_search(db, skip, limit, search, business_type, rating)

    async def get_total_vendors(
        self,
        db: AsyncSession,
        search: Optional[str] = None,
        business_type: Optional[str] = None,
        rating: Optional[int] = None
    ) -> int:
        """
        @deprecated v2.0 (2026-01-20) 使用 get_total_with_search 代替
        移除計畫: v3.0 (2026-03-01)
        """
        return await self.get_total_with_search(db, search, business_type, rating)

    async def create_vendor(self, db: AsyncSession, vendor: VendorCreate) -> PartnerVendor:
        """
        @deprecated v2.0 (2026-01-20) 使用 create 代替
        移除計畫: v3.0 (2026-03-01)
        """
        return await self.create(db, vendor)

    async def update_vendor(self, db: AsyncSession, vendor_id: int, vendor_update: VendorUpdate) -> Optional[PartnerVendor]:
        """
        @deprecated v2.0 (2026-01-20) 使用 update 代替
        移除計畫: v3.0 (2026-03-01)
        """
        return await self.update(db, vendor_id, vendor_update)

    async def delete_vendor(self, db: AsyncSession, vendor_id: int) -> bool:
        """
        @deprecated v2.0 (2026-01-20) 使用 delete 代替
        移除計畫: v3.0 (2026-03-01)
        """
        return await self.delete(db, vendor_id)

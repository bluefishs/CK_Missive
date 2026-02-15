"""
廠商服務層 - 工廠模式

使用工廠模式，db session 在建構函數注入。

版本: 2.0.0
更新日期: 2026-02-06
變更: 從 BaseService 繼承模式升級為工廠模式

使用方式:
    # 依賴注入（推薦）
    from app.core.dependencies import get_service

    @router.get("/vendors")
    async def list_vendors(
        service: VendorService = Depends(get_service(VendorService))
    ):
        return await service.get_list()

    # 手動建立
    async def some_function(db: AsyncSession):
        service = VendorService(db)
        vendors = await service.get_list()
"""

import logging
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.repositories import VendorRepository
from app.extended.models import PartnerVendor, project_vendor_association
from app.schemas.vendor import VendorCreate, VendorUpdate
from app.services.base import DeleteCheckHelper, StatisticsHelper

logger = logging.getLogger(__name__)


class VendorService:
    """
    協力廠商服務 - 工廠模式

    所有方法不再需要傳入 db 參數，db session 在建構時注入。

    Example:
        service = VendorService(db)

        # 列表查詢
        vendors = await service.get_list(search="測試")

        # 建立
        vendor = await service.create(VendorCreate(vendor_name="新廠商"))

        # 更新
        vendor = await service.update(1, VendorUpdate(phone="0912345678"))

        # 刪除
        success = await service.delete(1)
    """

    # 搜尋欄位
    SEARCH_FIELDS = ['vendor_name', 'vendor_code']

    def __init__(self, db: AsyncSession) -> None:
        """
        初始化廠商服務

        Args:
            db: AsyncSession 資料庫連線
        """
        self.db = db
        self.repository = VendorRepository(db)
        self.model = PartnerVendor

    # =========================================================================
    # 基礎 CRUD 方法
    # =========================================================================

    async def get_by_id(self, vendor_id: int) -> Optional[PartnerVendor]:
        """
        根據 ID 取得廠商

        Args:
            vendor_id: 廠商 ID

        Returns:
            廠商物件或 None
        """
        return await self.repository.get_by_id(vendor_id)

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        business_type: Optional[str] = None,
        rating: Optional[int] = None,
    ) -> List[PartnerVendor]:
        """
        取得廠商列表

        Args:
            skip: 跳過筆數
            limit: 取得筆數
            search: 搜尋關鍵字
            business_type: 營業項目篩選
            rating: 評價篩選

        Returns:
            廠商列表
        """
        query = select(self.model)

        # 搜尋條件
        if search:
            search_pattern = f"%{search}%"
            conditions = [
                getattr(self.model, field).ilike(search_pattern)
                for field in self.SEARCH_FIELDS
                if hasattr(self.model, field)
            ]
            if conditions:
                query = query.where(or_(*conditions))

        # 篩選條件
        if business_type:
            query = query.where(self.model.business_type == business_type)
        if rating:
            query = query.where(self.model.rating == rating)

        # 排序與分頁
        query = query.order_by(self.model.vendor_name)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_count(
        self,
        search: Optional[str] = None,
        business_type: Optional[str] = None,
        rating: Optional[int] = None,
    ) -> int:
        """
        取得廠商總數

        Args:
            search: 搜尋關鍵字
            business_type: 營業項目篩選
            rating: 評價篩選

        Returns:
            符合條件的廠商總數
        """
        query = select(func.count(self.model.id))

        # 搜尋條件
        if search:
            search_pattern = f"%{search}%"
            conditions = [
                getattr(self.model, field).ilike(search_pattern)
                for field in self.SEARCH_FIELDS
                if hasattr(self.model, field)
            ]
            if conditions:
                query = query.where(or_(*conditions))

        # 篩選條件
        if business_type:
            query = query.where(self.model.business_type == business_type)
        if rating:
            query = query.where(self.model.rating == rating)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        business_type: Optional[str] = None,
        rating: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        取得分頁列表

        Args:
            page: 頁碼（從 1 開始）
            page_size: 每頁筆數
            search: 搜尋關鍵字
            business_type: 營業項目篩選
            rating: 評價篩選

        Returns:
            包含 items, total, page, page_size, total_pages 的字典
        """
        skip = (page - 1) * page_size

        items = await self.get_list(
            skip=skip,
            limit=page_size,
            search=search,
            business_type=business_type,
            rating=rating,
        )

        total = await self.get_count(
            search=search,
            business_type=business_type,
            rating=rating,
        )

        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def create(self, data: VendorCreate) -> PartnerVendor:
        """
        建立廠商

        Args:
            data: 建立資料

        Returns:
            新建的廠商

        Raises:
            ValueError: 統一編號已存在
        """
        # 檢查統一編號是否重複
        if data.vendor_code:
            existing = await self.repository.get_by_field('vendor_code', data.vendor_code)
            if existing:
                raise ValueError(f"廠商統一編號 {data.vendor_code} 已存在")

        return await self.repository.create(data)

    async def update(
        self,
        vendor_id: int,
        data: VendorUpdate,
    ) -> Optional[PartnerVendor]:
        """
        更新廠商

        Args:
            vendor_id: 廠商 ID
            data: 更新資料

        Returns:
            更新後的廠商，或 None（如不存在）
        """
        return await self.repository.update(vendor_id, data)

    async def delete(self, vendor_id: int) -> bool:
        """
        刪除廠商

        Args:
            vendor_id: 廠商 ID

        Returns:
            是否刪除成功

        Raises:
            ValueError: 廠商仍有關聯專案
        """
        # 檢查是否有關聯專案
        can_delete, usage_count = await DeleteCheckHelper.check_association_usage(
            self.db,
            project_vendor_association,
            'vendor_id',
            vendor_id,
            'project_id'
        )

        if not can_delete:
            raise ValueError(f"無法刪除，此廠商仍與 {usage_count} 個專案關聯")

        return await self.repository.delete(vendor_id)

    # =========================================================================
    # 統計方法
    # =========================================================================

    async def get_statistics(self) -> Dict[str, Any]:
        """
        取得廠商統計資料

        Returns:
            統計資料字典
        """
        try:
            # 基本統計
            basic_stats = await StatisticsHelper.get_basic_stats(self.db, self.model)
            total = basic_stats.get("total", 0)

            # 營業項目分組統計
            grouped_stats = await StatisticsHelper.get_grouped_stats(
                self.db, self.model, 'business_type'
            )
            type_stats = [
                {"business_type": k if k != 'null' else "未分類", "count": v}
                for k, v in sorted(grouped_stats.items())
            ]

            # 平均評等
            rating_stats = await StatisticsHelper.get_average_stats(
                self.db, self.model, 'rating'
            )
            avg_rating = rating_stats.get("average") or 0.0

            return {
                "total_vendors": total,
                "business_types": type_stats,
                "average_rating": round(avg_rating, 2),
            }
        except Exception as e:
            logger.error(f"取得廠商統計失敗: {e}")
            return {
                "total_vendors": 0,
                "business_types": [],
                "average_rating": 0.0,
            }

    # =========================================================================
    # 工具方法
    # =========================================================================

    async def exists(self, vendor_id: int) -> bool:
        """檢查廠商是否存在"""
        return await self.repository.exists(vendor_id)

    async def get_by_code(self, vendor_code: str) -> Optional[PartnerVendor]:
        """根據統一編號取得廠商"""
        return await self.repository.get_by_field('vendor_code', vendor_code)

    def to_dict(self, vendor: PartnerVendor) -> Dict[str, Any]:
        """將廠商物件轉換為字典"""
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
            "updated_at": vendor.updated_at,
        }

    # =========================================================================
    # 向後相容方法 (保留至 v3.0)
    # =========================================================================

    async def get_vendor(self, vendor_id: int) -> Optional[PartnerVendor]:
        """
        @deprecated 使用 get_by_id 代替
        """
        return await self.get_by_id(vendor_id)

    async def get_vendors(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        business_type: Optional[str] = None,
        rating: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        @deprecated 使用 get_list 代替
        """
        vendors = await self.get_list(skip, limit, search, business_type, rating)
        return [self.to_dict(v) for v in vendors]

    async def get_total_vendors(
        self,
        search: Optional[str] = None,
        business_type: Optional[str] = None,
        rating: Optional[int] = None
    ) -> int:
        """
        @deprecated 使用 get_count 代替
        """
        return await self.get_count(search, business_type, rating)

    async def create_vendor(self, vendor: VendorCreate) -> PartnerVendor:
        """
        @deprecated 使用 create 代替
        """
        return await self.create(vendor)

    async def update_vendor(
        self, vendor_id: int, vendor_update: VendorUpdate
    ) -> Optional[PartnerVendor]:
        """
        @deprecated 使用 update 代替
        """
        return await self.update(vendor_id, vendor_update)

    async def delete_vendor(self, vendor_id: int) -> bool:
        """
        @deprecated 使用 delete 代替
        """
        return await self.delete(vendor_id)

    async def get_vendor_statistics(self) -> Dict[str, Any]:
        """
        @deprecated 使用 get_statistics 代替
        """
        return await self.get_statistics()

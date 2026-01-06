"""
Base Service - 提供 CRUD 操作的基礎類別

使用泛型支援不同的 Model 和 Schema 類型，減少重複代碼。
"""
import logging
from typing import TypeVar, Generic, Optional, List, Dict, Any, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.sql import Select
from pydantic import BaseModel

# 泛型類型變數
ModelType = TypeVar('ModelType')
CreateSchemaType = TypeVar('CreateSchemaType', bound=BaseModel)
UpdateSchemaType = TypeVar('UpdateSchemaType', bound=BaseModel)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    CRUD 操作基礎服務類別

    提供標準的資料庫操作方法，子類別可繼承並擴展。

    使用方式:
        class VendorService(BaseService[PartnerVendor, VendorCreate, VendorUpdate]):
            def __init__(self):
                super().__init__(PartnerVendor, "廠商")
    """

    def __init__(self, model: Type[ModelType], entity_name: str = "實體"):
        """
        初始化基礎服務

        Args:
            model: SQLAlchemy Model 類別
            entity_name: 實體名稱（用於錯誤訊息）
        """
        self.model = model
        self.entity_name = entity_name
        self.logger = logging.getLogger(self.__class__.__name__)

    # =========================================================================
    # 基礎查詢方法
    # =========================================================================

    async def get_by_id(
        self,
        db: AsyncSession,
        entity_id: int
    ) -> Optional[ModelType]:
        """
        根據 ID 取得單筆資料

        Args:
            db: 資料庫 session
            entity_id: 實體 ID

        Returns:
            實體物件，若不存在則返回 None
        """
        result = await db.execute(
            select(self.model).where(self.model.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        query: Optional[Select] = None
    ) -> List[ModelType]:
        """
        取得分頁列表

        Args:
            db: 資料庫 session
            skip: 跳過筆數
            limit: 取得筆數
            query: 自訂查詢（可選）

        Returns:
            實體列表
        """
        if query is None:
            query = select(self.model)

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_count(
        self,
        db: AsyncSession,
        query: Optional[Select] = None
    ) -> int:
        """
        取得資料總數

        Args:
            db: 資料庫 session
            query: 自訂查詢（可選）

        Returns:
            資料總數
        """
        if query is None:
            count_query = select(func.count(self.model.id))
        else:
            count_query = select(func.count()).select_from(query.subquery())

        result = await db.execute(count_query)
        return result.scalar() or 0

    async def get_paginated(
        self,
        db: AsyncSession,
        page: int = 1,
        limit: int = 20,
        query: Optional[Select] = None
    ) -> Dict[str, Any]:
        """
        取得分頁結果（含總數與分頁資訊）

        Args:
            db: 資料庫 session
            page: 頁碼（從 1 開始）
            limit: 每頁筆數
            query: 自訂查詢（可選）

        Returns:
            包含 items, total, page, limit, total_pages 的字典
        """
        skip = (page - 1) * limit

        total = await self.get_count(db, query)
        items = await self.get_list(db, skip, limit, query)

        total_pages = (total + limit - 1) // limit if limit > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }

    # =========================================================================
    # 基礎 CRUD 方法
    # =========================================================================

    async def create(
        self,
        db: AsyncSession,
        data: CreateSchemaType
    ) -> ModelType:
        """
        建立新實體

        Args:
            db: 資料庫 session
            data: 建立資料 schema

        Returns:
            新建的實體物件
        """
        # 支援 Pydantic v1 和 v2
        if hasattr(data, 'model_dump'):
            entity_data = data.model_dump()
        else:
            entity_data = data.dict()

        db_entity = self.model(**entity_data)
        db.add(db_entity)
        await db.commit()
        await db.refresh(db_entity)

        self.logger.info(f"建立{self.entity_name}: ID={db_entity.id}")
        return db_entity

    async def update(
        self,
        db: AsyncSession,
        entity_id: int,
        data: UpdateSchemaType
    ) -> Optional[ModelType]:
        """
        更新實體

        Args:
            db: 資料庫 session
            entity_id: 實體 ID
            data: 更新資料 schema

        Returns:
            更新後的實體物件，若不存在則返回 None
        """
        db_entity = await self.get_by_id(db, entity_id)
        if not db_entity:
            return None

        # 支援 Pydantic v1 和 v2
        if hasattr(data, 'model_dump'):
            update_data = data.model_dump(exclude_unset=True)
        else:
            update_data = data.dict(exclude_unset=True)

        for key, value in update_data.items():
            setattr(db_entity, key, value)

        await db.commit()
        await db.refresh(db_entity)

        self.logger.info(f"更新{self.entity_name}: ID={entity_id}")
        return db_entity

    async def delete(
        self,
        db: AsyncSession,
        entity_id: int
    ) -> bool:
        """
        刪除實體

        Args:
            db: 資料庫 session
            entity_id: 實體 ID

        Returns:
            刪除是否成功
        """
        db_entity = await self.get_by_id(db, entity_id)
        if not db_entity:
            return False

        await db.delete(db_entity)
        await db.commit()

        self.logger.info(f"刪除{self.entity_name}: ID={entity_id}")
        return True

    # =========================================================================
    # 工具方法
    # =========================================================================

    async def exists(
        self,
        db: AsyncSession,
        entity_id: int
    ) -> bool:
        """
        檢查實體是否存在

        Args:
            db: 資料庫 session
            entity_id: 實體 ID

        Returns:
            是否存在
        """
        result = await db.execute(
            select(func.count(self.model.id)).where(self.model.id == entity_id)
        )
        return (result.scalar() or 0) > 0

    async def get_by_field(
        self,
        db: AsyncSession,
        field_name: str,
        field_value: Any
    ) -> Optional[ModelType]:
        """
        根據欄位值取得單筆資料

        Args:
            db: 資料庫 session
            field_name: 欄位名稱
            field_value: 欄位值

        Returns:
            實體物件，若不存在則返回 None
        """
        field = getattr(self.model, field_name, None)
        if field is None:
            raise ValueError(f"欄位 {field_name} 不存在於 {self.model.__name__}")

        result = await db.execute(
            select(self.model).where(field == field_value)
        )
        return result.scalar_one_or_none()

    async def bulk_delete(
        self,
        db: AsyncSession,
        entity_ids: List[int]
    ) -> int:
        """
        批次刪除實體

        Args:
            db: 資料庫 session
            entity_ids: 實體 ID 列表

        Returns:
            成功刪除的數量
        """
        deleted_count = 0
        for entity_id in entity_ids:
            if await self.delete(db, entity_id):
                deleted_count += 1

        self.logger.info(f"批次刪除{self.entity_name}: {deleted_count}/{len(entity_ids)}")
        return deleted_count

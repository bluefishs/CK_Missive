"""
導覽服務 - 處理網站導覽項目的業務邏輯

提供導覽項目的 CRUD 操作與樹狀結構管理。

@version 1.0.0
@date 2026-01-10
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import SiteNavigationItem
from app.schemas.site_management import NavigationItemCreate


class NavigationService:
    """
    導覽服務類別

    處理網站導覽項目的 CRUD 操作和樹狀結構管理。
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    # =========================================================================
    # 查詢方法
    # =========================================================================

    async def get_navigation_tree(
        self,
        db: AsyncSession,
        include_disabled: bool = False
    ) -> List[Dict[str, Any]]:
        """
        取得完整的導覽樹狀結構

        Args:
            db: 資料庫 session
            include_disabled: 是否包含已停用項目

        Returns:
            導覽項目樹狀列表
        """
        # 查詢根層級項目
        query = select(SiteNavigationItem).where(
            SiteNavigationItem.parent_id.is_(None)
        ).order_by(SiteNavigationItem.sort_order)

        if not include_disabled:
            query = query.where(SiteNavigationItem.is_enabled == True)

        result = await db.execute(query)
        root_items = result.scalars().all()

        # 遞迴建立樹狀結構
        items = []
        for item in root_items:
            item_dict = await self._build_item_dict(db, item, include_disabled)
            items.append(item_dict)

        return items

    async def get_item_by_id(
        self,
        db: AsyncSession,
        item_id: int
    ) -> Optional[SiteNavigationItem]:
        """
        根據 ID 取得導覽項目

        Args:
            db: 資料庫 session
            item_id: 項目 ID

        Returns:
            導覽項目，若不存在則返回 None
        """
        result = await db.execute(
            select(SiteNavigationItem).where(SiteNavigationItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def get_children(
        self,
        db: AsyncSession,
        parent_id: int,
        include_disabled: bool = False
    ) -> List[SiteNavigationItem]:
        """
        取得指定父項目的子項目

        Args:
            db: 資料庫 session
            parent_id: 父項目 ID
            include_disabled: 是否包含已停用項目

        Returns:
            子項目列表
        """
        query = select(SiteNavigationItem).where(
            SiteNavigationItem.parent_id == parent_id
        ).order_by(SiteNavigationItem.sort_order)

        if not include_disabled:
            query = query.where(SiteNavigationItem.is_enabled == True)

        result = await db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # CRUD 方法
    # =========================================================================

    async def create_item(
        self,
        db: AsyncSession,
        data: NavigationItemCreate
    ) -> SiteNavigationItem:
        """
        建立新的導覽項目

        Args:
            db: 資料庫 session
            data: 導覽項目建立資料

        Returns:
            新建的導覽項目
        """
        new_item = SiteNavigationItem(**data.model_dump())
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)

        self.logger.info(f"建立導覽項目: ID={new_item.id}, title={new_item.title}")
        return new_item

    async def update_item(
        self,
        db: AsyncSession,
        item_id: int,
        data: Dict[str, Any]
    ) -> Optional[SiteNavigationItem]:
        """
        更新導覽項目

        Args:
            db: 資料庫 session
            item_id: 項目 ID
            data: 更新資料

        Returns:
            更新後的導覽項目，若不存在則返回 None
        """
        item = await self.get_item_by_id(db, item_id)
        if not item:
            return None

        # 過濾有效的更新欄位
        update_data = {k: v for k, v in data.items() if k != "id" and v is not None}

        for key, value in update_data.items():
            if hasattr(item, key):
                setattr(item, key, value)

        item.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(item)

        self.logger.info(f"更新導覽項目: ID={item_id}")
        return item

    async def delete_item(
        self,
        db: AsyncSession,
        item_id: int
    ) -> bool:
        """
        刪除導覽項目

        會同時刪除所有子項目。

        Args:
            db: 資料庫 session
            item_id: 項目 ID

        Returns:
            刪除是否成功
        """
        item = await self.get_item_by_id(db, item_id)
        if not item:
            return False

        # 遞迴刪除子項目
        await self._delete_children(db, item_id)

        # 刪除項目本身
        await db.delete(item)
        await db.commit()

        self.logger.info(f"刪除導覽項目: ID={item_id}")
        return True

    # =========================================================================
    # 輔助方法
    # =========================================================================

    async def _build_item_dict(
        self,
        db: AsyncSession,
        item: SiteNavigationItem,
        include_disabled: bool = False
    ) -> Dict[str, Any]:
        """
        將導覽項目轉換為字典格式（含子項目）
        """
        children = await self._get_children_recursive(db, item.id, include_disabled)

        return {
            "id": item.id,
            "title": item.title,
            "key": item.key,
            "path": item.path,
            "icon": item.icon,
            "parent_id": item.parent_id,
            "sort_order": item.sort_order,
            "is_visible": item.is_visible,
            "is_enabled": item.is_enabled,
            "level": getattr(item, 'level', 1),
            "description": getattr(item, 'description', None),
            "target": getattr(item, 'target', None),
            "permission_required": item.permission_required,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            "children": children
        }

    async def _get_children_recursive(
        self,
        db: AsyncSession,
        parent_id: int,
        include_disabled: bool = False
    ) -> List[Dict[str, Any]]:
        """
        遞迴取得子項目
        """
        children = await self.get_children(db, parent_id, include_disabled)
        result = []

        for child in children:
            child_dict = await self._build_item_dict(db, child, include_disabled)
            result.append(child_dict)

        return result

    async def _delete_children(
        self,
        db: AsyncSession,
        parent_id: int
    ) -> None:
        """
        遞迴刪除子項目
        """
        children = await self.get_children(db, parent_id, include_disabled=True)

        for child in children:
            await self._delete_children(db, child.id)
            await db.delete(child)

    def item_to_dict(self, item: SiteNavigationItem) -> Dict[str, Any]:
        """
        將導覽項目轉換為字典格式（不含子項目）
        """
        return {
            "id": item.id,
            "title": item.title,
            "key": item.key,
            "path": item.path,
            "icon": item.icon,
            "parent_id": item.parent_id,
            "sort_order": item.sort_order,
            "is_visible": item.is_visible,
            "is_enabled": item.is_enabled,
            "level": getattr(item, 'level', 1),
            "description": getattr(item, 'description', None),
            "target": getattr(item, 'target', None),
            "permission_required": item.permission_required,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None
        }


# 建立單例實例
navigation_service = NavigationService()

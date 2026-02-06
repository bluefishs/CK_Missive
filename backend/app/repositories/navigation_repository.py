"""
NavigationRepository - 導覽列資料存取層

提供 SiteNavigationItem 模型的 CRUD 操作。

版本: 1.0.0
建立日期: 2026-02-06
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.repositories.base_repository import BaseRepository
from app.extended.models import SiteNavigationItem

logger = logging.getLogger(__name__)


class NavigationRepository(BaseRepository[SiteNavigationItem]):
    """
    導覽列資料存取層

    提供導覽項目的樹狀結構查詢，包含：
    - 基礎 CRUD（繼承自 BaseRepository）
    - 根項目查詢（parent_id 為 None）
    - 子項目查詢（含遞迴）
    - 批次重排序
    - 子項目存在檢查

    Example:
        repo = NavigationRepository(db)
        root_items = await repo.get_root_items()
        tree = await repo.get_children_recursive(parent_id=1)
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, SiteNavigationItem)

    async def get_root_items(self) -> List[SiteNavigationItem]:
        """
        取得所有根層級導覽項目（parent_id 為 None），依 sort_order 排序

        Returns:
            根層級導覽項目列表
        """
        result = await self.db.execute(
            select(SiteNavigationItem)
            .filter(SiteNavigationItem.parent_id.is_(None))
            .order_by(SiteNavigationItem.sort_order)
        )
        return list(result.scalars().all())

    async def get_children(self, parent_id: int) -> List[SiteNavigationItem]:
        """
        取得指定父項目的直接子項目，依 sort_order 排序

        Args:
            parent_id: 父項目 ID

        Returns:
            子項目列表
        """
        result = await self.db.execute(
            select(SiteNavigationItem)
            .filter(SiteNavigationItem.parent_id == parent_id)
            .order_by(SiteNavigationItem.sort_order)
        )
        return list(result.scalars().all())

    async def get_children_recursive(
        self, parent_id: int, level: int = 2
    ) -> List[Dict[str, Any]]:
        """
        遞迴取得子項目樹狀結構

        Args:
            parent_id: 父項目 ID
            level: 目前遞迴層級（預設從第 2 層開始）

        Returns:
            子項目字典列表，每個項目包含 children 欄位
        """
        children = await self.get_children(parent_id)

        children_list = []
        for child in children:
            child_dict = {
                "id": child.id,
                "title": child.title,
                "key": child.key,
                "path": child.path,
                "icon": child.icon,
                "parent_id": child.parent_id,
                "sort_order": child.sort_order,
                "is_visible": child.is_visible,
                "is_enabled": child.is_enabled,
                "level": level,
                "description": child.description,
                "target": child.target,
                "permission_required": child.permission_required,
                "created_at": child.created_at.isoformat(),
                "updated_at": child.updated_at.isoformat(),
                "children": await self.get_children_recursive(child.id, level + 1),
            }
            children_list.append(child_dict)

        return children_list

    async def reorder_items(self, items: List[Dict[str, Any]]) -> int:
        """
        批次更新多個導覽項目的排序、父項目及層級

        Args:
            items: 項目字典列表，每個字典可包含 id, sort_order, parent_id, level

        Returns:
            成功更新的項目數量
        """
        updated_count = 0

        for item_data in items:
            item_id = item_data.get("id")
            if not item_id:
                continue

            item = await self.get_by_id(int(item_id))
            if not item:
                continue

            if "sort_order" in item_data and item_data["sort_order"] is not None:
                item.sort_order = int(item_data["sort_order"])
            if "parent_id" in item_data:
                item.parent_id = (
                    int(item_data["parent_id"])
                    if item_data["parent_id"] is not None
                    else None
                )
            if "level" in item_data and item_data["level"] is not None:
                item.level = int(item_data["level"])

            item.updated_at = datetime.utcnow()
            updated_count += 1

        await self.db.commit()

        self.logger.info(f"批次重排序導覽項目: {updated_count} 筆")
        return updated_count

    async def has_children(self, item_id: int) -> bool:
        """
        檢查指定項目是否有子項目

        Args:
            item_id: 項目 ID

        Returns:
            是否有子項目
        """
        result = await self.db.execute(
            select(func.count(SiteNavigationItem.id)).where(
                SiteNavigationItem.parent_id == item_id
            )
        )
        return (result.scalar() or 0) > 0

    async def get_siblings(
        self,
        parent_id: Optional[int],
        exclude_item_id: Optional[int] = None,
    ) -> List[SiteNavigationItem]:
        """
        取得同層級的項目（用於重排序），依 sort_order 排序

        Args:
            parent_id: 父項目 ID（None 表示根層級）
            exclude_item_id: 排除的項目 ID（可選）

        Returns:
            同層級項目列表
        """
        if parent_id is None:
            query = select(SiteNavigationItem).filter(
                SiteNavigationItem.parent_id.is_(None)
            )
        else:
            query = select(SiteNavigationItem).filter(
                SiteNavigationItem.parent_id == parent_id
            )

        if exclude_item_id is not None:
            query = query.filter(SiteNavigationItem.id != exclude_item_id)

        query = query.order_by(SiteNavigationItem.sort_order)
        result = await self.db.execute(query)
        return list(result.scalars().all())

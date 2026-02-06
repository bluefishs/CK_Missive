"""
ConfigurationRepository - 網站配置資料存取層

提供 SiteConfiguration 模型的 CRUD 操作。

版本: 1.1.0
建立日期: 2026-02-06
更新日期: 2026-02-06
更新內容: 新增 get_configs_filtered() 支援搜尋與分類篩選
"""

import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from app.repositories.base_repository import BaseRepository
from app.extended.models import SiteConfiguration

logger = logging.getLogger(__name__)


class ConfigurationRepository(BaseRepository[SiteConfiguration]):
    """
    網站配置資料存取層

    提供系統配置的 key-value 存取，包含：
    - 基礎 CRUD（繼承自 BaseRepository）
    - 依 key 取得/設定配置
    - 批次取得配置

    Example:
        repo = ConfigurationRepository(db)
        value = await repo.get_value("site_name")
        await repo.set_value("site_name", "乾坤公文管理系統")
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, SiteConfiguration)

    async def get_by_key(self, key: str) -> Optional[SiteConfiguration]:
        """根據 key 取得配置項"""
        result = await self.db.execute(
            select(SiteConfiguration).where(SiteConfiguration.key == key)
        )
        return result.scalar_one_or_none()

    async def get_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        取得配置值

        Args:
            key: 配置鍵
            default: 預設值

        Returns:
            配置值，或 default
        """
        config = await self.get_by_key(key)
        if config is None:
            return default
        return config.value

    async def set_value(self, key: str, value: str) -> SiteConfiguration:
        """
        設定配置值（不存在則建立）

        Args:
            key: 配置鍵
            value: 配置值

        Returns:
            更新後的配置項
        """
        config = await self.get_by_key(key)
        if config:
            config.value = value
        else:
            config = SiteConfiguration(key=key, value=value)
            self.db.add(config)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def get_all_configs(self) -> List[SiteConfiguration]:
        """取得所有配置項"""
        result = await self.db.execute(
            select(SiteConfiguration).order_by(SiteConfiguration.key)
        )
        return list(result.scalars().all())

    async def get_configs_dict(self) -> Dict[str, str]:
        """取得所有配置為字典格式"""
        configs = await self.get_all_configs()
        return {c.key: c.value for c in configs}

    async def get_configs_filtered(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[SiteConfiguration]:
        """
        根據搜尋條件和分類篩選配置項

        Args:
            search: 搜尋關鍵字（比對 key 和 description）
            category: 分類篩選

        Returns:
            符合條件的配置項列表，按 category 和 key 排序
        """
        filters = []

        if search:
            filters.append(
                or_(
                    SiteConfiguration.key.ilike(f"%{search}%"),
                    SiteConfiguration.description.ilike(f"%{search}%"),
                )
            )

        if category:
            filters.append(SiteConfiguration.category == category)

        query = select(SiteConfiguration)
        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(SiteConfiguration.category, SiteConfiguration.key)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_by_key(self, key: str) -> bool:
        """
        根據 key 刪除配置項

        Returns:
            是否成功刪除
        """
        config = await self.get_by_key(key)
        if config is None:
            return False
        await self.db.delete(config)
        await self.db.commit()
        return True

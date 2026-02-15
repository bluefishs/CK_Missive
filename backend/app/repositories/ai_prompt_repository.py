"""
AIPromptRepository - AI Prompt 版本資料存取層

提供 AIPromptVersion 模型的 CRUD 操作和版本管理查詢。

版本: 1.0.0
建立日期: 2026-02-11
"""

import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.repositories.base_repository import BaseRepository
from app.extended.models import AIPromptVersion

logger = logging.getLogger(__name__)


class AIPromptRepository(BaseRepository[AIPromptVersion]):
    """
    AI Prompt 版本資料存取層

    提供 Prompt 版本的資料庫操作，包含：
    - 基礎 CRUD（繼承自 BaseRepository）
    - 依 feature 篩選列表
    - 計算新版本號
    - 停用/啟用版本管理

    Example:
        repo = AIPromptRepository(db)
        versions = await repo.list_by_feature("summary")
        next_ver = await repo.get_next_version("summary")
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, AIPromptVersion)

    async def list_by_feature(
        self,
        feature: Optional[str] = None,
    ) -> List[AIPromptVersion]:
        """
        列出 Prompt 版本（支援 feature 篩選）

        Args:
            feature: 功能名稱篩選

        Returns:
            Prompt 版本列表（依 feature + version desc 排序）
        """
        query = select(AIPromptVersion).order_by(
            AIPromptVersion.feature,
            AIPromptVersion.version.desc(),
        )

        if feature:
            query = query.where(AIPromptVersion.feature == feature)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_next_version(self, feature: str) -> int:
        """
        取得指定 feature 的下一個版本號

        Args:
            feature: 功能名稱

        Returns:
            下一個版本號（最大版本號 + 1）
        """
        query = (
            select(AIPromptVersion.version)
            .where(AIPromptVersion.feature == feature)
            .order_by(AIPromptVersion.version.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        max_version = result.scalar()
        return (max_version or 0) + 1

    async def deactivate_feature(self, feature: str) -> int:
        """
        停用指定 feature 的所有版本

        Args:
            feature: 功能名稱

        Returns:
            受影響的列數
        """
        stmt = (
            update(AIPromptVersion)
            .where(AIPromptVersion.feature == feature)
            .values(is_active=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def activate_version(self, version_id: int) -> Optional[AIPromptVersion]:
        """
        啟用指定版本（自動停用同 feature 的其他版本）

        Args:
            version_id: 要啟用的版本 ID

        Returns:
            啟用後的版本物件，若不存在則返回 None
        """
        target = await self.db.get(AIPromptVersion, version_id)
        if not target:
            return None

        # 停用同 feature 的所有版本
        await self.deactivate_feature(target.feature)

        # 啟用目標版本
        target.is_active = True
        await self.db.commit()
        await self.db.refresh(target)

        return target

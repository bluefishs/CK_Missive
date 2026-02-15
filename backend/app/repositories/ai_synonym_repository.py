"""
AISynonymRepository - AI 同義詞資料存取層

提供 AISynonym 模型的 CRUD 操作和分類查詢。

版本: 1.0.0
建立日期: 2026-02-11
"""

import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct

from app.repositories.base_repository import BaseRepository
from app.extended.models import AISynonym

logger = logging.getLogger(__name__)


class AISynonymRepository(BaseRepository[AISynonym]):
    """
    AI 同義詞資料存取層

    提供同義詞群組的資料庫操作，包含：
    - 基礎 CRUD（繼承自 BaseRepository）
    - 依分類和啟用狀態篩選
    - 取得所有分類列表
    - 取得所有啟用的同義詞（供 hot reload）

    Example:
        repo = AISynonymRepository(db)
        synonyms = await repo.list_filtered(category="機關")
        categories = await repo.get_all_categories()
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, AISynonym)

    async def list_filtered(
        self,
        *,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[AISynonym]:
        """
        列出同義詞群組（支援篩選）

        Args:
            category: 分類篩選
            is_active: 啟用狀態篩選

        Returns:
            符合條件的同義詞列表
        """
        query = select(AISynonym)

        if category:
            query = query.where(AISynonym.category == category)

        if is_active is not None:
            query = query.where(AISynonym.is_active == is_active)

        query = query.order_by(AISynonym.category, AISynonym.id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_all_categories(self) -> List[str]:
        """
        取得所有分類名稱（去重排序）

        Returns:
            分類名稱列表
        """
        query = select(distinct(AISynonym.category)).order_by(AISynonym.category)
        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall()]

    async def get_active_synonyms(self) -> List[AISynonym]:
        """
        取得所有啟用的同義詞群組

        供 AIPromptManager.reload_synonyms_from_db() 使用。

        Returns:
            啟用的同義詞列表
        """
        query = (
            select(AISynonym)
            .where(AISynonym.is_active == True)  # noqa: E712
            .order_by(AISynonym.category)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

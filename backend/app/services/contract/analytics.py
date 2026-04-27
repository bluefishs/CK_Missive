"""
承攬案件分析服務 — 統計與選項查詢

從 project_service.py 拆分，負責非 CRUD 操作：
  - 專案統計
  - 選項查詢（下拉選單用）

Version: 1.0.0 (拆分自 ProjectService v4.0.0)
"""
import logging
from typing import List, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import ProjectRepository

logger = logging.getLogger(__name__)


class ProjectAnalyticsService:
    """承攬案件分析服務 — 統計與選項"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = ProjectRepository(db)

    # =========================================================================
    # 統計
    # =========================================================================

    async def get_project_statistics(self) -> dict:
        """取得專案統計資料"""
        try:
            return await self.repository.get_project_statistics()
        except Exception as e:
            logger.error(f"取得專案統計資料失敗: {e}", exc_info=True)
            return {
                "total_projects": 0,
                "status_breakdown": [],
                "year_breakdown": [],
                "average_contract_amount": 0.0,
            }

    # =========================================================================
    # 選項查詢方法 (下拉選單用)
    # =========================================================================

    async def get_distinct_options(
        self,
        field_name: str,
        sort_order: str = "asc",
        exclude_null: bool = True,
    ) -> List[Any]:
        """
        取得欄位的去重值（用於下拉選單選項）

        Args:
            field_name: 欄位名稱
            sort_order: 排序方向 ('asc' 或 'desc')
            exclude_null: 是否排除 NULL 值（預設 True）

        Returns:
            去重後的值列表
        """
        if sort_order.lower() == "desc" and field_name == "year":
            return await self.repository.get_year_options()
        return await self.repository.get_distinct_values(
            field_name, exclude_null=exclude_null
        )

    async def get_year_options(self) -> List[int]:
        """取得所有專案年度選項（降序排列）"""
        return await self.repository.get_year_options()

    async def get_category_options(self) -> List[str]:
        """取得所有專案類別選項（升序排列）"""
        return await self.repository.get_category_options()

    async def get_status_options(self) -> List[str]:
        """取得所有專案狀態選項（升序排列）"""
        return await self.repository.get_status_options()

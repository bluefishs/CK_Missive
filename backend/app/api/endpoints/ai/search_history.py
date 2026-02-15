"""
AI 搜尋歷史 API 端點

Version: 2.0.0
Created: 2026-02-09
Updated: 2026-02-11 - 遷移至 Repository 層

端點:
- POST /search-history/list   - 搜尋歷史列表（分頁、篩選）
- POST /search-history/stats  - 搜尋統計資訊
- POST /search-history/clear  - 清除搜尋歷史
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin, get_async_db
from app.extended.models import User
from app.repositories import AISearchHistoryRepository
from app.schemas.ai import (
    SearchHistoryListRequest,
    SearchHistoryListResponse,
    SearchStatsResponse,
    ClearSearchHistoryRequest,
    ClearSearchHistoryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search-history/list", response_model=SearchHistoryListResponse)
async def list_search_history(
    request: SearchHistoryListRequest,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    取得搜尋歷史列表

    支援分頁、日期範圍、搜尋策略、來源篩選、關鍵字模糊搜尋。
    需要管理員權限。
    """
    repo = AISearchHistoryRepository(db)
    items, total = await repo.list_with_user(
        page=request.page,
        page_size=request.page_size,
        date_from=request.date_from,
        date_to=request.date_to,
        search_strategy=request.search_strategy,
        source=request.source,
        keyword=request.keyword,
    )

    return SearchHistoryListResponse(
        items=items,
        total=total,
        page=request.page,
        page_size=request.page_size,
    )


@router.post("/search-history/stats", response_model=SearchStatsResponse)
async def get_search_stats(
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    取得搜尋統計資訊

    包含總搜尋次數、今日搜尋次數、規則引擎命中率、平均回應時間、
    平均信心度、每日趨勢、熱門查詢、策略/來源/實體分佈。
    需要管理員權限。
    """
    repo = AISearchHistoryRepository(db)
    stats = await repo.get_stats()

    return SearchStatsResponse(**stats)


@router.post("/search-history/clear", response_model=ClearSearchHistoryResponse)
async def clear_search_history(
    request: ClearSearchHistoryRequest,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    清除搜尋歷史

    可選擇清除指定日期前的記錄，或清除全部。
    需要管理員權限。
    """
    repo = AISearchHistoryRepository(db)

    try:
        deleted_count = await repo.clear_before_date(request.before_date)
    except ValueError as e:
        return ClearSearchHistoryResponse(
            success=False, deleted_count=0, error=str(e)
        )

    logger.info(
        f"搜尋歷史清除完成: 管理員 {current_user.full_name} (id={current_user.id}) "
        f"刪除 {deleted_count} 筆記錄 (before_date={request.before_date})"
    )

    return ClearSearchHistoryResponse(success=True, deleted_count=deleted_count)

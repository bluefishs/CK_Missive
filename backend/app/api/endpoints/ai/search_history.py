"""
AI 搜尋歷史 API 端點

Version: 1.2.0
Created: 2026-02-09
Updated: 2026-02-09 - 修復 AsyncSession 並行安全性（改循序執行）

端點:
- POST /search-history/list   - 搜尋歷史列表（分頁、篩選）
- POST /search-history/stats  - 搜尋統計資訊
- POST /search-history/clear  - 清除搜尋歷史
"""

import logging
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc, cast, Date, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin, get_async_db
from app.extended.models import AISearchHistory, User
from app.schemas.ai import (
    SearchHistoryItem,
    SearchHistoryListRequest,
    SearchHistoryListResponse,
    SearchStatsResponse,
    ClearSearchHistoryRequest,
    ClearSearchHistoryResponse,
    DailyTrend,
    TopQuery,
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
    # 基礎查詢：LEFT JOIN users 取得 user_name
    query = (
        select(
            AISearchHistory,
            User.full_name.label("user_name"),
        )
        .outerjoin(User, AISearchHistory.user_id == User.id)
    )

    count_query = select(func.count(AISearchHistory.id))

    # 篩選條件
    if request.date_from:
        try:
            date_from = datetime.strptime(request.date_from, "%Y-%m-%d")
            query = query.where(AISearchHistory.created_at >= date_from)
            count_query = count_query.where(AISearchHistory.created_at >= date_from)
        except ValueError:
            pass

    if request.date_to:
        try:
            date_to = datetime.strptime(request.date_to, "%Y-%m-%d")
            # 包含結束日期當天
            date_to = date_to.replace(hour=23, minute=59, second=59)
            query = query.where(AISearchHistory.created_at <= date_to)
            count_query = count_query.where(AISearchHistory.created_at <= date_to)
        except ValueError:
            pass

    if request.search_strategy:
        query = query.where(AISearchHistory.search_strategy == request.search_strategy)
        count_query = count_query.where(AISearchHistory.search_strategy == request.search_strategy)

    if request.source:
        query = query.where(AISearchHistory.source == request.source)
        count_query = count_query.where(AISearchHistory.source == request.source)

    if request.keyword:
        # 跳脫 LIKE 萬用字元，避免使用者輸入 % 或 _ 干擾查詢
        safe_keyword = request.keyword.replace("%", r"\%").replace("_", r"\_")
        keyword_filter = AISearchHistory.query.ilike(f"%{safe_keyword}%")
        query = query.where(keyword_filter)
        count_query = count_query.where(keyword_filter)

    # 取得總數
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 排序與分頁
    offset = (request.page - 1) * request.page_size
    query = query.order_by(desc(AISearchHistory.created_at)).offset(offset).limit(request.page_size)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        history = row[0]  # AISearchHistory instance
        user_name = row[1]  # user_name from JOIN
        items.append(
            SearchHistoryItem(
                id=history.id,
                user_id=history.user_id,
                user_name=user_name,
                query=history.query,
                parsed_intent=history.parsed_intent,
                results_count=history.results_count,
                search_strategy=history.search_strategy,
                source=history.source,
                synonym_expanded=history.synonym_expanded,
                related_entity=history.related_entity,
                latency_ms=history.latency_ms,
                confidence=history.confidence,
                created_at=history.created_at,
            )
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

    使用 asyncio.gather 並行執行獨立查詢以降低回應時間。
    """
    today_date = date.today()
    thirty_days_ago = today_date - timedelta(days=30)

    # 循序執行查詢（AsyncSession 不支援 asyncio.gather 並行操作同一 session）
    # 1. 總搜尋次數
    total_result = await db.execute(select(func.count(AISearchHistory.id)))
    # 2. 今日搜尋次數
    today_result = await db.execute(
        select(func.count(AISearchHistory.id))
        .where(cast(AISearchHistory.created_at, Date) == today_date)
    )
    # 3. 規則引擎命中次數
    rule_engine_result = await db.execute(
        select(func.count(AISearchHistory.id))
        .where(AISearchHistory.source.in_(["rule_engine", "merged"]))
    )
    # 4. 平均回應時間
    avg_latency_result = await db.execute(
        select(func.avg(AISearchHistory.latency_ms))
        .where(AISearchHistory.latency_ms.isnot(None))
    )
    # 5. 平均信心度
    avg_confidence_result = await db.execute(
        select(func.avg(AISearchHistory.confidence))
        .where(AISearchHistory.confidence.isnot(None))
    )
    # 6. 近 30 天每日搜尋量
    daily_trend_result = await db.execute(
        select(
            cast(AISearchHistory.created_at, Date).label("search_date"),
            func.count(AISearchHistory.id).label("count"),
        )
        .where(cast(AISearchHistory.created_at, Date) >= thirty_days_ago)
        .group_by(cast(AISearchHistory.created_at, Date))
        .order_by(cast(AISearchHistory.created_at, Date))
    )
    # 7. 熱門查詢 Top 10
    top_queries_result = await db.execute(
        select(
            AISearchHistory.query,
            func.count(AISearchHistory.id).label("count"),
            func.avg(AISearchHistory.results_count).label("avg_results"),
        )
        .group_by(AISearchHistory.query)
        .order_by(desc("count"))
        .limit(10)
    )
    # 8. 搜尋策略分佈
    strategy_result = await db.execute(
        select(
            AISearchHistory.search_strategy,
            func.count(AISearchHistory.id).label("count"),
        )
        .where(AISearchHistory.search_strategy.isnot(None))
        .group_by(AISearchHistory.search_strategy)
    )
    # 9. 來源分佈
    source_result = await db.execute(
        select(
            AISearchHistory.source,
            func.count(AISearchHistory.id).label("count"),
        )
        .where(AISearchHistory.source.isnot(None))
        .group_by(AISearchHistory.source)
    )
    # 10. 實體分佈
    entity_result = await db.execute(
        select(
            AISearchHistory.related_entity,
            func.count(AISearchHistory.id).label("count"),
        )
        .where(AISearchHistory.related_entity.isnot(None))
        .group_by(AISearchHistory.related_entity)
    )

    # 解析結果
    total_searches = total_result.scalar() or 0
    today_searches = today_result.scalar() or 0
    rule_engine_count = rule_engine_result.scalar() or 0
    rule_engine_hit_rate = (rule_engine_count / total_searches) if total_searches > 0 else 0.0
    avg_latency_ms = avg_latency_result.scalar() or 0.0
    avg_confidence = avg_confidence_result.scalar() or 0.0

    daily_trend = [
        DailyTrend(date=str(row.search_date), count=row.count)
        for row in daily_trend_result.all()
    ]
    top_queries = [
        TopQuery(query=row.query, count=row.count, avg_results=round(float(row.avg_results or 0), 1))
        for row in top_queries_result.all()
    ]
    strategy_distribution = {row.search_strategy: row.count for row in strategy_result.all()}
    source_distribution = {row.source: row.count for row in source_result.all()}
    entity_distribution = {row.related_entity: row.count for row in entity_result.all()}

    return SearchStatsResponse(
        total_searches=total_searches,
        today_searches=today_searches,
        rule_engine_hit_rate=round(rule_engine_hit_rate, 4),
        avg_latency_ms=round(float(avg_latency_ms), 1),
        avg_confidence=round(float(avg_confidence), 4),
        daily_trend=daily_trend,
        top_queries=top_queries,
        strategy_distribution=strategy_distribution,
        source_distribution=source_distribution,
        entity_distribution=entity_distribution,
    )


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
    stmt = delete(AISearchHistory)

    if request.before_date:
        try:
            cutoff = datetime.strptime(request.before_date, "%Y-%m-%d")
            cutoff = cutoff.replace(hour=23, minute=59, second=59)
            stmt = stmt.where(AISearchHistory.created_at <= cutoff)
        except ValueError:
            return ClearSearchHistoryResponse(
                success=False, deleted_count=0, error="日期格式無效，請使用 YYYY-MM-DD"
            )

    result = await db.execute(stmt)
    await db.commit()
    deleted_count = result.rowcount

    logger.info(
        f"搜尋歷史清除完成: 管理員 {current_user.full_name} (id={current_user.id}) "
        f"刪除 {deleted_count} 筆記錄 (before_date={request.before_date})"
    )

    return ClearSearchHistoryResponse(success=True, deleted_count=deleted_count)

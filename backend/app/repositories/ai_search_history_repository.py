"""
AISearchHistoryRepository - AI 搜尋歷史資料存取層

提供 AISearchHistory 模型的查詢、統計和清理操作。

版本: 1.0.0
建立日期: 2026-02-11
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, cast, Date, delete

from app.repositories.base_repository import BaseRepository
from app.extended.models import AISearchHistory, User
from app.schemas.ai import (
    SearchHistoryItem,
    DailyTrend,
    TopQuery,
)

logger = logging.getLogger(__name__)


class AISearchHistoryRepository(BaseRepository[AISearchHistory]):
    """
    AI 搜尋歷史資料存取層

    提供搜尋歷史的資料庫操作，包含：
    - 分頁列表（含 JOIN 使用者資訊）
    - 統計查詢（日趨勢、熱門查詢、策略/來源/實體分佈）
    - 條件清除

    注意：此 Repository 的查詢必須循序執行（同一 AsyncSession
    不支援 asyncio.gather 並行操作）。

    Example:
        repo = AISearchHistoryRepository(db)
        items, total = await repo.list_with_user(page=1, page_size=20)
        stats = await repo.get_stats()
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, AISearchHistory)

    async def list_with_user(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search_strategy: Optional[str] = None,
        source: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> Tuple[List[SearchHistoryItem], int]:
        """
        取得搜尋歷史列表（含使用者名稱 JOIN）

        Args:
            page: 頁碼
            page_size: 每頁筆數
            date_from: 起始日期 (YYYY-MM-DD)
            date_to: 結束日期 (YYYY-MM-DD)
            search_strategy: 搜尋策略篩選
            source: 來源篩選
            keyword: 關鍵字模糊搜尋

        Returns:
            (items, total) 元組
        """
        # 基礎查詢：LEFT JOIN users
        query = (
            select(AISearchHistory, User.full_name.label("user_name"))
            .outerjoin(User, AISearchHistory.user_id == User.id)
        )
        count_query = select(func.count(AISearchHistory.id))

        # 篩選條件
        if date_from:
            try:
                dt_from = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.where(AISearchHistory.created_at >= dt_from)
                count_query = count_query.where(AISearchHistory.created_at >= dt_from)
            except ValueError:
                pass

        if date_to:
            try:
                dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59
                )
                query = query.where(AISearchHistory.created_at <= dt_to)
                count_query = count_query.where(AISearchHistory.created_at <= dt_to)
            except ValueError:
                pass

        if search_strategy:
            query = query.where(AISearchHistory.search_strategy == search_strategy)
            count_query = count_query.where(AISearchHistory.search_strategy == search_strategy)

        if source:
            query = query.where(AISearchHistory.source == source)
            count_query = count_query.where(AISearchHistory.source == source)

        if keyword:
            safe_keyword = keyword.replace("%", r"\%").replace("_", r"\_")
            keyword_filter = AISearchHistory.query.ilike(f"%{safe_keyword}%")
            query = query.where(keyword_filter)
            count_query = count_query.where(keyword_filter)

        # 總數
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 分頁
        offset = (page - 1) * page_size
        query = query.order_by(desc(AISearchHistory.created_at)).offset(offset).limit(page_size)

        result = await self.db.execute(query)
        rows = result.all()

        items = []
        for row in rows:
            history = row[0]
            user_name = row[1]
            items.append(SearchHistoryItem(
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
            ))

        return items, total

    async def get_stats(self) -> Dict[str, Any]:
        """
        取得搜尋統計資訊

        包含：總搜尋次數、今日搜尋、規則引擎命中率、
        平均回應時間、平均信心度、日趨勢、熱門查詢、
        策略/來源/實體分佈。

        注意：所有查詢循序執行（AsyncSession 限制）。

        Returns:
            統計資料字典
        """
        today_date = date.today()
        thirty_days_ago = today_date - timedelta(days=30)

        # 1. 總搜尋次數
        total_result = await self.db.execute(select(func.count(AISearchHistory.id)))
        total_searches = total_result.scalar() or 0

        # 2. 今日搜尋次數
        today_result = await self.db.execute(
            select(func.count(AISearchHistory.id))
            .where(cast(AISearchHistory.created_at, Date) == today_date)
        )
        today_searches = today_result.scalar() or 0

        # 3. 規則引擎命中次數
        rule_engine_result = await self.db.execute(
            select(func.count(AISearchHistory.id))
            .where(AISearchHistory.source.in_(["rule_engine", "merged"]))
        )
        rule_engine_count = rule_engine_result.scalar() or 0
        rule_engine_hit_rate = (rule_engine_count / total_searches) if total_searches > 0 else 0.0

        # 4. 平均回應時間
        avg_latency_result = await self.db.execute(
            select(func.avg(AISearchHistory.latency_ms))
            .where(AISearchHistory.latency_ms.isnot(None))
        )
        avg_latency_ms = avg_latency_result.scalar() or 0.0

        # 5. 平均信心度
        avg_confidence_result = await self.db.execute(
            select(func.avg(AISearchHistory.confidence))
            .where(AISearchHistory.confidence.isnot(None))
        )
        avg_confidence = avg_confidence_result.scalar() or 0.0

        # 6. 近 30 天每日搜尋量
        daily_trend_result = await self.db.execute(
            select(
                cast(AISearchHistory.created_at, Date).label("search_date"),
                func.count(AISearchHistory.id).label("count"),
            )
            .where(cast(AISearchHistory.created_at, Date) >= thirty_days_ago)
            .group_by(cast(AISearchHistory.created_at, Date))
            .order_by(cast(AISearchHistory.created_at, Date))
        )
        daily_trend = [
            DailyTrend(date=str(row.search_date), count=row.count)
            for row in daily_trend_result.all()
        ]

        # 7. 熱門查詢 Top 10
        top_queries_result = await self.db.execute(
            select(
                AISearchHistory.query,
                func.count(AISearchHistory.id).label("count"),
                func.avg(AISearchHistory.results_count).label("avg_results"),
            )
            .group_by(AISearchHistory.query)
            .order_by(desc("count"))
            .limit(10)
        )
        top_queries = [
            TopQuery(
                query=row.query,
                count=row.count,
                avg_results=round(float(row.avg_results or 0), 1),
            )
            for row in top_queries_result.all()
        ]

        # 8. 搜尋策略分佈
        strategy_result = await self.db.execute(
            select(
                AISearchHistory.search_strategy,
                func.count(AISearchHistory.id).label("count"),
            )
            .where(AISearchHistory.search_strategy.isnot(None))
            .group_by(AISearchHistory.search_strategy)
        )
        strategy_distribution = {row.search_strategy: row.count for row in strategy_result.all()}

        # 9. 來源分佈
        source_result = await self.db.execute(
            select(
                AISearchHistory.source,
                func.count(AISearchHistory.id).label("count"),
            )
            .where(AISearchHistory.source.isnot(None))
            .group_by(AISearchHistory.source)
        )
        source_distribution = {row.source: row.count for row in source_result.all()}

        # 10. 實體分佈
        entity_result = await self.db.execute(
            select(
                AISearchHistory.related_entity,
                func.count(AISearchHistory.id).label("count"),
            )
            .where(AISearchHistory.related_entity.isnot(None))
            .group_by(AISearchHistory.related_entity)
        )
        entity_distribution = {row.related_entity: row.count for row in entity_result.all()}

        return {
            "total_searches": total_searches,
            "today_searches": today_searches,
            "rule_engine_hit_rate": round(rule_engine_hit_rate, 4),
            "avg_latency_ms": round(float(avg_latency_ms), 1),
            "avg_confidence": round(float(avg_confidence), 4),
            "daily_trend": daily_trend,
            "top_queries": top_queries,
            "strategy_distribution": strategy_distribution,
            "source_distribution": source_distribution,
            "entity_distribution": entity_distribution,
        }

    async def clear_before_date(self, before_date: Optional[str] = None) -> int:
        """
        清除搜尋歷史

        Args:
            before_date: 清除此日期前的記錄 (YYYY-MM-DD)，
                         None 則清除全部

        Returns:
            刪除的筆數

        Raises:
            ValueError: 日期格式無效
        """
        stmt = delete(AISearchHistory)

        if before_date:
            try:
                cutoff = datetime.strptime(before_date, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59
                )
                stmt = stmt.where(AISearchHistory.created_at <= cutoff)
            except ValueError:
                raise ValueError("日期格式無效，請使用 YYYY-MM-DD")

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

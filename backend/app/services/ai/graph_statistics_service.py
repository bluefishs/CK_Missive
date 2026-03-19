"""
圖譜統計服務

從 graph_query_service.py 提取的統計相關方法：
- get_timeline_aggregate
- get_top_entities
- get_graph_stats

Version: 1.0.0
Created: 2026-03-15
"""

import json
import logging
from typing import Optional

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    CanonicalEntity,
    EntityRelationship,
)
from .ai_config import get_ai_config
from .graph_helpers import _graph_cache, _CODE_ENTITY_TYPES

logger = logging.getLogger(__name__)


class GraphStatisticsService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self._config = get_ai_config()

    async def get_timeline_aggregate(
        self,
        relation_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        granularity: str = "month",
    ) -> dict:
        """
        跨實體時序聚合：按月/季/年統計關係數量趨勢。

        Returns: { granularity, buckets: [...], total_relationships }
        """
        try:
            trunc_map = {"month": "month", "quarter": "quarter", "year": "year"}
            trunc_unit = trunc_map.get(granularity, "month")

            filters = [
                EntityRelationship.valid_from.isnot(None),
                CanonicalEntity.entity_type.notin_(_CODE_ENTITY_TYPES),
            ]
            if relation_type:
                filters.append(EntityRelationship.relation_type == relation_type)

            if entity_type:
                filters.append(CanonicalEntity.entity_type == entity_type)

            period_col = sa_func.date_trunc(
                trunc_unit, EntityRelationship.valid_from
            ).label("period")

            stmt = (
                select(
                    period_col,
                    sa_func.count().label("cnt"),
                    sa_func.coalesce(sa_func.sum(EntityRelationship.weight), 0).label("total_weight"),
                    sa_func.count(sa_func.distinct(EntityRelationship.source_entity_id)).label("entity_count"),
                )
                .join(
                    CanonicalEntity,
                    CanonicalEntity.id == EntityRelationship.source_entity_id,
                )
                .where(*filters)
                .group_by(period_col)
                .order_by(period_col)
            )

            result = await self.db.execute(stmt)
            rows = result.all()

            buckets = []
            total = 0
            for row in rows:
                period_str = row.period.strftime("%Y-%m") if granularity == "month" else (
                    f"{row.period.year}-Q{(row.period.month - 1) // 3 + 1}" if granularity == "quarter"
                    else str(row.period.year)
                )
                buckets.append({
                    "period": period_str,
                    "count": row.cnt,
                    "total_weight": float(row.total_weight),
                    "entity_count": row.entity_count,
                })
                total += row.cnt

            return {
                "granularity": granularity,
                "buckets": buckets,
                "total_relationships": total,
            }
        except Exception as e:
            logger.error(f"get_timeline_aggregate failed: {e}")
            return {"granularity": granularity, "buckets": [], "total_relationships": 0}

    async def get_top_entities(
        self,
        entity_type: Optional[str] = None,
        sort_by: str = "mention_count",
        limit: int = 20,
        include_code: bool = False,
    ) -> list:
        """高頻實體排名（預設排除程式碼圖譜實體）"""
        try:
            query = select(CanonicalEntity)

            if entity_type:
                query = query.where(CanonicalEntity.entity_type == entity_type)
            elif not include_code:
                query = query.where(CanonicalEntity.entity_type.notin_(_CODE_ENTITY_TYPES))

            if sort_by == "alias_count":
                query = query.order_by(CanonicalEntity.alias_count.desc().nullslast())
            else:
                query = query.order_by(CanonicalEntity.mention_count.desc().nullslast())

            query = query.limit(limit)
            result = await self.db.execute(query)

            return [
                {
                    "id": e.id,
                    "canonical_name": e.canonical_name,
                    "entity_type": e.entity_type,
                    "mention_count": e.mention_count,
                    "alias_count": e.alias_count,
                    "first_seen_at": str(e.first_seen_at) if e.first_seen_at else None,
                    "last_seen_at": str(e.last_seen_at) if e.last_seen_at else None,
                }
                for e in result.scalars().all()
            ]
        except Exception as e:
            logger.error(f"get_top_entities failed: {e}")
            return []

    async def get_graph_stats(self) -> dict:
        """圖譜統計，帶 Redis 快取（TTL 30 分鐘）"""
        try:
            cache_key = "stats:global"
            cached = await _graph_cache.get(cache_key)
            if cached:
                return json.loads(cached)

            from .canonical_entity_service import CanonicalEntityService
            svc = CanonicalEntityService(self.db)
            result = await svc.get_stats()
            await _graph_cache.set(
                cache_key, json.dumps(result, ensure_ascii=False),
                self._config.graph_cache_ttl_stats,
            )
            return result
        except Exception as e:
            logger.error(f"get_graph_stats failed: {e}")
            return {}

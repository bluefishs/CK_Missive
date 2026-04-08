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

    async def get_federation_health(self) -> dict:
        """跨專案 KG 聯邦同步健康指標（30 分鐘快取）"""
        try:
            cache_key = "stats:federation_health"
            cached = await _graph_cache.get(cache_key)
            if cached:
                return json.loads(cached)

            # 各 source_project 的實體數量
            dist_result = await self.db.execute(
                select(
                    sa_func.coalesce(
                        CanonicalEntity.source_project, "ck-missive"
                    ).label("project"),
                    sa_func.count().label("count"),
                    sa_func.max(CanonicalEntity.updated_at).label("last_updated"),
                )
                .where(CanonicalEntity.entity_type.notin_(_CODE_ENTITY_TYPES))
                .group_by(
                    sa_func.coalesce(CanonicalEntity.source_project, "ck-missive")
                )
            )
            projects = []
            for row in dist_result.all():
                projects.append({
                    "source_project": row.project,
                    "entity_count": row.count,
                    "last_updated": str(row.last_updated) if row.last_updated else None,
                })

            # 跨專案關係數量
            cross_project_rels = await self.db.scalar(
                select(sa_func.count()).select_from(EntityRelationship)
                .where(
                    EntityRelationship.invalidated_at.is_(None),
                    EntityRelationship.source_project.isnot(None),
                    EntityRelationship.source_project != "ck-missive",
                )
            ) or 0

            # Embedding 覆蓋率 (per source_project)
            embedding_coverage = {}
            if hasattr(CanonicalEntity, "embedding"):
                emb_result = await self.db.execute(
                    select(
                        sa_func.coalesce(
                            CanonicalEntity.source_project, "ck-missive"
                        ).label("project"),
                        sa_func.count().label("total"),
                        sa_func.count(CanonicalEntity.embedding).label("with_embedding"),
                    )
                    .where(CanonicalEntity.entity_type.notin_(_CODE_ENTITY_TYPES))
                    .group_by(
                        sa_func.coalesce(CanonicalEntity.source_project, "ck-missive")
                    )
                )
                for row in emb_result.all():
                    pct = round(row.with_embedding / row.total * 100, 1) if row.total else 0
                    embedding_coverage[row.project] = {
                        "total": row.total,
                        "with_embedding": row.with_embedding,
                        "coverage_pct": pct,
                    }

            result = {
                "projects": projects,
                "cross_project_relations": cross_project_rels,
                "total_projects": len(projects),
                "embedding_coverage": embedding_coverage,
            }
            await _graph_cache.set(cache_key, json.dumps(result, default=str), ex=1800)
            return result
        except Exception as e:
            logger.error(f"get_federation_health failed: {e}")
            return {"projects": [], "cross_project_relations": 0, "total_projects": 0}

    async def centrality_analysis(self, top_n: int = 20) -> dict:
        """
        God Node 中心性分析：找出度數最高的樞紐實體及耦合風險。

        Uses pure SQL degree centrality (no NetworkX dependency).

        Returns:
            {
                "top_hubs": [...],
                "total_entities": int,
                "total_relationships": int,
                "avg_degree": float,
                "coupling_risk": [entities with degree > 2*avg],
            }
        """
        try:
            from sqlalchemy import literal_column, union_all, text

            # Count out-degree per entity
            out_deg = (
                select(
                    EntityRelationship.source_entity_id.label("entity_id"),
                    sa_func.count().label("cnt"),
                )
                .where(EntityRelationship.invalidated_at.is_(None))
                .group_by(EntityRelationship.source_entity_id)
            ).subquery("out_deg")

            # Count in-degree per entity
            in_deg = (
                select(
                    EntityRelationship.target_entity_id.label("entity_id"),
                    sa_func.count().label("cnt"),
                )
                .where(EntityRelationship.invalidated_at.is_(None))
                .group_by(EntityRelationship.target_entity_id)
            ).subquery("in_deg")

            # Join with CanonicalEntity to get name/type, compute total degree
            stmt = (
                select(
                    CanonicalEntity.id,
                    CanonicalEntity.canonical_name,
                    CanonicalEntity.entity_type,
                    sa_func.coalesce(in_deg.c.cnt, 0).label("in_degree"),
                    sa_func.coalesce(out_deg.c.cnt, 0).label("out_degree"),
                    (
                        sa_func.coalesce(in_deg.c.cnt, 0)
                        + sa_func.coalesce(out_deg.c.cnt, 0)
                    ).label("degree"),
                )
                .outerjoin(in_deg, CanonicalEntity.id == in_deg.c.entity_id)
                .outerjoin(out_deg, CanonicalEntity.id == out_deg.c.entity_id)
                .where(
                    (sa_func.coalesce(in_deg.c.cnt, 0) + sa_func.coalesce(out_deg.c.cnt, 0)) > 0
                )
                .where(CanonicalEntity.entity_type.notin_(_CODE_ENTITY_TYPES))
                .order_by(
                    (
                        sa_func.coalesce(in_deg.c.cnt, 0)
                        + sa_func.coalesce(out_deg.c.cnt, 0)
                    ).desc()
                )
            )

            result = await self.db.execute(stmt)
            all_rows = result.all()

            total_entities = len(all_rows)
            total_degree_sum = sum(r.degree for r in all_rows)
            avg_degree = round(total_degree_sum / total_entities, 2) if total_entities else 0.0

            # Total relationships (non-invalidated, excluding code graph)
            total_rels = await self.db.scalar(
                select(sa_func.count())
                .select_from(EntityRelationship)
                .where(EntityRelationship.invalidated_at.is_(None))
            ) or 0

            top_hubs = [
                {
                    "entity_id": r.id,
                    "name": r.canonical_name,
                    "type": r.entity_type,
                    "degree": r.degree,
                    "in_degree": r.in_degree,
                    "out_degree": r.out_degree,
                }
                for r in all_rows[:top_n]
            ]

            coupling_threshold = 2 * avg_degree if avg_degree > 0 else 1
            coupling_risk = [
                {
                    "entity_id": r.id,
                    "name": r.canonical_name,
                    "type": r.entity_type,
                    "degree": r.degree,
                }
                for r in all_rows
                if r.degree > coupling_threshold
            ]

            return {
                "top_hubs": top_hubs,
                "total_entities": total_entities,
                "total_relationships": total_rels,
                "avg_degree": avg_degree,
                "coupling_risk": coupling_risk,
            }
        except Exception as e:
            logger.error(f"centrality_analysis failed: {e}")
            return {
                "top_hubs": [],
                "total_entities": 0,
                "total_relationships": 0,
                "avg_degree": 0.0,
                "coupling_risk": [],
            }

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

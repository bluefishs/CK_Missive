"""
圖譜遍歷服務

從 graph_query_service.py 提取的路徑/遍歷相關方法：
- get_neighbors / _get_neighbors_uncached (K 跳鄰居 Recursive CTE)
- find_shortest_path (BFS 最短路徑)
- get_entity_timeline (實體關係時間軸)

Version: 1.0.0
Created: 2026-03-15
"""

import json
import logging
from typing import Optional

from sqlalchemy import select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    CanonicalEntity,
    EntityRelationship,
)
from app.services.ai.ai_config import get_ai_config
from .graph_helpers import _graph_cache, _CODE_ENTITY_TYPES

logger = logging.getLogger(__name__)


class GraphTraversalService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self._config = get_ai_config()

    async def get_neighbors(
        self,
        entity_id: int,
        max_hops: int = 2,
        limit: int = 50,
    ) -> dict:
        """K 跳鄰居查詢 — Recursive CTE，帶 Redis 快取"""
        max_hops = min(max_hops, 4)
        cache_key = f"neighbors:{entity_id}:{max_hops}:{limit}"
        cached = await _graph_cache.get(cache_key)
        if cached:
            return json.loads(cached)

        result = await self._get_neighbors_uncached(entity_id, max_hops, limit)
        await _graph_cache.set(
            cache_key, json.dumps(result, ensure_ascii=False),
            self._config.graph_cache_ttl_neighbors,
        )
        return result

    async def _get_neighbors_uncached(
        self,
        entity_id: int,
        max_hops: int,
        limit: int,
    ) -> dict:
        """K 跳鄰居查詢（無快取）"""
        from sqlalchemy import text

        result = await self.db.execute(text("""
            WITH RECURSIVE traversal AS (
                -- 起始節點 (hop 0)
                SELECT
                    :root_id AS entity_id,
                    0 AS hop,
                    ARRAY[:root_id] AS path,
                    NULL::int AS edge_source,
                    NULL::int AS edge_target,
                    NULL::text AS rel_type,
                    NULL::text AS rel_label,
                    NULL::int AS rel_weight
            UNION ALL
                -- 遞迴展開鄰居
                SELECT
                    CASE
                        WHEN r.source_entity_id = t.entity_id THEN r.target_entity_id
                        ELSE r.source_entity_id
                    END AS entity_id,
                    t.hop + 1 AS hop,
                    t.path || CASE
                        WHEN r.source_entity_id = t.entity_id THEN r.target_entity_id
                        ELSE r.source_entity_id
                    END,
                    r.source_entity_id AS edge_source,
                    r.target_entity_id AS edge_target,
                    r.relation_type AS rel_type,
                    r.relation_label AS rel_label,
                    r.weight AS rel_weight
                FROM traversal t
                JOIN entity_relationships r ON (
                    r.source_entity_id = t.entity_id
                    OR r.target_entity_id = t.entity_id
                )
                JOIN canonical_entities ce ON ce.id = CASE
                    WHEN r.source_entity_id = t.entity_id THEN r.target_entity_id
                    ELSE r.source_entity_id
                END
                WHERE t.hop < :max_hops
                    AND r.invalidated_at IS NULL
                    AND r.relation_label IS DISTINCT FROM 'code_graph'
                    AND ce.entity_type NOT IN (
                        'py_module', 'py_class', 'py_function',
                        'db_table',
                        'ts_module', 'ts_component', 'ts_hook'
                    )
                    AND NOT (
                        CASE
                            WHEN r.source_entity_id = t.entity_id THEN r.target_entity_id
                            ELSE r.source_entity_id
                        END = ANY(t.path)
                    )
            )
            SELECT DISTINCT ON (entity_id)
                entity_id, hop
            FROM traversal
            ORDER BY entity_id, hop
            LIMIT :limit
        """), {"root_id": entity_id, "max_hops": max_hops, "limit": limit})

        node_rows = result.all()
        node_ids = {row[0] for row in node_rows}
        hop_map = {row[0]: row[1] for row in node_rows}

        if not node_ids:
            return {"nodes": [], "edges": []}

        entities_result = await self.db.execute(
            select(CanonicalEntity)
            .where(CanonicalEntity.id.in_(node_ids))
            .where(CanonicalEntity.entity_type.notin_(_CODE_ENTITY_TYPES))
        )
        entities = entities_result.scalars().all()
        filtered_ids = {e.id for e in entities}
        all_nodes = [
            {
                "id": e.id,
                "name": e.canonical_name,
                "type": e.entity_type,
                "mention_count": e.mention_count,
                "hop": hop_map.get(e.id, 0),
                "source_project": getattr(e, "source_project", None) or "ck-missive",
            }
            for e in entities
        ]

        edges_result = await self.db.execute(
            select(EntityRelationship)
            .where(
                EntityRelationship.source_entity_id.in_(filtered_ids),
                EntityRelationship.target_entity_id.in_(filtered_ids),
                EntityRelationship.invalidated_at.is_(None),
            )
        )
        all_edges = [
            {
                "source_id": rel.source_entity_id,
                "target_id": rel.target_entity_id,
                "relation_type": rel.relation_type,
                "relation_label": rel.relation_label,
                "weight": rel.weight,
                "source_project": getattr(rel, "source_project", None) or "ck-missive",
            }
            for rel in edges_result.scalars().all()
        ]

        return {"nodes": all_nodes, "edges": all_edges}

    async def find_shortest_path(
        self,
        source_id: int,
        target_id: int,
        max_hops: int = 5,
    ) -> Optional[dict]:
        """兩實體間最短路徑查詢 — Recursive CTE BFS，帶 Redis 快取"""
        max_hops = min(max_hops, 6)

        cache_key = f"path:{source_id}:{target_id}:{max_hops}"
        cached = await _graph_cache.get(cache_key)
        if cached:
            return json.loads(cached)

        result = await self._find_shortest_path_uncached(source_id, target_id, max_hops)
        if result is not None:
            await _graph_cache.set(
                cache_key, json.dumps(result, ensure_ascii=False),
                self._config.graph_cache_ttl_path,
            )
        return result

    async def _find_shortest_path_uncached(
        self,
        source_id: int,
        target_id: int,
        max_hops: int,
    ) -> Optional[dict]:
        """兩實體間最短路徑查詢（無快取）"""
        try:
            from sqlalchemy import text

            _code_types_tuple = tuple(_CODE_ENTITY_TYPES)

            result = await self.db.execute(text("""
                WITH RECURSIVE pathfinder AS (
                    SELECT
                        :source_id AS current_id,
                        ARRAY[:source_id] AS path,
                        ARRAY[]::text[] AS relations,
                        0 AS depth
                UNION ALL
                    SELECT
                        CASE
                            WHEN r.source_entity_id = p.current_id THEN r.target_entity_id
                            ELSE r.source_entity_id
                        END,
                        p.path || CASE
                            WHEN r.source_entity_id = p.current_id THEN r.target_entity_id
                            ELSE r.source_entity_id
                        END,
                        p.relations || r.relation_label,
                        p.depth + 1
                    FROM pathfinder p
                    JOIN entity_relationships r ON (
                        r.source_entity_id = p.current_id
                        OR r.target_entity_id = p.current_id
                    )
                    WHERE p.depth < :max_hops
                        AND r.invalidated_at IS NULL
                        AND r.relation_label IS DISTINCT FROM 'code_graph'
                        AND (
                            CASE
                                WHEN r.source_entity_id = p.current_id THEN r.target_entity_id
                                ELSE r.source_entity_id
                            END
                        ) NOT IN (
                            SELECT id FROM canonical_entities
                            WHERE entity_type = ANY(:code_types)
                        )
                        AND NOT (
                            CASE
                                WHEN r.source_entity_id = p.current_id THEN r.target_entity_id
                                ELSE r.source_entity_id
                            END = ANY(p.path)
                        )
                )
                SELECT path, relations, depth
                FROM pathfinder
                WHERE current_id = :target_id
                ORDER BY depth
                LIMIT 1
            """), {
                "source_id": source_id,
                "target_id": target_id,
                "max_hops": max_hops,
                "code_types": list(_code_types_tuple),
            })

            row = result.first()
            if not row:
                return None

            path_ids, relations, depth = row

            entities_result = await self.db.execute(
                select(CanonicalEntity)
                .where(CanonicalEntity.id.in_(path_ids))
            )
            entity_map = {e.id: e for e in entities_result.scalars().all()}

            path_detail = [
                {
                    "id": eid,
                    "name": entity_map[eid].canonical_name if eid in entity_map else str(eid),
                    "type": entity_map[eid].entity_type if eid in entity_map else "unknown",
                    "source_project": (
                        getattr(entity_map[eid], "source_project", None) or "ck-missive"
                    ) if eid in entity_map else "unknown",
                }
                for eid in path_ids
            ]

            return {
                "found": True,
                "depth": depth,
                "path": path_detail,
                "relations": list(relations),
            }
        except Exception as e:
            logger.error(f"find_shortest_path failed: {e}")
            return None

    async def get_entity_timeline(self, entity_id: int) -> list:
        """取得實體的關係時間軸"""
        try:
            result = await self.db.execute(
                select(
                    EntityRelationship,
                    CanonicalEntity.canonical_name.label("other_name"),
                    CanonicalEntity.entity_type.label("other_type"),
                )
                .join(
                    CanonicalEntity,
                    CanonicalEntity.id == case(
                        (EntityRelationship.source_entity_id == entity_id,
                         EntityRelationship.target_entity_id),
                        else_=EntityRelationship.source_entity_id,
                    )
                )
                .where(
                    (EntityRelationship.source_entity_id == entity_id)
                    | (EntityRelationship.target_entity_id == entity_id)
                )
                .where(CanonicalEntity.entity_type.notin_(_CODE_ENTITY_TYPES))
                .order_by(EntityRelationship.valid_from.asc().nullslast())
            )

            timeline = []
            for row in result.all():
                rel = row[0]
                direction = "outgoing" if rel.source_entity_id == entity_id else "incoming"
                timeline.append({
                    "id": rel.id,
                    "direction": direction,
                    "relation_type": rel.relation_type,
                    "relation_label": rel.relation_label,
                    "other_name": row.other_name,
                    "other_type": row.other_type,
                    "weight": rel.weight,
                    "valid_from": str(rel.valid_from) if rel.valid_from else None,
                    "valid_to": str(rel.valid_to) if rel.valid_to else None,
                    "invalidated_at": str(rel.invalidated_at) if rel.invalidated_at else None,
                    "document_count": rel.document_count,
                })

            return timeline
        except Exception as e:
            logger.error(f"get_entity_timeline failed: {e}")
            return []

"""
圖譜查詢服務

使用 PostgreSQL Recursive CTE 實作圖譜遍歷：
- K 跳鄰居查詢
- 實體時間軸
- 高頻實體排名
- 圖譜統計

Version: 1.1.0
Created: 2026-02-24
Updated: 2026-02-26 - v1.1.0 Redis 快取層（detail/neighbors/search/stats）
"""

import json
import logging
from typing import Optional

import re

from sqlalchemy import select, func as sa_func, union_all, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    CanonicalEntity,
    EntityAlias,
    EntityRelationship,
    DocumentEntityMention,
)
from .ai_config import get_ai_config
from .base_ai_service import RedisCache

logger = logging.getLogger(__name__)

# 模組級快取實例（所有 GraphQueryService 共用）
_graph_cache = RedisCache(prefix="graph:query")


class GraphQueryService:
    """圖譜查詢服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._config = get_ai_config()

    async def get_entity_detail(self, entity_id: int) -> Optional[dict]:
        """取得實體詳情（含別名、提及公文、關係），帶 Redis 快取"""
        cache_key = f"detail:{entity_id}"
        cached = await _graph_cache.get(cache_key)
        if cached:
            return json.loads(cached)

        result = await self._get_entity_detail_uncached(entity_id)
        if result:
            await _graph_cache.set(
                cache_key, json.dumps(result, ensure_ascii=False),
                self._config.graph_cache_ttl_detail,
            )
        return result

    async def _get_entity_detail_uncached(self, entity_id: int) -> Optional[dict]:
        """取得實體詳情（無快取）"""
        entity = await self.db.get(CanonicalEntity, entity_id)
        if not entity:
            return None

        # 別名
        alias_result = await self.db.execute(
            select(EntityAlias)
            .where(EntityAlias.canonical_entity_id == entity_id)
        )
        aliases = [a.alias_name for a in alias_result.scalars().all()]

        # 提及的公文
        from app.extended.models import OfficialDocument
        mention_result = await self.db.execute(
            select(
                DocumentEntityMention.document_id,
                DocumentEntityMention.mention_text,
                DocumentEntityMention.confidence,
                OfficialDocument.subject,
                OfficialDocument.doc_number,
                OfficialDocument.doc_date,
            )
            .join(OfficialDocument, OfficialDocument.id == DocumentEntityMention.document_id)
            .where(DocumentEntityMention.canonical_entity_id == entity_id)
            .order_by(OfficialDocument.doc_date.desc().nullslast())
            .limit(50)
        )
        documents = [
            {
                "document_id": row.document_id,
                "mention_text": row.mention_text,
                "confidence": row.confidence,
                "subject": row.subject,
                "doc_number": row.doc_number,
                "doc_date": str(row.doc_date) if row.doc_date else None,
            }
            for row in mention_result.all()
        ]

        # 關係（出邊 + 入邊）
        out_result = await self.db.execute(
            select(EntityRelationship, CanonicalEntity.canonical_name, CanonicalEntity.entity_type)
            .join(CanonicalEntity, CanonicalEntity.id == EntityRelationship.target_entity_id)
            .where(EntityRelationship.source_entity_id == entity_id)
            .where(EntityRelationship.invalidated_at.is_(None))
        )
        in_result = await self.db.execute(
            select(EntityRelationship, CanonicalEntity.canonical_name, CanonicalEntity.entity_type)
            .join(CanonicalEntity, CanonicalEntity.id == EntityRelationship.source_entity_id)
            .where(EntityRelationship.target_entity_id == entity_id)
            .where(EntityRelationship.invalidated_at.is_(None))
        )

        relationships = []
        for row in out_result.all():
            rel = row[0]
            relationships.append({
                "id": rel.id,
                "direction": "outgoing",
                "relation_type": rel.relation_type,
                "relation_label": rel.relation_label,
                "target_name": row[1],
                "target_type": row[2],
                "target_id": rel.target_entity_id,
                "weight": rel.weight,
                "valid_from": str(rel.valid_from) if rel.valid_from else None,
                "valid_to": str(rel.valid_to) if rel.valid_to else None,
                "document_count": rel.document_count,
            })
        for row in in_result.all():
            rel = row[0]
            relationships.append({
                "id": rel.id,
                "direction": "incoming",
                "relation_type": rel.relation_type,
                "relation_label": rel.relation_label,
                "source_name": row[1],
                "source_type": row[2],
                "source_id": rel.source_entity_id,
                "weight": rel.weight,
                "valid_from": str(rel.valid_from) if rel.valid_from else None,
                "valid_to": str(rel.valid_to) if rel.valid_to else None,
                "document_count": rel.document_count,
            })

        return {
            "id": entity.id,
            "canonical_name": entity.canonical_name,
            "entity_type": entity.entity_type,
            "description": entity.description,
            "alias_count": entity.alias_count,
            "mention_count": entity.mention_count,
            "first_seen_at": str(entity.first_seen_at) if entity.first_seen_at else None,
            "last_seen_at": str(entity.last_seen_at) if entity.last_seen_at else None,
            "aliases": aliases,
            "documents": documents,
            "relationships": relationships,
        }

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

        # Recursive CTE: 一次查詢找到所有 K 跳內的節點和邊
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
                WHERE t.hop < :max_hops
                    AND r.invalidated_at IS NULL
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

        # 批次取得所有節點資訊
        entities_result = await self.db.execute(
            select(CanonicalEntity)
            .where(CanonicalEntity.id.in_(node_ids))
        )
        all_nodes = [
            {
                "id": e.id,
                "name": e.canonical_name,
                "type": e.entity_type,
                "mention_count": e.mention_count,
                "hop": hop_map.get(e.id, 0),
            }
            for e in entities_result.scalars().all()
        ]

        # 批次取得節點間所有邊
        edges_result = await self.db.execute(
            select(EntityRelationship)
            .where(
                EntityRelationship.source_entity_id.in_(node_ids),
                EntityRelationship.target_entity_id.in_(node_ids),
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
        """兩實體間最短路徑查詢 — Recursive CTE BFS"""
        from sqlalchemy import text

        max_hops = min(max_hops, 6)

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
        """), {"source_id": source_id, "target_id": target_id, "max_hops": max_hops})

        row = result.first()
        if not row:
            return None

        path_ids, relations, depth = row

        # 取得路徑上所有實體名稱
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
            }
            for eid in path_ids
        ]

        return {
            "found": True,
            "depth": depth,
            "path": path_detail,
            "relations": list(relations),
        }

    async def get_entity_timeline(self, entity_id: int) -> list:
        """取得實體的關係時間軸"""
        result = await self.db.execute(
            select(
                EntityRelationship,
                CanonicalEntity.canonical_name.label("other_name"),
                CanonicalEntity.entity_type.label("other_type"),
            )
            .join(
                CanonicalEntity,
                CanonicalEntity.id == sa_func.case(
                    (EntityRelationship.source_entity_id == entity_id,
                     EntityRelationship.target_entity_id),
                    else_=EntityRelationship.source_entity_id,
                )
            )
            .where(
                (EntityRelationship.source_entity_id == entity_id)
                | (EntityRelationship.target_entity_id == entity_id)
            )
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

    async def get_top_entities(
        self,
        entity_type: Optional[str] = None,
        sort_by: str = "mention_count",
        limit: int = 20,
    ) -> list:
        """高頻實體排名"""
        query = select(CanonicalEntity)

        if entity_type:
            query = query.where(CanonicalEntity.entity_type == entity_type)

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

    async def search_entities(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 20,
    ) -> list:
        """搜尋實體（名稱模糊匹配 + 同義詞擴展），帶 Redis 快取"""
        cache_key = f"search:{query}:{entity_type or ''}:{limit}"
        cached = await _graph_cache.get(cache_key)
        if cached:
            return json.loads(cached)

        result = await self._search_entities_uncached(query, entity_type, limit)
        await _graph_cache.set(
            cache_key, json.dumps(result, ensure_ascii=False),
            self._config.graph_cache_ttl_search,
        )
        return result

    async def _search_entities_uncached(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 20,
    ) -> list:
        """搜尋實體（無快取）"""
        from app.services.ai.synonym_expander import SynonymExpander

        # 擴展搜尋詞（原始 + 同義詞）
        search_terms = SynonymExpander.expand_search_terms(query)

        # 建構 ILIKE OR 條件
        ilike_conditions = []
        for term in search_terms:
            escaped = re.sub(r'([%_\\])', r'\\\1', term)
            ilike_conditions.append(
                CanonicalEntity.canonical_name.ilike(f"%{escaped}%")
            )

        # 也搜尋別名表
        alias_conditions = []
        for term in search_terms:
            escaped = re.sub(r'([%_\\])', r'\\\1', term)
            alias_conditions.append(
                EntityAlias.alias_name.ilike(f"%{escaped}%")
            )

        # 主查詢：canonical_name 匹配（獨立 ID 子查詢）
        main_id_query = select(CanonicalEntity.id).where(or_(*ilike_conditions))
        if entity_type:
            main_id_query = main_id_query.where(CanonicalEntity.entity_type == entity_type)

        # 別名查詢：alias_name 匹配（獨立 ID 子查詢，JOIN 保留在完整語句中）
        alias_id_query = (
            select(CanonicalEntity.id)
            .join(EntityAlias, EntityAlias.canonical_entity_id == CanonicalEntity.id)
            .where(or_(*alias_conditions))
        )
        if entity_type:
            alias_id_query = alias_id_query.where(CanonicalEntity.entity_type == entity_type)

        # 合併去重（兩個子查詢都直接 select ID，無需 with_only_columns）
        combined = union_all(main_id_query, alias_id_query).subquery()

        final_query = (
            select(CanonicalEntity)
            .where(CanonicalEntity.id.in_(select(combined.c.id)))
            .order_by(CanonicalEntity.mention_count.desc().nullslast())
            .limit(limit)
        )

        result = await self.db.execute(final_query)

        return [
            {
                "id": e.id,
                "canonical_name": e.canonical_name,
                "entity_type": e.entity_type,
                "mention_count": e.mention_count,
                "alias_count": e.alias_count,
                "description": e.description,
                "first_seen_at": str(e.first_seen_at) if e.first_seen_at else None,
                "last_seen_at": str(e.last_seen_at) if e.last_seen_at else None,
            }
            for e in result.scalars().all()
        ]

    async def get_graph_stats(self) -> dict:
        """圖譜統計，帶 Redis 快取（TTL 30 分鐘）"""
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

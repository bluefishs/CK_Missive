"""
圖譜查詢服務

使用 PostgreSQL Recursive CTE 實作圖譜遍歷：
- K 跳鄰居查詢
- 實體時間軸
- 高頻實體排名
- 圖譜統計

Version: 1.4.0
Created: 2026-02-24
Updated: 2026-03-18 - v1.4.0 entity_graph 建構拆分至 graph_entity_graph_builder
"""

import json
import logging
from typing import Optional

import re

from sqlalchemy import select, union_all, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    CanonicalEntity,
    EntityAlias,
    EntityRelationship,
    DocumentEntityMention,
    OfficialDocument,
)
from app.services.ai.core.ai_config import get_ai_config

from .graph_helpers import (
    _graph_cache,
    invalidate_graph_cache,  # noqa: F401 — re-exported for backward compat
)
from .graph_traversal_service import GraphTraversalService
from .graph_statistics_service import GraphStatisticsService
from .graph_code_wiki_service import GraphCodeWikiService
from .graph_entity_graph_builder import GraphEntityGraphBuilder

logger = logging.getLogger(__name__)


class GraphQueryService:
    """圖譜查詢服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._config = get_ai_config()
        self._traversal = GraphTraversalService(db)
        self._statistics = GraphStatisticsService(db)
        self._code_wiki = GraphCodeWikiService(db)
        self._graph_builder = GraphEntityGraphBuilder(db)

    # ── Traversal delegates ──

    async def get_neighbors(
        self,
        entity_id: int,
        max_hops: int = 2,
        limit: int = 50,
    ) -> dict:
        """K 跳鄰居查詢 — Recursive CTE，帶 Redis 快取"""
        return await self._traversal.get_neighbors(entity_id, max_hops, limit)

    async def find_shortest_path(
        self,
        source_id: int,
        target_id: int,
        max_hops: int = 5,
    ) -> Optional[dict]:
        """兩實體間最短路徑查詢 — Recursive CTE BFS"""
        return await self._traversal.find_shortest_path(source_id, target_id, max_hops)

    async def get_entity_timeline(self, entity_id: int) -> list:
        """取得實體的關係時間軸"""
        return await self._traversal.get_entity_timeline(entity_id)

    # ── Statistics delegates ──

    async def get_timeline_aggregate(
        self,
        relation_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        granularity: str = "month",
    ) -> dict:
        """跨實體時序聚合：按月/季/年統計關係數量趨勢。"""
        return await self._statistics.get_timeline_aggregate(relation_type, entity_type, granularity)

    async def get_top_entities(
        self,
        entity_type: Optional[str] = None,
        sort_by: str = "mention_count",
        limit: int = 20,
        include_code: bool = False,
    ) -> list:
        """高頻實體排名（預設排除程式碼圖譜實體）"""
        return await self._statistics.get_top_entities(entity_type, sort_by, limit, include_code)

    async def get_graph_stats(self) -> dict:
        """圖譜統計，帶 Redis 快取（TTL 30 分鐘）"""
        return await self._statistics.get_graph_stats()

    # ── Code Wiki delegates ──

    async def get_code_wiki_graph(
        self,
        entity_types: Optional[list] = None,
        module_prefix: Optional[str] = None,
        limit: int = 500,
    ) -> dict:
        """取得 Code Wiki 代碼圖譜（nodes + edges），帶 Redis 快取"""
        return await self._code_wiki.get_code_wiki_graph(entity_types, module_prefix, limit)

    async def get_module_overview(self) -> dict:
        """取得模組架構概覽：按 layer 分組統計 + DB ERD 資訊。"""
        return await self._code_wiki.get_module_overview()

    # ── Entity detail (kept in main service) ──

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

        # 關係（出邊 + 入邊），排除程式碼圖譜實體
        # 使用 2 查詢（JOIN target 不同，UNION 需 subquery 反而更慢）
        out_result = await self.db.execute(
            select(EntityRelationship, CanonicalEntity.canonical_name, CanonicalEntity.entity_type)
            .join(CanonicalEntity, CanonicalEntity.id == EntityRelationship.target_entity_id)
            .where(EntityRelationship.source_entity_id == entity_id)
            .where(EntityRelationship.invalidated_at.is_(None))
            .where(CanonicalEntity.graph_domain == 'knowledge')
        )
        in_result = await self.db.execute(
            select(EntityRelationship, CanonicalEntity.canonical_name, CanonicalEntity.entity_type)
            .join(CanonicalEntity, CanonicalEntity.id == EntityRelationship.source_entity_id)
            .where(EntityRelationship.target_entity_id == entity_id)
            .where(EntityRelationship.invalidated_at.is_(None))
            .where(CanonicalEntity.graph_domain == 'knowledge')
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

    # ── Search (kept in main service) ──

    async def search_entities(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 20,
    ) -> list:
        """搜尋實體（名稱模糊匹配 + 同義詞擴展），帶 Redis 快取"""
        try:
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
        except Exception as e:
            logger.error(f"search_entities failed: {e}")
            return []

    async def _search_entities_uncached(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 20,
    ) -> list:
        """搜尋實體（無快取）"""
        from app.services.ai.search.synonym_expander import SynonymExpander

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
        else:
            main_id_query = main_id_query.where(CanonicalEntity.graph_domain == 'knowledge')

        # 別名查詢：alias_name 匹配（獨立 ID 子查詢，JOIN 保留在完整語句中）
        alias_id_query = (
            select(CanonicalEntity.id)
            .join(EntityAlias, EntityAlias.canonical_entity_id == CanonicalEntity.id)
            .where(or_(*alias_conditions))
        )
        if entity_type:
            alias_id_query = alias_id_query.where(CanonicalEntity.entity_type == entity_type)
        else:
            alias_id_query = alias_id_query.where(CanonicalEntity.graph_domain == 'knowledge')

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

    # ── NL → KG Query (Gemma 4 powered) ──

    async def nl_graph_query(self, question: str) -> dict:
        """Translate natural language to knowledge graph query via Gemma 4.

        Examples:
        - "桃園市政府相關的公文" → search entities type=org, name contains "桃園市政府", then find related docs
        - "去年和乾坤有關的標案" → search entities type=project, time filter, related tenders

        Returns: {"entity_type": str, "search_term": str, "relation_filter": str,
                  "time_range": dict, "max_hops": int}
        """
        try:
            from app.core.ai_connector import get_ai_connector
            ai = get_ai_connector()
            prompt = (
                "將以下自然語言查詢轉換為知識圖譜查詢參數，以 JSON 回覆：\n\n"
                f"查詢: {question[:300]}\n\n"
                "可用參數:\n"
                "- entity_type: org(機關), person(人), project(專案), location(地點), date(日期)\n"
                "- search_term: 搜尋關鍵字\n"
                "- relation_filter: 關係類型篩選 (optional)\n"
                "- time_range: {\"start\": \"YYYY-MM-DD\", \"end\": \"YYYY-MM-DD\"} (optional)\n"
                "- max_hops: 搜尋跳數 1-3 (default 2)\n"
                "- include_documents: 是否包含關聯公文 (true/false)\n\n"
                '回覆: {"entity_type": "...", "search_term": "...", "relation_filter": null, '
                '"time_range": null, "max_hops": 2, "include_documents": true}'
            )
            result = await ai.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0, max_tokens=200, task_type="classify",
            )
            from app.services.ai.core.agent_utils import parse_json_safe
            parsed = parse_json_safe(result)
            if not parsed or not parsed.get("search_term"):
                return {"search_term": question[:100], "max_hops": 2, "include_documents": True}
            return parsed
        except Exception as e:
            logger.debug("NL graph query translation failed: %s", e)
            return {"search_term": question[:100], "max_hops": 2, "include_documents": True}

    async def smart_graph_search(self, question: str, limit: int = 20) -> dict:
        """Natural language → knowledge graph search (Gemma 4 powered)."""
        params = await self.nl_graph_query(question)

        entities = await self.search_entities(
            query=params.get("search_term", ""),
            entity_type=params.get("entity_type"),
            limit=limit,
        )

        result = {"query_params": params, "entities": entities, "count": len(entities)}

        # If include_documents, fetch related docs for top entities
        if params.get("include_documents") and entities:
            top_entity_ids = [e.get("id") for e in entities[:5] if e.get("id")]
            if top_entity_ids:
                docs = await self._get_related_documents(top_entity_ids, limit=10)
                result["related_documents"] = docs

        return result

    async def _get_related_documents(
        self, entity_ids: list[int], limit: int = 10,
    ) -> list[dict]:
        """Fetch documents related to a list of entity IDs via mention table."""
        try:
            stmt = (
                select(
                    OfficialDocument.id,
                    OfficialDocument.subject,
                    OfficialDocument.doc_number,
                    OfficialDocument.doc_date,
                    DocumentEntityMention.canonical_entity_id,
                )
                .join(OfficialDocument, OfficialDocument.id == DocumentEntityMention.document_id)
                .where(DocumentEntityMention.canonical_entity_id.in_(entity_ids))
                .order_by(OfficialDocument.doc_date.desc().nullslast())
                .limit(limit)
            )
            rows = await self.db.execute(stmt)
            return [
                {
                    "document_id": row.id,
                    "subject": row.subject,
                    "doc_number": row.doc_number,
                    "doc_date": str(row.doc_date) if row.doc_date else None,
                    "entity_id": row.canonical_entity_id,
                }
                for row in rows.all()
            ]
        except Exception as e:
            logger.debug("_get_related_documents failed: %s", e)
            return []

    # ── Entity Graph (delegated to GraphEntityGraphBuilder) ──

    async def get_entity_graph(
        self,
        entity_types: list[str] | None = None,
        min_mentions: int = 1,
        limit: int = 200,
        year: int | None = None,
        collapse_agency: bool = True,
    ) -> dict:
        """公文知識圖譜 — 委派至 GraphEntityGraphBuilder"""
        return await self._graph_builder.get_entity_graph(
            entity_types, min_mentions, limit, year, collapse_agency,
        )

"""
公文知識圖譜建構服務

從 graph_query_service.py 拆分，負責組裝 NER 實體 + 業務實體
（公文、派工、機關、專案）的完整知識圖譜。

Version: 1.0.0
Created: 2026-03-18
Extracted from: graph_query_service.py v1.3.0
"""

import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    CanonicalEntity,
    EntityRelationship,
    DocumentEntityMention,
    OfficialDocument,
)
from .ai_config import get_ai_config

from .graph_helpers import (
    _graph_cache,
    _CODE_ENTITY_TYPES,
)
from .graph_merge_strategy import GraphMergeStrategy
from .graph_business_entity_builder import (
    build_agency_nodes_and_edges,
    build_dispatch_and_project_nodes,
)

logger = logging.getLogger(__name__)


class GraphEntityGraphBuilder:
    """公文知識圖譜建構器 -- 組裝 NER + 業務實體圖譜。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._config = get_ai_config()

    async def get_entity_graph(
        self,
        entity_types: list[str] | None = None,
        min_mentions: int = 1,
        limit: int = 200,
        year: int | None = None,
        collapse_agency: bool = True,
    ) -> dict:
        """
        公文知識圖譜：NER 實體 + 業務實體（公文、派工、機關、專案）。

        回傳 { nodes: [...], edges: [...] } 格式，
        與 relation_graph_service 的 GraphNode/GraphEdge 相容。
        帶 Redis 快取（TTL 5 分鐘）。

        Args:
            year: 民國年篩選（如 114），只顯示該年度公文相關的實體。
        """
        try:
            types_key = ",".join(sorted(entity_types or []))
            cache_key = f"entity_graph:{types_key}:{min_mentions}:{limit}:{year or 'all'}:{collapse_agency}"
            cached = await _graph_cache.get(cache_key)
            if cached:
                return json.loads(cached)

            result = await self._get_entity_graph_uncached(entity_types, min_mentions, limit, year, collapse_agency)
            await _graph_cache.set(cache_key, json.dumps(result, ensure_ascii=False), 300)
            return result
        except Exception as e:
            logger.error(f"get_entity_graph failed: {e}")
            return {"nodes": [], "edges": []}

    async def _get_entity_graph_uncached(
        self,
        entity_types: list[str] | None = None,
        min_mentions: int = 1,
        limit: int = 200,
        year: int | None = None,
        collapse_agency: bool = True,
    ) -> dict:
        """公文知識圖譜（無快取實作）。"""
        nodes: list[dict] = []
        edges: list[dict] = []
        seen_nodes: set[str] = set()
        seen_edges: set[str] = set()

        def _add_node(n: dict) -> None:
            if n["id"] not in seen_nodes:
                seen_nodes.add(n["id"])
                nodes.append(n)

        def _add_edge(e: dict) -> None:
            key = f"{e['source']}->{e['target']}:{e.get('type', '')}"
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append(e)

        # -- Phase 0: 年度篩選 --
        year_doc_ids: set[int] | None = None
        year_entity_ids: set[int] | None = None
        if year:
            from sqlalchemy import extract as sa_extract
            ad_year = year + 1911  # 民國 -> 西元
            year_docs = await self.db.execute(
                select(OfficialDocument.id)
                .where(sa_extract('year', OfficialDocument.doc_date) == ad_year)
            )
            year_doc_ids = {r[0] for r in year_docs.all()}
            if not year_doc_ids:
                return {"nodes": nodes, "edges": edges}

            year_ent_result = await self.db.execute(
                select(DocumentEntityMention.canonical_entity_id)
                .where(DocumentEntityMention.document_id.in_(list(year_doc_ids)))
                .distinct()
            )
            year_entity_ids = {r[0] for r in year_ent_result.all()}
            logger.info(f"Year filter: ROC {year} -> {len(year_doc_ids)} docs, {len(year_entity_ids)} entities")

        # -- Phase 1: NER 正規化實體 --
        query = (
            select(CanonicalEntity)
            .where(CanonicalEntity.entity_type.notin_(_CODE_ENTITY_TYPES))
            .where(CanonicalEntity.mention_count >= min_mentions)
        )
        if entity_types:
            ner_types = [t for t in entity_types
                         if t not in _CODE_ENTITY_TYPES
                         and t not in ("document", "dispatch", "agency", "project", "typroject")]
            if ner_types:
                query = query.where(CanonicalEntity.entity_type.in_(ner_types))
        if year_entity_ids is not None:
            query = query.where(CanonicalEntity.id.in_(list(year_entity_ids)))

        query = query.order_by(CanonicalEntity.mention_count.desc().nullslast()).limit(limit)
        result = await self.db.execute(query)
        entities = result.scalars().all()

        entity_ids = [e.id for e in entities]
        entity_id_set = set(entity_ids)
        entity_by_id: dict[int, CanonicalEntity] = {e.id: e for e in entities}
        entity_type_by_id: dict[int, str] = {e.id: e.entity_type for e in entities}

        for e in entities:
            graph_type = "ner_project" if e.entity_type == "project" else e.entity_type
            full_name = e.canonical_name or f"Entity#{e.id}"
            _add_node({
                "id": f"ce_{e.id}",
                "type": graph_type,
                "label": full_name[:30] if len(full_name) > 30 else full_name,
                "fullLabel": full_name if len(full_name) > 30 else None,
                "mention_count": e.mention_count,
                "source_project": e.source_project,
            })

        # NER 實體間的關係
        if entity_ids:
            rel_result = await self.db.execute(
                select(EntityRelationship)
                .where(EntityRelationship.source_entity_id.in_(entity_ids))
                .where(EntityRelationship.target_entity_id.in_(entity_ids))
                .where(EntityRelationship.invalidated_at.is_(None))
            )
            for rel in rel_result.scalars().all():
                if rel.source_entity_id in entity_id_set and rel.target_entity_id in entity_id_set:
                    _add_edge({
                        "source": f"ce_{rel.source_entity_id}",
                        "target": f"ce_{rel.target_entity_id}",
                        "label": rel.relation_label or rel.relation_type,
                        "type": rel.relation_type,
                        "weight": rel.weight,
                    })

        # -- Phase 2: 業務實體整合 + 核心公文錨點 --
        if not entity_ids:
            return {"nodes": nodes, "edges": edges}

        mention_query = (
            select(
                DocumentEntityMention.canonical_entity_id,
                DocumentEntityMention.document_id,
            )
            .where(DocumentEntityMention.canonical_entity_id.in_(entity_ids))
        )
        if year_doc_ids is not None:
            mention_query = mention_query.where(
                DocumentEntityMention.document_id.in_(list(year_doc_ids))
            )
        mention_result = await self.db.execute(mention_query)
        mention_rows = mention_result.all()

        doc_entities: dict[int, list[int]] = {}
        entity_docs: dict[int, set[int]] = {}
        for row in mention_rows:
            doc_entities.setdefault(row.document_id, []).append(row.canonical_entity_id)
            entity_docs.setdefault(row.canonical_entity_id, set()).add(row.document_id)

        doc_ids = list(doc_entities.keys())

        doc_map: dict[int, OfficialDocument] = {}
        if doc_ids:
            doc_result = await self.db.execute(
                select(OfficialDocument).where(OfficialDocument.id.in_(doc_ids))
            )
            for doc in doc_result.scalars().all():
                doc_map[doc.id] = doc

        # -- 策略 1: 核心公文錨點 --
        hub_doc_ids: set[int] = set()
        for doc_id, ent_list in doc_entities.items():
            unique_types = set()
            for eid in ent_list:
                etype = entity_type_by_id.get(eid)
                if etype:
                    unique_types.add(etype)
            if len(unique_types) >= 3:
                hub_doc_ids.add(doc_id)

        if len(hub_doc_ids) > 60:
            hub_doc_ids = set(sorted(
                hub_doc_ids,
                key=lambda d: len(set(doc_entities.get(d, []))),
                reverse=True
            )[:60])

        for doc_id in hub_doc_ids:
            doc = doc_map.get(doc_id)
            if not doc:
                continue
            doc_label = doc.doc_number or doc.subject
            if doc_label and len(doc_label) > 20:
                doc_label = doc_label[:20]
            _add_node({
                "id": f"doc_{doc_id}",
                "type": "document",
                "label": doc_label or f"公文#{doc_id}",
                "category": doc.doc_type,
                "doc_number": doc.doc_number,
            })
            for eid in set(doc_entities.get(doc_id, [])):
                if eid in entity_id_set:
                    _add_edge({
                        "source": f"doc_{doc_id}",
                        "target": f"ce_{eid}",
                        "label": "提及",
                        "type": "mentions",
                        "weight": 0.6,
                    })

        # 2a. 機關節點（使用正規化名稱 + 層級折疊）— 委派 graph_business_entity_builder
        agency_parent_map, agency_name_map = await build_agency_nodes_and_edges(
            db=self.db,
            doc_ids=doc_ids,
            doc_entities=doc_entities,
            doc_map=doc_map,
            entity_id_set=entity_id_set,
            hub_doc_ids=hub_doc_ids,
            collapse_agency=collapse_agency,
            seen_nodes=seen_nodes,
            add_node=_add_node,
            add_edge=_add_edge,
        )

        # -- 策略 2: 派工單按工程聚合 — 委派 graph_business_entity_builder --
        ty_projects = await build_dispatch_and_project_nodes(
            db=self.db,
            doc_ids=doc_ids,
            doc_entities=doc_entities,
            entity_id_set=entity_id_set,
            add_node=_add_node,
            add_edge=_add_edge,
        )

        # -- Phase 2.5: 三階段同源實體合併（策略 5 強化） --
        ner_fullname: dict[str, str] = {}
        for e in entities:
            nid = f"ce_{e.id}"
            ner_fullname[nid] = e.canonical_name or ""

        biz_fullname: dict[str, str] = {}
        for n in nodes:
            if n["type"] == "agency":
                biz_fullname[n["id"]] = n["id"].replace("agency_", "", 1)
            elif n["type"] == "typroject":
                tp_id_str = n["id"].replace("typroject_", "", 1)
                try:
                    tp_id = int(tp_id_str)
                    tp = ty_projects.get(tp_id)
                    biz_fullname[n["id"]] = tp.project_name if tp else n["label"]
                except ValueError:
                    biz_fullname[n["id"]] = n["label"]

        merged_count, id_remap = GraphMergeStrategy.merge_same_origin_entities(
            nodes=nodes,
            edges=edges,
            seen_nodes=seen_nodes,
            seen_edges=seen_edges,
            ner_fullname=ner_fullname,
            biz_fullname=biz_fullname,
            entity_id_set=entity_id_set,
            entity_by_id=entity_by_id,
            doc_entities=doc_entities,
            doc_map=doc_map,
            doc_ids=doc_ids,
        )

        # -- Phase 2.5D: 統一節點類型 --
        GraphMergeStrategy.unify_node_types(nodes)

        # -- Phase 2.6: 地點聚合為行政區域 --
        GraphMergeStrategy.aggregate_locations(nodes, edges, seen_nodes, seen_edges, id_remap)

        # -- Phase 3: NER 實體間共現邊 --
        GraphMergeStrategy.add_co_mention_edges(
            nodes, edges, seen_nodes, seen_edges,
            doc_entities, entity_id_set, id_remap,
        )

        # -- Phase 4: 超級樞紐限流 --
        GraphMergeStrategy.throttle_hubs(edges)

        logger.info(
            f"Entity graph: {len(nodes)} nodes, {len(edges)} edges"
            f" ({len(entities)} NER, {len(doc_ids)} docs, {merged_count} merged)"
        )
        return {"nodes": nodes, "edges": edges}

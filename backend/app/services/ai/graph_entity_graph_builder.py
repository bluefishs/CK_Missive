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
from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    CanonicalEntity,
    EntityRelationship,
    DocumentEntityMention,
    OfficialDocument,
    TaoyuanDispatchOrder,
    TaoyuanDispatchDocumentLink,
    TaoyuanDispatchProjectLink,
    TaoyuanProject,
)
from .ai_config import get_ai_config

from .graph_helpers import (
    _graph_cache,
    _clean_agency_name,
    _CODE_ENTITY_TYPES,
)
from .graph_merge_strategy import GraphMergeStrategy

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

        # 2a. 機關節點（使用正規化名稱 + 層級折疊）
        agency_parent_map: dict[int, int] = {}
        agency_name_map: dict[int, str] = {}
        if doc_ids:
            from app.extended.models import GovernmentAgency
            ag_result = await self.db.execute(
                select(GovernmentAgency.id, GovernmentAgency.agency_name,
                       GovernmentAgency.parent_agency_id)
            )
            all_agencies = ag_result.all()
            parent_lookup: dict[int, int | None] = {}
            for ag in all_agencies:
                parent_lookup[ag.id] = ag.parent_agency_id
                agency_name_map[ag.id] = ag.agency_name
            for ag_id in parent_lookup:
                root = ag_id
                for _ in range(5):
                    p = parent_lookup.get(root)
                    if p is None:
                        break
                    root = p
                agency_parent_map[ag_id] = root

            agency_entity_counts: dict[str, dict[int, int]] = {}
            agency_doc_counts: dict[str, int] = {}
            for doc_id, ent_list in doc_entities.items():
                doc = doc_map.get(doc_id)
                if not doc:
                    continue
                for field, fk_field in [
                    ("normalized_sender", "sender_agency_id"),
                    ("normalized_receiver", "receiver_agency_id"),
                ]:
                    name = getattr(doc, field, None) or getattr(doc, field.replace("normalized_", ""), None)
                    if not name:
                        continue
                    fk_id = getattr(doc, fk_field, None)
                    if collapse_agency and fk_id and fk_id in agency_parent_map:
                        root_id = agency_parent_map[fk_id]
                        if root_id != fk_id:
                            name = agency_name_map.get(root_id, name)
                    clean_name = _clean_agency_name(name)
                    agency_doc_counts[clean_name] = agency_doc_counts.get(clean_name, 0) + 1
                    if clean_name not in agency_entity_counts:
                        agency_entity_counts[clean_name] = {}
                    for eid in set(ent_list):
                        if eid in entity_id_set:
                            agency_entity_counts[clean_name][eid] = (
                                agency_entity_counts[clean_name].get(eid, 0) + 1
                            )

            for agency_name, doc_count in agency_doc_counts.items():
                _add_node({
                    "id": f"agency_{agency_name}",
                    "type": "agency",
                    "label": agency_name[:25],
                    "mention_count": doc_count,
                })

            MAX_AGENCY_EDGES = 30
            for agency_name, ent_counts in agency_entity_counts.items():
                ag_id = f"agency_{agency_name}"
                sorted_ents = sorted(
                    ((eid, c) for eid, c in ent_counts.items() if c >= 2),
                    key=lambda x: x[1], reverse=True,
                )[:MAX_AGENCY_EDGES]
                for eid, count in sorted_ents:
                    _add_edge({
                        "source": ag_id,
                        "target": f"ce_{eid}",
                        "label": f"相關 {count} 篇",
                        "type": "agency_entity",
                        "weight": min(count / 10, 1.0),
                    })

            for doc_id in hub_doc_ids:
                doc = doc_map.get(doc_id)
                if not doc:
                    continue
                for norm_field, fk_field, rel_type, label in [
                    ("normalized_sender", "sender_agency_id", "sends", "發文"),
                    ("normalized_receiver", "receiver_agency_id", "receives", "收文"),
                ]:
                    name = getattr(doc, norm_field, None) or getattr(doc, norm_field.replace("normalized_", ""), None)
                    if not name:
                        continue
                    fk_id = getattr(doc, fk_field, None)
                    if collapse_agency and fk_id and fk_id in agency_parent_map:
                        root_id = agency_parent_map[fk_id]
                        if root_id != fk_id:
                            name = agency_name_map.get(root_id, name)
                    clean_name = _clean_agency_name(name)
                    ag_id = f"agency_{clean_name}"
                    if ag_id in seen_nodes:
                        _add_edge({
                            "source": ag_id,
                            "target": f"doc_{doc_id}",
                            "label": label,
                            "type": rel_type,
                            "weight": 0.8,
                        })

        # -- 策略 2: 派工單按工程聚合 --
        ty_projects: dict[int, TaoyuanProject] = {}
        if doc_ids:
            dispatch_link_result = await self.db.execute(
                select(TaoyuanDispatchDocumentLink)
                .where(TaoyuanDispatchDocumentLink.document_id.in_(doc_ids))
            )
            dispatch_links = dispatch_link_result.scalars().all()
            dispatch_ids = set(dl.dispatch_order_id for dl in dispatch_links)

            fk_result = await self.db.execute(
                select(TaoyuanDispatchOrder)
                .where(or_(
                    TaoyuanDispatchOrder.id.in_(list(dispatch_ids)) if dispatch_ids else False,
                    TaoyuanDispatchOrder.agency_doc_id.in_(doc_ids),
                    TaoyuanDispatchOrder.company_doc_id.in_(doc_ids),
                ))
            )
            all_dispatches = fk_result.scalars().all()

            dispatch_doc_map: dict[int, set[int]] = {}
            for dl in dispatch_links:
                dispatch_doc_map.setdefault(dl.dispatch_order_id, set()).add(dl.document_id)

            all_dispatch_ids = set(d.id for d in all_dispatches)
            dispatch_to_project: dict[int, int] = {}
            if all_dispatch_ids:
                proj_link_result = await self.db.execute(
                    select(TaoyuanDispatchProjectLink)
                    .where(TaoyuanDispatchProjectLink.dispatch_order_id.in_(list(all_dispatch_ids)))
                )
                proj_links = proj_link_result.scalars().all()
                ty_proj_ids = set(dpl.taoyuan_project_id for dpl in proj_links)
                for dpl in proj_links:
                    dispatch_to_project[dpl.dispatch_order_id] = dpl.taoyuan_project_id

                if ty_proj_ids:
                    ty_result = await self.db.execute(
                        select(TaoyuanProject).where(TaoyuanProject.id.in_(list(ty_proj_ids)))
                    )
                    for tp in ty_result.scalars().all():
                        ty_projects[tp.id] = tp

            project_dispatches: dict[int, list] = {}
            orphan_dispatches: list = []
            for disp in all_dispatches:
                proj_id = dispatch_to_project.get(disp.id)
                if proj_id and proj_id in ty_projects:
                    project_dispatches.setdefault(proj_id, []).append(disp)
                else:
                    orphan_dispatches.append(disp)

            for proj_id, dispatches in project_dispatches.items():
                tp = ty_projects[proj_id]
                disp_count = len(dispatches)
                _add_node({
                    "id": f"typroject_{proj_id}",
                    "type": "typroject",
                    "label": tp.project_name[:25] if tp.project_name else f"工程#{proj_id}",
                    "category": tp.district,
                    "mention_count": disp_count,
                    "status": f"含 {disp_count} 單",
                })

                for disp in dispatches:
                    disp_node_id = f"dispatch_{disp.id}"
                    _add_node({
                        "id": disp_node_id,
                        "type": "dispatch",
                        "label": f"派工 {disp.dispatch_no or disp.id}",
                        "status": disp.project_name[:20] if disp.project_name else None,
                    })
                    _add_edge({
                        "source": f"typroject_{proj_id}",
                        "target": disp_node_id,
                        "label": "包含",
                        "type": "project_dispatch",
                        "weight": 0.6,
                    })

                proj_entity_counts: dict[int, int] = {}
                for disp in dispatches:
                    related = dispatch_doc_map.get(disp.id, set()).copy()
                    if disp.agency_doc_id:
                        related.add(disp.agency_doc_id)
                    if disp.company_doc_id:
                        related.add(disp.company_doc_id)
                    for did in related:
                        for eid in doc_entities.get(did, []):
                            if eid in entity_id_set:
                                proj_entity_counts[eid] = proj_entity_counts.get(eid, 0) + 1

                MAX_PROJECT_EDGES = 20
                sorted_proj_ents = sorted(
                    proj_entity_counts.items(),
                    key=lambda x: x[1], reverse=True,
                )[:MAX_PROJECT_EDGES]
                for eid, count in sorted_proj_ents:
                    _add_edge({
                        "source": f"typroject_{proj_id}",
                        "target": f"ce_{eid}",
                        "label": f"關聯 {count} 篇" if count > 1 else "關聯",
                        "type": "project_entity",
                        "weight": min(count / 5, 1.0),
                    })

            MAX_ORPHAN_EDGES = 20
            orphan_with_edges = 0
            orphan_dispatches.sort(key=lambda d: d.dispatch_no or str(d.id))
            for disp in orphan_dispatches:
                related = dispatch_doc_map.get(disp.id, set()).copy()
                if disp.agency_doc_id:
                    related.add(disp.agency_doc_id)
                if disp.company_doc_id:
                    related.add(disp.company_doc_id)

                disp_entity_counts: dict[int, int] = {}
                for did in related:
                    for eid in doc_entities.get(did, []):
                        if eid in entity_id_set:
                            disp_entity_counts[eid] = disp_entity_counts.get(eid, 0) + 1

                disp_node_id = f"dispatch_{disp.id}"
                _add_node({
                    "id": disp_node_id,
                    "type": "dispatch",
                    "label": f"派工 {disp.dispatch_no or disp.id}",
                    "status": disp.project_name[:20] if disp.project_name else None,
                })
                if disp_entity_counts and orphan_with_edges < MAX_ORPHAN_EDGES:
                    for eid, count in disp_entity_counts.items():
                        _add_edge({
                            "source": disp_node_id,
                            "target": f"ce_{eid}",
                            "label": f"關聯 {count} 篇" if count > 1 else "關聯",
                            "type": "dispatch_entity",
                            "weight": min(count / 5, 1.0),
                        })
                    orphan_with_edges += 1

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

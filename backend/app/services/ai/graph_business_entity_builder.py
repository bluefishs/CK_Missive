"""
業務實體圖譜建構器

從 graph_entity_graph_builder.py 拆分，負責組裝業務實體
（機關、派工單、桃園工程）的節點與邊。

Version: 1.0.0
Created: 2026-03-19
Extracted from: graph_entity_graph_builder.py v1.0.0
"""

import logging
from typing import Callable

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    GovernmentAgency,
    OfficialDocument,
    TaoyuanDispatchOrder,
    TaoyuanDispatchDocumentLink,
    TaoyuanDispatchProjectLink,
    TaoyuanProject,
)

from .graph_helpers import _clean_agency_name

logger = logging.getLogger(__name__)


async def build_agency_nodes_and_edges(
    db: AsyncSession,
    doc_ids: list[int],
    doc_entities: dict[int, list[int]],
    doc_map: dict[int, OfficialDocument],
    entity_id_set: set[int],
    hub_doc_ids: set[int],
    collapse_agency: bool,
    seen_nodes: set[str],
    add_node: Callable[[dict], None],
    add_edge: Callable[[dict], None],
) -> tuple[dict[int, int], dict[int, str]]:
    """
    Phase 2a: 機關節點建構（正規化名稱 + 層級折疊）。

    Returns:
        (agency_parent_map, agency_name_map) for downstream use.
    """
    agency_parent_map: dict[int, int] = {}
    agency_name_map: dict[int, str] = {}

    if not doc_ids:
        return agency_parent_map, agency_name_map

    ag_result = await db.execute(
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

    # Collect agency-entity and agency-doc counts
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

    # Create agency nodes
    for agency_name, doc_count in agency_doc_counts.items():
        add_node({
            "id": f"agency_{agency_name}",
            "type": "agency",
            "label": agency_name[:25],
            "mention_count": doc_count,
        })

    # Create agency-entity edges (top 30 per agency, min 2 co-occurrences)
    MAX_AGENCY_EDGES = 30
    for agency_name, ent_counts in agency_entity_counts.items():
        ag_id = f"agency_{agency_name}"
        sorted_ents = sorted(
            ((eid, c) for eid, c in ent_counts.items() if c >= 2),
            key=lambda x: x[1], reverse=True,
        )[:MAX_AGENCY_EDGES]
        for eid, count in sorted_ents:
            add_edge({
                "source": ag_id,
                "target": f"ce_{eid}",
                "label": f"相關 {count} 篇",
                "type": "agency_entity",
                "weight": min(count / 10, 1.0),
            })

    # Create agency-document edges for hub docs
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
                add_edge({
                    "source": ag_id,
                    "target": f"doc_{doc_id}",
                    "label": label,
                    "type": rel_type,
                    "weight": 0.8,
                })

    return agency_parent_map, agency_name_map


async def build_dispatch_and_project_nodes(
    db: AsyncSession,
    doc_ids: list[int],
    doc_entities: dict[int, list[int]],
    entity_id_set: set[int],
    add_node: Callable[[dict], None],
    add_edge: Callable[[dict], None],
) -> dict[int, TaoyuanProject]:
    """
    Phase 2b: 派工單按工程聚合 — 桃園工程 + 派工單節點與邊。

    Returns:
        ty_projects dict for downstream merge strategy use.
    """
    ty_projects: dict[int, TaoyuanProject] = {}
    if not doc_ids:
        return ty_projects

    # Load dispatch-document links
    dispatch_link_result = await db.execute(
        select(TaoyuanDispatchDocumentLink)
        .where(TaoyuanDispatchDocumentLink.document_id.in_(doc_ids))
    )
    dispatch_links = dispatch_link_result.scalars().all()
    dispatch_ids = set(dl.dispatch_order_id for dl in dispatch_links)

    # Load dispatch orders (via link or FK)
    fk_result = await db.execute(
        select(TaoyuanDispatchOrder)
        .where(or_(
            TaoyuanDispatchOrder.id.in_(list(dispatch_ids)) if dispatch_ids else False,
            TaoyuanDispatchOrder.agency_doc_id.in_(doc_ids),
            TaoyuanDispatchOrder.company_doc_id.in_(doc_ids),
        ))
    )
    all_dispatches = fk_result.scalars().all()

    # Build dispatch-doc mapping
    dispatch_doc_map: dict[int, set[int]] = {}
    for dl in dispatch_links:
        dispatch_doc_map.setdefault(dl.dispatch_order_id, set()).add(dl.document_id)

    # Load dispatch-project links
    all_dispatch_ids = set(d.id for d in all_dispatches)
    dispatch_to_project: dict[int, int] = {}
    if all_dispatch_ids:
        proj_link_result = await db.execute(
            select(TaoyuanDispatchProjectLink)
            .where(TaoyuanDispatchProjectLink.dispatch_order_id.in_(list(all_dispatch_ids)))
        )
        proj_links = proj_link_result.scalars().all()
        ty_proj_ids = set(dpl.taoyuan_project_id for dpl in proj_links)
        for dpl in proj_links:
            dispatch_to_project[dpl.dispatch_order_id] = dpl.taoyuan_project_id

        if ty_proj_ids:
            ty_result = await db.execute(
                select(TaoyuanProject).where(TaoyuanProject.id.in_(list(ty_proj_ids)))
            )
            for tp in ty_result.scalars().all():
                ty_projects[tp.id] = tp

    # Group dispatches by project
    project_dispatches: dict[int, list] = {}
    orphan_dispatches: list = []
    for disp in all_dispatches:
        proj_id = dispatch_to_project.get(disp.id)
        if proj_id and proj_id in ty_projects:
            project_dispatches.setdefault(proj_id, []).append(disp)
        else:
            orphan_dispatches.append(disp)

    # Create project + dispatch nodes with edges
    for proj_id, dispatches in project_dispatches.items():
        tp = ty_projects[proj_id]
        disp_count = len(dispatches)
        add_node({
            "id": f"typroject_{proj_id}",
            "type": "typroject",
            "label": tp.project_name[:25] if tp.project_name else f"工程#{proj_id}",
            "category": tp.district,
            "mention_count": disp_count,
            "status": f"含 {disp_count} 單",
        })

        for disp in dispatches:
            disp_node_id = f"dispatch_{disp.id}"
            add_node({
                "id": disp_node_id,
                "type": "dispatch",
                "label": f"派工 {disp.dispatch_no or disp.id}",
                "status": disp.project_name[:20] if disp.project_name else None,
            })
            add_edge({
                "source": f"typroject_{proj_id}",
                "target": disp_node_id,
                "label": "包含",
                "type": "project_dispatch",
                "weight": 0.6,
            })

        # Project-entity edges
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
            add_edge({
                "source": f"typroject_{proj_id}",
                "target": f"ce_{eid}",
                "label": f"關聯 {count} 篇" if count > 1 else "關聯",
                "type": "project_entity",
                "weight": min(count / 5, 1.0),
            })

    # Orphan dispatches (no project)
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
        add_node({
            "id": disp_node_id,
            "type": "dispatch",
            "label": f"派工 {disp.dispatch_no or disp.id}",
            "status": disp.project_name[:20] if disp.project_name else None,
        })
        if disp_entity_counts and orphan_with_edges < MAX_ORPHAN_EDGES:
            for eid, count in disp_entity_counts.items():
                add_edge({
                    "source": disp_node_id,
                    "target": f"ce_{eid}",
                    "label": f"關聯 {count} 篇" if count > 1 else "關聯",
                    "type": "dispatch_entity",
                    "weight": min(count / 5, 1.0),
                })
            orphan_with_edges += 1

    return ty_projects

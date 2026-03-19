"""
Code Graph Analysis

循環偵測、架構分析、依賴指標計算。

Extracted from: code_graph_service.py (v3.0.0)
Version: 1.0.0
"""

import json
import logging
from typing import Any, Dict, List, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import CODE_ENTITY_TYPES

logger = logging.getLogger(__name__)

CODE_GRAPH_LABEL = "code_graph"

# Architecture layer classification rules
_LAYER_RULES: List[Tuple[str, str]] = [
    # Python backend
    ("app.core.", "core"),
    ("app.api.", "api"),
    ("app.services.", "services"),
    ("app.repositories.", "repository"),
    ("app.extended.", "model"),
    ("app.schemas.", "schema"),
    ("app.scripts.", "scripts"),
    # TypeScript frontend (canonical_name without src/ prefix)
    ("components/", "component"),
    ("hooks/", "hook"),
    ("api/", "api_client"),
    ("pages/", "page"),
    ("config/", "config"),
    ("services/", "services"),
    ("utils/", "utils"),
    ("types/", "schema"),
    ("constants/", "config"),
    ("providers/", "core"),
    ("router/", "core"),
    ("store/", "core"),
]


def _classify_layer(name: str) -> str:
    for prefix, layer in _LAYER_RULES:
        if name.startswith(prefix):
            return layer
    return "other"


async def detect_import_cycles(db: AsyncSession) -> Dict[str, Any]:
    """Detect circular import dependencies in the code graph.

    Uses DFS to find all import cycles among py_module entities.
    Returns cycle paths for diagnostic purposes.
    """
    from app.extended.models.knowledge_graph import (
        CanonicalEntity,
        EntityRelationship,
    )

    # Load all module names
    mod_rows = (await db.execute(
        select(CanonicalEntity.id, CanonicalEntity.canonical_name)
        .where(CanonicalEntity.entity_type == "py_module")
    )).all()
    id_to_name = {r[0]: r[1] for r in mod_rows}
    name_to_id = {r[1]: r[0] for r in mod_rows}

    # Load import edges
    edge_rows = (await db.execute(
        select(
            EntityRelationship.source_entity_id,
            EntityRelationship.target_entity_id,
        )
        .where(EntityRelationship.relation_label == CODE_GRAPH_LABEL)
        .where(EntityRelationship.relation_type == "imports")
    )).all()

    # Build adjacency list
    adj: Dict[int, List[int]] = {}
    for src_id, tgt_id in edge_rows:
        if src_id in id_to_name and tgt_id in id_to_name:
            adj.setdefault(src_id, []).append(tgt_id)

    # DFS cycle detection
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[int, int] = {nid: WHITE for nid in id_to_name}
    path: List[int] = []
    cycles: List[List[str]] = []

    def dfs(u: int) -> None:
        color[u] = GRAY
        path.append(u)
        for v in adj.get(u, []):
            if color[v] == GRAY:
                idx = path.index(v)
                cycle = [id_to_name[nid] for nid in path[idx:]]
                cycle.append(id_to_name[v])  # close the cycle
                cycles.append(cycle)
            elif color[v] == WHITE:
                dfs(v)
        path.pop()
        color[u] = BLACK

    for nid in id_to_name:
        if color[nid] == WHITE:
            dfs(nid)

    return {
        "total_modules": len(id_to_name),
        "total_import_edges": len(edge_rows),
        "cycles_found": len(cycles),
        "cycles": cycles[:50],  # limit output
    }


async def analyze_architecture(db: AsyncSession) -> Dict[str, Any]:
    """Analyze code graph for architecture insights.

    Computes:
    - Complexity hotspots: modules with most outgoing dependencies
    - Hub modules: modules imported by the most other modules
    - Large modules: modules with highest line count
    - Unused modules: modules with no incoming imports
    - God classes: classes with the most methods
    """
    from app.extended.models.knowledge_graph import (
        CanonicalEntity,
        EntityRelationship,
    )

    # Load all code entities
    entity_rows = (await db.execute(
        select(
            CanonicalEntity.id,
            CanonicalEntity.canonical_name,
            CanonicalEntity.entity_type,
            CanonicalEntity.description,
        ).where(CanonicalEntity.entity_type.in_(CODE_ENTITY_TYPES))
    )).all()

    id_to_name = {r[0]: r[1] for r in entity_rows}
    id_to_type = {r[0]: r[2] for r in entity_rows}
    id_to_desc: Dict[int, Dict[str, Any]] = {}
    for r in entity_rows:
        desc = r[3]
        if isinstance(desc, str):
            try:
                desc = json.loads(desc)
            except (json.JSONDecodeError, TypeError):
                desc = {}
        id_to_desc[r[0]] = desc if isinstance(desc, dict) else {}

    # Load all code relations
    rel_rows = (await db.execute(
        select(
            EntityRelationship.source_entity_id,
            EntityRelationship.target_entity_id,
            EntityRelationship.relation_type,
        ).where(EntityRelationship.relation_label == CODE_GRAPH_LABEL)
    )).all()

    # Compute metrics
    outgoing: Dict[int, int] = {}
    incoming: Dict[int, int] = {}
    method_count: Dict[int, int] = {}

    for src_id, tgt_id, rel_type in rel_rows:
        if rel_type == "imports":
            outgoing[src_id] = outgoing.get(src_id, 0) + 1
            incoming[tgt_id] = incoming.get(tgt_id, 0) + 1
        elif rel_type == "has_method":
            method_count[src_id] = method_count.get(src_id, 0) + 1

    # 1. Complexity hotspots (modules with most outgoing deps)
    complexity_hotspots = sorted(
        [
            {"module": id_to_name[nid], "outgoing_deps": cnt}
            for nid, cnt in outgoing.items()
            if nid in id_to_name and id_to_type.get(nid) in ("py_module", "ts_module")
        ],
        key=lambda x: x["outgoing_deps"],
        reverse=True,
    )[:15]

    # 2. Hub modules (most imported by others)
    hub_modules = sorted(
        [
            {"module": id_to_name[nid], "imported_by": cnt}
            for nid, cnt in incoming.items()
            if nid in id_to_name and id_to_type.get(nid) in ("py_module", "ts_module")
        ],
        key=lambda x: x["imported_by"],
        reverse=True,
    )[:15]

    # 3. Large modules (by line count)
    large_modules = sorted(
        [
            {
                "module": id_to_name[nid],
                "lines": id_to_desc[nid].get("lines", 0),
                "type": id_to_type[nid],
            }
            for nid in id_to_name
            if id_to_type.get(nid) in ("py_module", "ts_module")
            and id_to_desc.get(nid, {}).get("lines", 0) > 0
        ],
        key=lambda x: x["lines"],
        reverse=True,
    )[:15]

    # 4. Orphan modules (no incoming imports, exclude __init__)
    all_module_ids = {
        nid for nid in id_to_name
        if id_to_type.get(nid) in ("py_module", "ts_module")
    }
    imported_ids = {tgt for _, tgt, rt in rel_rows if rt == "imports" and tgt in all_module_ids}
    orphan_modules = [
        id_to_name[nid]
        for nid in (all_module_ids - imported_ids)
        if not id_to_name[nid].endswith("__init__")
        and not id_to_name[nid].endswith("/index")
    ][:30]

    # 5. God classes (classes with most methods)
    god_classes = sorted(
        [
            {"class": id_to_name[nid], "method_count": cnt}
            for nid, cnt in method_count.items()
            if nid in id_to_name and id_to_type.get(nid) == "py_class"
        ],
        key=lambda x: x["method_count"],
        reverse=True,
    )[:15]

    return {
        "complexity_hotspots": complexity_hotspots,
        "hub_modules": hub_modules,
        "large_modules": large_modules,
        "orphan_modules": orphan_modules,
        "god_classes": god_classes,
        "summary": {
            "total_entities": len(entity_rows),
            "total_relations": len(rel_rows),
            "py_modules": sum(1 for r in entity_rows if r[2] == "py_module"),
            "ts_modules": sum(1 for r in entity_rows if r[2] == "ts_module"),
            "classes": sum(1 for r in entity_rows if r[2] == "py_class"),
            "components": sum(1 for r in entity_rows if r[2] == "ts_component"),
            "hooks": sum(1 for r in entity_rows if r[2] == "ts_hook"),
        },
    }


async def compute_dependency_metrics(
    db: AsyncSession,
    CanonicalEntity: Any,
    EntityRelationship: Any,
) -> None:
    """為每個模組計算依賴指標（outgoing_deps / incoming_deps / layer）並回寫 description。"""

    mod_rows = (await db.execute(
        select(
            CanonicalEntity.id,
            CanonicalEntity.canonical_name,
            CanonicalEntity.entity_type,
            CanonicalEntity.description,
        ).where(CanonicalEntity.entity_type.in_(["py_module", "ts_module"]))
    )).all()

    if not mod_rows:
        return

    id_to_name = {r[0]: r[1] for r in mod_rows}
    mod_ids = set(id_to_name.keys())

    import_rows = (await db.execute(
        select(
            EntityRelationship.source_entity_id,
            EntityRelationship.target_entity_id,
        )
        .where(EntityRelationship.relation_label == CODE_GRAPH_LABEL)
        .where(EntityRelationship.relation_type == "imports")
    )).all()

    outgoing: Dict[int, int] = {}
    incoming: Dict[int, int] = {}
    for src_id, tgt_id in import_rows:
        if src_id in mod_ids:
            outgoing[src_id] = outgoing.get(src_id, 0) + 1
        if tgt_id in mod_ids:
            incoming[tgt_id] = incoming.get(tgt_id, 0) + 1

    updated = 0
    for row in mod_rows:
        eid, ename, etype, desc_raw = row
        desc = desc_raw
        if isinstance(desc, str):
            try:
                desc = json.loads(desc)
            except (json.JSONDecodeError, TypeError):
                desc = {}
        if not isinstance(desc, dict):
            desc = {}

        desc["outgoing_deps"] = outgoing.get(eid, 0)
        desc["incoming_deps"] = incoming.get(eid, 0)
        desc["layer"] = _classify_layer(ename)

        await db.execute(
            update(CanonicalEntity)
            .where(CanonicalEntity.id == eid)
            .values(description=json.dumps(desc, ensure_ascii=False))
        )
        updated += 1

    await db.flush()
    logger.info("依賴指標已回寫 %d 個模組", updated)

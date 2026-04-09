"""
Agent Diagram Builder — Mermaid 圖表生成

從 agent_tools.py 提取的圖表建構邏輯：
- ER Diagram (erDiagram)
- Module Dependency Graph (graph LR)
- Flowchart (flowchart TD)
- Class Diagram (classDiagram)

Version: 1.0.0
Created: 2026-03-15
Extracted-from: agent_tools.py v1.3.0
"""

import json
import logging
from typing import Any, Dict, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def build_er_diagram(
    er_data: Dict[str, Any], scope: str, detail_level: str,
) -> Tuple[str, str, List[str]]:
    """Build Mermaid ER diagram from er-model.json."""
    tables = er_data.get("tables", {})
    scope_lower = scope.lower() if scope else ""

    # Filter tables by scope
    if scope_lower:
        filtered = {
            k: v for k, v in tables.items()
            if scope_lower in k.lower()
            or any(scope_lower in fk.get("ref_table", "").lower() for fk in v.get("foreign_keys", []))
        }
        # Also include referenced tables
        ref_tables: set = set()
        for t_info in filtered.values():
            for fk in t_info.get("foreign_keys", []):
                ref = fk.get("ref_table", "")
                if ref in tables:
                    ref_tables.add(ref)
        for ref in ref_tables:
            if ref not in filtered:
                filtered[ref] = tables[ref]
        tables = filtered

    if not tables:
        return ("無匹配的表", f"範圍 '{scope}' 沒有匹配的資料表", ["erDiagram"])

    type_map = {
        "INTEGER": "int", "BIGINT": "bigint", "SMALLINT": "smallint",
        "BOOLEAN": "bool", "CHARACTER VARYING": "varchar", "TEXT": "text",
        "TIMESTAMP WITHOUT TIME ZONE": "timestamp",
        "TIMESTAMP WITH TIME ZONE": "timestamptz",
        "DATE": "date", "UUID": "uuid", "JSONB": "jsonb",
        "DOUBLE PRECISION": "float8", "NUMERIC": "numeric",
        "VECTOR": "vector",
    }

    lines: List[str] = ["erDiagram"]

    # Relationships
    seen_rels: set = set()
    for tbl_name, tbl_info in tables.items():
        for fk in tbl_info.get("foreign_keys", []):
            ref = fk.get("ref_table", "")
            if ref in tables:
                rel_key = f"{ref}-{tbl_name}-{fk.get('column', '')}"
                if rel_key not in seen_rels:
                    seen_rels.add(rel_key)
                    lines.append(f'    {ref} ||--o{{ {tbl_name} : "{fk.get("column", "")}"')

    lines.append("")

    # Table definitions
    for tbl_name in sorted(tables.keys()):
        tbl_info = tables[tbl_name]
        pk_set = set(tbl_info.get("primary_key", []))
        fk_cols = {fk["column"] for fk in tbl_info.get("foreign_keys", [])}
        cols = tbl_info.get("columns", [])

        if detail_level == "brief":
            cols = [c for c in cols if c["name"] in pk_set or c["name"] in fk_cols]

        lines.append(f"    {tbl_name} {{")
        for col in cols:
            mtype = type_map.get(col.get("type", ""), col.get("type", "").lower())
            markers: List[str] = []
            if col["name"] in pk_set:
                markers.append("PK")
            if col["name"] in fk_cols:
                markers.append("FK")
            marker_str = f' "{",".join(markers)}"' if markers else ""
            lines.append(f'        {mtype} {col["name"]}{marker_str}')
        lines.append("    }")

    table_count = len(tables)
    title = f"ER Diagram — {scope or '全部'} ({table_count} 表)"
    description = f"包含 {table_count} 個資料表及其外鍵關聯"
    return (title, description, lines)


async def build_dependency_graph(
    db: AsyncSession, scope: str, detail_level: str,
) -> Tuple[str, str, List[str]]:
    """Build module dependency graph from canonical_entities."""
    from sqlalchemy import select
    from app.extended.models import CanonicalEntity, EntityRelationship

    scope_lower = scope.lower() if scope else ""

    stmt = select(
        CanonicalEntity.id,
        CanonicalEntity.canonical_name,
        CanonicalEntity.entity_type,
    ).where(
        CanonicalEntity.entity_type.in_(["py_module", "ts_module"])
    )
    if scope_lower:
        stmt = stmt.where(CanonicalEntity.canonical_name.ilike(f"%{scope_lower}%"))

    mod_rows = (await db.execute(stmt)).all()
    if not mod_rows:
        return ("無匹配模組", f"範圍 '{scope}' 沒有匹配的模組", ["graph LR"])

    mod_ids = {r[0] for r in mod_rows}
    id_to_name = {r[0]: r[1] for r in mod_rows}

    rel_stmt = select(
        EntityRelationship.source_entity_id,
        EntityRelationship.target_entity_id,
    ).where(
        EntityRelationship.relation_type == "imports",
        EntityRelationship.source_entity_id.in_(mod_ids),
        EntityRelationship.target_entity_id.in_(mod_ids),
    )
    rel_rows = (await db.execute(rel_stmt)).all()

    lines: List[str] = ["graph LR"]
    max_nodes = 30 if detail_level != "full" else 60
    shown_ids: set = set()
    shown_rels: List[str] = []

    for src_id, tgt_id in rel_rows:
        if len(shown_ids) >= max_nodes:
            break
        shown_ids.add(src_id)
        shown_ids.add(tgt_id)
        src_name = id_to_name.get(src_id, str(src_id)).split(".")[-1].split("/")[-1]
        tgt_name = id_to_name.get(tgt_id, str(tgt_id)).split(".")[-1].split("/")[-1]
        shown_rels.append(f"    {src_name} --> {tgt_name}")

    lines.extend(shown_rels[:50])

    title = f"模組依賴圖 — {scope or '全部'} ({len(shown_ids)} 模組)"
    description = f"{len(shown_rels)} 條 import 關聯"
    return (title, description, lines)


async def build_flowchart(
    scope: str, ai_connector: Any = None,
) -> Tuple[str, str, List[str]]:
    """Build flowchart via LLM generation or known system flows."""
    known_flows: Dict[str, list] = {
        "document": [
            "flowchart TD",
            "    A[收文登錄] --> B[分文指派]",
            "    B --> C{需核稿?}",
            "    C -->|是| D[擬稿]",
            "    C -->|否| E[歸檔]",
            "    D --> F[核稿審查]",
            "    F -->|退回| D",
            "    F -->|通過| G[發文]",
            "    G --> H[送達追蹤]",
            "    H --> E",
        ],
        "dispatch": [
            "flowchart TD",
            "    A[接收派工單] --> B[建立工程紀錄]",
            "    B --> C[派工單匯入]",
            "    C --> D[公文配對]",
            "    D --> E{配對成功?}",
            "    E -->|是| F[建立作業歷程]",
            "    E -->|否| G[手動關聯]",
            "    G --> F",
            "    F --> H[進度追蹤]",
            "    H --> I{結案?}",
            "    I -->|否| H",
            "    I -->|是| J[結案歸檔]",
        ],
        "ai": [
            "flowchart TD",
            "    A[使用者提問] --> B[意圖解析]",
            "    B --> C[Agent Planner]",
            "    C --> D[工具選擇 1-3 個]",
            "    D --> E[平行執行工具]",
            "    E --> F[GraphRAG 鄰域擴展]",
            "    F --> G[答案合成]",
            "    G --> H[SSE 串流回覆]",
            "    H --> I[回饋收集]",
        ],
    }

    scope_lower = scope.lower() if scope else ""

    for key, flow_lines in known_flows.items():
        if key in scope_lower:
            title = f"流程圖 — {scope}"
            description = f"{scope} 處理流程"
            return (title, description, flow_lines)

    # LLM generation fallback
    if ai_connector:
        try:
            prompt = (
                f"請根據以下主題生成 Mermaid flowchart（flowchart TD 格式）：{scope}\n"
                "要求：\n"
                "- 節點數 5-12 個\n"
                "- 包含決策節點（菱形 {{}}）\n"
                "- 使用中文標籤\n"
                "- 只輸出 Mermaid 語法，不要任何解釋\n"
            )
            response = await ai_connector.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            content = response.get("content", "") if isinstance(response, dict) else str(response)
            if "```mermaid" in content:
                content = content.split("```mermaid")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            lines = content.strip().split("\n")
            if lines and lines[0].strip().startswith("flowchart"):
                title = f"流程圖 — {scope}"
                description = f"AI 生成的 {scope} 流程圖"
                return (title, description, lines)
        except Exception as e:
            logger.warning("Flowchart LLM generation failed: %s", e)

    # Ultimate fallback
    lines = [
        "flowchart TD",
        f"    A[{scope or '開始'}] --> B{{判斷條件}}",
        "    B -->|是| C[處理步驟]",
        "    B -->|否| D[替代路徑]",
        "    C --> E[結束]",
        "    D --> E",
    ]
    title = f"流程圖 — {scope or '通用'}"
    description = "基本流程圖模板"
    return (title, description, lines)


async def build_class_diagram(
    db: AsyncSession, scope: str, detail_level: str,
) -> Tuple[str, str, List[str]]:
    """Build class diagram from py_class entities."""
    from sqlalchemy import select
    from app.extended.models import CanonicalEntity, EntityRelationship

    scope_lower = scope.lower() if scope else ""

    stmt = select(
        CanonicalEntity.id,
        CanonicalEntity.canonical_name,
        CanonicalEntity.description,
    ).where(CanonicalEntity.entity_type == "py_class")
    if scope_lower:
        stmt = stmt.where(CanonicalEntity.canonical_name.ilike(f"%{scope_lower}%"))
    stmt = stmt.limit(20)

    class_rows = (await db.execute(stmt)).all()
    if not class_rows:
        return ("無匹配類別", f"範圍 '{scope}' 沒有匹配的類別", ["classDiagram"])

    class_ids = {r[0] for r in class_rows}
    lines: List[str] = ["classDiagram"]

    for row in class_rows:
        name = row[1].split(".")[-1]
        desc = row[2]
        if isinstance(desc, str):
            try:
                desc = json.loads(desc)
            except Exception:
                desc = {}
        if not isinstance(desc, dict):
            desc = {}

        lines.append(f"    class {name} {{")
        methods = desc.get("methods", [])
        if detail_level == "brief":
            methods = methods[:3]
        for m in methods[:10]:
            lines.append(f"        +{m}()")
        lines.append("    }")

    # Inheritance relations
    rel_stmt = select(
        EntityRelationship.source_entity_id,
        EntityRelationship.target_entity_id,
        EntityRelationship.relation_type,
    ).where(
        EntityRelationship.source_entity_id.in_(class_ids),
        EntityRelationship.relation_type.in_(["inherits", "defines_class"]),
    )
    rel_rows = (await db.execute(rel_stmt)).all()
    id_to_name = {r[0]: r[1].split(".")[-1] for r in class_rows}

    for src_id, tgt_id, rtype in rel_rows:
        src_name = id_to_name.get(src_id, "")
        if src_name:
            if rtype == "inherits":
                lines.append(f"    {src_name} --|> Parent")

    title = f"類別圖 — {scope or '全部'} ({len(class_rows)} 類別)"
    description = f"包含 {len(class_rows)} 個類別的結構"
    return (title, description, lines)

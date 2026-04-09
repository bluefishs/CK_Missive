"""
工具結果格式化 — 知識圖譜實體相關工具

Extracted from tool_result_formatter.py
"""

import json
from typing import Any, Dict, List


def format_search_entities(result: Dict[str, Any], remaining_chars: int) -> str:
    parts: list[str] = []
    for e in result.get("entities", []):
        part = (
            f"[實體] {e.get('canonical_name', '')} "
            f"({e.get('entity_type', '')}, "
            f"提及 {e.get('mention_count', 0)} 次)\n"
        )
        if sum(len(p) for p in parts) + len(part) > remaining_chars:
            break
        parts.append(part)
    return "".join(parts)


def format_get_entity_detail(result: Dict[str, Any], remaining_chars: int) -> str:
    parts: list[str] = []
    entity = result.get("entity", {})
    part = (
        f"[實體詳情] {entity.get('canonical_name', '')} "
        f"({entity.get('entity_type', '')})\n"
        f"  別名: {', '.join(entity.get('aliases', [])[:5])}\n"
    )
    for doc in entity.get("documents", [])[:5]:
        part += f"  關聯公文: {doc.get('doc_number', '')} - {doc.get('subject', '')}\n"
    for rel in entity.get("relationships", [])[:5]:
        target = rel.get("target_name") or rel.get("source_name", "")
        part += f"  關係: {rel.get('relation_label', '')} → {target}\n"
    if len(part) <= remaining_chars:
        parts.append(part)
    return "".join(parts)


def format_navigate_graph(result: Dict[str, Any], remaining_chars: int) -> str:
    parts: list[str] = []
    center = result.get("center_entity", {})
    cluster = result.get("cluster_nodes", [])
    part = (
        f"[導航] 已定位至「{center.get('name', '')}」叢集\n"
        f"  相關節點 {len(cluster)} 個:\n"
    )
    for node in cluster[:8]:
        part += f"    - {node.get('name', '')} ({node.get('type', '')})\n"
    if len(part) <= remaining_chars:
        parts.append(part)
    return "".join(parts)


def format_summarize_entity(result: Dict[str, Any], remaining_chars: int) -> str:
    parts: list[str] = []
    entity = result.get("entity", {})
    summary_text = result.get("summary", "")
    part = (
        f"[實體摘要] {entity.get('name', '')} ({entity.get('type', '')})\n"
        f"  {summary_text[:200]}\n"
    )
    for u in result.get("upstream", [])[:3]:
        part += f"  上游: {u.get('entity_name', '')} ({u.get('relation', '')})\n"
    for d in result.get("downstream", [])[:3]:
        part += f"  下游: {d.get('entity_name', '')} ({d.get('relation', '')})\n"
    timeline = result.get("timeline", [])
    if timeline:
        part += f"  時間軸: {len(timeline)} 個事件\n"
        for evt in timeline[:3]:
            part += f"    - {evt.get('date', '')} {evt.get('subject', '')[:40]}\n"
    docs = result.get("documents", [])
    if docs:
        part += f"  關聯公文 {len(docs)} 篇:\n"
        for doc in docs[:3]:
            part += f"    - {doc.get('doc_number', '')} {doc.get('subject', '')[:40]}\n"
    if len(part) <= remaining_chars:
        parts.append(part)
    return "".join(parts)


def format_explore_entity_path(result: Dict[str, Any], remaining_chars: int) -> str:
    parts: list[str] = []
    path_nodes = result.get("path", [])
    part = f"[路徑探索] {len(path_nodes)} 個節點\n"
    if path_nodes:
        names = [n.get("name", "") for n in path_nodes]
        part += f"  路徑: {' → '.join(names)}\n"
    relations = result.get("relations", [])
    for rel in relations[:5]:
        part += (
            f"  {rel.get('source', '')} —[{rel.get('label', '')}]→ "
            f"{rel.get('target', '')}\n"
        )
    if len(part) <= remaining_chars:
        parts.append(part)
    return "".join(parts)


# --- summarize handlers ---

def summarize_search_entities(result: Dict[str, Any]) -> str:
    count = result.get("count", 0)
    if count == 0:
        return "未找到匹配實體"
    entities = result.get("entities", [])
    names = [e.get("canonical_name", "") for e in entities[:5]]
    return f"找到 {count} 個實體: {', '.join(names)}"


def summarize_get_entity_detail(result: Dict[str, Any]) -> str:
    entity = result.get("entity", {})
    name = entity.get("canonical_name", "")
    doc_count = len(entity.get("documents", []))
    rel_count = len(entity.get("relationships", []))
    return f"實體「{name}」: {doc_count} 篇關聯公文, {rel_count} 條關係"


def summarize_navigate_graph(result: Dict[str, Any]) -> str:
    count = result.get("count", 0)
    center = result.get("center_entity", {})
    center_name = center.get("name", "") if center else ""
    return json.dumps({
        "action": "navigate",
        "center_entity": center,
        "highlight_ids": result.get("highlight_ids", []),
        "cluster_nodes": result.get("cluster_nodes", [])[:20],
        "count": count,
        "summary": f"已導航至「{center_name}」叢集，共 {count} 個相關節點",
    }, ensure_ascii=False)


def summarize_summarize_entity(result: Dict[str, Any]) -> str:
    entity = result.get("entity", {})
    name = entity.get("name", "")
    summary_text = result.get("summary", "")
    upstream_count = len(result.get("upstream", []))
    downstream_count = len(result.get("downstream", []))
    doc_count = len(result.get("documents", []))
    return json.dumps({
        "entity": entity,
        "upstream": result.get("upstream", [])[:10],
        "downstream": result.get("downstream", [])[:10],
        "doc_count": doc_count,
        "summary": (
            f"「{name}」摘要: {summary_text[:100]}... "
            f"(上游 {upstream_count}, 下游 {downstream_count}, 關聯公文 {doc_count})"
            if summary_text else
            f"「{name}」: 上游 {upstream_count}, 下游 {downstream_count}, 關聯公文 {doc_count}"
        ),
    }, ensure_ascii=False)


# Registry
ENTITY_FORMAT_HANDLERS = {
    "search_entities": format_search_entities,
    "get_entity_detail": format_get_entity_detail,
    "navigate_graph": format_navigate_graph,
    "summarize_entity": format_summarize_entity,
    "explore_entity_path": format_explore_entity_path,
}

ENTITY_SUMMARIZE_HANDLERS = {
    "search_entities": summarize_search_entities,
    "get_entity_detail": summarize_get_entity_detail,
    "navigate_graph": summarize_navigate_graph,
    "summarize_entity": summarize_summarize_entity,
}

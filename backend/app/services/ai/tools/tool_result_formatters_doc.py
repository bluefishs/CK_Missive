"""
工具結果格式化 — 公文/派工/統計/相似公文

Extracted from tool_result_formatter.py
"""

import json
from typing import Any, Dict, List


def _current_len(parts: List[str]) -> int:
    return sum(len(p) for p in parts)


def format_search_documents(result: Dict[str, Any], remaining_chars: int) -> str:
    parts: list[str] = []
    for i, doc in enumerate(result.get("documents", []), 1):
        part = (
            f"[公文{i}] 字號: {doc.get('doc_number', '')}\n"
            f"  主旨: {doc.get('subject', '')}\n"
            f"  類型: {doc.get('doc_type', '')} | 類別: {doc.get('category', '')}\n"
            f"  發文: {doc.get('sender', '')} → 受文: {doc.get('receiver', '')}\n"
            f"  日期: {doc.get('doc_date', '')}\n"
        )
        if _current_len(parts) + len(part) > remaining_chars:
            break
        parts.append(part)
    try:
        from app.services.ai.core.response_enricher import enrich_document_results
        enriched = enrich_document_results(result.get("documents", []))
        analysis = f"\n[分析摘要] {enriched.get('analysis_hint', '')}，類型分布: {enriched.get('by_type_summary', '')}\n"
        if _current_len(parts) + len(analysis) <= remaining_chars:
            parts.append(analysis)
    except Exception:
        pass
    return "".join(parts)


def format_search_dispatch_orders(result: Dict[str, Any], remaining_chars: int) -> str:
    parts: list[str] = []
    linked_docs = result.get("linked_documents", [])
    for i, d in enumerate(result.get("dispatch_orders", []), 1):
        d_linked = [
            ld for ld in linked_docs
            if ld.get("dispatch_order_id") == d.get("id")
        ]
        linked_str = ""
        if d_linked:
            linked_str = "  關聯公文:\n"
            for ld in d_linked[:3]:
                linked_str += (
                    f"    - {ld.get('doc_number', '')} "
                    f"{ld.get('subject', '')[:60]}\n"
                )
        part = (
            f"[派工單{i}] 單號: {d.get('dispatch_no', '')}\n"
            f"  工程名稱: {d.get('project_name', '')}\n"
            f"  作業類別: {d.get('work_type', '')}\n"
            f"  子案名稱: {d.get('sub_case_name', '')}\n"
            f"  承辦人: {d.get('case_handler', '')} | 測量單位: {d.get('survey_unit', '')}\n"
            f"  契約期限: {d.get('deadline', '')}\n"
            f"{linked_str}"
        )
        if _current_len(parts) + len(part) > remaining_chars:
            break
        parts.append(part)
    try:
        from app.services.ai.core.response_enricher import enrich_dispatch_results
        enriched = enrich_dispatch_results(result.get("dispatch_orders", []))
        analysis = (
            f"\n[分析摘要] {enriched.get('analysis_hint', '')}\n"
            f"完成率: {enriched.get('completion_rate', '?')}, "
            f"逾期: {enriched.get('overdue_count', 0)} 筆 ({enriched.get('overdue_pct', '0%')}), "
            f"承辦人: {', '.join(enriched.get('handlers', [])[:3])}\n"
        )
        if _current_len(parts) + len(analysis) <= remaining_chars:
            parts.append(analysis)
    except Exception:
        pass
    return "".join(parts)


def format_find_similar(result: Dict[str, Any], remaining_chars: int) -> str:
    parts: list[str] = []
    for doc in result.get("documents", []):
        part = (
            f"[相似公文] {doc.get('doc_number', '')} "
            f"(相似度 {doc.get('similarity', 0):.0%})\n"
            f"  主旨: {doc.get('subject', '')}\n"
        )
        if _current_len(parts) + len(part) > remaining_chars:
            break
        parts.append(part)
    return "".join(parts)


def format_get_statistics(result: Dict[str, Any], remaining_chars: int) -> str:
    parts: list[str] = []
    summary_text = result.get("summary", "")
    if summary_text:
        part = f"[統計] {summary_text}\n"
    else:
        doc_total = result.get("document_total", 0)
        doc_by_cat = result.get("document_by_category", {})
        cat_detail = "、".join(f"{k} {v}" for k, v in doc_by_cat.items()) if doc_by_cat else ""
        part = f"[統計] 系統共有 {doc_total} 筆公文"
        if cat_detail:
            part += f"（{cat_detail}）"
        part += "\n"
    graph_stats = result.get("graph_stats", {})
    if graph_stats:
        part += (
            f"  知識圖譜: {graph_stats.get('total_entities', 0)} 實體, "
            f"{graph_stats.get('total_relationships', 0)} 關係\n"
        )
    top = result.get("top_entities", [])
    if top:
        names = [f"{e.get('canonical_name', '')}({e.get('mention_count', 0)})" for e in top[:5]]
        part += f"  高頻實體: {', '.join(names)}\n"
    doc_by_cat = result.get("document_by_category", {})
    if doc_by_cat and len(doc_by_cat) > 1:
        max_cat = max(doc_by_cat, key=doc_by_cat.get) if doc_by_cat else ""
        min_cat = min(doc_by_cat, key=doc_by_cat.get) if doc_by_cat else ""
        part += (
            f"  [分析提示: 最多類別為「{max_cat}」"
            f"({doc_by_cat.get(max_cat, 0)} 筆)，"
            f"最少為「{min_cat}」"
            f"({doc_by_cat.get(min_cat, 0)} 筆)，"
            f"請比較各類別比例並指出分布特徵]\n"
        )
    if len(part) <= remaining_chars:
        parts.append(part)
    try:
        from app.services.ai.core.response_enricher import enrich_document_results
        docs_list = result.get("documents", [])
        if docs_list:
            enriched = enrich_document_results(docs_list)
            analysis = f"\n[分析摘要] {enriched.get('analysis_hint', '')}\n"
            if _current_len(parts) + len(analysis) <= remaining_chars:
                parts.append(analysis)
    except Exception:
        pass
    return "".join(parts)


# --- summarize handlers ---

def summarize_search_documents(result: Dict[str, Any]) -> str:
    count = result.get("count", 0)
    total = result.get("total", 0)
    if count == 0:
        return "未找到匹配公文"
    docs = result.get("documents", [])
    first_subjects = [d.get("subject", "")[:30] for d in docs[:3]]
    return f"找到 {total} 篇公文（顯示 {count} 篇）: {'; '.join(first_subjects)}"


def summarize_search_dispatch_orders(result: Dict[str, Any]) -> str:
    count = result.get("count", 0)
    total = result.get("total", 0)
    if count == 0:
        return "未找到匹配派工單"
    orders = result.get("dispatch_orders", [])
    linked_docs = result.get("linked_documents", [])
    first_items = [
        f"{d.get('dispatch_no', '')}({d.get('project_name', '')[:20]})"
        for d in orders[:3]
    ]
    summary = f"找到 {total} 筆派工單（顯示 {count} 筆）: {'; '.join(first_items)}"
    if linked_docs:
        summary += f"（含 {len(linked_docs)} 筆關聯公文）"
        for doc in linked_docs:
            dn = doc.get("doc_number", "?")
            subj = (doc.get("subject") or "")[:50]
            dt = doc.get("doc_date", "")
            summary += f"\n  - [{dn}] {subj} ({dt})"
    return summary


def summarize_find_similar(result: Dict[str, Any]) -> str:
    count = result.get("count", 0)
    return f"找到 {count} 篇相似公文" if count > 0 else "未找到相似公文"


def summarize_get_statistics(result: Dict[str, Any]) -> str:
    stats = result.get("stats", {})
    return (
        f"實體 {stats.get('total_entities', 0)} 個, "
        f"關係 {stats.get('total_relationships', 0)} 條"
    )


# Registry: tool_name -> (format_handler, summarize_handler)
DOC_FORMAT_HANDLERS = {
    "search_documents": format_search_documents,
    "search_dispatch_orders": format_search_dispatch_orders,
    "find_similar": format_find_similar,
    "get_statistics": format_get_statistics,
}

DOC_SUMMARIZE_HANDLERS = {
    "search_documents": summarize_search_documents,
    "search_dispatch_orders": summarize_search_dispatch_orders,
    "find_similar": summarize_find_similar,
    "get_statistics": summarize_get_statistics,
}

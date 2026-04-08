"""
工具結果格式化 — 業務/財務/系統健康/圖表/公文配對

Extracted from tool_result_formatter.py
"""

import json
from typing import Any, Dict, List


def _current_len(parts: List[str]) -> int:
    return sum(len(p) for p in parts)


def format_draw_diagram(result: Dict[str, Any], remaining_chars: int) -> str:
    parts: list[str] = []
    dtype = result.get("diagram_type", "er")
    mermaid = result.get("mermaid", "")
    related = result.get("related_entities", [])
    part = f"[圖表] 類型: {dtype}\n"
    if related:
        part += f"  涵蓋實體: {', '.join(str(e) for e in related[:10])}\n"
    if mermaid:
        part += f"  Mermaid 程式碼已產生 ({len(mermaid)} 字元)\n"
    if len(part) <= remaining_chars:
        parts.append(part)
    return "".join(parts)


def format_find_correspondence(result: Dict[str, Any], remaining_chars: int) -> str:
    parts: list[str] = []
    pairs = result.get("pairs", [])
    part = f"[公文配對] 共找到 {len(pairs)} 組收發對應\n"
    for p in pairs[:5]:
        conf = p.get("confidence", "")
        part += (
            f"  - {p.get('incoming_doc', '')} ↔ {p.get('outgoing_doc', '')} "
            f"({conf})\n"
        )
    shared = result.get("shared_entities", [])
    if shared:
        part += f"  共同實體: {', '.join(str(e) for e in shared[:8])}\n"
    if len(part) <= remaining_chars:
        parts.append(part)
    return "".join(parts)


def format_get_system_health(result: Dict[str, Any], remaining_chars: int) -> str:
    parts: list[str] = []
    summary = result.get("summary", {})
    db_info = summary.get("database", {})
    res_info = summary.get("resources", {})
    dq_info = summary.get("data_quality", {})
    backup_info = summary.get("backup", {})
    part = (
        f"[系統健康]\n"
        f"  資料庫: {db_info.get('status', 'unknown')}\n"
        f"  CPU: {res_info.get('cpu_percent', 'N/A')}% | "
        f"記憶體: {res_info.get('memory_percent', 'N/A')}%\n"
    )
    if dq_info:
        part += (
            f"  資料品質: FK覆蓋率 {dq_info.get('fk_coverage', 'N/A')} | "
            f"NER覆蓋率 {dq_info.get('ner_coverage', 'N/A')}\n"
        )
    if backup_info:
        part += f"  備份: {backup_info.get('status', 'N/A')}\n"
    benchmarks = summary.get("benchmarks", {})
    if benchmarks and not benchmarks.get("error"):
        part += f"  效能基準: 查詢延遲 {benchmarks.get('query_latency_ms', 'N/A')}ms\n"
    recommendations = summary.get("recommendations", [])
    if recommendations:
        part += "  建議:\n"
        for rec in recommendations[:5]:
            part += f"    - {rec}\n"
    if len(part) <= remaining_chars:
        parts.append(part)
    return "".join(parts)


def format_get_financial_summary(result: Dict[str, Any], remaining_chars: int) -> str:
    parts: list[str] = []
    budget = result.get("budget", 0)
    actual = result.get("actual_cost", 0)
    revenue = result.get("revenue", 0)
    profit = result.get("profit", 0)
    part = f"[財務彙總]\n"
    if budget:
        exec_rate = (actual / budget * 100) if budget else 0
        variance = ((actual - budget) / budget * 100) if budget else 0
        part += (
            f"  預算: NT${budget:,.0f} | 實際支出: NT${actual:,.0f}\n"
            f"  預算執行率: {exec_rate:.0f}%\n"
        )
        part += f"  [分析提示: 偏差 {variance:+.1f}%"
        if variance > 10:
            part += "，已超預算，請標記為風險"
        elif variance < -20:
            part += "，執行率偏低，請建議加速"
        part += "]\n"
    if revenue:
        part += f"  營收: NT${revenue:,.0f} | 利潤: NT${profit:,.0f}\n"
        if revenue > 0:
            margin = profit / revenue * 100
            part += f"  [分析提示: 利潤率 {margin:.1f}%]\n"
    for key in ("projects", "summary", "details"):
        val = result.get(key)
        if val:
            part += f"  {key}: {json.dumps(val, ensure_ascii=False)[:500]}\n"
    if len(part) <= remaining_chars:
        parts.append(part)
    try:
        from app.services.ai.response_enricher import enrich_financial_results
        enriched = enrich_financial_results(result)
        analysis = f"\n[分析摘要] {enriched.get('financial_hint', '')}\n"
        if _current_len(parts) + len(analysis) <= remaining_chars:
            parts.append(analysis)
    except Exception:
        pass
    return "".join(parts)


def format_get_expense_overview(result: Dict[str, Any], remaining_chars: int) -> str:
    parts: list[str] = []
    expenses = result.get("expenses", result.get("items", []))
    summary_text = result.get("summary", "")
    if summary_text:
        part = f"[費用] {summary_text}\n"
    else:
        part = f"[費用] 共 {result.get('count', len(expenses))} 筆\n"
    for i, e in enumerate(expenses[:10], 1):
        inv = e.get("inv_num", "") or e.get("invoice_number", "")
        amt = e.get("total_amount", 0) or e.get("amount", 0)
        status = e.get("status") or e.get("approval_status", "")
        case = e.get("case_code", "")
        part += f"  [{i}] {inv} NT${float(amt):,.0f} ({status}) {case}\n"
        if _current_len(parts) + len(part) > remaining_chars:
            break
    if len(part) <= remaining_chars:
        parts.append(part)
    try:
        from app.services.ai.response_enricher import enrich_expense_results
        enriched = enrich_expense_results(expenses)
        analysis = f"\n[分析摘要] {enriched.get('analysis_hint', '')}\n"
        if _current_len(parts) + len(analysis) <= remaining_chars:
            parts.append(analysis)
    except Exception:
        pass
    return "".join(parts)


def format_get_project_progress(result: Dict[str, Any], remaining_chars: int) -> str:
    parts: list[str] = []
    project = result.get("project", result)
    milestones = result.get("milestones", [])
    name = project.get("project_name") or project.get("case_name") or project.get("name", "")
    part = f"[專案進度] {name}\n"
    status = project.get("status", "")
    if status:
        part += f"  狀態: {status}\n"
    for m in milestones[:8]:
        m_status = m.get("status", "")
        icon = "\u2705" if m_status == "completed" else "\U0001f504"
        part += f"  {icon} {m.get('name', m.get('milestone_name', ''))} (期限: {m.get('due_date', 'N/A')})\n"
    if len(part) <= remaining_chars:
        parts.append(part)
    try:
        from app.services.ai.response_enricher import enrich_project_results
        enriched = enrich_project_results(project, milestones)
        analysis = f"\n[分析摘要] {enriched.get('progress_hint', '')}\n"
        if _current_len(parts) + len(analysis) <= remaining_chars:
            parts.append(analysis)
    except Exception:
        pass
    return "".join(parts)


# Registry
BUSINESS_FORMAT_HANDLERS = {
    "draw_diagram": format_draw_diagram,
    "find_correspondence": format_find_correspondence,
    "get_system_health": format_get_system_health,
    "get_financial_summary": format_get_financial_summary,
    "get_expense_overview": format_get_expense_overview,
    "list_pending_expenses": format_get_expense_overview,
    "get_project_progress": format_get_project_progress,
}

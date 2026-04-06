"""
Response Enricher -- Pre-compute analysis for Gemma 4 to narrate.

Philosophy: Let Python do the computing, let Gemma 4 do the narrating.
Instead of asking Gemma 4 to calculate "completion rate is 40%",
WE calculate it and give Gemma 4 the result to incorporate.

This module provides enrichment functions for each business domain:
- Dispatch orders (progress, overdue, handler distribution)
- Financial data (budget execution, profit margin, variance)
- Documents (type/status distribution, pending count)
- Projects (milestone progress, risk indicators)
- Expenses (approval status, category breakdown)
- Assets (category distribution, depreciation)
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dispatch enrichment
# ---------------------------------------------------------------------------

def enrich_dispatch_results(raw_results: list) -> dict:
    """Pre-compute dispatch analysis metrics.

    Args:
        raw_results: List of dispatch order dicts from search_dispatch_orders.

    Returns:
        Enriched dict with pre-computed metrics for Gemma 4.
    """
    total = len(raw_results)
    if total == 0:
        return {
            "total": 0,
            "completed": 0,
            "in_progress": 0,
            "overdue": 0,
            "completion_rate": "0%",
            "overdue_pct": "0%",
            "top_overdue": [],
            "upcoming_deadlines": [],
            "handlers": [],
            "handler_distribution": {},
            "analysis_hint": "無派工紀錄",
        }

    completed = sum(
        1 for d in raw_results
        if d.get("status") == "completed" or d.get("batch_no")
    )
    overdue = sum(1 for d in raw_results if _get_overdue_days(d) > 0)
    in_progress = total - completed - overdue

    # Handler distribution
    handler_counts: dict[str, int] = {}
    for d in raw_results:
        handler = d.get("case_handler") or d.get("handler") or ""
        if handler:
            handler_counts[handler] = handler_counts.get(handler, 0) + 1

    # Top overdue items (sorted by most overdue first)
    overdue_items = sorted(
        [d for d in raw_results if _get_overdue_days(d) > 0],
        key=lambda x: -_get_overdue_days(x),
    )[:5]

    top_overdue = []
    for d in overdue_items:
        top_overdue.append({
            "dispatch_no": d.get("dispatch_no", ""),
            "project_name": d.get("project_name", ""),
            "handler": d.get("case_handler") or d.get("handler", ""),
            "overdue_days": _get_overdue_days(d),
            "work_type": d.get("work_type", ""),
        })

    # Upcoming deadlines (next 7 days)
    upcoming = sorted(
        [d for d in raw_results if 0 < _get_days_left(d) <= 7],
        key=lambda x: _get_days_left(x),
    )[:5]

    upcoming_deadlines = []
    for d in upcoming:
        upcoming_deadlines.append({
            "dispatch_no": d.get("dispatch_no", ""),
            "project_name": d.get("project_name", ""),
            "days_left": _get_days_left(d),
            "deadline": d.get("deadline", ""),
        })

    return {
        "total": total,
        "completed": completed,
        "in_progress": max(0, in_progress),
        "overdue": overdue,
        "completion_rate": f"{completed / total * 100:.0f}%",
        "overdue_pct": f"{overdue / total * 100:.0f}%" if overdue else "0%",
        "top_overdue": top_overdue,
        "upcoming_deadlines": upcoming_deadlines,
        "handlers": list(handler_counts.keys()),
        "handler_distribution": handler_counts,
        "analysis_hint": _generate_dispatch_hint(total, completed, overdue),
    }


def _get_overdue_days(d: dict) -> int:
    """Extract overdue days from dispatch dict."""
    if d.get("overdue_days"):
        return int(d["overdue_days"])
    deadline = d.get("deadline") or d.get("contract_deadline")
    if not deadline:
        return 0
    try:
        if isinstance(deadline, str):
            dl = datetime.strptime(deadline[:10], "%Y-%m-%d").date()
        elif isinstance(deadline, datetime):
            dl = deadline.date()
        elif isinstance(deadline, date):
            dl = deadline
        else:
            return 0
        delta = (date.today() - dl).days
        # Only overdue if not completed
        if delta > 0 and not d.get("batch_no") and d.get("status") != "completed":
            return delta
    except (ValueError, TypeError):
        pass
    return 0


def _get_days_left(d: dict) -> int:
    """Calculate days until deadline."""
    if d.get("days_left") is not None:
        return int(d["days_left"])
    deadline = d.get("deadline") or d.get("contract_deadline")
    if not deadline:
        return 999
    try:
        if isinstance(deadline, str):
            dl = datetime.strptime(deadline[:10], "%Y-%m-%d").date()
        elif isinstance(deadline, datetime):
            dl = deadline.date()
        elif isinstance(deadline, date):
            dl = deadline
        else:
            return 999
        return (dl - date.today()).days
    except (ValueError, TypeError):
        return 999


def _generate_dispatch_hint(total: int, completed: int, overdue: int) -> str:
    """Generate plain-text analysis hint for Gemma 4."""
    hints = []
    rate = completed / total * 100 if total else 0
    if rate >= 80:
        hints.append("進度良好，大部分派工已完成")
    elif rate >= 50:
        hints.append("進度正常，過半數已完成")
    elif rate >= 20:
        hints.append("進度落後，需加速推進")
    else:
        hints.append("進度嚴重落後，需立即檢討")

    if overdue > 0:
        hints.append(f"有 {overdue} 筆逾期需立即處理")
    if overdue == 0 and rate < 100:
        hints.append("目前無逾期項目")

    return "；".join(hints)


# ---------------------------------------------------------------------------
# Financial enrichment
# ---------------------------------------------------------------------------

def enrich_financial_results(raw_results: dict) -> dict:
    """Pre-compute financial metrics for Gemma 4 narration.

    Handles both single-project and company-wide financial summaries.
    """
    result = {**raw_results}

    budget = _safe_float(raw_results.get("budget") or raw_results.get("contract_amount"))
    actual = _safe_float(raw_results.get("actual_cost") or raw_results.get("total_expense"))
    revenue = _safe_float(raw_results.get("revenue") or raw_results.get("total_income"))
    billed = _safe_float(raw_results.get("billed") or raw_results.get("total_billed"))
    received = _safe_float(raw_results.get("received") or raw_results.get("total_received"))

    # Budget analysis
    if budget > 0:
        result["budget_execution_rate"] = f"{actual / budget * 100:.1f}%"
        result["budget_variance"] = f"NT${actual - budget:+,.0f}"
        if actual > budget:
            result["budget_status"] = "超預算"
        elif actual > budget * 0.9:
            result["budget_status"] = "接近預算上限"
        elif actual > budget * 0.5:
            result["budget_status"] = "預算內"
        else:
            result["budget_status"] = "預算執行率偏低"
    else:
        result["budget_execution_rate"] = "N/A"
        result["budget_variance"] = "N/A"
        result["budget_status"] = "未設預算"

    # Profit analysis
    if revenue > 0:
        profit = revenue - actual
        result["profit"] = f"NT${profit:,.0f}"
        result["profit_margin"] = f"{profit / revenue * 100:.1f}%"
        if profit < 0:
            result["profit_status"] = "虧損"
        elif profit / revenue < 0.1:
            result["profit_status"] = "微利"
        elif profit / revenue < 0.25:
            result["profit_status"] = "正常"
        else:
            result["profit_status"] = "高利潤"
    else:
        result["profit_margin"] = "N/A"
        result["profit_status"] = "無收入資料"

    # Billing analysis
    if billed > 0 and budget > 0:
        result["billed_pct"] = f"{billed / budget * 100:.1f}%"
    else:
        result["billed_pct"] = "N/A"

    if billed > 0 and received >= 0:
        result["pending_amount"] = f"NT${billed - received:,.0f}"
        result["collection_rate"] = f"{received / billed * 100:.1f}%" if billed > 0 else "N/A"
    else:
        result["pending_amount"] = "NT$0"
        result["collection_rate"] = "N/A"

    # Overall financial hint
    hints = []
    if budget > 0 and actual > budget:
        hints.append(f"超預算 {(actual - budget) / budget * 100:.0f}%")
    if billed > 0 and received < billed * 0.5:
        hints.append("收款率低於 50%，需催款")
    if revenue > 0 and (revenue - actual) / revenue < 0.1:
        hints.append("利潤率偏低")
    result["financial_hint"] = "；".join(hints) if hints else "財務狀況正常"

    return result


# ---------------------------------------------------------------------------
# Document enrichment
# ---------------------------------------------------------------------------

def enrich_document_results(docs: list) -> dict:
    """Pre-compute document statistics for Gemma 4."""
    total = len(docs)
    if total == 0:
        return {
            "total": 0,
            "by_type": {},
            "by_status": {},
            "most_common_type": "無",
            "pending_count": 0,
            "type_breakdown_text": "無公文資料",
            "status_breakdown_text": "無公文資料",
            "analysis_hint": "查詢未找到符合條件的公文",
        }

    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    senders: dict[str, int] = {}

    for d in docs:
        t = d.get("doc_type") or "其他"
        by_type[t] = by_type.get(t, 0) + 1
        s = d.get("status") or "unknown"
        by_status[s] = by_status.get(s, 0) + 1
        sender = d.get("sender") or ""
        if sender:
            senders[sender] = senders.get(sender, 0) + 1

    most_common_type = max(by_type, key=by_type.get) if by_type else "無"
    pending = by_status.get("pending", 0) + by_status.get("待處理", 0)

    # Generate human-readable breakdowns
    type_parts = [f"{k}: {v} 筆 ({v / total * 100:.0f}%)" for k, v in
                  sorted(by_type.items(), key=lambda x: -x[1])]
    status_parts = [f"{k}: {v} 筆" for k, v in
                    sorted(by_status.items(), key=lambda x: -x[1])]

    # Top senders
    top_senders = sorted(senders.items(), key=lambda x: -x[1])[:5]

    hints = []
    if pending > 0:
        hints.append(f"{pending} 筆待處理公文需關注")
    if len(by_type) == 1:
        hints.append(f"全部為「{most_common_type}」類型")
    else:
        hints.append(f"最多為「{most_common_type}」({by_type[most_common_type]} 筆)")

    return {
        "total": total,
        "by_type": by_type,
        "by_status": by_status,
        "most_common_type": most_common_type,
        "pending_count": pending,
        "top_senders": top_senders,
        "type_breakdown_text": "、".join(type_parts),
        "status_breakdown_text": "、".join(status_parts),
        "analysis_hint": "；".join(hints) if hints else "公文分布正常",
    }


# ---------------------------------------------------------------------------
# Project progress enrichment
# ---------------------------------------------------------------------------

def enrich_project_results(project: dict, milestones: Optional[list] = None) -> dict:
    """Pre-compute project progress metrics."""
    result = {**project}

    # Milestone analysis
    if milestones:
        total_ms = len(milestones)
        completed_ms = sum(1 for m in milestones if m.get("status") == "completed")
        overdue_ms = sum(1 for m in milestones if _is_milestone_overdue(m))

        result["milestone_total"] = total_ms
        result["milestone_completed"] = completed_ms
        result["milestone_overdue"] = overdue_ms
        result["milestone_progress"] = f"{completed_ms / total_ms * 100:.0f}%" if total_ms else "0%"

        # Milestone summary text
        ms_parts = []
        for m in sorted(milestones, key=lambda x: x.get("due_date", "") or "9999"):
            status_icon = "✅" if m.get("status") == "completed" else (
                "🔴" if _is_milestone_overdue(m) else "🔄"
            )
            ms_parts.append(
                f"{status_icon} {m.get('name', '')} "
                f"(期限: {m.get('due_date', 'N/A')})"
            )
        result["milestone_summary_text"] = "\n".join(ms_parts[:10])

        # Progress hint
        if overdue_ms > 0:
            result["progress_hint"] = f"有 {overdue_ms} 個里程碑逾期，需立即處理"
        elif completed_ms == total_ms:
            result["progress_hint"] = "所有里程碑已完成"
        else:
            result["progress_hint"] = f"進度正常，{completed_ms}/{total_ms} 已完成"
    else:
        result["milestone_summary_text"] = "無里程碑資料"
        result["progress_hint"] = "無里程碑可追蹤"

    return result


def _is_milestone_overdue(m: dict) -> bool:
    """Check if a milestone is overdue."""
    if m.get("status") == "completed":
        return False
    due = m.get("due_date")
    if not due:
        return False
    try:
        if isinstance(due, str):
            due_date = datetime.strptime(due[:10], "%Y-%m-%d").date()
        else:
            due_date = due
        return date.today() > due_date
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Expense enrichment
# ---------------------------------------------------------------------------

def enrich_expense_results(expenses: list) -> dict:
    """Pre-compute expense review metrics."""
    total = len(expenses)
    if total == 0:
        return {
            "total": 0,
            "pending_count": 0,
            "pending_amount": "NT$0",
            "verified_count": 0,
            "verified_amount": "NT$0",
            "rejected_count": 0,
            "category_breakdown": {},
            "category_breakdown_text": "無費用資料",
            "analysis_hint": "無費用紀錄",
        }

    by_status: dict[str, list] = {"pending": [], "verified": [], "rejected": []}
    by_category: dict[str, float] = {}

    for e in expenses:
        status = e.get("status") or e.get("approval_status") or "pending"
        amount = _safe_float(e.get("total_amount") or e.get("amount"))
        if status in by_status:
            by_status[status].append(amount)
        category = e.get("category") or e.get("expense_type") or "其他"
        by_category[category] = by_category.get(category, 0) + amount

    pending_amounts = by_status["pending"]
    verified_amounts = by_status["verified"]

    cat_parts = [
        f"{k}: NT${v:,.0f}" for k, v in
        sorted(by_category.items(), key=lambda x: -x[1])
    ]

    hints = []
    if len(pending_amounts) > 5:
        hints.append(f"累積 {len(pending_amounts)} 筆待審核，建議儘快處理")
    total_pending = sum(pending_amounts)
    if total_pending > 100000:
        hints.append(f"待審核金額達 NT${total_pending:,.0f}，金額較大")

    return {
        "total": total,
        "pending_count": len(pending_amounts),
        "pending_amount": f"NT${sum(pending_amounts):,.0f}",
        "verified_count": len(verified_amounts),
        "verified_amount": f"NT${sum(verified_amounts):,.0f}",
        "rejected_count": len(by_status["rejected"]),
        "category_breakdown": by_category,
        "category_breakdown_text": "、".join(cat_parts) if cat_parts else "無分類",
        "analysis_hint": "；".join(hints) if hints else "費用審核正常",
    }


# ---------------------------------------------------------------------------
# Asset enrichment
# ---------------------------------------------------------------------------

def enrich_asset_results(assets: list) -> dict:
    """Pre-compute asset statistics."""
    total = len(assets)
    if total == 0:
        return {
            "total": 0,
            "total_value": "NT$0",
            "by_category": {},
            "by_status": {},
            "analysis_hint": "無資產資料",
        }

    by_category: dict[str, int] = {}
    by_status: dict[str, int] = {}
    total_value = 0.0

    for a in assets:
        cat = a.get("category") or "未分類"
        by_category[cat] = by_category.get(cat, 0) + 1
        status = a.get("status") or "unknown"
        by_status[status] = by_status.get(status, 0) + 1
        total_value += _safe_float(a.get("purchase_amount") or a.get("value"))

    idle = by_status.get("idle", 0)
    hints = []
    if idle > 0 and total > 0:
        idle_rate = idle / total * 100
        if idle_rate > 20:
            hints.append(f"閒置率 {idle_rate:.0f}%，建議盤點調配")
    repair = by_status.get("repair", 0)
    if repair > 0:
        hints.append(f"{repair} 項維修中")

    return {
        "total": total,
        "total_value": f"NT${total_value:,.0f}",
        "by_category": by_category,
        "by_status": by_status,
        "in_use": by_status.get("in_use", 0),
        "idle": idle,
        "repair": repair,
        "analysis_hint": "；".join(hints) if hints else "資產狀況正常",
    }


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _safe_float(val: Any) -> float:
    """Safely convert value to float."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

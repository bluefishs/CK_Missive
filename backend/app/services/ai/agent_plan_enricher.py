"""
Agent 計劃充實器 — 合併 hints + 強制工具注入

從 agent_planner.py 提取的計劃後處理邏輯：
- _merge_hints_into_plan: 合併預處理 hints 到 LLM plan
- _build_forced_calls: 空計劃時的強制工具呼叫
- _build_fallback_plan: 規劃失敗回退

Version: 1.0.0 (拆分自 agent_planner v2.9.0)
Created: 2026-03-25
"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# 統計問題關鍵字
_STATS_KEYWORDS = {"多少筆", "總數", "有幾筆", "幾筆", "共有", "共幾", "總共"}


def merge_hints_into_plan(
    plan: Dict[str, Any],
    hints: Dict[str, Any],
    sanitized_q: str,
) -> Dict[str, Any]:
    """合併預處理 hints 到 LLM 生成的 plan"""
    if not hints:
        return plan

    # ── 統計快速路徑 ──
    if any(kw in sanitized_q for kw in _STATS_KEYWORDS):
        plan["tool_calls"] = [{"name": "get_statistics", "params": {}}]
        logger.info("統計快速路徑: 只用 get_statistics")
        return plan

    if plan.get("tool_calls"):
        _enrich_search_documents(plan, hints)
        _inject_dispatch_if_needed(plan, hints, sanitized_q)
        _inject_search_docs_if_missing(plan, hints)

    # 空計劃修復
    if not plan.get("tool_calls"):
        forced_calls = build_forced_calls(hints, sanitized_q)
        if forced_calls:
            plan["tool_calls"] = forced_calls
            logger.info(
                "Force-injected %d tool(s) from hints: %s",
                len(forced_calls),
                [tc["name"] for tc in forced_calls],
            )

    return plan


def _enrich_search_documents(plan: Dict[str, Any], hints: Dict[str, Any]) -> None:
    """補充 LLM 未抽取的篩選欄位到 search_documents"""
    for tc in plan["tool_calls"]:
        if tc.get("name") == "search_documents":
            params = tc.get("params", {})
            for key in ("sender", "receiver", "doc_type", "date_from", "date_to", "status"):
                if key not in params and key in hints:
                    params[key] = hints[key]
            if "keywords" not in params and "keywords" in hints:
                params["keywords"] = hints["keywords"]
            elif "keywords" in params and "keywords" in hints:
                existing = set(params["keywords"])
                for kw in hints["keywords"]:
                    if kw not in existing:
                        params["keywords"].append(kw)
            tc["params"] = params


def _inject_dispatch_if_needed(
    plan: Dict[str, Any], hints: Dict[str, Any], sanitized_q: str,
) -> None:
    """意圖偵測到 dispatch_order → 確保有 search_dispatch_orders"""
    has_dispatch = any(
        tc.get("name") == "search_dispatch_orders"
        for tc in plan["tool_calls"]
    )
    if hints.get("related_entity") == "dispatch_order" and not has_dispatch:
        dp: Dict[str, Any] = {"limit": 10}
        match = re.search(r"派工單[號]?\s*(\d{2,4})", sanitized_q)
        if match:
            dp["dispatch_no"] = match.group(1)
        elif hints.get("keywords"):
            dp["search"] = " ".join(hints["keywords"])
        plan["tool_calls"].insert(0, {"name": "search_dispatch_orders", "params": dp})
        logger.info("Auto-injected search_dispatch_orders from intent hint")


def _inject_search_docs_if_missing(plan: Dict[str, Any], hints: Dict[str, Any]) -> None:
    """hints 有 keywords 但 plan 沒有 search_documents → 強制注入"""
    has_search = any(
        tc.get("name") == "search_documents"
        for tc in plan["tool_calls"]
    )
    if not has_search and hints.get("keywords"):
        params: Dict[str, Any] = {"keywords": hints["keywords"], "limit": 8}
        for key in ("sender", "receiver", "doc_type", "date_from", "date_to"):
            if hints.get(key):
                params[key] = hints[key]
        plan["tool_calls"].insert(0, {"name": "search_documents", "params": params})
        logger.info("Auto-injected search_documents from hints keywords: %s", hints["keywords"])


def build_forced_calls(
    hints: Dict[str, Any],
    sanitized_q: str,
) -> List[Dict[str, Any]]:
    """從 hints 建構強制工具呼叫（LLM 回傳空計劃時使用）"""
    forced: List[Dict[str, Any]] = []

    if hints.get("related_entity") == "dispatch_order":
        dp: Dict[str, Any] = {"limit": 10}
        match = re.search(r"派工單[號]?\s*(\d{2,4})", sanitized_q)
        if match:
            dp["dispatch_no"] = match.group(1)
        elif hints.get("keywords"):
            dp["search"] = " ".join(hints["keywords"])
        else:
            dp["search"] = sanitized_q[:100]
        forced.append({"name": "search_dispatch_orders", "params": dp})

    if hints.get("keywords") or any(
        hints.get(k) for k in ("sender", "receiver", "doc_type", "date_from", "date_to")
    ):
        doc_params: Dict[str, Any] = {"limit": 10}
        if hints.get("keywords"):
            doc_params["keywords"] = hints["keywords"]
        for key in ("sender", "receiver", "doc_type", "date_from", "date_to"):
            if key in hints:
                doc_params[key] = hints[key]
        forced.append({"name": "search_documents", "params": doc_params})

    return forced


def build_fallback_plan(
    question: str,
    hints: Dict[str, Any],
) -> Dict[str, Any]:
    """規劃失敗時的回退計劃"""
    params: Dict[str, Any] = {"limit": 10}
    if hints.get("keywords"):
        params["keywords"] = hints["keywords"]
    else:
        params["keywords"] = [question]
    for key in ("sender", "receiver", "doc_type", "date_from", "date_to"):
        if key in hints:
            params[key] = hints[key]

    return {
        "reasoning": "規劃失敗，使用預處理線索搜尋",
        "tool_calls": [{"name": "search_documents", "params": params}],
    }

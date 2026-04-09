"""
工具鏈參數解析器 — 自動從前輪工具結果提取關鍵值，注入後續工具參數

對標 OpenClaw Chain-of-Tools：讓工具結果成為下一輪工具的輸入，
實現 search → detail → navigate 等多步推理資料流。

Version: 1.0.0
Created: 2026-03-15
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def extract_chain_context(tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    從已執行工具結果中萃取可鏈式傳遞的上下文。

    Returns:
        {
            "entity_ids": [int, ...],
            "entity_names": [str, ...],
            "document_ids": [int, ...],
            "dispatch_ids": [int, ...],
            "project_ids": [int, ...],
            "project_names": [str, ...],
            "agency_names": [str, ...],
            "keywords": [str, ...],
        }
    """
    ctx: Dict[str, List] = {
        "entity_ids": [],
        "entity_names": [],
        "document_ids": [],
        "dispatch_ids": [],
        "project_ids": [],
        "project_names": [],
        "agency_names": [],
        "keywords": [],
    }

    for tr in tool_results:
        tool = tr.get("tool", "")
        result = tr.get("result", {})
        if result.get("error"):
            continue

        if tool == "search_entities":
            for e in result.get("entities", [])[:5]:
                if e.get("id"):
                    ctx["entity_ids"].append(e["id"])
                if e.get("name"):
                    ctx["entity_names"].append(e["name"])
                etype = e.get("entity_type", "")
                if etype in ("org", "agency") and e.get("name"):
                    ctx["agency_names"].append(e["name"])

        elif tool == "search_documents":
            for doc in result.get("documents", [])[:5]:
                if doc.get("id"):
                    ctx["document_ids"].append(doc["id"])
                sender = doc.get("sender") or doc.get("normalized_sender")
                if sender:
                    ctx["agency_names"].append(sender)

        elif tool == "search_dispatch_orders":
            for d in result.get("dispatch_orders", [])[:5]:
                if d.get("id"):
                    ctx["dispatch_ids"].append(d["id"])
                if d.get("contract_project_id"):
                    ctx["project_ids"].append(d["contract_project_id"])
                if d.get("project_name"):
                    ctx["project_names"].append(d["project_name"])

        elif tool == "get_entity_detail":
            entity = result.get("entity", {})
            if entity.get("id"):
                ctx["entity_ids"].append(entity["id"])
            for rel in result.get("relations", [])[:3]:
                target = rel.get("target_name") or rel.get("source_name")
                if target:
                    ctx["entity_names"].append(target)

        elif tool in ("search_projects", "get_contract_summary"):
            for p in result.get("projects", [])[:3]:
                if p.get("id"):
                    ctx["project_ids"].append(p["id"])
                if p.get("name"):
                    ctx["project_names"].append(p["name"])

    # Deduplicate while preserving order
    for key in ctx:
        seen = set()
        deduped = []
        for v in ctx[key]:
            if v not in seen:
                seen.add(v)
                deduped.append(v)
        ctx[key] = deduped

    return ctx


def resolve_chain_params(
    tool_call: Dict[str, Any],
    chain_ctx: Dict[str, Any],
) -> Dict[str, Any]:
    """
    根據鏈式上下文自動補全工具參數。

    規則：
    - get_entity_detail: 自動填入第一個未使用的 entity_id
    - navigate_graph: 自動填入 source/target entity_id
    - find_correspondence: 自動填入 dispatch_id
    - find_similar: 自動填入 document_id
    - summarize_entity: 自動填入 entity_id
    - explore_entity_path: 自動填入 start_entity_id
    - search_entities: 從已知 project/agency names 補充 query
    - draw_diagram: 從已知 scope 推斷
    """
    name = tool_call.get("name", "")
    params = dict(tool_call.get("params", {}))

    if name == "get_entity_detail":
        if "entity_id" not in params and chain_ctx.get("entity_ids"):
            params["entity_id"] = chain_ctx["entity_ids"][0]

    elif name == "navigate_graph":
        if "source_id" not in params and len(chain_ctx.get("entity_ids", [])) >= 2:
            params["source_id"] = chain_ctx["entity_ids"][0]
            params["target_id"] = chain_ctx["entity_ids"][1]
        elif "source_id" not in params and chain_ctx.get("entity_ids"):
            params["source_id"] = chain_ctx["entity_ids"][0]

    elif name == "find_correspondence":
        if "dispatch_id" not in params and chain_ctx.get("dispatch_ids"):
            params["dispatch_id"] = chain_ctx["dispatch_ids"][0]

    elif name == "find_similar":
        if "document_id" not in params and chain_ctx.get("document_ids"):
            params["document_id"] = chain_ctx["document_ids"][0]

    elif name == "summarize_entity":
        if "entity_id" not in params and chain_ctx.get("entity_ids"):
            params["entity_id"] = chain_ctx["entity_ids"][0]

    elif name == "explore_entity_path":
        if "start_entity_id" not in params and chain_ctx.get("entity_ids"):
            params["start_entity_id"] = chain_ctx["entity_ids"][0]

    elif name == "search_entities":
        if "query" not in params:
            names = chain_ctx.get("project_names", []) + chain_ctx.get("agency_names", [])
            if names:
                params["query"] = names[0]

    return params


def enrich_plan_with_chain(
    plan: Dict[str, Any],
    tool_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    主入口：將鏈式上下文注入 plan 中的 tool_calls 參數。

    在 orchestrator 中 replan/react 之後、execute 之前呼叫，
    確保後續工具能使用前輪結果中的 ID/名稱。
    """
    if not tool_results or not plan.get("tool_calls"):
        return plan

    chain_ctx = extract_chain_context(tool_results)

    # 只有當有可用上下文時才注入
    has_context = any(bool(v) for v in chain_ctx.values())
    if not has_context:
        return plan

    enriched_calls = []
    for tc in plan["tool_calls"]:
        enriched_params = resolve_chain_params(tc, chain_ctx)
        enriched_calls.append({
            "name": tc.get("name", ""),
            "params": enriched_params,
        })

    plan["tool_calls"] = enriched_calls

    # 記錄注入狀況
    injected = []
    for orig, enriched in zip(plan.get("_original_calls", plan["tool_calls"]), enriched_calls):
        orig_params = orig.get("params", {}) if isinstance(orig, dict) else {}
        for k, v in enriched["params"].items():
            if k not in orig_params:
                injected.append(f"{enriched['name']}.{k}={v}")
    if injected:
        logger.info("Chain-of-Tools injected: %s", ", ".join(injected[:5]))

    return plan

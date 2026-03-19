"""
Agent 自動修正模組 -- 規則式工具結果評估與重試策略

從 agent_planner.py 提取，提供 6 種策略：
1. search_documents 0 結果 -> 放寬條件重試
2. search_entities 0 結果 -> 改用文件搜尋
2.5. search_documents 重試無果 -> 嘗試派工單搜尋
3. 全部無結果 -> 統計概覽
4. find_similar 錯誤 -> 改用文件搜尋
5. search_entities 有結果 -> 展開實體詳情
6. search_dispatch_orders 有結果 -> 追查收發文配對
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def auto_correct_plan(
    question: str,
    tool_results: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    規則式自我修正 -- 不需 LLM 即可快速決定重試策略

    Returns:
        修正後的 plan dict (含 tool_calls), 或 None 若不需要修正
    """
    if not tool_results:
        return None

    last = tool_results[-1]
    last_tool = last.get("tool", "")
    last_result = last.get("result", {})
    last_error = last_result.get("error")
    last_count = last_result.get("count", 0)
    used_tools = {tr["tool"] for tr in tool_results}

    # 策略 1: search_documents 返回 0 結果 -> 放寬條件重試
    doc_search_count = sum(
        1 for tr in tool_results
        if tr["tool"] == "search_documents" and tr["result"].get("count", 0) == 0
    )
    if last_tool == "search_documents" and last_count == 0 and not last_error and doc_search_count < 2:
        original_params = last.get("params", {})
        relaxed_params: Dict[str, Any] = {"keywords": [question], "limit": 8}
        if original_params.get("keywords"):
            relaxed_params["keywords"] = original_params["keywords"]

        extra_tools: List[Dict[str, Any]] = [
            {"name": "search_documents", "params": relaxed_params},
        ]
        if "search_entities" not in used_tools:
            extra_tools.append(
                {"name": "search_entities", "params": {"query": question, "limit": 10}}
            )

        return {
            "reasoning": "公文搜尋無結果，放寬條件重試（移除篩選限制）",
            "tool_calls": extra_tools,
        }

    # 策略 2: search_entities 返回 0 結果且尚未搜文件 -> 改用文件搜尋
    if last_tool == "search_entities" and last_count == 0 and not last_error:
        if "search_documents" not in used_tools:
            return {
                "reasoning": "實體搜尋無結果，改用公文全文搜尋",
                "tool_calls": [
                    {"name": "search_documents", "params": {"keywords": [question], "limit": 10}},
                ],
            }

    # 策略 2.5: search_documents 無結果且未搜尋派工單 -> 嘗試派工單搜尋
    if (
        last_tool == "search_documents"
        and last_count == 0
        and "search_dispatch_orders" not in used_tools
    ):
        return {
            "reasoning": "公文搜尋無結果，嘗試搜尋派工單紀錄",
            "tool_calls": [
                {"name": "search_dispatch_orders", "params": {"search": question, "limit": 10}},
            ],
        }

    # 策略 3: 所有工具都返回 0 結果或錯誤 -> 嘗試統計概覽
    all_empty = all(
        tr["result"].get("count", 0) == 0 or tr["result"].get("error")
        for tr in tool_results
    )
    if all_empty and "get_statistics" not in used_tools:
        return {
            "reasoning": "所有查詢均無結果，取得系統概覽供參考",
            "tool_calls": [
                {"name": "get_statistics", "params": {}},
            ],
        }

    # 策略 4: 工具執行錯誤 -> 如果是 find_similar 缺向量，改用文件搜尋
    if last_tool == "find_similar" and last_error and "search_documents" not in used_tools:
        return {
            "reasoning": f"相似公文查詢失敗（{last_error}），改用關鍵字搜尋",
            "tool_calls": [
                {"name": "search_documents", "params": {"keywords": [question], "limit": 10}},
            ],
        }

    # 策略 6: search_dispatch_orders 有結果 -> 自動追查收發文配對 + 相關實體
    if (
        last_tool == "search_dispatch_orders"
        and last_count > 0
        and not last_error
    ):
        extra_calls: List[Dict[str, Any]] = []
        dispatches = last_result.get("dispatch_orders", [])
        # 取第一筆派工單的 ID 做收發文配對
        first_dispatch = dispatches[0] if dispatches else None
        if first_dispatch and "find_correspondence" not in used_tools:
            d_id = first_dispatch.get("id")
            if d_id:
                extra_calls.append({
                    "name": "find_correspondence",
                    "params": {"dispatch_id": d_id},
                })
        # 搜尋相關實體（工程名稱、機關）
        if "search_entities" not in used_tools and first_dispatch:
            proj_name = first_dispatch.get("project_name", "")
            if proj_name:
                extra_calls.append({
                    "name": "search_entities",
                    "params": {"query": proj_name, "limit": 5},
                })
        if extra_calls:
            return {
                "reasoning": "派工單已找到，自動追查收發文配對與相關實體以提供完整簡報",
                "tool_calls": extra_calls,
            }

    # 策略 5: search_entities 有結果但未取得 detail -> 自動展開前 2 個實體
    if "get_entity_detail" not in used_tools:
        for tr in tool_results:
            if (
                tr.get("tool") == "search_entities"
                and tr["result"].get("count", 0) > 0
                and not tr["result"].get("error")
            ):
                entities = tr["result"].get("entities", [])
                detail_calls = [
                    {
                        "name": "get_entity_detail",
                        "params": {"entity_id": e.get("id")},
                    }
                    for e in entities[:2]
                    if e.get("id")
                ]
                if detail_calls:
                    return {
                        "reasoning": "實體搜尋命中，自動取得詳細關係與關聯公文",
                        "tool_calls": detail_calls,
                    }
                break

    return None

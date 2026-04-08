"""
工具結果格式化模組 — 工具上下文建構、結果摘要、品質自省

職責：
- format_tool_context: 格式化單一工具結果為上下文字串
- summarize_tool_result: 生成工具結果的簡短摘要
- self_reflect: 答案品質自省（輕量 LLM 評估）

Extracted from agent_synthesis.py v1.8.0
Refactored v2.0.0: registry-based dispatch to domain-specific formatters
"""

import asyncio
import json
import logging
from typing import Any, Dict, List

from app.services.ai.tool_result_formatters_doc import (
    DOC_FORMAT_HANDLERS,
    DOC_SUMMARIZE_HANDLERS,
)
from app.services.ai.tool_result_formatters_entity import (
    ENTITY_FORMAT_HANDLERS,
    ENTITY_SUMMARIZE_HANDLERS,
)
from app.services.ai.tool_result_formatters_business import (
    BUSINESS_FORMAT_HANDLERS,
)

logger = logging.getLogger(__name__)

# Merged format handler registry
_FORMAT_REGISTRY: Dict[str, Any] = {
    **DOC_FORMAT_HANDLERS,
    **ENTITY_FORMAT_HANDLERS,
    **BUSINESS_FORMAT_HANDLERS,
}

# Merged summarize handler registry
_SUMMARIZE_REGISTRY: Dict[str, Any] = {
    **DOC_SUMMARIZE_HANDLERS,
    **ENTITY_SUMMARIZE_HANDLERS,
}


def _format_generic(tool: str, result: Dict[str, Any], remaining_chars: int) -> str:
    """通用處理：PM/ERP/其他未明確處理的工具結果"""
    parts: list[str] = []
    part = f"[{tool}]\n"
    if result.get("summary"):
        part += f"  {result['summary']}\n"
    skip_keys = {"error", "guarded", "guard_reason", "summary"}
    for key, val in result.items():
        if key in skip_keys:
            continue
        if isinstance(val, list):
            part += f"  {key}: {len(val)} 筆\n"
            for item in val[:5]:
                if isinstance(item, dict):
                    label = (
                        item.get("name")
                        or item.get("project_name")
                        or item.get("case_code")
                        or item.get("doc_number")
                        or item.get("title")
                        or str(item)[:80]
                    )
                    part += f"    - {label}\n"
                else:
                    part += f"    - {str(item)[:80]}\n"
        elif isinstance(val, dict):
            part += f"  {key}: {json.dumps(val, ensure_ascii=False)[:200]}\n"
        elif isinstance(val, (int, float)):
            part += f"  {key}: {val:,}\n" if isinstance(val, int) else f"  {key}: {val:,.2f}\n"
        elif val is not None:
            part += f"  {key}: {str(val)[:200]}\n"
        if sum(len(p) for p in parts) + len(part) > remaining_chars:
            break
    if len(part) > len(f"[{tool}]\n") and len(part) <= remaining_chars:
        parts.append(part)
    return "".join(parts)


def format_tool_context(tool: str, result: Dict[str, Any], remaining_chars: int) -> str:
    """格式化單一工具結果為上下文字串"""
    handler = _FORMAT_REGISTRY.get(tool)
    if handler:
        return handler(result, remaining_chars)
    return _format_generic(tool, result, remaining_chars)


def summarize_tool_result(tool_name: str, result: Dict[str, Any]) -> str:
    """生成工具結果的簡短摘要"""
    if result.get("error"):
        return f"錯誤: {result['error']}"

    handler = _SUMMARIZE_REGISTRY.get(tool_name)
    if handler:
        return handler(result)

    return f"完成 (count={result.get('count', 0)})"


# ============================================================================
# 品質自省 — 對標 OpenClaw Thinking/Reflection (Phase 2C)
# ============================================================================

async def self_reflect(
    ai_connector,
    question: str,
    answer: str,
    tool_results: List[Dict[str, Any]],
    config,
) -> Dict[str, Any]:
    """
    答案品質自省 — 輕量 LLM 評估。

    Returns:
        {"score": 0-10, "issues": [...], "suggested_tools": [...]}
        失敗時回傳 {"score": 10, "issues": []}（安全預設，不觸發重試）
    """
    try:
        total_count = sum(
            tr.get("result", {}).get("count", 0) for tr in tool_results
        )
        prompt = (
            f"評估以下回答的品質（0-10 分，10=完美）：\n\n"
            f"問題：{question[:200]}\n"
            f"回答：{answer[:500]}\n"
            f"可用資料量：{total_count} 筆\n\n"
            f"評估標準：完整性、相關性、引用準確性。\n"
            f"回傳 JSON：{{\"score\": N, \"issues\": [\"問題描述\"], "
            f"\"suggested_tools\": [\"tool_name\"]}}"
        )

        response = await asyncio.wait_for(
            ai_connector.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=128,
                task_type="chat",
                response_format={"type": "json_object"},
            ),
            timeout=config.self_reflect_timeout,
        )

        from app.services.ai.agent_utils import parse_json_safe
        result = parse_json_safe(response)
        if result and "score" in result:
            return result
        return {"score": 10, "issues": []}

    except Exception as e:
        logger.debug("self_reflect failed: %s", e)
        return {"score": 10, "issues": []}

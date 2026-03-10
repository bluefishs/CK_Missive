"""
Agent 共用工具函式

- parse_json_safe: 安全解析 LLM 回傳的 JSON（容錯處理）
- sse: 格式化 SSE data line

Extracted from agent_orchestrator.py v1.8.0
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def parse_json_safe(text: str) -> Optional[Dict[str, Any]]:
    """安全解析 LLM 回傳的 JSON（容錯處理）"""
    if not text:
        return None

    # 嘗試直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 嘗試提取 ```json ... ``` 區塊
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 嘗試找第一個 { ... } 區塊
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start:brace_end + 1])
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse agent JSON: %s", text[:200])
    return None


def sse(**kwargs: Any) -> str:
    """格式化 SSE data line"""
    return f"data: {json.dumps(kwargs, ensure_ascii=False)}\n\n"


_HISTORY_CONTENT_MAX_LEN = 1000


def sanitize_history(
    history: Optional[List[Dict[str, str]]],
    max_turns: int,
) -> List[Dict[str, str]]:
    """
    清理對話歷史 — 截斷輪數與單則內容長度

    防止 Prompt Injection 透過超長歷史訊息耗盡 token 或注入指令。
    """
    if not history:
        return []
    result: List[Dict[str, str]] = []
    for turn in history[-(max_turns * 2):]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            result.append({"role": role, "content": content[:_HISTORY_CONTENT_MAX_LEN]})
    return result

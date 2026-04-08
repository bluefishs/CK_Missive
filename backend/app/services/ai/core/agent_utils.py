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


def compute_adaptive_timeout(
    base_timeout: int,
    planned_tool_count: int,
    question_length: int,
) -> float:
    """
    Compute adaptive timeout based on query complexity.

    Formula: base + (tool_count * 2) + min(question_len / 100, 5), capped at 30s.
    """
    adaptive = base_timeout + (planned_tool_count * 2) + min(question_length / 100, 5)
    return min(adaptive, 30)


def collect_sources(
    tool_name: str,
    result: Dict[str, Any],
    all_sources: List[Dict[str, Any]],
) -> None:
    """從工具結果收集來源文件"""
    if tool_name in ("search_documents", "find_similar") and result.get("documents"):
        for doc in result["documents"]:
            if not any(s.get("document_id") == doc.get("id") for s in all_sources):
                all_sources.append({
                    "document_id": doc.get("id"),
                    "doc_number": doc.get("doc_number", ""),
                    "subject": doc.get("subject", ""),
                    "doc_type": doc.get("doc_type", ""),
                    "category": doc.get("category", ""),
                    "sender": doc.get("sender", ""),
                    "receiver": doc.get("receiver", ""),
                    "doc_date": doc.get("doc_date", ""),
                    "similarity": doc.get("similarity", 0),
                })

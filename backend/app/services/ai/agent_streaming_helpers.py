"""
Agent 串流輔助模組 — 從 agent_orchestrator.py 提取

負責非核心串流路徑：
1. 閒聊對話串流 (chitchat streaming)
2. Fallback RAG 串流

Version: 1.0.0
Created: 2026-03-18
Extracted from: agent_orchestrator.py v2.5.0
"""

import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.services.ai.agent_chitchat import (
    get_smart_fallback,
    clean_chitchat_response,
    get_chat_system_prompt,
)
from app.services.ai.agent_roles import get_role_profile
from app.services.ai.agent_utils import sse, sanitize_history

logger = logging.getLogger(__name__)


async def stream_chitchat(
    ai: Any,
    config: Any,
    question: str,
    history: Optional[List[Dict[str, str]]],
    t0: float,
    context: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    閒聊模式 — 僅 1 次 LLM 呼叫，自然語言回應。

    跳過工具規劃 + 向量檢索，直接 LLM 對話。
    """
    # 發送角色身份（閒聊同樣需要前端顯示正確角色名稱）
    role = get_role_profile(context)
    yield sse(type="role", identity=role.identity, context=role.context)
    yield sse(type="thinking", step="正在回覆您...", step_index=0)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": get_chat_system_prompt(context)},
    ]
    messages.extend(sanitize_history(history, config.rag_max_history_turns))
    messages.append({"role": "user", "content": question})

    model_used = "chat"
    try:
        raw = await ai.chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=300,
            task_type="chat",
        )
        answer = clean_chitchat_response(raw, question)
        from app.services.ai.agent_post_processing import _sc2tc
        yield sse(type="token", token=_sc2tc(answer))
    except Exception as e:
        logger.warning("Chitchat failed: %s", e)
        yield sse(
            type="token",
            token=get_smart_fallback(question),
        )
        model_used = "fallback"

    yield sse(
        type="done",
        latency_ms=int((time.time() - t0) * 1000),
        model=model_used,
        tools_used=[],
        iterations=0,
    )


async def stream_fallback_rag(
    db: Any,
    question: str,
    history: Optional[List[Dict[str, str]]],
) -> AsyncGenerator[str, None]:
    """回退到基本 RAG 管線（無工具直接回答）"""
    from app.services.ai.rag_query_service import RAGQueryService

    svc = RAGQueryService(db)
    async for event in svc.stream_query(
        question=question,
        history=history,
    ):
        yield event

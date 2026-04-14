# -*- coding: utf-8 -*-
"""
Shadow trace helper — 統一 shadow_logger 呼叫 + provider 自動解析。

取代 agent_query_sync.py 三處重複的 try/except 區塊，並把 Hermes 遷移期
A/B 比對所需的 ``provider`` / ``X-Hermes-Session`` 邏輯集中在此。
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional

from app.services.ai.agent.provider_resolver import resolve_provider
from app.services.ai.agent.shadow_logger import is_enabled, log_trace

logger = logging.getLogger(__name__)


async def fire_shadow_trace(
    *,
    request: Any,
    channel: Optional[str],
    question: str,
    answer: str,
    success: bool,
    latency_ms: int,
    session_id: Optional[str] = None,
    tools_used: Optional[List[str]] = None,
    sources_count: Optional[int] = None,
    error_code: Optional[str] = None,
) -> None:
    """Fire-and-forget shadow trace。

    ``request`` 需具備 ``headers`` attribute（FastAPI Request 或 mock）。
    任何內部錯誤一律吞掉，生產流程不可受影響。
    """
    try:
        if not is_enabled():
            return

        headers = getattr(request, "headers", {}) or {}
        # headers 可能是 Starlette Headers（大小寫不敏感）或 dict
        try:
            header_dict = {k: v for k, v in headers.items()}
        except Exception:  # noqa: BLE001
            header_dict = dict(headers) if hasattr(headers, "__iter__") else {}

        provider = resolve_provider(channel=channel, headers=header_dict)
        hermes_session = (
            header_dict.get("X-Hermes-Session")
            or header_dict.get("x-hermes-session")
        )

        await log_trace(
            channel=channel,
            provider=provider,
            question=question,
            answer=answer,
            success=success,
            latency_ms=latency_ms,
            tools_used=tools_used,
            sources_count=sources_count,
            error_code=error_code,
            session_id=session_id,
            request_id=hermes_session,
        )
    except Exception as e:  # noqa: BLE001
        logger.debug("fire_shadow_trace swallowed error: %s", e)

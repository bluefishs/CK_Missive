"""
SSE (Server-Sent Events) 串流共用工具

統一 RAG / Agent 等串流端點的 event_generator 包裝與錯誤處理。

Version: 1.1.0
Created: 2026-02-27
Updated: 2026-05-08 - v1.1.0 R1 加 stream_e2e hard cutoff（ADR-0028 / ADR-0030）
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Callable, Dict, Optional

from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)

# 共用 SSE 回應標頭
# - X-Accel-Buffering: no → nginx/CF 不緩衝
# - Content-Encoding: identity → 跳過 GZipMiddleware（防 SSE chunk 被壓縮緩衝，導致前端收不到即時 event）
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
    "Content-Encoding": "identity",
}


def sse_error_event(error_msg: str, **extra: Any) -> str:
    """格式化 SSE 錯誤事件"""
    payload: Dict[str, Any] = {"type": "error", "error": error_msg, **extra}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def sse_done_event(**extra: Any) -> str:
    """格式化 SSE 完成事件"""
    payload: Dict[str, Any] = {"type": "done", "latency_ms": 0, **extra}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def create_sse_response(
    stream_fn: Callable[[], AsyncGenerator[str, None]],
    endpoint_name: str = "SSE",
    done_extra: Dict[str, Any] | None = None,
    timeout_s: Optional[int] = None,
) -> StreamingResponse:
    """
    建立 SSE StreamingResponse，統一錯誤處理。

    Args:
        stream_fn: 無參數 async generator（已 bind 好參數的串流函數）
        endpoint_name: 端點名稱（用於日誌）
        done_extra: 錯誤時 done 事件的額外欄位
        timeout_s: SSE 端到端 hard cutoff（秒）。None = 從 ai_config.agent_stream_timeout
            讀取（預設 60s，對齊 ADR-0028 stream_e2e）。

    R1 (v6.9 / 2026-05-08)：加 hard cutoff timeout。
        - shadow_baseline p95=58s 接近 60s 邊界，影響 ADR-0030 5/20 GO/NO-GO 投票。
        - 原 event_generator 只包 try/except，無 asyncio.timeout 限時。
        - 超時送 STREAM_TIMEOUT error event + done(model="timeout") 而非無限等待。
    """
    # Lazy import 避免 ai_config 循環引用
    if timeout_s is None:
        try:
            from app.services.ai.core.ai_config import get_ai_config
            timeout_s = get_ai_config().agent_stream_timeout
        except Exception:
            timeout_s = 60  # ADR-0028 default

    async def event_generator():
        try:
            # R1: 包 asyncio.timeout 強制 stream_e2e 上限
            async with asyncio.timeout(timeout_s):
                async for chunk in stream_fn():
                    yield chunk
        except asyncio.TimeoutError:
            logger.warning(
                "%s stream endpoint timed out after %ds (ADR-0028 hard cutoff)",
                endpoint_name, timeout_s,
            )
            yield sse_error_event(
                f"查詢逾時（{timeout_s} 秒），請簡化問題或稍後重試",
                code="STREAM_TIMEOUT",
            )
            yield sse_done_event(model="timeout", **(done_extra or {}))
        except Exception as e:
            logger.error("%s stream endpoint error: %s", endpoint_name, e, exc_info=True)
            yield sse_error_event(
                "AI 服務暫時無法處理您的請求，請稍後再試。",
                code="SERVICE_ERROR",
            )
            yield sse_done_event(model="error", **(done_extra or {}))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )

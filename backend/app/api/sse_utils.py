"""
SSE (Server-Sent Events) 串流共用工具

統一 RAG / Agent 等串流端點的 event_generator 包裝與錯誤處理。

Version: 1.0.0
Created: 2026-02-27
"""

import json
import logging
from typing import Any, AsyncGenerator, Callable, Dict

from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)

# 共用 SSE 回應標頭
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
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
) -> StreamingResponse:
    """
    建立 SSE StreamingResponse，統一錯誤處理。

    Args:
        stream_fn: 無參數 async generator（已 bind 好參數的串流函數）
        endpoint_name: 端點名稱（用於日誌）
        done_extra: 錯誤時 done 事件的額外欄位
    """
    async def event_generator():
        try:
            async for chunk in stream_fn():
                yield chunk
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

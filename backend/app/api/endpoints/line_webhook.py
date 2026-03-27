"""
LINE Bot Webhook 端點

- POST /line/webhook — LINE 事件接收（HMAC-SHA256 簽名驗證）
- POST /line/push — 主動推播通知（內部系統使用）

Version: 1.0.0
Created: 2026-03-15
"""

import json
import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from starlette.responses import Response

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_db
from app.core.rate_limiter import limiter
from app.schemas.line import LinePushRequest, LinePushAlertsRequest, LinePushAlertsResponse, WebhookResponse
from app.services.line_bot_service import get_line_bot_service

logger = logging.getLogger(__name__)

router = APIRouter()

# ── 訊息去重快取 (防止 LINE 重發同一事件) ──
_DEDUP_CACHE: dict[str, float] = {}
_DEDUP_TTL = 10.0  # 10 秒內的重複事件忽略
_DEDUP_MAX_SIZE = 500  # 快取上限


def _is_duplicate_event(message_id: str) -> bool:
    """檢查是否為重複訊息（LRU 風格去重）"""
    now = time.time()
    # 清理過期條目
    if len(_DEDUP_CACHE) > _DEDUP_MAX_SIZE:
        expired = [k for k, v in _DEDUP_CACHE.items() if now - v > _DEDUP_TTL]
        for k in expired:
            del _DEDUP_CACHE[k]
    # 檢查重複
    if message_id in _DEDUP_CACHE and now - _DEDUP_CACHE[message_id] < _DEDUP_TTL:
        return True
    _DEDUP_CACHE[message_id] = now
    return False


# ── Webhook ──


@router.post("/webhook", response_model=WebhookResponse, summary="LINE Webhook")
@limiter.limit("10/minute")
async def line_webhook(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
) -> WebhookResponse:
    """
    LINE Messaging API Webhook 端點。

    1. 驗證 X-Line-Signature (HMAC-SHA256)
    2. 解析事件，文字訊息交由 Agent 處理
    3. 立即回傳 200（處理在背景執行）
    """
    service = get_line_bot_service()

    # Feature flag 關閉時直接回 200
    if not service.enabled:
        return WebhookResponse()

    # 讀取原始 body（簽名驗證需要原始 bytes）
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    if not service.verify_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 解析事件
    try:
        payload = json.loads(body)
        events = payload.get("events", [])
    except (json.JSONDecodeError, KeyError):
        return WebhookResponse()

    # 派發訊息事件（文字 + 語音 + 圖片）
    for event in events:
        if event.get("type") != "message":
            continue

        msg = event.get("message", {})
        msg_type = msg.get("type")
        reply_token = event.get("replyToken", "")
        user_id = event.get("source", {}).get("userId", "")

        if not reply_token or not user_id:
            continue

        # 訊息去重 (防止 LINE 重發同一事件)
        msg_id = msg.get("id", "")
        if msg_id and _is_duplicate_event(msg_id):
            logger.debug("Duplicate LINE message ignored: %s", msg_id)
            continue

        if msg_type == "text":
            text = msg.get("text", "").strip()
            if text:
                background_tasks.add_task(
                    service.handle_text_message,
                    reply_token,
                    user_id,
                    text,
                )

        elif msg_type == "audio":
            message_id = msg.get("id", "")
            if message_id:
                background_tasks.add_task(
                    service.handle_audio_message,
                    reply_token,
                    user_id,
                    message_id,
                )

        elif msg_type == "image":
            message_id = msg.get("id", "")
            if message_id:
                background_tasks.add_task(
                    service.handle_image_message,
                    reply_token,
                    user_id,
                    message_id,
                )

    return WebhookResponse()


# ── Push 通知 ──


from app.core.service_token import verify_service_token  # S-3 集中式雙 token 驗證


@router.post("/push", summary="LINE Push 通知（內部系統使用）")
async def line_push(
    body: LinePushRequest,
    request: Request,
    _auth: dict = Depends(verify_service_token),
) -> WebhookResponse:
    """
    主動推播 LINE 訊息。

    認證：X-Service-Token header（與 agent_query_sync 共用 MCP_SERVICE_TOKEN）
    """
    service = get_line_bot_service()

    if not service.enabled:
        raise HTTPException(status_code=503, detail="LINE Bot is not enabled")

    success = await service.push_message(body.user_id, body.message)
    if not success:
        raise HTTPException(status_code=502, detail="Failed to send LINE message")

    return WebhookResponse(status="sent")


# ── Push Alerts ──


@router.post(
    "/push-alerts",
    response_model=LinePushAlertsResponse,
    summary="LINE 警報推播（定時排程使用）",
)
async def line_push_alerts(
    request: Request,
    body: LinePushAlertsRequest = LinePushAlertsRequest(),
    _auth: dict = Depends(verify_service_token),
    db: AsyncSession = Depends(get_async_db),
) -> LinePushAlertsResponse:
    """
    掃描 ProactiveAlerts 並推播給指定使用者。

    認證：X-Service-Token header
    可由 cron job / APScheduler 定期呼叫。
    """
    from app.services.line_push_scheduler import LinePushScheduler

    scheduler = LinePushScheduler(db)
    result = await scheduler.scan_and_push(
        target_user_ids=body.target_user_ids or None,
        min_severity=body.min_severity,
    )

    return LinePushAlertsResponse(**result)

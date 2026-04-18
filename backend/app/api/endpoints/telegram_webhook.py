"""
Telegram Bot Webhook 端點

- POST /telegram/webhook — Telegram Update 接收（Secret Token 驗證）
- POST /telegram/push — 主動推播通知（內部系統使用）

Version: 1.0.0
Created: 2026-04-05
"""

import logging
import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from starlette.responses import JSONResponse

from app.core.rate_limiter import limiter
from app.schemas.telegram import TelegramPushRequest, TelegramWebhookResponse
from app.services.telegram_bot_service import get_telegram_bot_service

logger = logging.getLogger(__name__)

router = APIRouter()

# ── 訊息去重快取 (防止 Telegram 重發同一 update) ──
_DEDUP_CACHE: dict[int, float] = {}
_DEDUP_TTL = 10.0
_DEDUP_MAX_SIZE = 500


def _is_duplicate_update(update_id: int) -> bool:
    """檢查是否為重複 update（LRU 風格去重）"""
    now = time.time()
    if len(_DEDUP_CACHE) > _DEDUP_MAX_SIZE:
        expired = [k for k, v in _DEDUP_CACHE.items() if now - v > _DEDUP_TTL]
        for k in expired:
            del _DEDUP_CACHE[k]
    if update_id in _DEDUP_CACHE and now - _DEDUP_CACHE[update_id] < _DEDUP_TTL:
        return True
    _DEDUP_CACHE[update_id] = now
    return False


# ── Webhook ──


@router.post("/webhook", response_model=TelegramWebhookResponse, summary="Telegram Webhook")
@limiter.limit("30/minute")
async def telegram_webhook(
    request: Request,
    response: Response,  # slowapi rate-limiter 需此參數 inject X-RateLimit headers
    background_tasks: BackgroundTasks,
) -> TelegramWebhookResponse:
    """
    Telegram Bot API Webhook 端點。

    1. 驗證 X-Telegram-Bot-Api-Secret-Token
    2. 解析 Update，文字/圖片/語音訊息交由 Agent 處理
    3. 立即回傳 200（處理在背景執行）
    """
    service = get_telegram_bot_service()

    # Feature flag 關閉時直接回 200
    if not service.enabled:
        return TelegramWebhookResponse()

    # 驗證 Secret Token
    header_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not service.verify_secret_token(header_token):
        raise HTTPException(status_code=403, detail="Invalid secret token")

    # 解析 Update
    try:
        update = await request.json()
    except Exception:
        return TelegramWebhookResponse()

    # Update 去重
    update_id = update.get("update_id")
    if update_id and _is_duplicate_update(update_id):
        logger.debug("Duplicate Telegram update ignored: %s", update_id)
        return TelegramWebhookResponse()

    # 解析 message
    message = update.get("message", {})
    if not message:
        return TelegramWebhookResponse()

    chat_id = message.get("chat", {}).get("id")
    user_id = message.get("from", {}).get("id")
    username = message.get("from", {}).get("username", "")

    if not chat_id or not user_id:
        return TelegramWebhookResponse()

    # 文字訊息
    if "text" in message:
        text = message["text"].strip()
        if not text:
            return TelegramWebhookResponse()

        # 基本指令處理
        if text == "/start":
            background_tasks.add_task(
                service.send_message,
                chat_id,
                "👋 你好！我是乾坤 AI 助理。\n\n"
                "直接輸入問題即可查詢公文、專案、派工單等資訊。\n"
                "輸入 /help 查看可用功能。",
            )
            return TelegramWebhookResponse()

        if text == "/help":
            background_tasks.add_task(
                service.send_message,
                chat_id,
                "📋 *可用功能*\n\n"
                "• 公文查詢 — 搜尋收發文\n"
                "• 派工單搜尋 — 查估派工進度\n"
                "• 專案進度 — 承攬案件狀態\n"
                "• 費用查詢 — 核銷與帳款\n"
                "• 標案搜尋 — 政府招標資訊\n"
                "• 知識圖譜 — 關聯探索\n\n"
                "📸 傳送發票照片可自動辨識\n"
                "🎙 傳送語音可自動轉文字查詢",
            )
            return TelegramWebhookResponse()

        # 一般文字 → Agent (傳入 user_message_id 供反應+回覆串接)
        msg_id = message.get("message_id")
        background_tasks.add_task(
            service.handle_text_message,
            chat_id,
            user_id,
            text,
            username,
            msg_id,
        )

    # 圖片
    elif "photo" in message:
        photos = message["photo"]
        file_id = photos[-1]["file_id"]  # 最大解析度
        caption = message.get("caption", "")
        background_tasks.add_task(
            service.handle_photo,
            chat_id,
            user_id,
            file_id,
            caption,
        )

    # 語音
    elif "voice" in message:
        file_id = message["voice"]["file_id"]
        background_tasks.add_task(
            service.handle_voice,
            chat_id,
            user_id,
            file_id,
        )

    # 文件 (暫不支援)
    elif "document" in message:
        background_tasks.add_task(
            service.send_message,
            chat_id,
            "📎 文件處理功能開發中，請先以圖片方式傳送。",
        )

    return TelegramWebhookResponse()


# ── Push 通知 ──


from app.core.service_token import verify_service_token


@router.post("/push", summary="Telegram Push 通知（內部系統使用）")
async def telegram_push(
    body: TelegramPushRequest,
    request: Request,
    _auth: dict = Depends(verify_service_token),
) -> TelegramWebhookResponse:
    """
    主動推播 Telegram 訊息。

    認證：X-Service-Token header（與 agent_query_sync 共用 MCP_SERVICE_TOKEN）
    """
    service = get_telegram_bot_service()

    if not service.enabled:
        raise HTTPException(status_code=503, detail="Telegram Bot is not enabled")

    success = await service.push_message(body.chat_id, body.message)
    if not success:
        raise HTTPException(status_code=502, detail="Failed to send Telegram message")

    return TelegramWebhookResponse(status="sent")

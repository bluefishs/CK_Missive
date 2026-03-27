"""
Discord Bot Webhook 端點

- POST /discord/webhook — Discord Interactions Endpoint (Ed25519 簽名驗證)
- POST /discord/push — 主動推播通知（內部系統使用）

Version: 1.0.0
Created: 2026-03-25
"""

import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from starlette.responses import JSONResponse

from app.core.rate_limiter import limiter
from app.schemas.discord import DiscordPushRequest, DiscordWebhookResponse
from app.services.discord_bot_service import get_discord_bot_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Webhook ──


@router.post("/webhook", summary="Discord Interactions Endpoint")
@limiter.limit("30/minute")
async def discord_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Discord Interactions Endpoint (HTTP Webhook 模式)。

    1. 驗證 Ed25519 簽名 (X-Signature-Ed25519 + X-Signature-Timestamp)
    2. 回應 PING (type=1)
    3. 處理 Slash Commands (type=2)
    """
    service = get_discord_bot_service()

    # Feature flag
    if not service.enabled:
        return JSONResponse(
            status_code=200,
            content={"type": 1},  # PONG
        )

    body = await request.body()
    signature = request.headers.get("X-Signature-Ed25519", "")
    timestamp = request.headers.get("X-Signature-Timestamp", "")

    if not service.verify_signature(body, signature, timestamp):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    interaction_type = payload.get("type", 0)

    # Type 1: PING — Discord 驗證用
    if interaction_type == 1:
        return JSONResponse(content={"type": 1})

    # Type 2: APPLICATION_COMMAND — Slash Commands
    if interaction_type == 2:
        data = payload.get("data", {})
        command_name = data.get("name", "")
        options = {}
        for opt in data.get("options", []):
            options[opt.get("name", "")] = opt.get("value", "")

        user = payload.get("member", {}).get("user", {}) or payload.get("user", {})
        user_id = user.get("id", "unknown")

        # 短命令快速回覆，長命令用 deferred
        if command_name == "ck-ask":
            # 先回 deferred (type=5)，背景處理後 followup
            background_tasks.add_task(
                _handle_deferred_command,
                service, command_name, options, user_id,
                payload.get("token", ""),
                payload.get("application_id", service.application_id),
            )
            return JSONResponse(content={"type": 5})  # DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE
        else:
            result = await service.handle_slash_command(command_name, options, user_id)
            return JSONResponse(content=result)

    # Type 3: MESSAGE_COMPONENT
    if interaction_type == 3:
        return JSONResponse(content={"type": 6})  # DEFERRED_UPDATE_MESSAGE

    return JSONResponse(content={"type": 1})


async def _handle_deferred_command(
    service, command_name: str, options: dict, user_id: str,
    interaction_token: str, application_id: str,
):
    """背景處理耗時 Slash Command，透過 followup webhook 回覆"""
    try:
        result = await service.handle_slash_command(command_name, options, user_id)
        # 透過 Discord followup webhook 回覆
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://discord.com/api/v10/webhooks/{application_id}/{interaction_token}",
                json=result.get("data", {}),
                timeout=10,
            )
    except Exception as e:
        logger.error("Discord deferred command failed: %s", e)


# ── Push 通知 ──


from app.core.service_token import verify_service_token  # S-3 集中式雙 token 驗證


@router.post("/push", summary="Discord Push 通知（內部系統使用）")
async def discord_push(
    body: DiscordPushRequest,
    request: Request,
    _auth: dict = Depends(verify_service_token),
) -> DiscordWebhookResponse:
    """
    主動推播 Discord 訊息到指定 Channel。

    認證：X-Service-Token header
    """
    service = get_discord_bot_service()

    if not service.enabled:
        raise HTTPException(status_code=503, detail="Discord Bot is not enabled")

    success = await service.send_channel_message(body.channel_id, body.message)
    if not success:
        raise HTTPException(status_code=502, detail="Failed to send Discord message")

    return DiscordWebhookResponse()

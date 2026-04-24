"""
LINE Bot admin 指令處理

2026-04-22 (ADR-0027 後續)：Telegram 個人號永封後，LINE 成為主要 admin push 通道。
提供 `/subscribe <token>` 指令讓管理員自行註冊為晨報接收人。

安全設計：
- 驗證 LINE_SUBSCRIBE_TOKEN（從 env 讀），避免任意用戶訂閱
- 寫入 UserMorningReportSubscription，enabled=True, sections="all"
- 同一 LINE user_id 重複訂閱 → 更新為 enabled=True（不重複新增）
"""
from __future__ import annotations

import logging
import os

from app.db.database import async_session_maker
from app.extended.models import UserMorningReportSubscription
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def handle_subscribe_command(line_user_id: str, token: str) -> str:
    """
    處理 `/subscribe <token>` 指令。

    Args:
        line_user_id: LINE user_id（webhook event.source.userId）
        token: 用戶提供的驗證 token

    Returns:
        回覆訊息（繁中，給用戶看）
    """
    expected = os.getenv("LINE_SUBSCRIBE_TOKEN", "")
    if not expected:
        logger.warning("LINE /subscribe 嘗試但 LINE_SUBSCRIBE_TOKEN 未設")
        return "晨報訂閱功能未啟用（LINE_SUBSCRIBE_TOKEN 未設定）。"

    if token != expected:
        logger.warning("LINE /subscribe token 不符: user=%s", line_user_id)
        return "驗證 token 錯誤，訂閱失敗。"

    try:
        async with async_session_maker() as db:
            # 查是否已訂閱
            result = await db.execute(
                select(UserMorningReportSubscription).where(
                    UserMorningReportSubscription.channel == "line",
                    UserMorningReportSubscription.channel_recipient == line_user_id,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.enabled = True
                existing.sections = "all"
                await db.commit()
                logger.info("LINE subscription re-enabled for %s", line_user_id)
                return "✅ 已重新啟用晨報訂閱。每日 08:00 將推送至此聊天室。"

            db.add(UserMorningReportSubscription(
                display_name="Admin (LINE)",
                channel="line",
                channel_recipient=line_user_id,
                sections="all",
                enabled=True,
            ))
            await db.commit()
            logger.info("LINE subscription created for %s", line_user_id)
            return (
                "✅ 晨報訂閱成功！\n"
                "每日 08:00 將推送公文 / 派工 / 財務 / 標案摘要至此。\n"
                "如需停用請聯繫系統管理員。"
            )
    except Exception as e:
        logger.error("LINE /subscribe DB 失敗: %s", e)
        return f"訂閱失敗（系統錯誤），請稍後再試或聯繫管理員。"


__all__ = ["handle_subscribe_command"]

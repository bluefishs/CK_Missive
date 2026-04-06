"""
LINE Bot Service — LINE Messaging API 整合服務

提供：
- HMAC-SHA256 Webhook 簽名驗證
- 文字訊息 → AgentOrchestrator 同步問答 → LINE 回覆
- 語音訊息 → VoiceTranscriber 轉文字 → AgentOrchestrator 問答 → LINE 回覆
- 圖片訊息 → OCR 發票辨識 → 建立費用紀錄 → LINE 回覆
- Push 通知（截止日提醒、異常警報）

Version: 1.2.0
Created: 2026-03-15
Updated: 2026-03-23 - v1.2.0 Image → OCR invoice parsing
"""

import asyncio
import hashlib
import hmac
import base64
import json
import logging
import os
from typing import Optional

import httpx

from app.services.line_flex_builder import (
    build_agent_reply_flex,
    build_deadline_flex,
    build_quick_reply_items,
)
from app.services.line_image_handler import (
    download_line_content,
    format_ocr_reply,
    try_create_expense_from_ocr,
)

logger = logging.getLogger(__name__)

# LINE API base URL
LINE_API_BASE = "https://api.line.me/v2/bot"


class LineBotService:
    """LINE Bot 整合服務"""

    def __init__(self):
        self._channel_secret = os.getenv("LINE_CHANNEL_SECRET", "")
        self._channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        self._enabled = os.getenv("LINE_BOT_ENABLED", "false").lower() == "true"
        self._reply_timeout = 25  # LINE 30s 限制，留 5s 緩衝

    @property
    def enabled(self) -> bool:
        return self._enabled and bool(self._channel_secret) and bool(self._channel_access_token)

    def verify_signature(self, body: bytes, signature: str) -> bool:
        """
        驗證 LINE Webhook HMAC-SHA256 簽名。

        Args:
            body: 原始 request body (bytes)
            signature: X-Line-Signature header 值

        Returns:
            True 如果簽名有效
        """
        if not self._channel_secret or not signature:
            return False

        hash_value = hmac.new(
            self._channel_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).digest()
        expected = base64.b64encode(hash_value).decode("utf-8")

        return hmac.compare_digest(signature, expected)

    async def handle_image_message(
        self,
        reply_token: str,
        user_id: str,
        message_id: str,
    ) -> None:
        """
        處理圖片訊息：下載圖片 → OCR 辨識發票 → 回覆解析結果。
        在 BackgroundTask 中執行。
        """
        try:
            file_path = await download_line_content(message_id, self._channel_access_token)
            if not file_path:
                await self.reply_message(reply_token, "圖片下載失敗，請重新傳送。")
                return

            # 統一辨識器: QR 優先 + OCR 補充
            from app.services.invoice_recognizer import recognize_invoice

            recognition = recognize_invoice(str(file_path))

            expense_msg = await try_create_expense_from_recognition(
                user_id, recognition, str(file_path)
            ) if recognition.success else None

            reply = format_recognition_reply(recognition, expense_msg)
            await self.reply_message(reply_token, reply)

        except Exception as e:
            logger.error("LINE image processing failed: %s", e, exc_info=True)
            await self.reply_message(reply_token, "圖片處理時發生錯誤，請重新傳送。")

    async def handle_audio_message(
        self,
        reply_token: str,
        user_id: str,
        message_id: str,
    ) -> None:
        """
        處理語音訊息：VoiceTranscriber 轉文字 → AgentOrchestrator → 回覆 LINE。

        在 BackgroundTask 中執行。
        """
        from app.services.ai.voice_transcriber import get_voice_transcriber

        transcriber = get_voice_transcriber()

        try:
            result = await asyncio.wait_for(
                transcriber.transcribe_line_audio(message_id),
                timeout=self._reply_timeout,
            )
        except asyncio.TimeoutError:
            await self.reply_message(reply_token, "語音處理超時，請改用文字訊息。")
            return
        except Exception as e:
            logger.error("Voice transcription failed: %s", e)
            await self.reply_message(reply_token, "語音處理時發生錯誤，請改用文字訊息。")
            return

        if result["source"] == "error":
            await self.reply_message(reply_token, result["text"])
            return

        transcribed_text = result["text"]
        source = result["source"]
        duration_ms = result.get("duration_ms", 0)

        logger.info(
            "Voice transcribed: user=%s, source=%s, duration=%dms, text=%s",
            user_id,
            source,
            duration_ms,
            transcribed_text[:100],
        )

        # Pass transcribed text to agent (same as text message flow)
        try:
            answer = await asyncio.wait_for(
                self._query_agent(user_id, transcribed_text),
                timeout=self._reply_timeout,
            )
        except asyncio.TimeoutError:
            answer = "查詢處理時間較長，請稍後再試。"
            logger.warning("LINE agent query timeout for voice user %s", user_id)
        except Exception as e:
            answer = "處理時發生錯誤，請稍後再試。"
            logger.error("LINE agent query failed for voice: %s", e)

        # Prepend transcription notice so user knows what was recognized
        prefix = f"🎤 語音辨識：{transcribed_text}\n\n"
        full_answer = prefix + answer

        # LINE 文字訊息上限 5000 字
        if len(full_answer) > 5000:
            full_answer = full_answer[:4990] + "\n...(已截斷)"

        await self.reply_message(reply_token, full_answer)

    async def handle_text_message(
        self,
        reply_token: str,
        user_id: str,
        text: str,
    ) -> None:
        """
        處理文字訊息：呼叫 AgentOrchestrator → Flex Message 回覆 LINE。

        LINE 不支援 editMessage，因此無法做 edit-streaming。改為：
        1. 顯示 LINE loading indicator (氣泡動畫)
        2. 使用 AgentStreamCollector 收集完整回答 + 追蹤工具使用
        3. 一次性回覆完整答案

        使用獨立 DB session（因為此方法在 BackgroundTask 中執行）。
        """
        from app.services.agent_stream_helper import AgentStreamCollector

        # Show loading indicator (bubble animation) while processing
        await self._show_loading(user_id)

        # Collect full answer (no periodic updates -- LINE can't edit)
        collector = AgentStreamCollector(update_interval=999)

        try:
            result = await asyncio.wait_for(
                self._stream_agent(user_id, text, collector),
                timeout=self._reply_timeout,
            )
            answer = result.answer
            tools_used = result.tools_used
        except asyncio.TimeoutError:
            answer = "查詢處理時間較長，請稍後再試。"
            tools_used = []
            logger.warning("LINE agent query timeout for user %s", user_id)
        except Exception as e:
            answer = "處理時發生錯誤，請稍後再試。"
            tools_used = []
            logger.error("LINE agent query failed: %s", e)

        # Append tool footer
        answer += AgentStreamCollector.build_tool_footer(tools_used)

        # Flex Message 回覆 (含工具摘要 + Quick Reply)
        if tools_used and len(answer) > 60:
            flex = build_agent_reply_flex(text, answer[:4000], tools_used)
            quick = build_quick_reply_items(["還有其他結果嗎？", "請幫我整理重點", "查詢相關案件"])
            success = await self.reply_flex(reply_token, flex, alt_text=answer[:400])
            if not success:
                # 回退到純文字
                if len(answer) > 5000:
                    answer = answer[:4990] + "\n...(已截斷)"
                await self.reply_message(reply_token, answer)
        else:
            if len(answer) > 5000:
                answer = answer[:4990] + "\n...(已截斷)"
            await self.reply_message(reply_token, answer)

    async def _stream_agent(
        self,
        user_id: str,
        text: str,
        collector: "AgentStreamCollector",
    ) -> "StreamResult":
        """Run agent orchestrator and collect results via shared collector."""
        from app.db.database import AsyncSessionLocal
        from app.services.ai.agent_orchestrator import AgentOrchestrator
        from app.services.ai.agent_conversation_memory import get_conversation_memory
        from app.services.sender_context import SenderContext

        session_id = f"line:{user_id}"

        sender_ctx = SenderContext(
            user_id=user_id,
            display_name=f"LINE#{user_id[:8]}",
            channel="line",
        )

        conv_memory = get_conversation_memory()
        history = await conv_memory.load(session_id)

        async with AsyncSessionLocal() as db:
            orchestrator = AgentOrchestrator(db)
            result = await collector.collect(
                orchestrator.stream_agent_query(
                    question=text,
                    history=history,
                    session_id=session_id,
                    sender_context=sender_ctx,
                )
            )

        await conv_memory.save(session_id, text, result.answer, history)
        return result

    async def _show_loading(self, user_id: str) -> None:
        """Show LINE loading indicator (bubble animation).

        Uses POST /v2/bot/chat/loading/start which shows a typing
        indicator for up to 20 seconds (or until a message is sent).
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    "https://api.line.me/v2/bot/chat/loading/start",
                    json={"chatId": user_id},
                    headers={
                        "Authorization": f"Bearer {self._channel_access_token}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code != 200:
                    logger.debug("LINE loading indicator failed: %d", resp.status_code)
        except Exception:
            # Non-critical; silently ignore
            pass

    async def reply_message(self, reply_token: str, text: str) -> bool:
        """使用 reply token 回覆 LINE 訊息"""
        if not self.enabled:
            logger.debug("LINE Bot disabled, skip reply")
            return False

        payload = {
            "replyToken": reply_token,
            "messages": [{"type": "text", "text": text}],
        }

        return await self._call_line_api("/message/reply", payload)

    async def push_message(self, user_id: str, text: str) -> bool:
        """主動推播訊息給指定使用者"""
        if not self.enabled:
            return False

        payload = {
            "to": user_id,
            "messages": [{"type": "text", "text": text}],
        }

        return await self._call_line_api("/message/push", payload)

    async def reply_flex(self, reply_token: str, flex: dict, alt_text: str = "訊息") -> bool:
        """使用 Flex Message 回覆 (卡片式訊息)"""
        payload = {
            "replyToken": reply_token,
            "messages": [{"type": "flex", "altText": alt_text, "contents": flex}],
        }
        return await self._call_line_api("/message/reply", payload)

    async def push_flex(self, user_id: str, flex: dict, alt_text: str = "訊息") -> bool:
        """主動推播 Flex Message"""
        payload = {
            "to": user_id,
            "messages": [{"type": "flex", "altText": alt_text, "contents": flex}],
        }
        return await self._call_line_api("/message/push", payload)

    async def reply_quick(self, reply_token: str, text: str, quick_items: list) -> bool:
        """回覆附帶 Quick Reply 按鈕"""
        payload = {
            "replyToken": reply_token,
            "messages": [{
                "type": "text", "text": text,
                "quickReply": {"items": quick_items},
            }],
        }
        return await self._call_line_api("/message/reply", payload)

    async def push_deadline_reminder(
        self,
        user_id: str,
        doc_subject: str,
        deadline: str,
    ) -> bool:
        """推播截止日提醒 (Flex Message 卡片)"""
        flex = build_deadline_flex(doc_subject, deadline)
        return await self.push_flex(user_id, flex, alt_text=f"公文截止提醒: {doc_subject[:30]}")

    async def _call_line_api(self, path: str, payload: dict) -> bool:
        """呼叫 LINE Messaging API"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{LINE_API_BASE}{path}",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self._channel_access_token}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code != 200:
                    logger.warning(
                        "LINE API %s failed: %d %s",
                        path,
                        resp.status_code,
                        resp.text[:200],
                    )
                    return False
                return True
        except Exception as e:
            logger.error("LINE API call failed: %s", e)
            return False


# ── Singleton ──

_service: Optional[LineBotService] = None


def get_line_bot_service() -> LineBotService:
    """取得 LineBotService 單例"""
    global _service
    if _service is None:
        _service = LineBotService()
    return _service



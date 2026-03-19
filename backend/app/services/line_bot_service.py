"""
LINE Bot Service — LINE Messaging API 整合服務

提供：
- HMAC-SHA256 Webhook 簽名驗證
- 文字訊息 → AgentOrchestrator 同步問答 → LINE 回覆
- 語音訊息 → VoiceTranscriber 轉文字 → AgentOrchestrator 問答 → LINE 回覆
- Push 通知（截止日提醒、異常警報）

Version: 1.1.0
Created: 2026-03-15
Updated: 2026-03-16 - v1.1.0 Voice-to-Text for audio messages
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
        處理文字訊息：呼叫 AgentOrchestrator → 回覆 LINE。

        使用獨立 DB session（因為此方法在 BackgroundTask 中執行）。
        """
        try:
            answer = await asyncio.wait_for(
                self._query_agent(user_id, text),
                timeout=self._reply_timeout,
            )
        except asyncio.TimeoutError:
            answer = "查詢處理時間較長，請稍後再試。"
            logger.warning("LINE agent query timeout for user %s", user_id)
        except Exception as e:
            answer = "處理時發生錯誤，請稍後再試。"
            logger.error("LINE agent query failed: %s", e)

        # LINE 文字訊息上限 5000 字
        if len(answer) > 5000:
            answer = answer[:4990] + "\n...(已截斷)"

        await self.reply_message(reply_token, answer)

    async def _query_agent(self, user_id: str, text: str) -> str:
        """呼叫 AgentOrchestrator 取得回答（含 Redis 對話記憶）"""
        from app.db.database import AsyncSessionLocal
        from app.services.ai.agent_orchestrator import AgentOrchestrator
        from app.services.ai.agent_conversation_memory import get_conversation_memory

        session_id = f"line:{user_id}"

        # Load conversation history from Redis
        conv_memory = get_conversation_memory()
        history = await conv_memory.load(session_id)

        async with AsyncSessionLocal() as db:
            orchestrator = AgentOrchestrator(db)

            answer_tokens = []

            async for event_str in orchestrator.stream_agent_query(
                question=text,
                history=history,
                session_id=session_id,
            ):
                if not event_str.startswith("data: "):
                    continue
                try:
                    event = json.loads(event_str[6:])
                except (json.JSONDecodeError, IndexError):
                    continue

                event_type = event.get("type")
                if event_type == "token":
                    answer_tokens.append(event.get("token", ""))
                elif event_type == "error":
                    return event.get("error", "查詢失敗")

            answer = "".join(answer_tokens) or "無法產生回答，請換個方式提問。"

        # Save Q&A to conversation memory
        await conv_memory.save(session_id, text, answer, history)

        return answer

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

    async def push_deadline_reminder(
        self,
        user_id: str,
        doc_subject: str,
        deadline: str,
    ) -> bool:
        """推播截止日提醒"""
        message = (
            f"📋 公文截止提醒\n\n"
            f"主旨：{doc_subject}\n"
            f"截止日：{deadline}\n\n"
            f"請儘速處理。"
        )
        return await self.push_message(user_id, message)

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

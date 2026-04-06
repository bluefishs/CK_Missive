"""
Telegram Bot Service — Telegram Bot API 整合服務

提供：
- Webhook Secret Token 驗證
- 文字訊息 → AgentOrchestrator 同步問答 → Telegram 回覆
- 語音訊息 → VoiceTranscriber 轉文字 → AgentOrchestrator 問答 → Telegram 回覆
- 圖片訊息 → Vision 辨識 → Telegram 回覆
- Push 通知（主動推播）

Version: 1.0.0
Created: 2026-04-05
"""

import asyncio
import json
import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Telegram Bot API base URL
TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramBotService:
    """Telegram Bot 整合服務 (mirror of LineBotService)"""

    def __init__(self):
        self._bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self._webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
        self._enabled = os.getenv("TELEGRAM_BOT_ENABLED", "false").lower() == "true"
        self._reply_timeout = 25  # Telegram 沒有硬限，但保持一致

    @property
    def enabled(self) -> bool:
        return self._enabled and bool(self._bot_token)

    def verify_secret_token(self, header_token: str) -> bool:
        """
        驗證 Telegram Webhook Secret Token。

        Telegram 在設定 webhook 時可指定 secret_token，
        之後每次推送會透過 X-Telegram-Bot-Api-Secret-Token header 傳送。

        Args:
            header_token: X-Telegram-Bot-Api-Secret-Token header 值

        Returns:
            True 如果驗證通過（未設定 secret 時一律通過）
        """
        if not self._webhook_secret:
            return True
        return header_token == self._webhook_secret

    # ── 文字訊息處理 (Edit-Streaming) ──

    async def handle_text_message(
        self,
        chat_id: int,
        user_id: int,
        text: str,
        username: str = "",
    ) -> None:
        """
        處理文字訊息：呼叫 AgentOrchestrator → Edit-Streaming 回覆 Telegram。

        Telegram 支援 editMessageText，因此採用與 Discord 相同的
        edit-streaming 模式：先發一則「思考中」，再不斷 edit 更新內容。

        使用獨立 DB session（因為此方法在 BackgroundTask 中執行）。
        """
        from app.services.agent_stream_helper import AgentStreamCollector

        # Step 1: 送出初始訊息，取得 message_id
        initial_msg_id = await self._send_and_get_id(chat_id, "\U0001f914 思考中...")

        # Step 2: 建立 edit-streaming collector
        async def on_text_update(partial: str) -> None:
            """Edit 訊息以呈現部分回答 (附閃爍游標)"""
            if not initial_msg_id or not partial:
                return
            # Telegram 4096 char limit; keep room for cursor
            display = partial[:4000] + " \u258d" if len(partial) <= 4000 else partial[:4090] + "..."
            await self._edit_message(chat_id, initial_msg_id, display)

        collector = AgentStreamCollector(
            on_text_update=on_text_update if initial_msg_id else None,
            update_interval=1.5,
        )

        # Step 3: Stream from orchestrator
        try:
            result = await asyncio.wait_for(
                self._stream_agent(user_id, text, collector),
                timeout=self._reply_timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("Telegram agent query timeout for user %s", user_id)
            final = "\u23f1 查詢處理時間較長，請稍後再試。"
            if initial_msg_id:
                await self._edit_message(chat_id, initial_msg_id, final)
            else:
                await self.send_message(chat_id, final)
            return
        except Exception as e:
            logger.error("Telegram agent query failed: %s", e)
            final = "系統暫時無法回應，請稍後再試。"
            if initial_msg_id:
                await self._edit_message(chat_id, initial_msg_id, final)
            else:
                await self.send_message(chat_id, final)
            return

        # Step 4: Final edit with complete response + tool footer
        final = result.answer
        final += AgentStreamCollector.build_tool_footer(result.tools_used)
        if len(final) > 4090:
            final = final[:4087] + "..."

        if initial_msg_id:
            await self._edit_message(chat_id, initial_msg_id, final)
        else:
            await self.send_message(chat_id, final)

    async def _stream_agent(
        self,
        user_id: int,
        text: str,
        collector: "AgentStreamCollector",
    ) -> "StreamResult":
        """Run agent orchestrator and collect results via shared collector."""
        from app.db.database import AsyncSessionLocal
        from app.services.ai.agent_orchestrator import AgentOrchestrator
        from app.services.ai.agent_conversation_memory import get_conversation_memory
        from app.services.sender_context import SenderContext
        from app.services.agent_stream_helper import StreamResult

        session_id = f"telegram:{user_id}"

        sender_ctx = SenderContext(
            user_id=str(user_id),
            display_name=f"Telegram#{str(user_id)[:8]}",
            channel="telegram",
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

    # ── 圖片訊息處理 ──

    async def handle_photo(
        self,
        chat_id: int,
        user_id: int,
        file_id: str,
        caption: str = "",
    ) -> None:
        """處理圖片訊息：下載圖片 → Vision 辨識 → 回覆。"""
        try:
            image_bytes = await self._download_file(file_id)
            if not image_bytes:
                await self.send_message(chat_id, "無法下載圖片，請重新傳送。")
                return

            # 統一辨識器: 嘗試發票辨識
            from app.services.invoice_recognizer import recognize_invoice
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name

            recognition = recognize_invoice(tmp_path)

            # 清理暫存
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

            if recognition and recognition.get("success"):
                data = recognition.get("data", {})
                lines = ["📄 發票辨識結果："]
                if data.get("inv_num"):
                    lines.append(f"發票號碼: {data['inv_num']}")
                if data.get("inv_date"):
                    lines.append(f"日期: {data['inv_date']}")
                if data.get("total_amount"):
                    lines.append(f"金額: {data['total_amount']}")
                if data.get("seller_name"):
                    lines.append(f"賣方: {data['seller_name']}")
                reply = "\n".join(lines)
            else:
                # 非發票：使用 Vision 模型描述
                prompt = caption or "請描述這張圖片的內容。如果是發票或公文，請提取重要資訊。"
                try:
                    from app.core.ai_connector import get_ai_connector
                    ai = get_ai_connector()
                    result = await ai.vision_completion(prompt, image_bytes)
                    reply = result or "無法辨識圖片內容。"
                except Exception:
                    reply = "圖片辨識功能暫不可用。"

            if len(reply) > 4000:
                reply = reply[:3997] + "..."
            await self.send_message(chat_id, reply)

        except Exception as e:
            logger.error("Telegram photo handling failed: %s", e)
            await self.send_message(chat_id, "圖片處理失敗，請稍後再試。")

    # ── 語音訊息處理 ──

    async def handle_voice(
        self,
        chat_id: int,
        user_id: int,
        file_id: str,
    ) -> None:
        """處理語音訊息：下載 → 轉文字 → Agent 問答 → 回覆。"""
        try:
            audio_bytes = await self._download_file(file_id)
            if not audio_bytes:
                await self.send_message(chat_id, "無法下載語音，請重新傳送。")
                return

            from app.services.ai.voice_transcriber import VoiceTranscriber
            transcriber = VoiceTranscriber()
            text = await transcriber.transcribe(audio_bytes, format="ogg")

            if not text:
                await self.send_message(chat_id, "無法辨識語音內容，請重試。")
                return

            # 先回覆辨識結果
            await self.send_message(chat_id, f"🎙 語音辨識: {text}")

            # 再以文字查詢 Agent
            await self.handle_text_message(chat_id, user_id, text)

        except Exception as e:
            logger.error("Telegram voice handling failed: %s", e)
            await self.send_message(chat_id, "語音處理失敗。")

    # ── Telegram Bot API 方法 ──

    async def send_message(
        self, chat_id: int, text: str, parse_mode: str = "Markdown",
    ) -> bool:
        """發送訊息至 Telegram chat"""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        success = await self._call_telegram_api("/sendMessage", payload)
        if not success and parse_mode == "Markdown":
            # Markdown 失敗時回退到純文字
            payload["parse_mode"] = ""
            success = await self._call_telegram_api("/sendMessage", payload)
        return success

    async def _send_and_get_id(
        self, chat_id: int, text: str, parse_mode: str = "",
    ) -> Optional[int]:
        """Send a message and return its message_id (for later editing).

        Returns None if the send fails.
        """
        if not self._bot_token:
            return None

        url = f"{TELEGRAM_API_BASE}/bot{self._bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.error("Telegram sendMessage failed: %d %s", resp.status_code, resp.text[:200])
                    return None
                data = resp.json()
                if not data.get("ok"):
                    return None
                return data.get("result", {}).get("message_id")
        except Exception as e:
            logger.error("Telegram sendMessage request failed: %s", e)
            return None

    async def _edit_message(
        self, chat_id: int, message_id: int, text: str, parse_mode: str = "",
    ) -> bool:
        """Edit an existing message via editMessageText."""
        if not self._bot_token:
            return False

        url = f"{TELEGRAM_API_BASE}/bot{self._bot_token}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text or "(empty)",
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    # 400 "message is not modified" is expected if text unchanged
                    if resp.status_code == 400 and "not modified" in resp.text.lower():
                        return True
                    logger.debug("Telegram editMessageText failed: %d %s", resp.status_code, resp.text[:200])
                    return False
                return True
        except Exception as e:
            logger.debug("Telegram editMessageText request failed: %s", e)
            return False

    async def push_message(self, chat_id: int, text: str) -> bool:
        """主動推播訊息（與 send_message 相同，語意對齊 LineBotService）"""
        return await self.send_message(chat_id, text)

    async def _call_telegram_api(self, path: str, payload: dict) -> bool:
        """呼叫 Telegram Bot API"""
        if not self._bot_token:
            logger.warning("Telegram Bot token not configured")
            return False

        url = f"{TELEGRAM_API_BASE}/bot{self._bot_token}{path}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.error(
                        "Telegram API %s failed: %d %s",
                        path,
                        resp.status_code,
                        resp.text[:200],
                    )
                    return False
                result = resp.json()
                if not result.get("ok"):
                    logger.error("Telegram API %s error: %s", path, result.get("description"))
                    return False
                return True
        except Exception as e:
            logger.error("Telegram API call failed: %s", e)
            return False

    async def _download_file(self, file_id: str) -> Optional[bytes]:
        """從 Telegram 伺服器下載檔案"""
        if not self._bot_token:
            return None

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Step 1: 取得檔案路徑
                resp = await client.get(
                    f"{TELEGRAM_API_BASE}/bot{self._bot_token}/getFile",
                    params={"file_id": file_id},
                )
                if resp.status_code != 200:
                    return None

                file_path = resp.json().get("result", {}).get("file_path")
                if not file_path:
                    return None

                # Step 2: 下載檔案
                dl_resp = await client.get(
                    f"{TELEGRAM_API_BASE}/file/bot{self._bot_token}/{file_path}"
                )
                return dl_resp.content if dl_resp.status_code == 200 else None
        except Exception as e:
            logger.error("Telegram file download failed: %s", e)
            return None


# ── Singleton ──

_service: Optional[TelegramBotService] = None


def get_telegram_bot_service() -> TelegramBotService:
    """取得 TelegramBotService 單例"""
    global _service
    if _service is None:
        _service = TelegramBotService()
    return _service

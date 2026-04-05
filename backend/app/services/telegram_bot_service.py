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

    # ── 文字訊息處理 ──

    async def handle_text_message(
        self,
        chat_id: int,
        user_id: int,
        text: str,
        username: str = "",
    ) -> None:
        """
        處理文字訊息：呼叫 AgentOrchestrator → Telegram 回覆。

        使用獨立 DB session（因為此方法在 BackgroundTask 中執行）。
        """
        tools_used: list[str] = []
        try:
            answer = await asyncio.wait_for(
                self._query_agent(user_id, text, tools_used),
                timeout=self._reply_timeout,
            )
        except asyncio.TimeoutError:
            answer = "⏱ 查詢處理時間較長，請稍後再試。"
            logger.warning("Telegram agent query timeout for user %s", user_id)
        except Exception as e:
            answer = "系統暫時無法回應，請稍後再試。"
            logger.error("Telegram agent query failed: %s", e)

        # 附加工具摘要
        if tools_used:
            tools_str = "、".join(tools_used[:5])
            answer += f"\n\n🔧 {tools_str}"

        # Telegram message limit: 4096 chars
        if len(answer) > 4000:
            answer = answer[:3997] + "..."

        await self.send_message(chat_id, answer)

    async def _query_agent(
        self, user_id: int, text: str, tools_used: list[str] | None = None,
    ) -> str:
        """呼叫 AgentOrchestrator 取得回答（含 Redis 對話記憶）"""
        from app.db.database import AsyncSessionLocal
        from app.services.ai.agent_orchestrator import AgentOrchestrator
        from app.services.ai.agent_conversation_memory import get_conversation_memory

        session_id = f"telegram:{user_id}"

        conv_memory = get_conversation_memory()
        history = await conv_memory.load(session_id)

        async with AsyncSessionLocal() as db:
            orchestrator = AgentOrchestrator(db)
            answer_tokens: list[str] = []

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
                elif event_type == "tool_call" and tools_used is not None:
                    tool_name = event.get("tool", "")
                    if tool_name and tool_name not in tools_used:
                        tools_used.append(tool_name)
                elif event_type == "error":
                    return event.get("error", "查詢失敗")

            answer = "".join(answer_tokens) or "無法產生回答，請換個方式提問。"

        await conv_memory.save(session_id, text, answer, history)
        return answer

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

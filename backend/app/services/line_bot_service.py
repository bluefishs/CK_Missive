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

import uuid
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# LINE API base URL
LINE_API_BASE = "https://api.line.me/v2/bot"
LINE_DATA_API_BASE = "https://api-data.line.me/v2/bot"

# 收據影像儲存目錄 (與 einvoice_sync.py 共用)
RECEIPT_UPLOAD_DIR = Path(os.getenv("RECEIPT_UPLOAD_DIR", "uploads/receipts"))

# 支援的圖片格式
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


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

        流程：
        1. 從 LINE Content API 下載圖片
        2. Tesseract OCR 辨識 (免費本地)
        3. 提取發票號碼/金額/日期/統編
        4. 回覆辨識結果

        在 BackgroundTask 中執行。
        """
        try:
            # 1. 下載圖片
            file_path = await self._download_line_content(message_id)
            if not file_path:
                await self.reply_message(reply_token, "圖片下載失敗，請重新傳送。")
                return

            # 2. OCR 辨識
            from app.services.invoice_ocr_service import InvoiceOCRService

            ocr_service = InvoiceOCRService()
            result = ocr_service.parse_image(str(file_path))

            # 3. 組裝回覆訊息
            if result.inv_num:
                lines = [
                    "📄 發票辨識結果",
                    f"發票號碼：{result.inv_num}",
                ]
                if result.date:
                    lines.append(f"日期：{result.date.strftime('%Y-%m-%d')}")
                if result.amount:
                    lines.append(f"金額：NT$ {result.amount:,.0f}")
                if result.tax_amount:
                    lines.append(f"稅額：NT$ {result.tax_amount:,.0f}")
                if result.seller_ban:
                    lines.append(f"賣方統編：{result.seller_ban}")
                if result.buyer_ban:
                    lines.append(f"買方統編：{result.buyer_ban}")

                lines.append(f"信心度：{result.confidence:.0%}")

                # 4. 嘗試建立費用紀錄 (需要 LINE user → system user 對應)
                expense_msg = await self._try_create_expense_from_ocr(
                    user_id, result, str(file_path)
                )
                if expense_msg:
                    lines.append("")
                    lines.append(expense_msg)

                if result.warnings:
                    lines.append("")
                    lines.append("⚠️ " + "、".join(result.warnings))

                reply = "\n".join(lines)
            else:
                reply = (
                    "📄 未能辨識發票資訊\n\n"
                    "請確認：\n"
                    "• 拍攝清晰、光線充足\n"
                    "• 發票完整入鏡\n"
                    "• 避免反光或模糊\n"
                )
                if result.warnings:
                    reply += "\n⚠️ " + "、".join(result.warnings)

            await self.reply_message(reply_token, reply)

        except Exception as e:
            logger.error("LINE image processing failed: %s", e, exc_info=True)
            await self.reply_message(reply_token, "圖片處理時發生錯誤，請重新傳送。")

    async def _download_line_content(self, message_id: str) -> Optional[Path]:
        """從 LINE Content API 下載檔案"""
        RECEIPT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{LINE_DATA_API_BASE}/message/{message_id}/content",
                    headers={
                        "Authorization": f"Bearer {self._channel_access_token}",
                    },
                )
                if resp.status_code != 200:
                    logger.warning(
                        "LINE content download failed: %d", resp.status_code
                    )
                    return None

                # 從 Content-Type 判斷副檔名
                content_type = resp.headers.get("content-type", "image/jpeg")
                ext_map = {
                    "image/jpeg": ".jpg",
                    "image/png": ".png",
                    "image/webp": ".webp",
                }
                ext = ext_map.get(content_type, ".jpg")

                filename = f"line_{uuid.uuid4().hex}{ext}"
                file_path = RECEIPT_UPLOAD_DIR / filename

                file_path.write_bytes(resp.content)
                logger.info("LINE image saved: %s (%d bytes)", filename, len(resp.content))
                return file_path

        except Exception as e:
            logger.error("LINE content download error: %s", e)
            return None

    async def _try_create_expense_from_ocr(
        self,
        line_user_id: str,
        ocr_result: "InvoiceOCRResult",
        image_path: str,
    ) -> Optional[str]:
        """嘗試用 OCR 結果建立費用紀錄 (需要 LINE user → system user 對應)"""
        if not ocr_result.inv_num or not ocr_result.amount:
            return None

        try:
            from app.db.database import AsyncSessionLocal
            from sqlalchemy import select
            from app.extended.models import User

            async with AsyncSessionLocal() as db:
                # 找到 LINE user 對應的系統使用者
                result = await db.execute(
                    select(User).where(User.line_user_id == line_user_id)
                )
                user = result.scalars().first()

                if not user:
                    return "💡 請先在系統中綁定 LINE 帳號，即可自動建立費用紀錄。"

                # 檢查發票號碼是否已存在
                from app.services.expense_invoice_service import ExpenseInvoiceService

                expense_service = ExpenseInvoiceService(db)

                # 建立相對路徑 (receipts/line_xxx.jpg)
                relative_path = f"receipts/{Path(image_path).name}"

                from app.schemas.erp.expense import ExpenseInvoiceCreate
                from datetime import date as date_cls

                create_data = ExpenseInvoiceCreate(
                    inv_num=ocr_result.inv_num,
                    amount=ocr_result.amount,
                    tax_amount=ocr_result.tax_amount,
                    date=ocr_result.date or date_cls.today(),
                    buyer_ban=ocr_result.buyer_ban or "",
                    seller_ban=ocr_result.seller_ban or "",
                    category="其他",
                    source="line_upload",
                    receipt_image_path=relative_path,
                )

                try:
                    expense = await expense_service.create(create_data, user_id=user.id)
                    return f"✅ 費用紀錄已建立 (ID: {expense.get('id', '?')})"
                except ValueError as e:
                    err_msg = str(e)
                    if "已存在" in err_msg:
                        return f"ℹ️ 發票 {ocr_result.inv_num} 已存在系統中。"
                    return f"⚠️ 建立失敗：{err_msg}"

        except Exception as e:
            logger.warning("Auto-create expense from LINE failed: %s", e)
            return None

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

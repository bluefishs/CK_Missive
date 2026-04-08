"""
Discord Bot 整合服務

支援 Discord Interactions Endpoint (HTTP webhook 模式)：
- Ed25519 簽名驗證
- Slash Command 處理 (/ck-ask, /ck-doc, /ck-case)
- 文字訊息回覆 (Embed)
- Push 通知 (Channel Message)
- Edit-Streaming: 逐步編輯同一訊息呈現 Agent 串流回答
- StatusIndicator: 訊息前綴狀態指示器 (inspired by agent-broker)

Version: 1.2.0
Created: 2026-03-25
Updated: 2026-04-08 - v1.2.0 Extract helpers to discord_helpers.py
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional

from app.services.discord_helpers import (
    StatusIndicator,
    COLOR_SUCCESS,
    COLOR_INFO,
    COLOR_WARNING,
    COLOR_ERROR,
    MAX_EMBED_DESCRIPTION,
    MAX_MESSAGE_CONTENT,
    EDIT_INTERVAL,
    SAFE_CONTENT_LEN,
    truncate,
    edit_followup,
    make_embed_response,
    make_fields_embed,
)

logger = logging.getLogger(__name__)

# Backward-compatible aliases for private names used in tests
_COLOR_SUCCESS = COLOR_SUCCESS
_COLOR_INFO = COLOR_INFO
_COLOR_WARNING = COLOR_WARNING
_COLOR_ERROR = COLOR_ERROR
_MAX_EMBED_DESCRIPTION = MAX_EMBED_DESCRIPTION
_MAX_MESSAGE_CONTENT = MAX_MESSAGE_CONTENT
_EDIT_INTERVAL = EDIT_INTERVAL
_SAFE_CONTENT_LEN = SAFE_CONTENT_LEN
_truncate = truncate
_edit_followup = edit_followup
_make_embed_response = make_embed_response
_make_fields_embed = make_fields_embed


class DiscordBotService:
    """Discord Bot Service — Interactions Endpoint 模式"""

    def __init__(self):
        self.enabled = os.getenv("DISCORD_BOT_ENABLED", "false").lower() == "true"
        self.public_key = os.getenv("DISCORD_PUBLIC_KEY", "")
        self.bot_token = os.getenv("DISCORD_BOT_TOKEN", "")
        self.application_id = os.getenv("DISCORD_APPLICATION_ID", "")

    def verify_signature(self, body: bytes, signature: str, timestamp: str) -> bool:
        """
        驗證 Discord Interaction 簽名 (Ed25519)

        Discord 使用 Ed25519 而非 HMAC：
        message = timestamp_bytes + body_bytes
        verify(public_key, message, signature)
        """
        if not self.public_key:
            logger.warning("DISCORD_PUBLIC_KEY not configured")
            return False

        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            key_bytes = bytes.fromhex(self.public_key)
            public_key = Ed25519PublicKey.from_public_bytes(key_bytes)
            message = timestamp.encode() + body
            sig_bytes = bytes.fromhex(signature)
            public_key.verify(sig_bytes, message)
            return True
        except ImportError:
            logger.error("cryptography package required for Discord Ed25519 verification")
            return False
        except Exception as e:
            logger.debug("Discord signature verification failed: %s", e)
            return False

    async def handle_slash_command(
        self, command_name: str, options: Dict[str, Any], user_id: str,
    ) -> Dict[str, Any]:
        """
        處理 Slash Command — 委派給 Agent 或直接查詢

        Returns:
            Discord Interaction Response (type 4 = CHANNEL_MESSAGE_WITH_SOURCE)
        """
        if command_name == "ck-ask":
            question = options.get("question", "")
            return await self._handle_agent_query(question, user_id)
        elif command_name == "ck-doc":
            doc_number = options.get("doc_number", "")
            return await self._handle_doc_query(doc_number)
        elif command_name == "ck-case":
            case_code = options.get("case_code", "")
            return await self._handle_case_query(case_code)
        else:
            return _make_embed_response(
                title="未知指令",
                description=f"不支援的指令: `/{command_name}`",
                color=_COLOR_WARNING,
            )

    async def handle_deferred_agent_query(
        self,
        question: str,
        user_id: str,
        interaction_token: str,
        application_id: str,
        channel_id: Optional[str] = None,
        user_display_name: Optional[str] = None,
    ) -> None:
        """Edit-Streaming: send initial followup, then edit as tokens arrive.

        Uses AgentStreamCollector for shared streaming logic:
        1. POST initial "thinking" followup message
        2. Stream tokens from agent, editing the message every ~1.5s via collector
        3. Final edit with complete response (removes cursor indicator)
        """
        import httpx
        from app.services.sender_context import SenderContext
        from app.services.agent_stream_helper import AgentStreamCollector

        webhook_base = f"https://discord.com/api/v10/webhooks/{application_id}/{interaction_token}"

        status = StatusIndicator()

        # Build sender context for agent
        sender_ctx = SenderContext(
            user_id=user_id,
            display_name=user_display_name or f"Discord#{user_id[:8]}",
            channel="discord",
            channel_id=channel_id,
        )

        # Step 1: Send initial "thinking" followup
        try:
            async with httpx.AsyncClient() as client:
                init_resp = await client.post(
                    webhook_base,
                    json={"content": f"{status.format_prefix()}\u601d\u8003\u4e2d..."},
                    timeout=10,
                )
                if init_resp.status_code not in (200, 204):
                    logger.error(
                        "Discord followup init failed: %s %s",
                        init_resp.status_code, init_resp.text,
                    )
                    return
        except Exception as e:
            logger.error("Discord followup init request failed: %s", e)
            return

        # Step 2: Stream via shared collector with edit callbacks
        async def on_status_change(emoji: str, description: str) -> None:
            status.set_status(emoji)

        async def on_text_update(partial: str) -> None:
            display = _truncate(partial, _SAFE_CONTENT_LEN)
            await _edit_followup(
                webhook_base,
                f"{status.format_prefix()}{display} \u258d",  # cursor
            )

        collector = AgentStreamCollector(
            on_status_change=on_status_change,
            on_text_update=on_text_update,
            update_interval=_EDIT_INTERVAL,
        )

        try:
            from app.services.ai.agent_orchestrator import AgentOrchestrator
            from app.services.ai.agent_conversation_memory import get_conversation_memory
            from app.db.database import AsyncSessionLocal

            session_id = f"discord:{user_id}"
            conv_memory = get_conversation_memory()
            history = await conv_memory.load(session_id)

            async with AsyncSessionLocal() as db:
                orchestrator = AgentOrchestrator(db)
                result = await collector.collect(
                    orchestrator.stream_agent_query(
                        question=question[:2000],
                        session_id=session_id,
                        history=history,
                        sender_context=sender_ctx,
                    )
                )

            await conv_memory.save(session_id, question, result.answer, history)

        except Exception as e:
            logger.error("Discord edit-streaming agent query failed: %s", e)
            if not collector._tokens:
                collector._tokens.append("Agent \u8655\u7406\u6642\u767c\u751f\u932f\u8aa4\uff0c\u8acb\u7a0d\u5f8c\u518d\u8a66\u3002")
            collector._had_error = True
            # Build a minimal result for the final edit
            from app.services.agent_stream_helper import StreamResult
            result = StreamResult(
                answer="".join(collector._tokens),
                tools_used=list(collector._tools),
                latency_ms=0,
                token_count=len(collector._tokens),
            )

        # Step 3: Final edit with complete response
        final_status = StatusIndicator.ERROR if collector.had_error else StatusIndicator.DONE
        display = _truncate(result.answer, _SAFE_CONTENT_LEN)

        footer = ""
        if result.tools_used:
            footer = f"\n\n`tools: {', '.join(result.tools_used[:5])}`"

        final_content = f"{final_status} {display}{footer}"
        await _edit_followup(webhook_base, final_content)

    async def _handle_agent_query(self, question: str, user_id: str) -> Dict[str, Any]:
        """Agent 問答 — 同步模式 (非 deferred 的 fallback)"""
        if not question.strip():
            return _make_embed_response(
                title="請輸入問題",
                description="用法: `/ck-ask question:你的問題`",
                color=_COLOR_WARNING,
            )

        try:
            from app.services.ai.agent_orchestrator import AgentOrchestrator
            from app.services.sender_context import SenderContext
            from app.db.database import AsyncSessionLocal as async_session_factory

            sender_ctx = SenderContext(
                user_id=user_id,
                display_name=f"Discord#{user_id[:8]}",
                channel="discord",
            )

            async with async_session_factory() as db:
                orchestrator = AgentOrchestrator(db)
                # 收集 SSE 事件轉為文字回覆
                answer_parts = []
                async for event in orchestrator.stream_agent_query(
                    question=question[:2000],
                    session_id=f"discord:{user_id}",
                    sender_context=sender_ctx,
                ):
                    try:
                        data = json.loads(event.replace("data: ", "").strip())
                        if data.get("type") == "token":
                            answer_parts.append(data.get("token", ""))
                    except (ValueError, AttributeError):
                        pass

                answer = "".join(answer_parts) or "抱歉，我無法回答這個問題。"
                return _make_embed_response(
                    title=f"\U0001f50d {question[:80]}",
                    description=answer[:_MAX_EMBED_DESCRIPTION],
                    color=_COLOR_INFO,
                )
        except Exception as e:
            logger.error("Discord agent query failed: %s", e)
            return _make_embed_response(
                title="查詢失敗",
                description="Agent 處理時發生錯誤，請稍後再試。",
                color=_COLOR_ERROR,
            )

    async def _handle_doc_query(self, doc_number: str) -> Dict[str, Any]:
        """公文查詢 — 依文號搜尋 DB"""
        if not doc_number.strip():
            return _make_embed_response(
                title="請輸入文號",
                description="用法: `/ck-doc doc_number:文號`",
                color=_COLOR_WARNING,
            )
        try:
            from app.db.database import AsyncSessionLocal as async_session_factory
            from app.repositories.document_repository import DocumentRepository

            async with async_session_factory() as db:
                repo = DocumentRepository(db)
                doc = await repo.get_by_doc_number(doc_number.strip())
                if doc:
                    fields = [
                        {"name": "文號", "value": doc.doc_number or "\u2014", "inline": True},
                        {"name": "類型", "value": doc.doc_type or "\u2014", "inline": True},
                        {"name": "發文機關", "value": doc.sender or "\u2014", "inline": True},
                        {"name": "受文者", "value": doc.receiver or "\u2014", "inline": True},
                        {"name": "日期", "value": str(doc.doc_date) if doc.doc_date else "\u2014", "inline": True},
                    ]
                    return _make_fields_embed(
                        title=f"\U0001f4c4 {doc.subject or doc_number}",
                        fields=fields,
                        color=_COLOR_SUCCESS,
                    )
                return _make_embed_response(
                    title=f"\U0001f4c4 查無公文: {doc_number}",
                    description="找不到符合的公文，請確認文號是否正確。",
                    color=_COLOR_WARNING,
                )
        except Exception as e:
            logger.error("Discord doc query failed: %s", e)
            return _make_embed_response(
                title="查詢失敗", description="資料庫查詢時發生錯誤。",
                color=_COLOR_ERROR,
            )

    async def _handle_case_query(self, case_code: str) -> Dict[str, Any]:
        """案件查詢 — 依案號搜尋 DB"""
        if not case_code.strip():
            return _make_embed_response(
                title="請輸入案號",
                description="用法: `/ck-case case_code:案號`",
                color=_COLOR_WARNING,
            )
        try:
            from app.db.database import AsyncSessionLocal as async_session_factory
            from app.repositories.project_repository import ProjectRepository

            async with async_session_factory() as db:
                repo = ProjectRepository(db)
                project = await repo.get_by_project_code(case_code.strip())
                if project:
                    fields = [
                        {"name": "案號", "value": project.project_code or project.case_code or "\u2014", "inline": True},
                        {"name": "狀態", "value": project.status or "\u2014", "inline": True},
                        {"name": "委託單位", "value": getattr(project, "client_name", None) or "\u2014", "inline": True},
                    ]
                    return _make_fields_embed(
                        title=f"\U0001f4cb {project.project_name or case_code}",
                        fields=fields,
                        color=_COLOR_SUCCESS,
                    )
                return _make_embed_response(
                    title=f"\U0001f4cb 查無案件: {case_code}",
                    description="找不到符合的案件，請確認案號格式。",
                    color=_COLOR_WARNING,
                )
        except Exception as e:
            logger.error("Discord case query failed: %s", e)
            return _make_embed_response(
                title="查詢失敗", description="資料庫查詢時發生錯誤。",
                color=_COLOR_ERROR,
            )

    async def send_channel_message(self, channel_id: str, content: str) -> bool:
        """推送訊息到 Discord Channel"""
        return await self._post_channel(channel_id, {"content": content[:_MAX_MESSAGE_CONTENT]})

    async def send_channel_embed(
        self, channel_id: str, title: str, description: str,
        color: int = _COLOR_INFO, fields: list = None,
    ) -> bool:
        """推送 Embed 到 Discord Channel"""
        embed: dict = {"title": title, "description": description[:4096], "color": color}
        if fields:
            embed["fields"] = [
                {"name": f["name"][:256], "value": f["value"][:1024], "inline": f.get("inline", True)}
                for f in fields[:25]
            ]
        return await self._post_channel(channel_id, {"embeds": [embed]})

    async def send_dispatch_progress(self, channel_id: str, summary: dict) -> bool:
        """推送派工進度彙整 Embed"""
        completed = summary.get('completed', [])
        overdue = summary.get('overdue', [])
        in_progress = summary.get('in_progress', [])
        alerts = summary.get('key_alerts', [])

        desc = f"\u2705 已完成 {len(completed)} | \U0001f504 進行中 {len(in_progress)} | \U0001f534 逾期 {len(overdue)}"
        fields = []

        if overdue:
            overdue_text = "\n".join(
                f"\u26a0\ufe0f {o['dispatch_no'].replace('115年_', '')} ({o.get('case_handler','?')}) 逾期{o.get('overdue_days',0)}天"
                for o in overdue[:5]
            )
            fields.append({"name": "\U0001f534 逾期派工單", "value": overdue_text, "inline": False})

        if alerts:
            fields.append({"name": "關鍵提醒", "value": "\n".join(f"\u30fb{a}" for a in alerts[:3]), "inline": False})

        return await self.send_channel_embed(
            channel_id, "\U0001f4ca 派工進度彙整", desc,
            color=0xE74C3C if overdue else _COLOR_SUCCESS, fields=fields,
        )

    async def _post_channel(self, channel_id: str, payload: dict) -> bool:
        """POST 訊息到 Discord Channel"""
        if not self.bot_token:
            logger.warning("DISCORD_BOT_TOKEN not configured")
            return False
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://discord.com/api/v10/channels/{channel_id}/messages",
                    headers={"Authorization": f"Bot {self.bot_token}"},
                    json=payload,
                    timeout=10,
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error("Discord push failed: %s", e)
            return False


# ── Singleton ──

_instance: Optional[DiscordBotService] = None


def get_discord_bot_service() -> DiscordBotService:
    global _instance
    if _instance is None:
        _instance = DiscordBotService()
    return _instance

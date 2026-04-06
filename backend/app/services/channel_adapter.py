"""
統一通道抽象 — LINE / Discord / Telegram 共用介面

為各通道提供一致的訊息處理接口：
- 簽名驗證
- 訊息解析
- 回覆/推送
- Agent 問答整合

Version: 1.0.0
Created: 2026-03-25
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ChannelMessage:
    """統一訊息結構"""
    platform: str               # "line" | "discord" | "telegram"
    message_id: str             # 平台原生 message ID
    user_id: str                # 平台原生 user ID
    channel_id: str             # 群組/頻道 ID (1:1 時為空)
    content: str                # 文字內容
    message_type: str = "text"  # "text" | "audio" | "image" | "command"
    reply_token: str = ""       # LINE reply token / Discord interaction token
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RichCard:
    """統一卡片結構 (Flex Message / Embed / 等)"""
    title: str
    description: str
    color: str = "#1890FF"
    fields: List[Dict[str, str]] = field(default_factory=list)
    footer: str = "CK Missive Agent"


class ChannelAdapter(ABC):
    """統一通道抽象基類"""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台識別名稱"""
        ...

    @abstractmethod
    def verify_request(self, body: bytes, headers: Dict[str, str]) -> bool:
        """驗證請求簽名"""
        ...

    @abstractmethod
    def parse_messages(self, payload: Dict[str, Any]) -> List[ChannelMessage]:
        """解析原生 payload 為統一訊息"""
        ...

    @abstractmethod
    async def send_reply(self, message: ChannelMessage, text: str) -> bool:
        """回覆訊息"""
        ...

    @abstractmethod
    async def send_rich(self, message: ChannelMessage, card: RichCard) -> bool:
        """發送卡片訊息"""
        ...

    @abstractmethod
    async def push_message(self, target_id: str, text: str) -> bool:
        """主動推送訊息"""
        ...

    async def handle_agent_query(
        self, message: ChannelMessage, timeout: float = 25.0,
    ) -> str:
        """統一 Agent 問答路徑（含 SenderContext 注入）"""
        try:
            from app.services.ai.agent_orchestrator import AgentOrchestrator
            from app.services.sender_context import SenderContext
            from app.db.database import AsyncSessionLocal as async_session_factory
            import json

            sender_ctx = SenderContext(
                user_id=message.user_id,
                display_name=f"{self.platform_name}#{message.user_id[:8]}",
                channel=self.platform_name,
                channel_id=message.channel_id or None,
            )

            async with async_session_factory() as db:
                orchestrator = AgentOrchestrator(db)
                answer_parts = []
                async for event in orchestrator.stream_agent_query(
                    question=message.content[:2000],
                    session_id=f"{self.platform_name}:{message.user_id}",
                    sender_context=sender_ctx,
                ):
                    try:
                        data = json.loads(event.replace("data: ", "").strip())
                        if data.get("type") == "token":
                            answer_parts.append(data.get("token", ""))
                    except (ValueError, AttributeError):
                        pass

                return "".join(answer_parts) or "抱歉，我無法回答這個問題。"
        except Exception as e:
            logger.error("%s agent query failed: %s", self.platform_name, e)
            return "Agent 處理時發生錯誤，請稍後再試。"


# ── Registry ──

_adapters: Dict[str, ChannelAdapter] = {}


def register_adapter(adapter: ChannelAdapter) -> None:
    """註冊通道 adapter"""
    _adapters[adapter.platform_name] = adapter


def get_adapter(platform: str) -> Optional[ChannelAdapter]:
    """取得通道 adapter"""
    return _adapters.get(platform)


def list_adapters() -> List[str]:
    """列出已註冊的通道"""
    return list(_adapters.keys())

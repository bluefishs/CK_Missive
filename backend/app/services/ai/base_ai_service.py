"""
AI 服務基類

Version: 1.0.0
Created: 2026-02-04
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.core.ai_connector import AIConnector, get_ai_connector
from .ai_config import AIConfig, get_ai_config

logger = logging.getLogger(__name__)


class BaseAIService(ABC):
    """AI 服務基類"""

    def __init__(
        self,
        connector: Optional[AIConnector] = None,
        config: Optional[AIConfig] = None,
    ):
        self.connector = connector or get_ai_connector()
        self.config = config or get_ai_config()

    def is_enabled(self) -> bool:
        """檢查 AI 服務是否啟用"""
        return self.config.enabled

    async def _call_ai(
        self,
        system_prompt: str,
        user_content: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        呼叫 AI 服務

        Args:
            system_prompt: 系統提示詞
            user_content: 使用者輸入
            temperature: 生成溫度（可選）
            max_tokens: 最大回應長度（可選）

        Returns:
            AI 生成的回應
        """
        if not self.is_enabled():
            raise RuntimeError("AI 服務未啟用")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        return await self.connector.chat_completion(
            messages=messages,
            temperature=temperature or self.config.default_temperature,
            max_tokens=max_tokens or 1024,
        )

    async def check_health(self) -> Dict[str, Any]:
        """檢查 AI 服務健康狀態"""
        return await self.connector.check_health()

"""
混合 AI 連接器

Version: 1.0.0
Created: 2026-02-04
Author: CK_Missive Team

支援的 AI 服務優先順序:
1. Groq API (免費，超快 ~100-500ms，llama3-70b)
2. 本地 Ollama (離線備援)
3. 智慧預設回應 (最終備援)

免費方案設計:
- Groq 免費額度：30 req/min, 14,400/day
- Ollama 完全免費（本地運行）
"""

import asyncio
import json
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Groq API 配置
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Ollama 配置
OLLAMA_DEFAULT_URL = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "llama3.1:8b"


class AIConnector:
    """
    混合 AI 連接器 - Groq（雲端）+ Ollama（本地）

    優先使用 Groq API（免費、快速），
    失敗時自動切換到本地 Ollama。
    """

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        cloud_timeout: int = 30,
        local_timeout: int = 60,
    ):
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY", "")
        self.ollama_base_url = ollama_base_url or os.getenv(
            "OLLAMA_BASE_URL", OLLAMA_DEFAULT_URL
        )
        self.cloud_timeout = cloud_timeout
        self.local_timeout = local_timeout

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """
        執行 AI 對話完成

        Args:
            messages: 對話訊息列表，格式為 [{"role": "user/assistant/system", "content": "..."}]
            model: 指定模型（可選）
            temperature: 生成溫度（0-1）
            max_tokens: 最大回應長度

        Returns:
            AI 生成的回應文字

        Raises:
            AIServiceException: 所有 AI 服務均不可用時拋出
        """
        # 嘗試 Groq API（雲端、免費）
        if self.groq_api_key:
            try:
                logger.info("嘗試 Groq API...")
                return await self._groq_completion(
                    messages, model or GROQ_DEFAULT_MODEL, temperature, max_tokens
                )
            except Exception as e:
                logger.warning(f"Groq API 失敗: {e}")

        # 嘗試 Ollama（本地）
        try:
            logger.info("嘗試本地 Ollama...")
            return await self._ollama_completion(
                messages, model or OLLAMA_DEFAULT_MODEL, temperature, max_tokens
            )
        except Exception as e:
            logger.warning(f"Ollama 失敗: {e}")

        # 最終備援
        logger.error("所有 AI 服務均不可用，使用預設回應")
        return self._generate_fallback_response(
            messages[-1]["content"] if messages else ""
        )

    async def _groq_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """查詢 Groq API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=self.cloud_timeout,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"Groq API 回應成功 (model={model})")
            return content

    async def _ollama_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """查詢本地 Ollama"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                    "stream": False,
                },
                timeout=self.local_timeout,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("message", {}).get("content", "")
            logger.info(f"Ollama 回應成功 (model={model})")
            return content

    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """
        串流 AI 回應生成器

        Yields:
            每個文字片段 (chunk)
        """
        # 嘗試 Groq 串流
        if self.groq_api_key:
            try:
                logger.info("嘗試 Groq 串流 API...")
                async for chunk in self._stream_groq(
                    messages, model or GROQ_DEFAULT_MODEL, temperature, max_tokens
                ):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"Groq 串流失敗: {e}")

        # 嘗試 Ollama 串流
        try:
            logger.info("嘗試 Ollama 串流...")
            async for chunk in self._stream_ollama(
                messages, model or OLLAMA_DEFAULT_MODEL, temperature, max_tokens
            ):
                yield chunk
            return
        except Exception as e:
            logger.warning(f"Ollama 串流失敗: {e}")

        # 備援：一次輸出
        fallback = self._generate_fallback_response(
            messages[-1]["content"] if messages else ""
        )
        yield fallback

    async def _stream_groq(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Groq API 串流回應"""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                },
                timeout=self.cloud_timeout,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        logger.info(f"Groq 串流完成 (model={model})")

    async def _stream_ollama(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Ollama 串流回應"""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.ollama_base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                    "stream": True,
                },
                timeout=self.local_timeout,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        logger.info(f"Ollama 串流完成 (model={model})")

    def _generate_fallback_response(self, question: str) -> str:
        """生成智慧備用回應（公文相關）"""
        fallback_responses = {
            "公文": "這是一份公文，建議您確認收發類別與處理狀態後進行適當歸檔。",
            "函": "此為「函」類公文，通常用於機關間業務聯繫或答復事項。",
            "收文": "收文公文已登錄，請確認處理時限並指派承辦人員。",
            "發文": "發文公文準備中，請確認內容正確後進行核章程序。",
            "分類": "公文分類建議根據業務性質與主旨內容判斷，常見類型包括：函、令、公告、書函等。",
            "摘要": "公文摘要應簡要說明主旨、目的及處理要求，建議控制在100字以內。",
        }

        for keyword, response in fallback_responses.items():
            if keyword in question:
                return f"{response}\n\n（AI 服務暫時不可用，以上為系統預設建議）"

        return (
            "感謝您的詢問。目前 AI 服務暫時不可用，建議您：\n\n"
            "1. 檢查公文類型與分類是否正確\n"
            "2. 確認處理時限與承辦人員\n"
            "3. 稍後再次嘗試使用 AI 助理\n\n"
            "系統正在努力恢復服務。"
        )

    async def check_health(self) -> Dict[str, Any]:
        """檢查 AI 服務健康狀態"""
        status = {
            "groq": {"available": False, "message": ""},
            "ollama": {"available": False, "message": ""},
        }

        # 檢查 Groq
        if self.groq_api_key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.groq.com/openai/v1/models",
                        headers={"Authorization": f"Bearer {self.groq_api_key}"},
                        timeout=10,
                    )
                    if response.status_code == 200:
                        status["groq"]["available"] = True
                        status["groq"]["message"] = "Groq API 可用"
                    else:
                        status["groq"]["message"] = f"HTTP {response.status_code}"
            except Exception as e:
                status["groq"]["message"] = str(e)
        else:
            status["groq"]["message"] = "未設定 GROQ_API_KEY"

        # 檢查 Ollama
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.ollama_base_url}/api/tags",
                    timeout=5,
                )
                if response.status_code == 200:
                    status["ollama"]["available"] = True
                    models = response.json().get("models", [])
                    status["ollama"]["message"] = f"Ollama 可用，{len(models)} 個模型"
                else:
                    status["ollama"]["message"] = f"HTTP {response.status_code}"
        except Exception as e:
            status["ollama"]["message"] = str(e)

        return status


# 全域 AI 連接器實例
_ai_connector: Optional[AIConnector] = None


def get_ai_connector() -> AIConnector:
    """獲取 AI 連接器實例（Singleton）"""
    global _ai_connector
    if _ai_connector is None:
        _ai_connector = AIConnector()
    return _ai_connector


async def get_ai_connector_async() -> AIConnector:
    """異步獲取 AI 連接器實例"""
    return get_ai_connector()

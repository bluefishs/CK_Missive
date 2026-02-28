"""
混合 AI 連接器

Version: 1.1.0
Created: 2026-02-04
Updated: 2026-02-26 - v1.1.0 Qwen3 thinking mode 支援 + format=json

支援的 AI 服務優先順序:
1. Groq API (免費，超快 ~100-500ms，llama3-70b)
2. 本地 Ollama (離線備援)
3. 智慧預設回應 (最終備援)

免費方案設計:
- Groq 免費額度：30 req/min, 14,400/day
- Ollama 完全免費（本地運行）

Qwen3 thinking mode 處理:
- 結構化任務 (NER/intent/classify): think=false + format=json
- 生成任務 (RAG chat/summary): think=false（4B 推理品質不足以抵消延遲開銷）
- 安全網: 內容後處理移除殘留 <think> 區塊
"""

import asyncio
import json
import logging
import os
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Groq API 配置
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Ollama 配置
OLLAMA_DEFAULT_URL = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")

# Retry 配置
MAX_RETRIES = 2
RETRY_BASE_DELAY = 0.5  # 秒（首次重試加速）
RETRYABLE_STATUS_CODES = {429, 500, 502, 503}

# 任務→模型映射 — 不同任務可配置不同模型（未來可替換為更適合的模型）
TASK_MODEL_MAP = {
    "chat": os.getenv("OLLAMA_CHAT_MODEL", OLLAMA_DEFAULT_MODEL),
    "ner": os.getenv("OLLAMA_NER_MODEL", OLLAMA_DEFAULT_MODEL),
    "summary": os.getenv("OLLAMA_SUMMARY_MODEL", OLLAMA_DEFAULT_MODEL),
    "classify": os.getenv("OLLAMA_CLASSIFY_MODEL", OLLAMA_DEFAULT_MODEL),
    "embedding": os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
}

# 需要禁用 thinking mode 的模型前綴（Qwen3、DeepSeek-R1 等推理模型）
_THINKING_MODEL_PREFIXES = ("qwen3", "deepseek-r1")

# 系統所需模型清單（啟動時自動檢查 + 拉取）
REQUIRED_MODELS: set = {
    OLLAMA_DEFAULT_MODEL,
    os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
}


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
        local_timeout: int = 120,
        embed_timeout: int = 30,
    ):
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY", "")
        self.ollama_base_url = ollama_base_url or os.getenv(
            "OLLAMA_BASE_URL", OLLAMA_DEFAULT_URL
        )
        self.cloud_timeout = cloud_timeout
        self.local_timeout = local_timeout
        self.embed_timeout = embed_timeout

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        prefer_local: bool = False,
        task_type: Optional[str] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        執行 AI 對話完成

        Args:
            messages: 對話訊息列表，格式為 [{"role": "user/assistant/system", "content": "..."}]
            model: 指定模型（可選，未指定時根據 task_type 從 TASK_MODEL_MAP 取得）
            temperature: 生成溫度（0-1）
            max_tokens: 最大回應長度
            prefer_local: True 時 Ollama 優先（適用於 NER、批次等非即時任務）
            task_type: 任務類型（ner/summary/classify/chat），用於選擇對應模型
            response_format: 回應格式（Groq 專用，如 {"type": "json_object"}）

        Returns:
            AI 生成的回應文字

        Raises:
            AIServiceException: 所有 AI 服務均不可用時拋出
        """
        # 分離 Groq / Ollama 模型選擇
        # TASK_MODEL_MAP 是 Ollama 專用模型名（如 qwen3:4b）
        # Groq 必須使用 GROQ_DEFAULT_MODEL（如 llama-3.3-70b-versatile）
        ollama_model = model or OLLAMA_DEFAULT_MODEL
        # 若 model 是 Ollama 格式（含冒號如 qwen3:4b）或等於 Ollama 預設，使用 Groq 預設模型
        groq_model = GROQ_DEFAULT_MODEL if not model or ":" in model else model

        if not model and task_type:
            ollama_model = TASK_MODEL_MAP.get(task_type, OLLAMA_DEFAULT_MODEL)
            groq_model = GROQ_DEFAULT_MODEL  # task_type 映射僅影響 Ollama

        # Ollama-First 路徑（NER、批次、非即時任務 — 本地無限量）
        if prefer_local:
            try:
                logger.info("Ollama-first: 嘗試本地 Ollama (model=%s)...", ollama_model)
                return await self._ollama_completion(
                    messages, ollama_model, temperature, max_tokens,
                    response_format=response_format,
                )
            except Exception as e:
                logger.warning("Ollama-first 失敗，降級至 Groq: %s", e)
                # 繼續到下方 Groq-first 邏輯作為 fallback

        # 嘗試 Groq API（雲端、免費）— 含重試機制
        if self.groq_api_key:
            last_error: Optional[Exception] = None
            for attempt in range(MAX_RETRIES + 1):
                try:
                    if attempt == 0:
                        logger.info("嘗試 Groq API (model=%s)...", groq_model)
                    else:
                        delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                        logger.info(
                            "Groq API 重試 %d/%d（延遲 %.1f 秒）...",
                            attempt, MAX_RETRIES, delay,
                        )
                        await asyncio.sleep(delay)
                    return await self._groq_completion(
                        messages, groq_model, temperature, max_tokens,
                        response_format=response_format,
                    )
                except httpx.TimeoutException as e:
                    last_error = e
                    logger.warning("Groq API 逾時 (attempt %d/%d): %s",
                                   attempt + 1, MAX_RETRIES + 1, e)
                except httpx.HTTPStatusError as e:
                    last_error = e
                    if e.response.status_code in RETRYABLE_STATUS_CODES:
                        logger.warning(
                            "Groq API HTTP %d (attempt %d/%d): %s",
                            e.response.status_code, attempt + 1,
                            MAX_RETRIES + 1, e,
                        )
                    else:
                        logger.warning("Groq API 不可重試錯誤 HTTP %d: %s",
                                       e.response.status_code, e)
                        break
                except Exception as e:
                    last_error = e
                    logger.warning("Groq API 非預期錯誤: %s", e)
                    break
            if last_error:
                logger.warning("Groq API 最終失敗: %s", last_error)

        # 嘗試 Ollama（本地）
        try:
            logger.info("嘗試本地 Ollama (model=%s)...", ollama_model)
            return await self._ollama_completion(
                messages, ollama_model, temperature, max_tokens,
                response_format=response_format,
            )
        except Exception as e:
            logger.warning("Ollama 失敗: %s", e)

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
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """查詢 Groq API"""
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.cloud_timeout,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"Groq API 回應成功 (model={model})")
            return content

    @staticmethod
    def _is_thinking_model(model: str) -> bool:
        """判斷是否為推理模型（需禁用 thinking mode 以避免 token 浪費）"""
        model_lower = model.lower().split(":")[0]
        return any(model_lower.startswith(p) for p in _THINKING_MODEL_PREFIXES)

    @staticmethod
    def _strip_think_tags(content: str) -> str:
        """移除殘留的 <think>...</think> 區塊（安全網）"""
        if "<think>" not in content:
            return content
        return re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL).strip()

    async def _ollama_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        查詢本地 Ollama

        Args:
            response_format: 與 Groq/OpenAI 相容的格式設定。
                {"type": "json_object"} 會映射到 Ollama 的 format="json"。
        """
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": False,
        }

        # Qwen3/DeepSeek-R1 等推理模型：禁用 thinking mode
        if self._is_thinking_model(model):
            payload["think"] = False

        # response_format 映射：OpenAI 格式 → Ollama 格式
        if response_format and response_format.get("type") == "json_object":
            payload["format"] = "json"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/chat",
                json=payload,
                timeout=self.local_timeout,
            )
            response.raise_for_status()
            data = response.json()
            msg = data.get("message", {})
            content = msg.get("content", "")

            # 若 content 為空但有 thinking 欄位，記錄警告
            if not content and msg.get("thinking"):
                logger.warning(
                    "Ollama %s: content 為空但有 thinking 內容 (%d chars)，"
                    "可能 num_predict 不足或 think 參數未生效",
                    model, len(msg["thinking"]),
                )

            # 安全網：移除殘留 <think> 區塊
            content = self._strip_think_tags(content)

            logger.info("Ollama 回應成功 (model=%s, len=%d)", model, len(content))
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
        """Ollama 串流回應（含 thinking mode 過濾）"""
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": True,
        }

        # 推理模型：禁用 thinking mode
        if self._is_thinking_model(model):
            payload["think"] = False

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.ollama_base_url}/api/chat",
                json=payload,
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
        logger.info("Ollama 串流完成 (model=%s)", model)

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

    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> Optional[List[float]]:
        """
        使用 Ollama nomic-embed-text 生成 768 維向量嵌入

        透過 Ollama /api/embed 端點呼叫 nomic-embed-text 模型，
        將文字轉換為 768 維的向量表示，用於語意搜尋。

        Args:
            text: 要生成 embedding 的文字
            model: embedding 模型名稱（預設: nomic-embed-text）

        Returns:
            768 維的 embedding 向量（浮點數列表），失敗時回傳 None
        """
        embed_model = model or os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        # 截斷過長文字（nomic-embed-text 建議 8192 tokens）
        truncated_text = text[:8000] if text else ""
        if not truncated_text.strip():
            logger.warning("Embedding 生成跳過：輸入文字為空")
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/embed",
                    json={
                        "model": embed_model,
                        "input": truncated_text,
                    },
                    timeout=self.embed_timeout,
                )
                response.raise_for_status()
                data = response.json()

                # Ollama /api/embed 回傳格式: {"embeddings": [[...]]}
                embeddings = data.get("embeddings", [])
                if embeddings and len(embeddings) > 0:
                    embedding = embeddings[0]
                    logger.debug(
                        f"Embedding 生成成功 (model={embed_model}, "
                        f"dim={len(embedding)}, text_len={len(truncated_text)})"
                    )
                    return embedding

                logger.warning(f"Embedding 回應中無有效向量: {data}")
                return None
        except Exception as e:
            logger.warning(f"Embedding 生成失敗 (model={embed_model}): {e}")
            return None

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        model: Optional[str] = None,
    ) -> List[Optional[List[float]]]:
        """
        批次生成 embedding 向量（使用 Ollama /api/embed 陣列模式）

        Ollama /api/embed 的 "input" 欄位支援字串陣列，
        一次請求可為多段文字生成 embedding，大幅減少 HTTP 往返。

        Args:
            texts: 要生成 embedding 的文字列表
            model: embedding 模型名稱（預設: nomic-embed-text）

        Returns:
            與 texts 等長的列表，每項為 embedding 向量或 None（失敗時）
        """
        if not texts:
            return []

        embed_model = model or os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

        # 截斷每段文字並記錄有效索引
        truncated_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            t = text[:8000] if text else ""
            if t.strip():
                truncated_texts.append(t)
                valid_indices.append(i)

        if not truncated_texts:
            return [None] * len(texts)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/embed",
                    json={
                        "model": embed_model,
                        "input": truncated_texts,
                    },
                    timeout=self.embed_timeout,
                )
                response.raise_for_status()
                data = response.json()

            embeddings_raw = data.get("embeddings", [])

            # 建立結果陣列，預設為 None
            results: List[Optional[List[float]]] = [None] * len(texts)
            for idx, valid_i in enumerate(valid_indices):
                if idx < len(embeddings_raw) and embeddings_raw[idx]:
                    results[valid_i] = embeddings_raw[idx]

            success_count = sum(1 for r in results if r is not None)
            logger.debug(
                "批次 embedding 完成: model=%s, 請求=%s, 成功=%s",
                embed_model, len(truncated_texts), success_count,
            )
            return results

        except Exception as e:
            logger.warning(
                "批次 embedding 失敗 (model=%s, count=%s): %s",
                embed_model, len(truncated_texts), e,
            )
            return [None] * len(texts)

    async def ensure_models(self) -> Dict[str, Any]:
        """
        檢查 Ollama 已安裝模型，自動拉取缺少的必要模型。

        Returns:
            {"installed": [...], "pulled": [...], "failed": [...]}
        """
        result: Dict[str, Any] = {
            "installed": [],
            "pulled": [],
            "failed": [],
            "ollama_available": False,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.ollama_base_url}/api/tags", timeout=5
                )
                if resp.status_code != 200:
                    logger.warning("Ollama /api/tags 回應 HTTP %s", resp.status_code)
                    return result

                result["ollama_available"] = True
                installed_models = {
                    m["name"] for m in resp.json().get("models", [])
                }
                # 正規化：移除 ":latest" 後綴以便比較
                installed_normalized = set()
                for m in installed_models:
                    installed_normalized.add(m)
                    if ":" in m:
                        installed_normalized.add(m.split(":")[0])
                    else:
                        installed_normalized.add(f"{m}:latest")
                result["installed"] = sorted(installed_models)

                # 檢查缺少的模型
                for required in REQUIRED_MODELS:
                    req_norm = required.split(":")[0] if ":" in required else required
                    if (
                        required not in installed_normalized
                        and req_norm not in installed_normalized
                    ):
                        logger.info("模型 '%s' 未安裝，開始拉取...", required)
                        try:
                            pull_resp = await client.post(
                                f"{self.ollama_base_url}/api/pull",
                                json={"name": required, "stream": False},
                                timeout=600,  # 模型拉取可能需要較長時間
                            )
                            if pull_resp.status_code == 200:
                                result["pulled"].append(required)
                                logger.info("模型 '%s' 拉取成功", required)
                            else:
                                result["failed"].append(required)
                                logger.warning(
                                    "模型 '%s' 拉取失敗: HTTP %s",
                                    required, pull_resp.status_code,
                                )
                        except Exception as pull_err:
                            result["failed"].append(required)
                            logger.warning(
                                "模型 '%s' 拉取異常: %s", required, pull_err
                            )

        except Exception as e:
            logger.warning("Ollama 模型檢查失敗: %s", e)

        return result

    async def warmup_models(self) -> Dict[str, bool]:
        """
        對每個必要模型發送最小請求，預載入 GPU 記憶體以消除冷啟動延遲。

        Returns:
            {model_name: True/False} 表示每個模型的 warm-up 結果
        """
        results: Dict[str, bool] = {}

        for required_model in REQUIRED_MODELS:
            try:
                async with httpx.AsyncClient() as client:
                    if required_model == TASK_MODEL_MAP.get("embedding", "nomic-embed-text"):
                        # Embedding 模型：發送最小 embed 請求
                        resp = await client.post(
                            f"{self.ollama_base_url}/api/embed",
                            json={"model": required_model, "input": "warmup"},
                            timeout=60,
                        )
                    else:
                        # Chat 模型：發送最小 generate 請求
                        resp = await client.post(
                            f"{self.ollama_base_url}/api/generate",
                            json={
                                "model": required_model,
                                "prompt": "hi",
                                "stream": False,
                                "options": {"num_predict": 1},
                            },
                            timeout=120,  # 首次載入可能需要較長時間
                        )

                    if resp.status_code == 200:
                        results[required_model] = True
                        logger.info("模型 '%s' warm-up 完成", required_model)
                    else:
                        results[required_model] = False
                        logger.warning(
                            "模型 '%s' warm-up 失敗: HTTP %s",
                            required_model, resp.status_code,
                        )
            except Exception as e:
                results[required_model] = False
                logger.warning("模型 '%s' warm-up 異常: %s", required_model, e)

        return results

    async def check_health(self) -> Dict[str, Any]:
        """
        檢查 AI 服務健康狀態（增強版）

        除了基本可用性外，還驗證每個必要模型是否已安裝，
        以及 GPU 使用情況（若可用）。
        """
        status: Dict[str, Any] = {
            "groq": {"available": False, "message": ""},
            "ollama": {
                "available": False,
                "message": "",
                "models": [],
                "required_models_ready": False,
                "gpu_info": None,
            },
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

        # 檢查 Ollama（增強：模型驗證 + GPU 資訊）
        try:
            async with httpx.AsyncClient() as client:
                # 基本可用性
                response = await client.get(
                    f"{self.ollama_base_url}/api/tags",
                    timeout=5,
                )
                if response.status_code == 200:
                    status["ollama"]["available"] = True
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    status["ollama"]["models"] = model_names
                    status["ollama"]["message"] = (
                        f"Ollama 可用，{len(models)} 個模型"
                    )

                    # 驗證必要模型是否全部就緒
                    installed_set = set(model_names)
                    # 也加入不含 tag 的名稱
                    for m in list(installed_set):
                        installed_set.add(m.split(":")[0])
                    missing = []
                    for req in REQUIRED_MODELS:
                        req_base = req.split(":")[0]
                        if req not in installed_set and req_base not in installed_set:
                            missing.append(req)
                    status["ollama"]["required_models_ready"] = len(missing) == 0
                    if missing:
                        status["ollama"]["missing_models"] = missing
                else:
                    status["ollama"]["message"] = f"HTTP {response.status_code}"

                # GPU / 已載入模型資訊
                try:
                    ps_resp = await client.get(
                        f"{self.ollama_base_url}/api/ps", timeout=3
                    )
                    if ps_resp.status_code == 200:
                        ps_data = ps_resp.json()
                        running_models = ps_data.get("models", [])
                        status["ollama"]["gpu_info"] = {
                            "loaded_models": [
                                {
                                    "name": rm.get("name", ""),
                                    "size": rm.get("size", 0),
                                    "size_vram": rm.get("size_vram", 0),
                                }
                                for rm in running_models
                            ],
                        }
                except Exception:
                    pass  # /api/ps 不可用不影響整體健康檢查

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

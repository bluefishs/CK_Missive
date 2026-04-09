"""
Voice message transcription service.

Supports:
- LINE audio messages (m4a format)
- Whisper API via Groq (fast, free tier)
- Fallback: local Whisper via Ollama (if available)
- Final fallback: graceful error message

Version: 1.0.0
Created: 2026-03-16
"""

import hashlib
import io
import json
import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# LINE Data API for downloading binary content
LINE_DATA_API_BASE = "https://api-data.line.me/v2/bot"

# Groq Whisper endpoint
GROQ_AUDIO_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# Supported audio formats for Groq Whisper
SUPPORTED_FORMATS = {"m4a", "mp3", "wav", "webm", "mp4", "mpga", "mpeg", "ogg", "flac"}

# Groq Whisper file size limit (25 MB)
MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024


class VoiceTranscriber:
    """語音訊息轉文字服務

    優先順序:
    1. Groq Whisper API (whisper-large-v3-turbo) — 快速、免費額度
    2. Ollama whisper 模型 (如已部署)
    3. 錯誤回退 — 回傳友善提示
    """

    def __init__(self):
        from app.services.ai.core.ai_config import get_ai_config

        self._config = get_ai_config()
        self._groq_api_key = self._config.groq_api_key
        self._ollama_base_url = self._config.ollama_base_url
        self._line_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        self._cache_ttl = 86400  # 24 hours

    async def transcribe(
        self,
        audio_data: bytes,
        audio_format: str = "m4a",
        language: str = "zh",
    ) -> dict:
        """Transcribe audio bytes to text.

        Args:
            audio_data: Raw audio bytes
            audio_format: Audio format (m4a, mp3, wav, etc.)
            language: ISO 639-1 language code (default: zh for Chinese)

        Returns:
            {
                "text": str,
                "language": str,
                "duration_ms": int,
                "source": "groq" | "ollama" | "error"
            }
        """
        if not audio_data:
            return self._error_result("音訊資料為空")

        if len(audio_data) > MAX_AUDIO_SIZE_BYTES:
            return self._error_result("音訊檔案超過 25MB 限制")

        if audio_format not in SUPPORTED_FORMATS:
            return self._error_result(f"不支援的音訊格式: {audio_format}")

        start_time = time.time()

        # Strategy 1: Groq Whisper API
        if self._groq_api_key:
            result = await self._transcribe_groq(audio_data, audio_format, language)
            if result["source"] != "error":
                result["duration_ms"] = int((time.time() - start_time) * 1000)
                return result

        # Strategy 2: Ollama Whisper (if available)
        result = await self._transcribe_ollama(audio_data, audio_format, language)
        if result["source"] != "error":
            result["duration_ms"] = int((time.time() - start_time) * 1000)
            return result

        # Strategy 3: Graceful error
        return self._error_result("語音轉文字服務暫時無法使用，請改用文字訊息。")

    async def transcribe_line_audio(self, message_id: str) -> dict:
        """Download and transcribe a LINE audio message.

        Args:
            message_id: LINE message ID for the audio message

        Returns:
            Same as transcribe() output, with Redis caching.
        """
        if not message_id:
            return self._error_result("缺少 LINE 訊息 ID")

        # Check Redis cache first
        cache_key = f"voice:transcription:{message_id}"
        cached = await self._get_cached(cache_key)
        if cached is not None:
            logger.debug("Voice transcription cache hit: %s", message_id)
            return cached

        # Download audio from LINE Data API
        audio_data = await self._download_line_content(message_id)
        if audio_data is None:
            return self._error_result("無法下載 LINE 語音訊息")

        logger.info(
            "Downloaded LINE audio: message_id=%s, size=%d bytes",
            message_id,
            len(audio_data),
        )

        # LINE audio messages are typically m4a
        result = await self.transcribe(audio_data, audio_format="m4a", language="zh")

        # Cache successful results
        if result["source"] != "error":
            await self._set_cached(cache_key, result, self._cache_ttl)

        return result

    async def _download_line_content(self, message_id: str) -> Optional[bytes]:
        """Download binary content from LINE Data API.

        Uses: GET https://api-data.line.me/v2/bot/message/{messageId}/content
        """
        if not self._line_access_token:
            logger.warning("LINE_CHANNEL_ACCESS_TOKEN not set, cannot download content")
            return None

        url = f"{LINE_DATA_API_BASE}/message/{message_id}/content"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self._line_access_token}",
                    },
                )
                if resp.status_code != 200:
                    logger.warning(
                        "LINE content download failed: %d %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    return None
                return resp.content
        except Exception as e:
            logger.error("LINE content download error: %s", e)
            return None

    async def _transcribe_groq(
        self,
        audio_data: bytes,
        audio_format: str,
        language: str,
    ) -> dict:
        """Transcribe via Groq Whisper API (whisper-large-v3-turbo)."""
        try:
            filename = f"audio.{audio_format}"

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    GROQ_AUDIO_URL,
                    headers={
                        "Authorization": f"Bearer {self._groq_api_key}",
                    },
                    files={
                        "file": (filename, io.BytesIO(audio_data), f"audio/{audio_format}"),
                    },
                    data={
                        "model": "whisper-large-v3-turbo",
                        "language": language,
                        "response_format": "verbose_json",
                    },
                )

                if resp.status_code != 200:
                    logger.warning(
                        "Groq Whisper failed: %d %s",
                        resp.status_code,
                        resp.text[:300],
                    )
                    return self._error_result(f"Groq API 錯誤: {resp.status_code}")

                data = resp.json()
                text = data.get("text", "").strip()
                detected_language = data.get("language", language)
                duration = data.get("duration", 0)

                if not text:
                    return self._error_result("語音內容無法辨識")

                logger.info(
                    "Groq Whisper success: lang=%s, duration=%.1fs, text_len=%d",
                    detected_language,
                    duration,
                    len(text),
                )

                return {
                    "text": text,
                    "language": detected_language,
                    "duration_ms": int(duration * 1000),
                    "source": "groq",
                }

        except httpx.TimeoutException:
            logger.warning("Groq Whisper timeout")
            return self._error_result("Groq Whisper 超時")
        except Exception as e:
            logger.error("Groq Whisper error: %s", e)
            return self._error_result(str(e))

    async def _transcribe_ollama(
        self,
        audio_data: bytes,
        audio_format: str,
        language: str,
    ) -> dict:
        """Transcribe via Ollama Whisper model (local fallback).

        Note: Ollama whisper support is experimental. This attempts to use
        the /api/audio endpoint if available.
        """
        try:
            # Check if Ollama is reachable and has a whisper model
            async with httpx.AsyncClient(timeout=10) as client:
                # Probe Ollama for whisper model availability
                tags_resp = await client.get(f"{self._ollama_base_url}/api/tags")
                if tags_resp.status_code != 200:
                    return self._error_result("Ollama 不可用")

                models = tags_resp.json().get("models", [])
                whisper_model = None
                for m in models:
                    name = m.get("name", "").lower()
                    if "whisper" in name:
                        whisper_model = m["name"]
                        break

                if not whisper_model:
                    return self._error_result("Ollama 無 whisper 模型")

                # Attempt transcription via Ollama audio API
                # This is experimental — Ollama may not support this yet
                import base64

                audio_b64 = base64.b64encode(audio_data).decode("utf-8")

                resp = await client.post(
                    f"{self._ollama_base_url}/api/generate",
                    json={
                        "model": whisper_model,
                        "prompt": "Transcribe this audio to text.",
                        "images": [audio_b64],  # Ollama uses 'images' for binary data
                    },
                    timeout=120,
                )

                if resp.status_code != 200:
                    return self._error_result("Ollama whisper 轉錄失敗")

                # Parse streaming response (Ollama returns NDJSON)
                text_parts = []
                for line in resp.text.strip().split("\n"):
                    try:
                        chunk = json.loads(line)
                        text_parts.append(chunk.get("response", ""))
                    except json.JSONDecodeError:
                        continue

                text = "".join(text_parts).strip()
                if not text:
                    return self._error_result("Ollama 無法辨識語音內容")

                logger.info(
                    "Ollama Whisper success: model=%s, text_len=%d",
                    whisper_model,
                    len(text),
                )

                return {
                    "text": text,
                    "language": language,
                    "duration_ms": 0,
                    "source": "ollama",
                }

        except httpx.TimeoutException:
            logger.warning("Ollama Whisper timeout")
            return self._error_result("Ollama Whisper 超時")
        except Exception as e:
            logger.debug("Ollama Whisper unavailable: %s", e)
            return self._error_result(str(e))

    # ── Redis Cache Helpers ──

    async def _get_cached(self, key: str) -> Optional[dict]:
        """Get cached transcription from Redis."""
        try:
            from app.core.redis_client import get_redis

            r = await get_redis()
            if r is None:
                return None
            raw = await r.get(key)
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.debug("Voice cache get error: %s", e)
        return None

    async def _set_cached(self, key: str, value: dict, ttl: int) -> None:
        """Store transcription result in Redis."""
        try:
            from app.core.redis_client import get_redis

            r = await get_redis()
            if r is None:
                return
            await r.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
        except Exception as e:
            logger.debug("Voice cache set error: %s", e)

    @staticmethod
    def _error_result(message: str) -> dict:
        """Build a standard error result."""
        return {
            "text": message,
            "language": "",
            "duration_ms": 0,
            "source": "error",
        }


# ── Singleton ──

_transcriber: Optional[VoiceTranscriber] = None


def get_voice_transcriber() -> VoiceTranscriber:
    """取得 VoiceTranscriber 單例"""
    global _transcriber
    if _transcriber is None:
        _transcriber = VoiceTranscriber()
    return _transcriber

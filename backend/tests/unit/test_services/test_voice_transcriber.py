"""
Tests for VoiceTranscriber service.

Tests:
- transcribe() with Groq success/failure
- transcribe() with Ollama fallback
- transcribe() input validation (empty, too large, bad format)
- transcribe_line_audio() with cache hit/miss
- LINE content download
- Error result format
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai.voice_transcriber import (
    MAX_AUDIO_SIZE_BYTES,
    VoiceTranscriber,
    get_voice_transcriber,
)


@pytest.fixture
def transcriber():
    """Create a VoiceTranscriber with mocked config."""
    with patch("app.services.ai.ai_config.get_ai_config") as mock_config:
        config = MagicMock()
        config.groq_api_key = "test-groq-key"
        config.ollama_base_url = "http://localhost:11434"
        mock_config.return_value = config
        t = VoiceTranscriber()
    return t


@pytest.fixture
def sample_audio():
    """Minimal fake audio bytes."""
    return b"\x00\x01\x02\x03" * 100


# ── Input Validation ──


@pytest.mark.asyncio
async def test_transcribe_empty_audio(transcriber):
    result = await transcriber.transcribe(b"")
    assert result["source"] == "error"
    assert "為空" in result["text"]


@pytest.mark.asyncio
async def test_transcribe_too_large(transcriber):
    data = b"\x00" * (MAX_AUDIO_SIZE_BYTES + 1)
    result = await transcriber.transcribe(data)
    assert result["source"] == "error"
    assert "25MB" in result["text"]


@pytest.mark.asyncio
async def test_transcribe_unsupported_format(transcriber, sample_audio):
    result = await transcriber.transcribe(sample_audio, audio_format="xyz")
    assert result["source"] == "error"
    assert "不支援" in result["text"]


# ── Groq Whisper ──


@pytest.mark.asyncio
async def test_transcribe_groq_success(transcriber, sample_audio):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "text": "這是測試語音",
        "language": "zh",
        "duration": 3.5,
    }

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.post.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await transcriber.transcribe(sample_audio)

    assert result["source"] == "groq"
    assert result["text"] == "這是測試語音"
    assert result["language"] == "zh"
    # duration_ms is set by transcribe() wrapper using wall-clock time
    assert isinstance(result["duration_ms"], int)


@pytest.mark.asyncio
async def test_transcribe_groq_failure_falls_through(transcriber, sample_audio):
    """When Groq fails and Ollama is unavailable, return error."""
    mock_groq_resp = MagicMock()
    mock_groq_resp.status_code = 500
    mock_groq_resp.text = "Internal Server Error"

    # Ollama tags returns no whisper model
    mock_ollama_tags = MagicMock()
    mock_ollama_tags.status_code = 200
    mock_ollama_tags.json.return_value = {"models": [{"name": "gemma4"}]}

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.post.return_value = mock_groq_resp
        client_instance.get.return_value = mock_ollama_tags
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await transcriber.transcribe(sample_audio)

    assert result["source"] == "error"


@pytest.mark.asyncio
async def test_transcribe_groq_empty_text(transcriber, sample_audio):
    """Empty text from Groq should return error."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "text": "",
        "language": "zh",
        "duration": 1.0,
    }

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.post.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        # Also mock Ollama as unavailable
        mock_tags = MagicMock()
        mock_tags.status_code = 200
        mock_tags.json.return_value = {"models": []}
        client_instance.get.return_value = mock_tags

        result = await transcriber.transcribe(sample_audio)

    assert result["source"] == "error"


# ── Ollama Fallback ──


@pytest.mark.asyncio
async def test_transcribe_ollama_fallback(transcriber, sample_audio):
    """When Groq fails, Ollama whisper should be attempted."""
    # No Groq key
    transcriber._groq_api_key = ""

    mock_tags = MagicMock()
    mock_tags.status_code = 200
    mock_tags.json.return_value = {"models": [{"name": "whisper:base"}]}

    mock_generate = MagicMock()
    mock_generate.status_code = 200
    mock_generate.text = '{"response": "測試語音內容"}\n{"response": "。", "done": true}'

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_tags
        client_instance.post.return_value = mock_generate
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await transcriber.transcribe(sample_audio)

    assert result["source"] == "ollama"
    assert "測試語音內容" in result["text"]


# ── LINE Audio ──


@pytest.mark.asyncio
async def test_transcribe_line_audio_cache_hit(transcriber):
    """Cached result should be returned directly."""
    cached_data = {
        "text": "快取的文字",
        "language": "zh",
        "duration_ms": 2000,
        "source": "groq",
    }

    with patch.object(transcriber, "_get_cached", return_value=cached_data):
        result = await transcriber.transcribe_line_audio("msg123")

    assert result == cached_data


@pytest.mark.asyncio
async def test_transcribe_line_audio_download_fail(transcriber):
    """Failed LINE download should return error."""
    with (
        patch.object(transcriber, "_get_cached", return_value=None),
        patch.object(transcriber, "_download_line_content", return_value=None),
    ):
        result = await transcriber.transcribe_line_audio("msg456")

    assert result["source"] == "error"
    assert "下載" in result["text"]


@pytest.mark.asyncio
async def test_transcribe_line_audio_empty_message_id(transcriber):
    result = await transcriber.transcribe_line_audio("")
    assert result["source"] == "error"


@pytest.mark.asyncio
async def test_transcribe_line_audio_success(transcriber, sample_audio):
    """Full flow: cache miss → download → transcribe → cache set."""
    groq_result = {
        "text": "辨識結果",
        "language": "zh",
        "duration_ms": 1500,
        "source": "groq",
    }

    with (
        patch.object(transcriber, "_get_cached", return_value=None),
        patch.object(transcriber, "_download_line_content", return_value=sample_audio),
        patch.object(transcriber, "transcribe", return_value=groq_result),
        patch.object(transcriber, "_set_cached", new_callable=AsyncMock) as mock_cache_set,
    ):
        result = await transcriber.transcribe_line_audio("msg789")

    assert result["source"] == "groq"
    assert result["text"] == "辨識結果"
    mock_cache_set.assert_called_once()


# ── LINE Content Download ──


@pytest.mark.asyncio
async def test_download_line_content_no_token(transcriber):
    transcriber._line_access_token = ""
    result = await transcriber._download_line_content("msg123")
    assert result is None


@pytest.mark.asyncio
async def test_download_line_content_success(transcriber, sample_audio):
    # Set a valid token so the method doesn't bail out early
    transcriber._line_access_token = "test-token"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = sample_audio

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_resp
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await transcriber._download_line_content("msg123")

    assert result == sample_audio


# ── Error Result Helper ──


def test_error_result():
    result = VoiceTranscriber._error_result("test error")
    assert result["source"] == "error"
    assert result["text"] == "test error"
    assert result["language"] == ""
    assert result["duration_ms"] == 0


# ── Singleton ──


def test_get_voice_transcriber_singleton():
    """get_voice_transcriber should return same instance."""
    import app.services.ai.voice_transcriber as mod

    mod._transcriber = None  # Reset

    with patch("app.services.ai.ai_config.get_ai_config") as mock_config:
        config = MagicMock()
        config.groq_api_key = ""
        config.ollama_base_url = "http://localhost:11434"
        mock_config.return_value = config

        t1 = get_voice_transcriber()
        t2 = get_voice_transcriber()

    assert t1 is t2

    mod._transcriber = None  # Cleanup

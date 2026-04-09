"""
BaseAIService 單元測試

測試 AI 服務基類的核心功能：快取鍵生成、JSON 解析、回應驗證。
不需要實際 AI 連線 — 所有外部依賴都被 mock。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel

from app.services.ai.core.base_ai_service import BaseAIService


class MockSchema(BaseModel):
    summary: str
    confidence: float = 0.0


@pytest.fixture
def service():
    """建立帶 mock 依賴的 BaseAIService"""
    with patch("app.services.ai.core.base_ai_service.get_ai_connector") as mock_conn, \
         patch("app.services.ai.core.base_ai_service.get_ai_config") as mock_cfg:
        cfg = MagicMock()
        cfg.enabled = True
        cfg.cache_enabled = False
        cfg.rate_limit_requests = 100
        cfg.rate_limit_window = 60
        cfg.default_temperature = 0.7
        mock_cfg.return_value = cfg
        mock_conn.return_value = AsyncMock()

        svc = BaseAIService()
        # Mock rate limiter to always allow
        svc._rate_limiter = AsyncMock()
        svc._rate_limiter.acquire = AsyncMock(return_value=(True, 0))
        svc._rate_limiter.can_proceed = MagicMock(return_value=True)
        svc._rate_limiter.requests = []
        svc._rate_limiter.max_requests = 100
        svc._rate_limiter.window_seconds = 60
        # Mock stats
        svc._stats_manager = AsyncMock()
        svc._stats_manager.record = AsyncMock()
        svc._stats_manager.get_stats = AsyncMock(return_value={})
        # Mock cache
        svc._redis_cache = AsyncMock()
        svc._redis_cache.get = AsyncMock(return_value=None)
        svc._redis_cache.set = AsyncMock()
        svc._redis_cache.clear = AsyncMock(return_value=0)
        svc._cache = MagicMock()
        svc._cache.get = MagicMock(return_value=None)
        svc._cache._cache = {}

        yield svc


class TestCacheKeyGeneration:
    def test_generate_cache_key(self, service):
        key = service._generate_cache_key("summary", "doc123", "hello")
        assert key.startswith("summary:")
        assert len(key) > len("summary:")

    def test_same_input_same_key(self, service):
        k1 = service._generate_cache_key("feat", "a", "b")
        k2 = service._generate_cache_key("feat", "a", "b")
        assert k1 == k2

    def test_different_input_different_key(self, service):
        k1 = service._generate_cache_key("feat", "a")
        k2 = service._generate_cache_key("feat", "b")
        assert k1 != k2


class TestParseJsonResponse:
    def test_parse_plain_json(self, service):
        result = service._parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_code_block(self, service):
        text = '```json\n{"summary": "test"}\n```'
        result = service._parse_json_response(text)
        assert result == {"summary": "test"}

    def test_parse_embedded_json(self, service):
        text = 'Here is the result: {"count": 42} end.'
        result = service._parse_json_response(text)
        assert result == {"count": 42}

    def test_parse_invalid_json(self, service):
        result = service._parse_json_response("not json at all")
        assert result == {}

    def test_parse_nested_json(self, service):
        text = '{"outer": {"inner": [1, 2, 3]}}'
        result = service._parse_json_response(text)
        assert result["outer"]["inner"] == [1, 2, 3]


class TestIsEnabled:
    def test_enabled(self, service):
        assert service.is_enabled() is True

    def test_disabled(self, service):
        service.config.enabled = False
        assert service.is_enabled() is False


class TestCallAIWithValidation:
    @pytest.mark.asyncio
    async def test_no_schema_returns_raw(self, service):
        service.connector.chat_completion = AsyncMock(return_value="raw text")
        service.config.cache_enabled = False
        result = await service._call_ai_with_validation(
            cache_key="test:1", ttl=60,
            system_prompt="sys", user_content="hello",
        )
        assert result == "raw text"

    @pytest.mark.asyncio
    async def test_with_schema_valid(self, service):
        service.connector.chat_completion = AsyncMock(
            return_value='{"summary": "good", "confidence": 0.9}'
        )
        service.config.cache_enabled = False
        result = await service._call_ai_with_validation(
            cache_key="test:2", ttl=60,
            system_prompt="sys", user_content="hello",
            response_schema=MockSchema,
        )
        assert result["summary"] == "good"
        assert result["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_with_schema_invalid_returns_raw(self, service):
        service.connector.chat_completion = AsyncMock(return_value="not json")
        service.config.cache_enabled = False
        result = await service._call_ai_with_validation(
            cache_key="test:3", ttl=60,
            system_prompt="sys", user_content="hello",
            response_schema=MockSchema,
        )
        assert result == "not json"


class TestCallAIDisabled:
    @pytest.mark.asyncio
    async def test_raises_when_disabled(self, service):
        service.config.enabled = False
        with pytest.raises(RuntimeError, match="AI 服務未啟用"):
            await service._call_ai("sys", "user")

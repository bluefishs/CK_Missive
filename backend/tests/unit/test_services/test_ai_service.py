# -*- coding: utf-8 -*-
"""
AI 服務單元測試

測試範圍:
- AIConnector: Groq/Ollama 連接器
- DocumentAIService: 公文 AI 服務
- 摘要生成、分類建議、關鍵字提取

v1.0.0 - 2026-02-04
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# 測試目標
from app.core.ai_connector import AIConnector, get_ai_connector
from app.services.ai.ai_config import AIConfig, get_ai_config
from app.services.ai.document_ai_service import DocumentAIService


# ============================================================
# AIConfig 測試
# ============================================================

class TestAIConfig:
    """AI 配置測試"""

    def test_default_config(self):
        """測試預設配置"""
        config = AIConfig()
        assert config.enabled is True
        assert config.groq_model == "llama-3.3-70b-versatile"
        assert config.ollama_model == "llama3.1:8b"
        assert config.cloud_timeout == 30
        assert config.local_timeout == 60

    def test_from_env_with_defaults(self):
        """測試從環境變數建立配置（使用預設值）"""
        with patch.dict("os.environ", {}, clear=True):
            config = AIConfig.from_env()
            assert config.enabled is True
            assert config.groq_api_key == ""

    def test_from_env_with_values(self):
        """測試從環境變數建立配置（使用指定值）"""
        env_vars = {
            "AI_ENABLED": "false",
            "GROQ_API_KEY": "test_key",
            "AI_DEFAULT_MODEL": "test_model",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            config = AIConfig.from_env()
            assert config.enabled is False
            assert config.groq_api_key == "test_key"
            assert config.groq_model == "test_model"


# ============================================================
# AIConnector 測試
# ============================================================

class TestAIConnector:
    """AI 連接器測試"""

    @pytest.fixture
    def connector(self):
        """建立測試用連接器"""
        return AIConnector(
            groq_api_key="test_groq_key",
            ollama_base_url="http://localhost:11434",
        )

    @pytest.fixture
    def connector_no_groq(self):
        """建立無 Groq Key 的連接器"""
        return AIConnector(
            groq_api_key="",
            ollama_base_url="http://localhost:11434",
        )

    @pytest.mark.asyncio
    async def test_groq_completion_success(self, connector):
        """測試 Groq API 成功回應"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "測試摘要"}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await connector._groq_completion(
                messages=[{"role": "user", "content": "測試"}],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=100,
            )

            assert result == "測試摘要"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_ollama_completion_success(self, connector):
        """測試 Ollama 成功回應"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "本地摘要"}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await connector._ollama_completion(
                messages=[{"role": "user", "content": "測試"}],
                model="llama3.1:8b",
                temperature=0.7,
                max_tokens=100,
            )

            assert result == "本地摘要"

    @pytest.mark.asyncio
    async def test_chat_completion_fallback_to_ollama(self, connector):
        """測試 Groq 失敗時切換到 Ollama"""
        # Groq 失敗
        groq_error = Exception("Groq API error")

        # Ollama 成功
        ollama_response = MagicMock()
        ollama_response.status_code = 200
        ollama_response.json.return_value = {"message": {"content": "備援回應"}}
        ollama_response.raise_for_status = MagicMock()

        with patch.object(connector, "_groq_completion", side_effect=groq_error):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = ollama_response

                result = await connector.chat_completion(
                    messages=[{"role": "user", "content": "測試"}]
                )

                assert result == "備援回應"

    @pytest.mark.asyncio
    async def test_chat_completion_fallback_response(self, connector_no_groq):
        """測試所有服務失敗時的備援回應"""
        ollama_error = Exception("Ollama error")

        with patch("httpx.AsyncClient.post", side_effect=ollama_error):
            result = await connector_no_groq.chat_completion(
                messages=[{"role": "user", "content": "公文摘要"}]
            )

            # 應返回備援回應
            assert "AI 服務暫時不可用" in result or "公文" in result

    def test_generate_fallback_response_document(self, connector):
        """測試公文相關備援回應"""
        result = connector._generate_fallback_response("這是一份公文")
        assert "公文" in result

    def test_generate_fallback_response_generic(self, connector):
        """測試通用備援回應"""
        result = connector._generate_fallback_response("隨機問題")
        assert "AI 服務暫時不可用" in result

    @pytest.mark.asyncio
    async def test_check_health(self, connector):
        """測試健康檢查"""
        # Mock Groq 健康
        groq_response = MagicMock()
        groq_response.status_code = 200

        # Mock Ollama 健康
        ollama_response = MagicMock()
        ollama_response.status_code = 200
        ollama_response.json.return_value = {"models": [{"name": "llama3.1:8b"}]}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [groq_response, ollama_response]

            result = await connector.check_health()

            assert "groq" in result
            assert "ollama" in result


# ============================================================
# DocumentAIService 測試
# ============================================================

class TestDocumentAIService:
    """公文 AI 服務測試"""

    @pytest.fixture
    def mock_connector(self):
        """建立 mock AI 連接器"""
        connector = MagicMock(spec=AIConnector)
        connector.chat_completion = AsyncMock()
        connector.check_health = AsyncMock(return_value={
            "groq": {"available": True, "message": "OK"},
            "ollama": {"available": False, "message": "Not running"},
        })
        return connector

    @pytest.fixture
    def mock_config(self):
        """建立 mock 配置"""
        return AIConfig(
            enabled=True,
            groq_api_key="test_key",
            summary_max_tokens=256,
            classify_max_tokens=128,
            keywords_max_tokens=64,
        )

    @pytest.fixture
    def service(self, mock_connector, mock_config):
        """建立測試服務"""
        return DocumentAIService(connector=mock_connector, config=mock_config)

    @pytest.fixture
    def disabled_service(self, mock_connector):
        """建立停用的服務"""
        config = AIConfig(enabled=False)
        return DocumentAIService(connector=mock_connector, config=config)

    @pytest.mark.asyncio
    async def test_generate_summary_success(self, service, mock_connector):
        """測試摘要生成成功"""
        mock_connector.chat_completion.return_value = "這是AI生成的公文摘要，簡潔明瞭。"

        result = await service.generate_summary(
            subject="關於XX案件之函復",
            content="茲因...",
            sender="桃園市政府",
        )

        assert result["summary"] == "這是AI生成的公文摘要，簡潔明瞭。"
        assert result["confidence"] == 0.85
        assert result["source"] == "ai"

    @pytest.mark.asyncio
    async def test_generate_summary_disabled(self, disabled_service):
        """測試 AI 停用時的摘要生成"""
        result = await disabled_service.generate_summary(
            subject="測試主旨",
        )

        assert result["summary"] == "測試主旨"
        assert result["confidence"] == 0.0
        assert result["source"] == "disabled"

    @pytest.mark.asyncio
    async def test_suggest_classification_success(self, service, mock_connector):
        """測試分類建議成功"""
        mock_connector.chat_completion.return_value = json.dumps({
            "doc_type": "函",
            "category": "收文",
            "doc_type_confidence": 0.9,
            "category_confidence": 0.95,
            "reasoning": "根據主旨判斷為收文函覆",
        })

        result = await service.suggest_classification(
            subject="關於XX案件之函復",
            sender="桃園市政府",
        )

        assert result["doc_type"] == "函"
        assert result["category"] == "收文"
        assert result["doc_type_confidence"] == 0.9
        assert result["source"] == "ai"

    @pytest.mark.asyncio
    async def test_suggest_classification_invalid_response(self, service, mock_connector):
        """測試分類建議處理無效回應"""
        mock_connector.chat_completion.return_value = "無效的 JSON 回應"

        result = await service.suggest_classification(
            subject="測試主旨",
        )

        # 應使用預設值
        assert result["doc_type"] == "函"
        assert result["category"] == "收文"
        assert result["source"] == "ai"

    @pytest.mark.asyncio
    async def test_extract_keywords_success(self, service, mock_connector):
        """測試關鍵字提取成功"""
        mock_connector.chat_completion.return_value = json.dumps({
            "keywords": ["桃園市政府", "工程", "驗收"]
        })

        result = await service.extract_keywords(
            subject="桃園市XX工程驗收案",
            max_keywords=5,
        )

        assert result["keywords"] == ["桃園市政府", "工程", "驗收"]
        assert result["confidence"] == 0.85
        assert result["source"] == "ai"

    @pytest.mark.asyncio
    async def test_extract_keywords_empty(self, service, mock_connector):
        """測試關鍵字提取空結果"""
        mock_connector.chat_completion.return_value = json.dumps({
            "keywords": []
        })

        result = await service.extract_keywords(subject="測試")

        assert result["keywords"] == []
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_match_agency_enhanced_success(self, service, mock_connector):
        """測試 AI 機關匹配成功"""
        mock_connector.chat_completion.return_value = json.dumps({
            "best_match_id": 1,
            "confidence": 0.95,
            "reasoning": "名稱完全匹配",
        })

        candidates = [
            {"id": 1, "name": "桃園市政府", "short_name": "桃市府"},
            {"id": 2, "name": "新北市政府", "short_name": "新北府"},
        ]

        result = await service.match_agency_enhanced(
            agency_name="桃園市政府",
            candidates=candidates,
        )

        assert result["best_match"]["id"] == 1
        assert result["best_match"]["score"] == 0.95
        assert result["is_new"] is False

    @pytest.mark.asyncio
    async def test_match_agency_enhanced_no_match(self, service, mock_connector):
        """測試 AI 機關匹配無結果"""
        mock_connector.chat_completion.return_value = json.dumps({
            "best_match_id": None,
            "confidence": 0,
            "reasoning": "找不到匹配的機關",
        })

        result = await service.match_agency_enhanced(
            agency_name="不存在的機關",
            candidates=[],
        )

        assert result["best_match"] is None
        assert result["is_new"] is True

    def test_parse_json_response_valid(self, service):
        """測試 JSON 解析 - 有效 JSON"""
        result = service._parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_response_code_block(self, service):
        """測試 JSON 解析 - 代碼塊格式"""
        result = service._parse_json_response('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_parse_json_response_with_text(self, service):
        """測試 JSON 解析 - 包含額外文字"""
        result = service._parse_json_response('這是回應：{"key": "value"} 結束')
        assert result == {"key": "value"}

    def test_parse_json_response_invalid(self, service):
        """測試 JSON 解析 - 無效格式"""
        result = service._parse_json_response("這不是 JSON")
        assert result == {}

    @pytest.mark.asyncio
    async def test_check_health(self, service, mock_connector):
        """測試健康檢查"""
        result = await service.check_health()

        assert result["groq"]["available"] is True
        assert result["ollama"]["available"] is False


# ============================================================
# 速率限制與快取測試 (v1.1.0)
# ============================================================

class TestRateLimiterAndCache:
    """速率限制與快取測試"""

    def test_rate_limiter_allows_requests(self):
        """測試速率限制器允許請求"""
        from app.services.ai.base_ai_service import RateLimiter

        limiter = RateLimiter(max_requests=5, window_seconds=60)

        # 應該允許前 5 個請求
        for _ in range(5):
            assert limiter.can_proceed() is True
            limiter.record_request()

        # 第 6 個請求應該被拒絕
        assert limiter.can_proceed() is False

    def test_rate_limiter_wait_time(self):
        """測試速率限制器等待時間計算"""
        from app.services.ai.base_ai_service import RateLimiter

        limiter = RateLimiter(max_requests=1, window_seconds=60)
        limiter.record_request()

        # 應該需要等待
        wait_time = limiter.get_wait_time()
        assert wait_time > 0
        assert wait_time <= 60

    def test_simple_cache_set_get(self):
        """測試簡單快取的設定與取得"""
        from app.services.ai.base_ai_service import SimpleCache

        cache = SimpleCache()
        cache.set("test_key", "test_value", ttl=3600)

        result = cache.get("test_key")
        assert result == "test_value"

    def test_simple_cache_miss(self):
        """測試快取未命中"""
        from app.services.ai.base_ai_service import SimpleCache

        cache = SimpleCache()
        result = cache.get("nonexistent_key")
        assert result is None

    def test_simple_cache_clear(self):
        """測試快取清除"""
        from app.services.ai.base_ai_service import SimpleCache

        cache = SimpleCache()
        cache.set("key1", "value1", ttl=3600)
        cache.set("key2", "value2", ttl=3600)

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_generate_cache_key(self):
        """測試快取鍵生成"""
        from app.services.ai.base_ai_service import BaseAIService
        from app.services.ai.ai_config import AIConfig

        config = AIConfig(enabled=True)
        service = DocumentAIService(config=config)

        key1 = service._generate_cache_key("summary", "主旨1", "內容1")
        key2 = service._generate_cache_key("summary", "主旨2", "內容2")
        key3 = service._generate_cache_key("summary", "主旨1", "內容1")

        # 相同輸入應產生相同鍵
        assert key1 == key3
        # 不同輸入應產生不同鍵
        assert key1 != key2
        # 鍵應包含前綴
        assert key1.startswith("summary:")

    @pytest.mark.asyncio
    async def test_service_with_rate_limit(self):
        """測試服務的速率限制整合"""
        from app.services.ai.ai_config import AIConfig
        from app.services.ai.base_ai_service import RateLimiter

        config = AIConfig(
            enabled=True,
            groq_api_key="test_key",
            rate_limit_requests=2,
            rate_limit_window=60,
            cache_enabled=False,  # 停用快取以測試速率限制
        )

        mock_connector = MagicMock(spec=AIConnector)
        mock_connector.chat_completion = AsyncMock(return_value="測試摘要")

        service = DocumentAIService(connector=mock_connector, config=config)

        # 建立獨立的速率限制器以避免全域狀態干擾
        service._rate_limiter = RateLimiter(max_requests=2, window_seconds=60)

        # 前兩個請求應該成功
        result1 = await service.generate_summary(subject="主旨1")
        result2 = await service.generate_summary(subject="主旨2")

        assert result1["source"] == "ai"
        assert result2["source"] == "ai"

        # 第三個請求應該被速率限制
        result3 = await service.generate_summary(subject="主旨3")

        assert result3["source"] == "rate_limited"
        assert "error" in result3

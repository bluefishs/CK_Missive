"""
EmbeddingManager 單元測試

測試範圍：
- 延遲初始化 (_ensure_initialized)
- LRU 快取命中/未命中
- 過期清除
- 批次快取 (get_embeddings_batch)
- 統計

共 12 test cases
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.core.embedding_manager import EmbeddingManager


@pytest.fixture(autouse=True)
def reset_singleton():
    """每個測試前重設 Singleton 狀態"""
    EmbeddingManager._instance = None
    EmbeddingManager._cache.clear()
    EmbeddingManager._max_cache_size = 0
    EmbeddingManager._cache_ttl = 0.0
    EmbeddingManager._write_lock = None
    EmbeddingManager._embed_semaphore = None
    EmbeddingManager._hits = 0
    EmbeddingManager._misses = 0
    yield
    # 清理
    EmbeddingManager._instance = None
    EmbeddingManager._cache.clear()
    EmbeddingManager._max_cache_size = 0
    EmbeddingManager._cache_ttl = 0.0
    EmbeddingManager._write_lock = None
    EmbeddingManager._embed_semaphore = None


@pytest.fixture
def mock_connector():
    connector = MagicMock()
    connector.generate_embedding = AsyncMock(return_value=[0.1] * 768)
    return connector


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.embedding_cache_max_size = 100
    config.embedding_cache_ttl = 60
    return config


class TestLazyInit:
    """延遲初始化測試"""

    def test_initial_state_uninitialized(self):
        assert EmbeddingManager._write_lock is None
        assert EmbeddingManager._embed_semaphore is None
        assert EmbeddingManager._max_cache_size == 0

    def test_ensure_initialized_creates_lock(self, mock_config):
        with patch("app.services.ai.core.embedding_manager.get_ai_config", return_value=mock_config):
            EmbeddingManager._ensure_initialized()

        assert EmbeddingManager._write_lock is not None
        assert isinstance(EmbeddingManager._write_lock, asyncio.Lock)
        assert EmbeddingManager._embed_semaphore is not None
        assert EmbeddingManager._max_cache_size == 100
        assert EmbeddingManager._cache_ttl == 60.0

    def test_ensure_initialized_idempotent(self, mock_config):
        with patch("app.services.ai.core.embedding_manager.get_ai_config", return_value=mock_config):
            EmbeddingManager._ensure_initialized()
            lock1 = EmbeddingManager._write_lock
            EmbeddingManager._ensure_initialized()
            lock2 = EmbeddingManager._write_lock

        assert lock1 is lock2  # 同一個 Lock 實例


class TestCacheHitMiss:
    """快取命中/未命中測試"""

    @pytest.mark.asyncio
    async def test_cache_miss_then_hit(self, mock_connector, mock_config):
        with patch("app.services.ai.core.embedding_manager.get_ai_config", return_value=mock_config):
            # 第一次：cache miss
            result1 = await EmbeddingManager.get_embedding("hello", mock_connector)
            assert result1 is not None
            assert len(result1) == 768
            assert EmbeddingManager._misses == 1
            assert EmbeddingManager._hits == 0

            # 第二次：cache hit
            result2 = await EmbeddingManager.get_embedding("hello", mock_connector)
            assert result2 is not None
            assert EmbeddingManager._hits == 1
            # connector 只被呼叫一次
            assert mock_connector.generate_embedding.call_count == 1

    @pytest.mark.asyncio
    async def test_empty_text_returns_none(self, mock_connector, mock_config):
        with patch("app.services.ai.core.embedding_manager.get_ai_config", return_value=mock_config):
            result = await EmbeddingManager.get_embedding("", mock_connector)
            assert result is None
            mock_connector.generate_embedding.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_eviction_when_full(self, mock_connector):
        """快取滿時驅逐最舊的項目"""
        small_config = MagicMock()
        small_config.embedding_cache_max_size = 2
        small_config.embedding_cache_ttl = 3600

        with patch("app.services.ai.core.embedding_manager.get_ai_config", return_value=small_config):
            await EmbeddingManager.get_embedding("text1", mock_connector)
            await EmbeddingManager.get_embedding("text2", mock_connector)
            await EmbeddingManager.get_embedding("text3", mock_connector)

            # 快取大小不超過 max
            assert len(EmbeddingManager._cache) <= 2


class TestBatchEmbedding:
    """批次 embedding 測試"""

    @pytest.mark.asyncio
    async def test_batch_empty_list(self, mock_connector, mock_config):
        with patch("app.services.ai.core.embedding_manager.get_ai_config", return_value=mock_config):
            results = await EmbeddingManager.get_embeddings_batch([], mock_connector)
            assert results == []

    @pytest.mark.asyncio
    async def test_batch_with_cache_hits(self, mock_connector, mock_config):
        with patch("app.services.ai.core.embedding_manager.get_ai_config", return_value=mock_config):
            # 預填快取
            await EmbeddingManager.get_embedding("cached", mock_connector)
            assert mock_connector.generate_embedding.call_count == 1

            # 批次查詢：一個命中、一個未命中
            results = await EmbeddingManager.get_embeddings_batch(
                ["cached", "new_text"], mock_connector
            )
            assert len(results) == 2
            assert results[0] is not None
            assert results[1] is not None
            # "new_text" 需要再生成一次
            assert mock_connector.generate_embedding.call_count == 2


class TestStats:
    """統計測試"""

    @pytest.mark.asyncio
    async def test_stats_accuracy(self, mock_connector, mock_config):
        with patch("app.services.ai.core.embedding_manager.get_ai_config", return_value=mock_config):
            await EmbeddingManager.get_embedding("a", mock_connector)
            await EmbeddingManager.get_embedding("a", mock_connector)
            await EmbeddingManager.get_embedding("b", mock_connector)

            stats = EmbeddingManager.get_stats()
            assert stats["cache_size"] == 2
            assert stats["hits"] == 1
            assert stats["misses"] == 2
            assert stats["hit_rate_percent"] == pytest.approx(33.3, abs=0.1)

    def test_invalidate_clears_all(self, mock_config):
        with patch("app.services.ai.core.embedding_manager.get_ai_config", return_value=mock_config):
            EmbeddingManager._ensure_initialized()
            EmbeddingManager._cache["test"] = ([0.1], time.monotonic())
            EmbeddingManager._hits = 5
            EmbeddingManager._misses = 10

            EmbeddingManager.invalidate()

            assert len(EmbeddingManager._cache) == 0
            assert EmbeddingManager._hits == 0
            assert EmbeddingManager._misses == 0


class TestTTLExpiration:
    """TTL 過期測試"""

    @pytest.mark.asyncio
    async def test_expired_entry_is_evicted(self, mock_connector):
        """過期的快取條目被驅逐，需重新生成"""
        short_ttl_config = MagicMock()
        short_ttl_config.embedding_cache_max_size = 100
        short_ttl_config.embedding_cache_ttl = 0.01  # 10ms TTL

        with patch("app.services.ai.core.embedding_manager.get_ai_config", return_value=short_ttl_config):
            # 第一次呼叫: cache miss
            result1 = await EmbeddingManager.get_embedding("expire_test", mock_connector)
            assert result1 is not None
            assert mock_connector.generate_embedding.call_count == 1

            # 等待 TTL 過期
            await asyncio.sleep(0.05)

            # 第二次呼叫: 應為 cache miss (已過期)
            result2 = await EmbeddingManager.get_embedding("expire_test", mock_connector)
            assert result2 is not None
            assert mock_connector.generate_embedding.call_count == 2


class TestConnectorFailure:
    """Connector 失敗處理測試"""

    @pytest.mark.asyncio
    async def test_connector_error_returns_none(self, mock_config):
        """Connector 拋出異常時回傳 None"""
        failing_connector = MagicMock()
        failing_connector.generate_embedding = AsyncMock(side_effect=Exception("Ollama down"))

        with patch("app.services.ai.core.embedding_manager.get_ai_config", return_value=mock_config):
            result = await EmbeddingManager.get_embedding("test_fail", failing_connector)

            assert result is None

    @pytest.mark.asyncio
    async def test_batch_partial_failure(self, mock_config):
        """批次中部分失敗不影響成功的項目"""
        call_count = 0

        async def selective_fail(text):
            nonlocal call_count
            call_count += 1
            if "fail" in text:
                raise Exception("Selective failure")
            return [0.1] * 768

        connector = MagicMock()
        connector.generate_embedding = selective_fail

        with patch("app.services.ai.core.embedding_manager.get_ai_config", return_value=mock_config):
            results = await EmbeddingManager.get_embeddings_batch(
                ["good_text", "fail_text", "another_good"], connector
            )

            assert len(results) == 3
            assert results[0] is not None  # good_text succeeded
            assert results[1] is None      # fail_text failed
            assert results[2] is not None  # another_good succeeded


class TestCoverageStats:
    """覆蓋率統計測試"""

    @pytest.mark.asyncio
    async def test_get_coverage_stats(self):
        """測試 get_coverage_stats 回傳正確結構"""
        mock_db = AsyncMock()

        # Mock total count
        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 100

        # Mock with_embedding count
        mock_with_result = MagicMock()
        mock_with_result.scalar.return_value = 75

        mock_db.execute.side_effect = [mock_total_result, mock_with_result]

        result = await EmbeddingManager.get_coverage_stats(mock_db)

        assert result["total"] == 100
        assert result["with_embedding"] == 75
        assert result["without_embedding"] == 25
        assert result["coverage"] == 75.0

    @pytest.mark.asyncio
    async def test_get_coverage_stats_empty_db(self):
        """測試空資料庫的覆蓋率統計"""
        mock_db = AsyncMock()

        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 0

        mock_with_result = MagicMock()
        mock_with_result.scalar.return_value = 0

        mock_db.execute.side_effect = [mock_total_result, mock_with_result]

        result = await EmbeddingManager.get_coverage_stats(mock_db)

        assert result["total"] == 0
        assert result["coverage"] == 0.0


class TestCacheKeyConsistency:
    """快取 key 一致性測試"""

    def test_same_text_same_key(self):
        """相同文字產生相同 key"""
        key1 = EmbeddingManager._cache_key("測試文字")
        key2 = EmbeddingManager._cache_key("測試文字")
        assert key1 == key2

    def test_different_text_different_key(self):
        """不同文字產生不同 key"""
        key1 = EmbeddingManager._cache_key("文字A")
        key2 = EmbeddingManager._cache_key("文字B")
        assert key1 != key2

    def test_key_length_is_16(self):
        """key 長度為 16（SHA256 前綴）"""
        key = EmbeddingManager._cache_key("any text")
        assert len(key) == 16


class TestIsAvailable:
    """is_available 測試"""

    def test_is_available_returns_bool(self):
        """is_available 回傳布林值"""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.PGVECTOR_ENABLED = True
            assert EmbeddingManager.is_available() is True

            mock_settings.PGVECTOR_ENABLED = False
            assert EmbeddingManager.is_available() is False

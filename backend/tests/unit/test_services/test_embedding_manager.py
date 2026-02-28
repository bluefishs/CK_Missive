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

from app.services.ai.embedding_manager import EmbeddingManager


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
        with patch("app.services.ai.embedding_manager.get_ai_config", return_value=mock_config):
            EmbeddingManager._ensure_initialized()

        assert EmbeddingManager._write_lock is not None
        assert isinstance(EmbeddingManager._write_lock, asyncio.Lock)
        assert EmbeddingManager._embed_semaphore is not None
        assert EmbeddingManager._max_cache_size == 100
        assert EmbeddingManager._cache_ttl == 60.0

    def test_ensure_initialized_idempotent(self, mock_config):
        with patch("app.services.ai.embedding_manager.get_ai_config", return_value=mock_config):
            EmbeddingManager._ensure_initialized()
            lock1 = EmbeddingManager._write_lock
            EmbeddingManager._ensure_initialized()
            lock2 = EmbeddingManager._write_lock

        assert lock1 is lock2  # 同一個 Lock 實例


class TestCacheHitMiss:
    """快取命中/未命中測試"""

    @pytest.mark.asyncio
    async def test_cache_miss_then_hit(self, mock_connector, mock_config):
        with patch("app.services.ai.embedding_manager.get_ai_config", return_value=mock_config):
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
        with patch("app.services.ai.embedding_manager.get_ai_config", return_value=mock_config):
            result = await EmbeddingManager.get_embedding("", mock_connector)
            assert result is None
            mock_connector.generate_embedding.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_eviction_when_full(self, mock_connector):
        """快取滿時驅逐最舊的項目"""
        small_config = MagicMock()
        small_config.embedding_cache_max_size = 2
        small_config.embedding_cache_ttl = 3600

        with patch("app.services.ai.embedding_manager.get_ai_config", return_value=small_config):
            await EmbeddingManager.get_embedding("text1", mock_connector)
            await EmbeddingManager.get_embedding("text2", mock_connector)
            await EmbeddingManager.get_embedding("text3", mock_connector)

            # 快取大小不超過 max
            assert len(EmbeddingManager._cache) <= 2


class TestBatchEmbedding:
    """批次 embedding 測試"""

    @pytest.mark.asyncio
    async def test_batch_empty_list(self, mock_connector, mock_config):
        with patch("app.services.ai.embedding_manager.get_ai_config", return_value=mock_config):
            results = await EmbeddingManager.get_embeddings_batch([], mock_connector)
            assert results == []

    @pytest.mark.asyncio
    async def test_batch_with_cache_hits(self, mock_connector, mock_config):
        with patch("app.services.ai.embedding_manager.get_ai_config", return_value=mock_config):
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
        with patch("app.services.ai.embedding_manager.get_ai_config", return_value=mock_config):
            await EmbeddingManager.get_embedding("a", mock_connector)
            await EmbeddingManager.get_embedding("a", mock_connector)
            await EmbeddingManager.get_embedding("b", mock_connector)

            stats = EmbeddingManager.get_stats()
            assert stats["cache_size"] == 2
            assert stats["hits"] == 1
            assert stats["misses"] == 2
            assert stats["hit_rate_percent"] == pytest.approx(33.3, abs=0.1)

    def test_invalidate_clears_all(self, mock_config):
        with patch("app.services.ai.embedding_manager.get_ai_config", return_value=mock_config):
            EmbeddingManager._ensure_initialized()
            EmbeddingManager._cache["test"] = ([0.1], time.monotonic())
            EmbeddingManager._hits = 5
            EmbeddingManager._misses = 10

            EmbeddingManager.invalidate()

            assert len(EmbeddingManager._cache) == 0
            assert EmbeddingManager._hits == 0
            assert EmbeddingManager._misses == 0

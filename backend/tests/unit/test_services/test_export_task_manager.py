"""
ExportTaskManager 單元測試

測試非同步匯出任務管理：進度追蹤、結果暫存、任務生命週期。

@version 1.1.0 - 配合 v1.1.0 重構更新
@date 2026-02-25
"""

import pytest
from io import BytesIO
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.taoyuan.export_task_manager import (
    ExportTaskManager,
    _result_store,
    _result_timestamps,
    _validate_task_id,
    _evict_expired_results,
    STATUS_PENDING,
    STATUS_COMPLETED,
    STATUS_FAILED,
    EXPORT_TASK_PREFIX,
    TASK_TTL,
    _MAX_STORE_SIZE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_result_store():
    """每次測試後清理記憶體暫存"""
    _result_store.clear()
    _result_timestamps.clear()
    yield
    _result_store.clear()
    _result_timestamps.clear()


def make_mock_redis():
    """建立 mock Redis 實例"""
    redis_mock = AsyncMock()
    redis_mock.hset = AsyncMock()
    redis_mock.expire = AsyncMock()
    redis_mock.hgetall = AsyncMock(return_value={})
    redis_mock.delete = AsyncMock()
    return redis_mock


# ---------------------------------------------------------------------------
# TestValidateTaskId
# ---------------------------------------------------------------------------

class TestValidateTaskId:
    def test_valid_hex_12(self):
        assert _validate_task_id("abcdef012345") is True

    def test_invalid_too_short(self):
        assert _validate_task_id("abcdef") is False

    def test_invalid_too_long(self):
        assert _validate_task_id("abcdef01234567") is False

    def test_invalid_non_hex(self):
        assert _validate_task_id("abcdefghijkl") is False

    def test_invalid_uppercase(self):
        assert _validate_task_id("ABCDEF012345") is False

    def test_empty_string(self):
        assert _validate_task_id("") is False

    def test_injection_attempt(self):
        assert _validate_task_id("../../../etc") is False
        assert _validate_task_id("key:injection") is False


# ---------------------------------------------------------------------------
# TestEvictExpiredResults
# ---------------------------------------------------------------------------

class TestEvictExpiredResults:
    def test_evicts_expired_entries(self):
        import time
        _result_store["old"] = b"data"
        _result_timestamps["old"] = time.time() - TASK_TTL - 10
        _result_store["new"] = b"data2"
        _result_timestamps["new"] = time.time()

        _evict_expired_results()

        assert "old" not in _result_store
        assert "old" not in _result_timestamps
        assert "new" in _result_store

    def test_evicts_oldest_when_over_limit(self):
        import time
        # 填滿超過 _MAX_STORE_SIZE
        for i in range(_MAX_STORE_SIZE + 5):
            tid = f"{i:012x}"
            _result_store[tid] = b"x"
            _result_timestamps[tid] = time.time() + i * 0.001

        _evict_expired_results()

        assert len(_result_store) <= _MAX_STORE_SIZE


# ---------------------------------------------------------------------------
# TestGetProgress
# ---------------------------------------------------------------------------

class TestGetProgress:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_redis(self):
        with patch("app.services.taoyuan.export_task_manager.get_redis", return_value=None):
            result = await ExportTaskManager.get_progress("abcdef012345")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_task_id(self):
        result = await ExportTaskManager.get_progress("INVALID!")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_task_not_found(self):
        redis_mock = make_mock_redis()
        redis_mock.hgetall = AsyncMock(return_value={})
        with patch("app.services.taoyuan.export_task_manager.get_redis", return_value=redis_mock):
            result = await ExportTaskManager.get_progress("abcdef012345")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_progress_data(self):
        redis_mock = make_mock_redis()
        redis_mock.hgetall = AsyncMock(return_value={
            "status": "running",
            "progress": "60",
            "total": "100",
            "message": "建構 Excel...",
            "filename": "",
        })
        with patch("app.services.taoyuan.export_task_manager.get_redis", return_value=redis_mock):
            result = await ExportTaskManager.get_progress("abcdef012345")
            assert result["task_id"] == "abcdef012345"
            assert result["status"] == "running"
            assert result["progress"] == 60
            assert result["total"] == 100
            assert result["message"] == "建構 Excel..."


# ---------------------------------------------------------------------------
# TestGetResult
# ---------------------------------------------------------------------------

class TestGetResult:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_result(self):
        with patch("app.services.taoyuan.export_task_manager.get_redis", return_value=make_mock_redis()):
            result = await ExportTaskManager.get_result("abcdef012345")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_task_id(self):
        result = await ExportTaskManager.get_result("INVALID!")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_bytesio_and_cleans_up(self):
        import time
        test_data = b"PK\x03\x04fake_excel_data"
        _result_store["abcdef012345"] = test_data
        _result_timestamps["abcdef012345"] = time.time()

        redis_mock = make_mock_redis()
        with patch("app.services.taoyuan.export_task_manager.get_redis", return_value=redis_mock):
            result = await ExportTaskManager.get_result("abcdef012345")

            assert isinstance(result, BytesIO)
            assert result.read() == test_data
            # 確認已從 store 中移除
            assert "abcdef012345" not in _result_store
            assert "abcdef012345" not in _result_timestamps
            # 確認 Redis key 已刪除
            redis_mock.delete.assert_called_once_with(f"{EXPORT_TASK_PREFIX}abcdef012345")

    @pytest.mark.asyncio
    async def test_second_get_returns_none(self):
        import time
        _result_store["abcdef012345"] = b"data"
        _result_timestamps["abcdef012345"] = time.time()
        redis_mock = make_mock_redis()
        with patch("app.services.taoyuan.export_task_manager.get_redis", return_value=redis_mock):
            first = await ExportTaskManager.get_result("abcdef012345")
            assert first is not None
            second = await ExportTaskManager.get_result("abcdef012345")
            assert second is None


# ---------------------------------------------------------------------------
# TestUpdateProgress
# ---------------------------------------------------------------------------

class TestUpdateProgress:
    @pytest.mark.asyncio
    async def test_updates_redis_hash(self):
        redis_mock = make_mock_redis()
        with patch("app.services.taoyuan.export_task_manager.get_redis", return_value=redis_mock):
            await ExportTaskManager._update_progress(
                "abcdef012345", STATUS_COMPLETED, progress=100, total=50,
                message="完成", filename="test.xlsx"
            )
            redis_mock.hset.assert_called_once()
            call_kwargs = redis_mock.hset.call_args
            assert call_kwargs[1]["mapping"]["status"] == STATUS_COMPLETED
            assert call_kwargs[1]["mapping"]["progress"] == "100"
            assert call_kwargs[1]["mapping"]["filename"] == "test.xlsx"

    @pytest.mark.asyncio
    async def test_skips_when_no_redis(self):
        with patch("app.services.taoyuan.export_task_manager.get_redis", return_value=None):
            # 不應拋出異常
            await ExportTaskManager._update_progress("abcdef012345", STATUS_FAILED, message="err")


# ---------------------------------------------------------------------------
# TestSubmitExport
# ---------------------------------------------------------------------------

class TestSubmitExport:
    @pytest.mark.asyncio
    async def test_returns_task_id(self):
        redis_mock = make_mock_redis()
        mock_db = AsyncMock()

        with patch("app.services.taoyuan.export_task_manager.get_redis", return_value=redis_mock):
            with patch("asyncio.create_task") as mock_create_task:
                task_id = await ExportTaskManager.submit_export(mock_db)

                assert isinstance(task_id, str)
                assert len(task_id) == 12
                # 確認 Redis 初始狀態已寫入
                redis_mock.hset.assert_called_once()
                redis_mock.expire.assert_called_once()
                # 確認背景任務已建立
                mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_id_is_valid_hex(self):
        redis_mock = make_mock_redis()
        with patch("app.services.taoyuan.export_task_manager.get_redis", return_value=redis_mock):
            with patch("asyncio.create_task"):
                task_id = await ExportTaskManager.submit_export(AsyncMock())
                assert _validate_task_id(task_id) is True


# ---------------------------------------------------------------------------
# TestConstants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_task_ttl(self):
        assert TASK_TTL == 1800  # 30 min

    def test_status_values(self):
        assert STATUS_PENDING == "pending"
        assert STATUS_COMPLETED == "completed"
        assert STATUS_FAILED == "failed"

    def test_max_store_size(self):
        assert _MAX_STORE_SIZE == 50

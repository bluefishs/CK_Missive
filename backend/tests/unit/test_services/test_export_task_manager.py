"""
ExportTaskManager 單元測試

測試非同步匯出任務管理：進度追蹤、結果暫存、任務生命週期。

@version 1.0.0
@date 2026-02-25
"""

import pytest
from io import BytesIO
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.taoyuan.export_task_manager import (
    ExportTaskManager,
    _result_store,
    STATUS_PENDING,
    STATUS_COMPLETED,
    STATUS_FAILED,
    EXPORT_TASK_PREFIX,
    TASK_TTL,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_result_store():
    """每次測試後清理記憶體暫存"""
    _result_store.clear()
    yield
    _result_store.clear()


def make_mock_redis():
    """建立 mock Redis 實例"""
    redis_mock = AsyncMock()
    redis_mock.hset = AsyncMock()
    redis_mock.expire = AsyncMock()
    redis_mock.hgetall = AsyncMock(return_value={})
    redis_mock.delete = AsyncMock()
    return redis_mock


# ---------------------------------------------------------------------------
# TestGetProgress
# ---------------------------------------------------------------------------

class TestGetProgress:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_redis(self):
        with patch("app.services.taoyuan.export_task_manager.get_redis", return_value=None):
            result = await ExportTaskManager.get_progress("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_task_not_found(self):
        redis_mock = make_mock_redis()
        redis_mock.hgetall = AsyncMock(return_value={})
        with patch("app.services.taoyuan.export_task_manager.get_redis", return_value=redis_mock):
            result = await ExportTaskManager.get_progress("nonexistent")
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
            result = await ExportTaskManager.get_progress("task-123")
            assert result["task_id"] == "task-123"
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
            result = await ExportTaskManager.get_result("no-such-task")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_bytesio_and_cleans_up(self):
        test_data = b"PK\x03\x04fake_excel_data"
        _result_store["task-abc"] = test_data

        redis_mock = make_mock_redis()
        with patch("app.services.taoyuan.export_task_manager.get_redis", return_value=redis_mock):
            result = await ExportTaskManager.get_result("task-abc")

            assert isinstance(result, BytesIO)
            assert result.read() == test_data
            # 確認已從 store 中移除
            assert "task-abc" not in _result_store
            # 確認 Redis key 已刪除
            redis_mock.delete.assert_called_once_with(f"{EXPORT_TASK_PREFIX}task-abc")

    @pytest.mark.asyncio
    async def test_second_get_returns_none(self):
        _result_store["task-once"] = b"data"
        redis_mock = make_mock_redis()
        with patch("app.services.taoyuan.export_task_manager.get_redis", return_value=redis_mock):
            first = await ExportTaskManager.get_result("task-once")
            assert first is not None
            second = await ExportTaskManager.get_result("task-once")
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
                "task-1", STATUS_COMPLETED, progress=100, total=50,
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
            await ExportTaskManager._update_progress("task-x", STATUS_FAILED, message="err")


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

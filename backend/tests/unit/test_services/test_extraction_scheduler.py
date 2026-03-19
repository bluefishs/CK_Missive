"""
extraction_scheduler NER 提取排程器單元測試

測試範圍：
- ExtractionScheduler 初始化與配置
- get_status 狀態查詢
- start / stop 生命週期
- notify_new_documents 事件驅動觸發
- _check_ollama_available Ollama 可用性
- 模組級便利函數
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.extraction_scheduler import (
    ExtractionScheduler,
    DEFAULT_INTERVAL_MINUTES,
    BATCH_LIMIT,
    COMMIT_EVERY,
    INTER_DOC_SLEEP_OLLAMA,
    INTER_DOC_SLEEP_GROQ,
    MAX_CONSECUTIVE_FAILURES,
    notify_new_documents,
    get_extraction_scheduler,
)


class TestConstants:
    """排程器常數驗證"""

    def test_default_interval_minutes(self):
        assert DEFAULT_INTERVAL_MINUTES == 60

    def test_batch_limit(self):
        assert BATCH_LIMIT == 50

    def test_commit_every(self):
        assert COMMIT_EVERY == 10

    def test_ollama_sleep_faster_than_groq(self):
        assert INTER_DOC_SLEEP_OLLAMA < INTER_DOC_SLEEP_GROQ

    def test_max_consecutive_failures(self):
        assert MAX_CONSECUTIVE_FAILURES == 30


class TestExtractionSchedulerInit:
    """排程器初始化測試"""

    def test_default_state(self):
        scheduler = ExtractionScheduler()
        assert scheduler.is_running is False
        assert scheduler._structured_registered is False
        assert scheduler._last_run_stats is None

    def test_default_interval(self):
        scheduler = ExtractionScheduler()
        assert scheduler.interval_seconds == DEFAULT_INTERVAL_MINUTES * 60

    @patch.dict("os.environ", {"NER_SCHEDULER_INTERVAL_MINUTES": "30"})
    def test_custom_interval_from_env(self):
        scheduler = ExtractionScheduler()
        assert scheduler.interval_seconds == 30 * 60


class TestGetStatus:
    """get_status 狀態查詢"""

    def test_initial_status(self):
        scheduler = ExtractionScheduler()
        status = scheduler.get_status()
        assert status["is_running"] is False
        assert status["interval_minutes"] == DEFAULT_INTERVAL_MINUTES
        assert status["structured_registered"] is False
        assert status["last_run_stats"] is None
        assert status["mode"] == "hybrid (polling + event-driven)"
        assert status["task_active"] is False

    def test_status_after_start(self):
        scheduler = ExtractionScheduler()
        scheduler.is_running = True
        scheduler._structured_registered = True
        scheduler._last_run_stats = {"total": 10, "success": 8, "skipped": 1, "errors": 1}
        status = scheduler.get_status()
        assert status["is_running"] is True
        assert status["structured_registered"] is True
        assert status["last_run_stats"]["total"] == 10


class TestNotifyNewDocuments:
    """事件驅動觸發"""

    def test_notify_sets_trigger_event(self):
        scheduler = ExtractionScheduler()
        scheduler.is_running = True
        scheduler.notify_new_documents(5)
        assert scheduler._trigger_event.is_set()

    def test_notify_when_not_running(self):
        scheduler = ExtractionScheduler()
        scheduler.is_running = False
        scheduler.notify_new_documents(5)
        # 不應設置 trigger event
        assert not scheduler._trigger_event.is_set()


class TestStartStop:
    """生命週期測試"""

    @pytest.mark.asyncio
    async def test_start_creates_task(self):
        scheduler = ExtractionScheduler()
        with patch.object(scheduler, '_run_loop', new_callable=AsyncMock):
            await scheduler.start()
            assert scheduler.is_running is True
            assert scheduler._task is not None
            # 清理
            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        scheduler = ExtractionScheduler()
        scheduler.is_running = True
        # 不應建立新 task
        await scheduler.start()
        assert scheduler._task is None

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self):
        scheduler = ExtractionScheduler()
        # 不應拋出例外
        await scheduler.stop()
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self):
        scheduler = ExtractionScheduler()
        with patch.object(scheduler, '_run_loop', new_callable=AsyncMock):
            await scheduler.start()
            assert scheduler.is_running is True
            await scheduler.stop()
            assert scheduler.is_running is False
            assert scheduler._task is None


class TestCheckOllamaAvailable:
    """Ollama 可用性檢查"""

    @pytest.mark.asyncio
    async def test_ollama_available(self):
        scheduler = ExtractionScheduler()
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.services.ai.extraction_scheduler.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await scheduler._check_ollama_available()
            assert result is True

    @pytest.mark.asyncio
    async def test_ollama_unavailable(self):
        scheduler = ExtractionScheduler()

        with patch("app.services.ai.extraction_scheduler.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await scheduler._check_ollama_available()
            assert result is False


class TestSafeRegisterStructuredEntities:
    """結構化實體註冊安全包裝"""

    @pytest.mark.asyncio
    async def test_skip_if_already_registered(self):
        scheduler = ExtractionScheduler()
        scheduler._structured_registered = True
        await scheduler._safe_register_structured_entities()
        # 已註冊，不應再次執行
        assert scheduler._structured_registered is True

    @pytest.mark.asyncio
    async def test_failure_does_not_crash(self):
        scheduler = ExtractionScheduler()
        with patch.object(
            scheduler, '_register_structured_entities',
            new_callable=AsyncMock,
            side_effect=Exception("DB error"),
        ):
            # 不應拋出例外
            await scheduler._safe_register_structured_entities()
            assert scheduler._structured_registered is False


class TestModuleLevelFunctions:
    """模組級便利函數"""

    def test_notify_new_documents_no_scheduler(self):
        import app.services.ai.extraction_scheduler as mod
        original = mod._scheduler
        mod._scheduler = None
        # 不應拋出例外
        notify_new_documents(3)
        mod._scheduler = original

    def test_get_extraction_scheduler_returns_instance(self):
        import app.services.ai.extraction_scheduler as mod
        original = mod._scheduler
        mock_scheduler = MagicMock()
        mod._scheduler = mock_scheduler
        assert get_extraction_scheduler() is mock_scheduler
        mod._scheduler = original

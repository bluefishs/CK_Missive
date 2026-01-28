# -*- coding: utf-8 -*-
"""
交易隔離測試 (Transaction Isolation Tests)

驗證審計/通知服務的獨立 session 機制，
確保非關鍵操作失敗不會影響主業務流程。

測試案例：
1. 審計服務失敗不影響主操作
2. 通知服務失敗不影響主操作
3. 連接池在連續失敗後保持健康
4. 背景任務正確處理異常
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime


class TestAuditServiceIsolation:
    """審計服務隔離測試"""

    @pytest.mark.asyncio
    async def test_audit_failure_returns_false(self):
        """測試：審計服務失敗時返回 False，不拋出異常"""
        from app.services.audit_service import AuditService

        # Mock 資料庫連接失敗
        with patch('app.db.database.AsyncSessionLocal') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")

            result = await AuditService.log_change(
                table_name="documents",
                record_id=1,
                action="UPDATE",
                changes={"subject": {"old": "舊", "new": "新"}},
                user_id=1,
                user_name="test_user"
            )

            # 應返回 False 而非拋出異常
            assert result == False

    @pytest.mark.asyncio
    async def test_audit_success_returns_true(self):
        """測試：審計服務成功時返回 True"""
        from app.services.audit_service import AuditService

        # Mock 成功的資料庫操作
        with patch('app.db.database.AsyncSessionLocal') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            result = await AuditService.log_change(
                table_name="documents",
                record_id=1,
                action="CREATE",
                changes={"created": {"doc_number": "TEST001"}},
                user_id=1
            )

            # 應返回 True
            assert result == True

    @pytest.mark.asyncio
    async def test_audit_uses_independent_session(self):
        """測試：審計服務使用獨立 session"""
        from app.services.audit_service import AuditService

        with patch('app.db.database.AsyncSessionLocal') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            await AuditService.log_document_change(
                document_id=123,
                action="UPDATE",
                changes={"status": {"old": "pending", "new": "completed"}},
                user_id=1
            )

            # 確認使用了獨立的 session（AsyncSessionLocal 被呼叫）
            mock_session.assert_called_once()


class TestNotificationServiceIsolation:
    """通知服務隔離測試"""

    @pytest.mark.asyncio
    async def test_safe_notify_failure_returns_false(self):
        """測試：safe_notify_critical_change 失敗時返回 False"""
        from app.services.notification_service import NotificationService

        with patch('app.db.database.AsyncSessionLocal') as mock_session:
            mock_session.side_effect = Exception("Database error")

            result = await NotificationService.safe_notify_critical_change(
                document_id=1,
                field="subject",
                old_value="舊主旨",
                new_value="新主旨",
                user_id=1
            )

            assert result == False

    @pytest.mark.asyncio
    async def test_safe_notify_document_deleted_isolation(self):
        """測試：safe_notify_document_deleted 使用獨立 session"""
        from app.services.notification_service import NotificationService

        with patch('app.db.database.AsyncSessionLocal') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            result = await NotificationService.safe_notify_document_deleted(
                document_id=123,
                doc_number="TEST123",
                subject="測試公文",
                user_id=1,
                user_name="admin"
            )

            # 確認使用了獨立 session
            mock_session.assert_called_once()
            assert result == True


class TestNonCriticalDecorator:
    """@non_critical 裝飾器測試"""

    @pytest.mark.asyncio
    async def test_decorator_catches_exception(self):
        """測試：裝飾器捕獲異常並返回預設值"""
        from app.core.decorators import non_critical

        @non_critical(default_return="default_value")
        async def failing_function():
            raise ValueError("Something went wrong")

        result = await failing_function()
        assert result == "default_value"

    @pytest.mark.asyncio
    async def test_decorator_passes_on_success(self):
        """測試：裝飾器在成功時傳遞原始返回值"""
        from app.core.decorators import non_critical

        @non_critical(default_return=None)
        async def successful_function():
            return "success"

        result = await successful_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_logs_failure(self):
        """測試：裝飾器記錄失敗日誌"""
        from app.core.decorators import non_critical
        import logging

        @non_critical
        async def failing_function():
            raise Exception("Test error")

        with patch('app.core.decorators.logger') as mock_logger:
            await failing_function()
            mock_logger.log.assert_called()


class TestRetryDecorator:
    """@retry_on_failure 裝飾器測試"""

    @pytest.mark.asyncio
    async def test_retry_eventually_succeeds(self):
        """測試：重試後最終成功"""
        from app.core.decorators import retry_on_failure

        call_count = 0

        @retry_on_failure(max_retries=3, delay=0.01)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        result = await flaky_function()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_gives_up_after_max_retries(self):
        """測試：達到最大重試次數後拋出異常"""
        from app.core.decorators import retry_on_failure

        @retry_on_failure(max_retries=2, delay=0.01)
        async def always_failing():
            raise Exception("Always fails")

        with pytest.raises(Exception, match="Always fails"):
            await always_failing()


class TestBackgroundTaskManager:
    """背景任務管理器測試"""

    @pytest.mark.asyncio
    async def test_audit_task_updates_stats(self):
        """測試：審計任務更新統計"""
        from app.core.background_tasks import BackgroundTaskManager
        from fastapi import BackgroundTasks

        # 重置統計
        BackgroundTaskManager._stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "last_task_time": None
        }

        background_tasks = BackgroundTasks()

        with patch('app.services.audit_service.AuditService.log_change') as mock_audit:
            mock_audit.return_value = True

            BackgroundTaskManager.add_audit_task(
                background_tasks=background_tasks,
                table_name="documents",
                record_id=1,
                action="UPDATE",
                changes={},
                user_id=1
            )

            # 執行背景任務
            for task in background_tasks.tasks:
                await task()

            # 統計應已更新
            stats = BackgroundTaskManager.get_stats()
            assert stats["total_tasks"] == 1
            assert stats["completed_tasks"] == 1


class TestDatabaseMonitor:
    """連接池監控測試"""

    def test_get_pool_stats_returns_metrics(self):
        """測試：取得連接池統計"""
        from app.core.db_monitor import DatabaseMonitor

        stats = DatabaseMonitor.get_pool_stats()

        # 應包含必要的指標
        assert "active_connections" in stats
        assert "checkout_count" in stats
        assert "error_count" in stats
        assert "thresholds" in stats

    def test_get_health_status_evaluates_correctly(self):
        """測試：健康狀態評估"""
        from app.core.db_monitor import DatabaseMonitor

        # 重置指標
        DatabaseMonitor.reset_metrics()

        health = DatabaseMonitor.get_health_status()

        # 初始狀態應為健康
        assert health["status"] == "healthy"
        assert "stats" in health


class TestIntegrationScenarios:
    """整合情境測試"""

    @pytest.mark.asyncio
    async def test_main_operation_succeeds_when_audit_fails(self):
        """
        整合測試：主操作在審計失敗時仍應成功

        模擬情境：
        1. 公文更新操作成功
        2. 審計日誌寫入失敗
        3. 整體操作應回傳成功
        """
        # 這個測試需要完整的應用程式上下文
        # 在實際整合測試中實作
        pass

    @pytest.mark.asyncio
    async def test_main_operation_succeeds_when_notification_fails(self):
        """
        整合測試：主操作在通知失敗時仍應成功

        模擬情境：
        1. 公文刪除操作成功
        2. 刪除通知發送失敗
        3. 整體操作應回傳成功
        """
        # 這個測試需要完整的應用程式上下文
        # 在實際整合測試中實作
        pass


# 測試配置
@pytest.fixture
def reset_monitors():
    """重置所有監控器狀態"""
    from app.core.db_monitor import DatabaseMonitor
    from app.core.background_tasks import BackgroundTaskManager

    DatabaseMonitor.reset_metrics()
    BackgroundTaskManager._stats = {
        "total_tasks": 0,
        "completed_tasks": 0,
        "failed_tasks": 0,
        "last_task_time": None
    }

    yield

    # 測試後清理
    DatabaseMonitor.reset_metrics()

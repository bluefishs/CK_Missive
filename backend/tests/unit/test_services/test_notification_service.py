# -*- coding: utf-8 -*-
"""
NotificationService 單元測試

測試範圍:
- 通知建立: create_notification (靜態方法，使用 ORM)
- 業務通知: notify_critical_change, notify_document_deleted, notify_import_result
- 實例模式 (Repository): list_notifications, mark_notifications_read, mark_all_read_for_user, get_unread_count_for_user
- 無 DB 初始化錯誤
- 常數驗證
- 異常處理: 資料庫錯誤回退

測試策略: Mock AsyncSession 和 NotificationRepository，不使用真實資料庫。

v1.1.0 - 2026-02-27 移除 4 個過時 ORM 靜態方法測試（已由 Repository 實例測試取代）
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.notification_service import (
    NotificationService,
    NotificationType,
    NotificationSeverity,
    CRITICAL_FIELDS,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_db():
    """建立 mock AsyncSession"""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def mock_repository():
    """建立 mock NotificationRepository"""
    repo = MagicMock()
    repo.filter_notifications = AsyncMock()
    repo.mark_read_batch = AsyncMock()
    repo.mark_all_read = AsyncMock()
    repo.get_unread_count = AsyncMock()
    repo.get_statistics = AsyncMock()
    repo.delete_read_older_than = AsyncMock()
    repo.delete_old = AsyncMock()
    return repo


@pytest.fixture
def service(mock_db, mock_repository):
    """建立 NotificationService 實例"""
    with patch(
        "app.services.notification_service.NotificationRepository"
    ) as MockRepoClass:
        MockRepoClass.return_value = mock_repository
        svc = NotificationService(mock_db)
        svc.repository = mock_repository
        return svc


@pytest.fixture
def mock_notification():
    """建立模擬通知實體"""
    notification = MagicMock()
    notification.id = 1
    notification.user_id = 1
    notification.title = "測試通知"
    notification.message = "測試通知內容"
    notification.notification_type = NotificationType.SYSTEM
    notification.is_read = False
    notification.read_at = None
    notification.created_at = datetime(2026, 2, 1, 10, 0, 0)
    notification.data = {
        "severity": "info",
        "source_table": None,
        "source_id": None,
        "changes": None,
        "user_name": "admin",
    }
    return notification


# ============================================================
# create_notification 測試 (靜態方法)
# ============================================================

class TestCreateNotification:
    """create_notification 方法測試"""

    @pytest.mark.asyncio
    async def test_create_notification_success(self, mock_db):
        """測試成功建立通知"""
        mock_db.refresh = AsyncMock()

        # Mock refresh 後 notification.id 有值
        def set_id_on_refresh(obj):
            obj.id = 42

        mock_db.refresh.side_effect = set_id_on_refresh

        result = await NotificationService.create_notification(
            db=mock_db,
            notification_type=NotificationType.SYSTEM,
            severity=NotificationSeverity.INFO,
            title="系統通知",
            message="測試通知內容",
        )

        assert result == 42
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_notification_with_all_fields(self, mock_db):
        """測試建立含所有欄位的通知"""
        def set_id_on_refresh(obj):
            obj.id = 99

        mock_db.refresh = AsyncMock(side_effect=set_id_on_refresh)

        result = await NotificationService.create_notification(
            db=mock_db,
            notification_type=NotificationType.CRITICAL_CHANGE,
            severity=NotificationSeverity.WARNING,
            title="欄位變更",
            message="公文主旨已修改",
            source_table="documents",
            source_id=100,
            changes={"field": "subject", "old_value": "舊", "new_value": "新"},
            user_id=1,
            user_name="admin",
        )

        assert result == 99
        # 驗證 add 的 notification 物件包含正確的 data payload
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.notification_type == NotificationType.CRITICAL_CHANGE
        assert added_obj.data["severity"] == "warning"
        assert added_obj.data["source_table"] == "documents"

    @pytest.mark.asyncio
    async def test_create_notification_db_error(self, mock_db):
        """測試資料庫錯誤時回傳 None 並回滾"""
        mock_db.commit.side_effect = Exception("DB Error")

        result = await NotificationService.create_notification(
            db=mock_db,
            notification_type=NotificationType.SYSTEM,
            severity=NotificationSeverity.INFO,
            title="失敗通知",
            message="將失敗",
        )

        assert result is None
        mock_db.rollback.assert_awaited_once()


# ============================================================
# 業務通知測試
# ============================================================

class TestNotifyCriticalChange:
    """notify_critical_change 方法測試"""

    @pytest.mark.asyncio
    async def test_notify_critical_change(self, mock_db):
        """測試關鍵欄位變更通知"""
        def set_id_on_refresh(obj):
            obj.id = 10

        mock_db.refresh = AsyncMock(side_effect=set_id_on_refresh)

        result = await NotificationService.notify_critical_change(
            db=mock_db,
            document_id=100,
            field="subject",
            old_value="舊主旨",
            new_value="新主旨",
            user_id=1,
            user_name="admin",
        )

        assert result == 10
        mock_db.add.assert_called_once()

        # 驗證通知內容
        added = mock_db.add.call_args[0][0]
        assert added.notification_type == NotificationType.CRITICAL_CHANGE
        assert "主旨" in added.title  # 因為 CRITICAL_FIELDS 中 subject -> 主旨
        assert "admin" in added.message

    @pytest.mark.asyncio
    async def test_notify_critical_change_unknown_field(self, mock_db):
        """測試未知欄位的變更通知（使用原始欄位名）"""
        def set_id_on_refresh(obj):
            obj.id = 11

        mock_db.refresh = AsyncMock(side_effect=set_id_on_refresh)

        result = await NotificationService.notify_critical_change(
            db=mock_db,
            document_id=200,
            field="unknown_field",
            old_value="old",
            new_value="new",
        )

        assert result == 11
        added = mock_db.add.call_args[0][0]
        # 未知欄位應直接顯示欄位名
        assert "unknown_field" in added.title


class TestNotifyDocumentDeleted:
    """notify_document_deleted 方法測試"""

    @pytest.mark.asyncio
    async def test_notify_document_deleted(self, mock_db):
        """測試公文刪除通知"""
        def set_id_on_refresh(obj):
            obj.id = 20

        mock_db.refresh = AsyncMock(side_effect=set_id_on_refresh)

        result = await NotificationService.notify_document_deleted(
            db=mock_db,
            document_id=500,
            doc_number="府工測字第001號",
            subject="測試主旨",
            user_name="admin",
        )

        assert result == 20
        added = mock_db.add.call_args[0][0]
        assert "府工測字第001號" in added.title
        assert added.data["changes"]["action"] == "DELETE"


class TestNotifyImportResult:
    """notify_import_result 方法測試"""

    @pytest.mark.asyncio
    async def test_notify_import_success(self, mock_db):
        """測試匯入成功通知"""
        def set_id_on_refresh(obj):
            obj.id = 30

        mock_db.refresh = AsyncMock(side_effect=set_id_on_refresh)

        result = await NotificationService.notify_import_result(
            db=mock_db,
            success_count=50,
            error_count=0,
        )

        assert result == 30
        added = mock_db.add.call_args[0][0]
        assert added.data["severity"] == NotificationSeverity.INFO
        assert "50" in added.message

    @pytest.mark.asyncio
    async def test_notify_import_with_errors(self, mock_db):
        """測試匯入有錯誤通知"""
        def set_id_on_refresh(obj):
            obj.id = 31

        mock_db.refresh = AsyncMock(side_effect=set_id_on_refresh)

        result = await NotificationService.notify_import_result(
            db=mock_db,
            success_count=45,
            error_count=5,
            errors=["行 3: 格式錯誤", "行 7: 缺少欄位"],
        )

        assert result == 31
        added = mock_db.add.call_args[0][0]
        assert added.data["severity"] == NotificationSeverity.WARNING
        assert "45" in added.message
        assert "5" in added.message


# ============================================================
# 實例模式方法測試 (Repository-based)
# ============================================================

class TestInstanceListNotifications:
    """list_notifications 方法測試 (實例模式)"""

    @pytest.mark.asyncio
    async def test_list_notifications(self, service, mock_repository, mock_notification):
        """測試實例模式查詢通知列表"""
        mock_repository.filter_notifications.return_value = (
            [mock_notification],
            1,
        )

        items, total = await service.list_notifications(user_id=1)

        assert total == 1
        assert len(items) == 1
        assert items[0]["title"] == "測試通知"
        mock_repository.filter_notifications.assert_awaited_once_with(
            user_id=1,
            is_read=None,
            notification_type=None,
            limit=50,
            offset=0,
        )

    @pytest.mark.asyncio
    async def test_list_notifications_with_filters(
        self, service, mock_repository
    ):
        """測試帶篩選條件的通知列表"""
        mock_repository.filter_notifications.return_value = ([], 0)

        items, total = await service.list_notifications(
            user_id=1, is_read=False, notification_type="system", limit=10
        )

        assert total == 0
        mock_repository.filter_notifications.assert_awaited_once_with(
            user_id=1,
            is_read=False,
            notification_type="system",
            limit=10,
            offset=0,
        )


class TestInstanceMarkNotificationsRead:
    """mark_notifications_read 方法測試 (實例模式)"""

    @pytest.mark.asyncio
    async def test_mark_notifications_read(self, service, mock_repository):
        """測試實例模式批次標記已讀"""
        mock_repository.mark_read_batch.return_value = 3

        result = await service.mark_notifications_read([1, 2, 3])

        assert result == 3
        mock_repository.mark_read_batch.assert_awaited_once_with([1, 2, 3])


class TestInstanceMarkAllRead:
    """mark_all_read_for_user 方法測試 (實例模式)"""

    @pytest.mark.asyncio
    async def test_mark_all_read_for_user(self, service, mock_repository):
        """測試實例模式全部已讀"""
        mock_repository.mark_all_read.return_value = 5

        result = await service.mark_all_read_for_user(user_id=1)

        assert result == 5
        mock_repository.mark_all_read.assert_awaited_once_with(1)


class TestInstanceGetUnreadCount:
    """get_unread_count_for_user 方法測試 (實例模式)"""

    @pytest.mark.asyncio
    async def test_get_unread_count_for_user(self, service, mock_repository):
        """測試實例模式取得未讀數量"""
        mock_repository.get_unread_count.return_value = 7

        result = await service.get_unread_count_for_user(user_id=1)

        assert result == 7
        mock_repository.get_unread_count.assert_awaited_once_with(1)


# ============================================================
# 無 DB 初始化錯誤測試
# ============================================================

class TestNoDbInitialization:
    """未初始化 db session 的錯誤測試"""

    @pytest.mark.asyncio
    async def test_list_notifications_no_db_raises(self):
        """測試未初始化 db 時呼叫 list_notifications 拋出 RuntimeError"""
        svc = NotificationService(db=None)

        with pytest.raises(RuntimeError, match="未初始化"):
            await svc.list_notifications(user_id=1)

    @pytest.mark.asyncio
    async def test_mark_notifications_read_no_db_raises(self):
        """測試未初始化 db 時呼叫 mark_notifications_read 拋出 RuntimeError"""
        svc = NotificationService(db=None)

        with pytest.raises(RuntimeError, match="未初始化"):
            await svc.mark_notifications_read([1])


# ============================================================
# 常數驗證測試
# ============================================================

class TestNotificationConstants:
    """通知常數測試"""

    def test_notification_types(self):
        """測試通知類型常數存在"""
        assert NotificationType.SYSTEM == "system"
        assert NotificationType.CRITICAL_CHANGE == "critical_change"
        assert NotificationType.IMPORT == "import"
        assert NotificationType.ERROR == "error"

    def test_notification_severity(self):
        """測試嚴重程度常數存在"""
        assert NotificationSeverity.INFO == "info"
        assert NotificationSeverity.WARNING == "warning"
        assert NotificationSeverity.ERROR == "error"
        assert NotificationSeverity.CRITICAL == "critical"

    def test_critical_fields_documents(self):
        """測試關鍵欄位定義包含公文欄位"""
        assert "documents" in CRITICAL_FIELDS
        assert "subject" in CRITICAL_FIELDS["documents"]
        assert CRITICAL_FIELDS["documents"]["subject"] == "主旨"

    def test_critical_fields_projects(self):
        """測試關鍵欄位定義包含專案欄位"""
        assert "contract_projects" in CRITICAL_FIELDS
        assert "project_name" in CRITICAL_FIELDS["contract_projects"]

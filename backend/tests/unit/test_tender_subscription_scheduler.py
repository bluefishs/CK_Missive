"""
標案訂閱排程器單元測試

測試 check_all_subscriptions 的核心邏輯：
- 無訂閱時快速返回
- 有新增公告時觸發通知
- 首次執行不發送通知 (避免噪音)
- 搜尋失敗時跳過但不中斷
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


@pytest.fixture
def mock_db():
    """模擬 AsyncSession"""
    db = AsyncMock()
    db.commit = AsyncMock()
    return db


def _make_subscription(
    id=1, keyword="水利", category=None, is_active=True,
    last_count=10, last_checked_at=None,
    notify_system=True, notify_line=False,
):
    sub = MagicMock()
    sub.id = id
    sub.keyword = keyword
    sub.category = category
    sub.is_active = is_active
    sub.last_count = last_count
    sub.last_checked_at = last_checked_at
    sub.notify_system = notify_system
    sub.notify_line = notify_line
    return sub


class TestCheckAllSubscriptions:
    """check_all_subscriptions 核心邏輯測試"""

    @pytest.mark.asyncio
    async def test_no_subscriptions_returns_empty(self, mock_db):
        """無訂閱時應快速返回空結果"""
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        from app.services.tender_subscription_scheduler import check_all_subscriptions
        result = await check_all_subscriptions(mock_db)

        assert result == {"checked": 0, "notified": 0, "details": []}
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_new_tenders_trigger_notification(self, mock_db):
        """有新增公告 (diff > 0, old_total > 0) 應觸發通知"""
        sub = _make_subscription(last_count=10, notify_system=True)

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [sub]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        with patch(
            "app.services.tender_subscription_scheduler.TenderSearchService"
        ) as MockService:
            instance = MockService.return_value
            instance.search_by_title = AsyncMock(return_value={
                "total_records": 15,
                "records": [
                    {"title": "新增標案一"},
                    {"title": "新增標案二"},
                ],
            })

            with patch(
                "app.services.notification_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ):
                from app.services.tender_subscription_scheduler import check_all_subscriptions
                result = await check_all_subscriptions(mock_db)

        assert result["checked"] == 1
        assert result["notified"] == 1
        assert result["details"][0]["diff"] == 5
        assert result["details"][0]["notified"] is True
        assert sub.last_count == 15

    @pytest.mark.asyncio
    async def test_first_run_no_notification(self, mock_db):
        """首次執行 (old_total=0) 不應發送通知"""
        sub = _make_subscription(last_count=0)

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [sub]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        with patch(
            "app.services.tender_subscription_scheduler.TenderSearchService"
        ) as MockService:
            instance = MockService.return_value
            instance.search_by_title = AsyncMock(return_value={
                "total_records": 20, "records": [],
            })

            from app.services.tender_subscription_scheduler import check_all_subscriptions
            result = await check_all_subscriptions(mock_db)

        assert result["notified"] == 0
        assert result["details"][0]["notified"] is False
        assert sub.last_count == 20

    @pytest.mark.asyncio
    async def test_no_change_no_notification(self, mock_db):
        """數量無變化不應發送通知"""
        sub = _make_subscription(last_count=10)

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [sub]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        with patch(
            "app.services.tender_subscription_scheduler.TenderSearchService"
        ) as MockService:
            instance = MockService.return_value
            instance.search_by_title = AsyncMock(return_value={
                "total_records": 10, "records": [],
            })

            from app.services.tender_subscription_scheduler import check_all_subscriptions
            result = await check_all_subscriptions(mock_db)

        assert result["notified"] == 0
        assert result["details"][0]["diff"] == 0

    @pytest.mark.asyncio
    async def test_search_failure_skips_subscription(self, mock_db):
        """搜尋失敗時應記錄錯誤但不中斷"""
        sub = _make_subscription(keyword="失敗測試")

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [sub]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        with patch(
            "app.services.tender_subscription_scheduler.TenderSearchService"
        ) as MockService:
            instance = MockService.return_value
            instance.search_by_title = AsyncMock(side_effect=Exception("API timeout"))

            from app.services.tender_subscription_scheduler import check_all_subscriptions
            result = await check_all_subscriptions(mock_db)

        assert result["checked"] == 0
        assert "error" in result["details"][0]

    @pytest.mark.asyncio
    async def test_multiple_subscriptions(self, mock_db):
        """多個訂閱各自獨立處理"""
        sub1 = _make_subscription(id=1, keyword="水利", last_count=5)
        sub2 = _make_subscription(id=2, keyword="資訊", last_count=3)

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [sub1, sub2]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        with patch(
            "app.services.tender_subscription_scheduler.TenderSearchService"
        ) as MockService:
            instance = MockService.return_value
            instance.search_by_title = AsyncMock(side_effect=[
                {"total_records": 8, "records": [{"title": "T1"}]},
                {"total_records": 3, "records": []},
            ])

            with patch(
                "app.services.notification_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ):
                from app.services.tender_subscription_scheduler import check_all_subscriptions
                result = await check_all_subscriptions(mock_db)

        assert result["checked"] == 2
        assert result["notified"] == 1  # 只有 sub1 有新增
        mock_db.commit.assert_called_once()

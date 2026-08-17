"""
ExpenseApprovalService 單元測試

測試多層審核流程、預算聯防、駁回邏輯。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from app.services.erp.expense_approval import ExpenseApprovalService


def _make_invoice(
    id=1, status="pending", amount=Decimal("15000"), case_code="B114-B001",
    inv_num="AB12345678", user_id=1,
):
    inv = MagicMock()
    inv.id = id
    inv.status = status
    inv.amount = amount
    inv.case_code = case_code
    inv.inv_num = inv_num
    inv.user_id = user_id
    return inv


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def service(mock_db):
    svc = ExpenseApprovalService.__new__(ExpenseApprovalService)
    svc.db = mock_db
    svc.repo = AsyncMock()
    svc.ledger_service = AsyncMock()
    # 冪等檢查：預設無已存在的帳本記錄
    svc.ledger_service.find_by_source = AsyncMock(return_value=None)
    return svc


# 2026-08-17：核准機制**暫緩**（owner：系統無財務獨立權限與人資），
# 預設 `EXPENSE_APPROVAL_ENABLED=False` → `approve()` 一律拒絕。
#
# 這些測試**不刪除也不 skip** —— 它們保護的是「日後開回來時流程要正確」，
# 而暫緩不是移除。改為在啟用狀態下執行：patch 掉旗標即可。
# （skip 掉的話，開回來的那天沒有任何東西在保護這條路徑。）
@pytest.fixture(autouse=True)
def _enable_approval(monkeypatch):
    monkeypatch.setattr(
        "app.services.erp.expense_approval.EXPENSE_APPROVAL_ENABLED", True, raising=False
    )


class TestApprove:
    """多層審核推進"""

    @pytest.mark.asyncio
    async def test_low_value_pending_to_manager(self, service):
        """≤30K: pending → manager_approved"""
        inv = _make_invoice(amount=Decimal("15000"))
        service.repo.get_by_id_for_update = AsyncMock(return_value=inv)
        service.repo.update_status = AsyncMock()
        service.repo.commit = AsyncMock()

        with patch.object(service, '_notify_status_change', new_callable=AsyncMock):
            with patch.object(service, 'audit_update', new_callable=AsyncMock):
                result = await service.approve(1)

        service.repo.update_status.assert_called_once_with(inv, "manager_approved")
        service.ledger_service.record_from_expense.assert_not_called()

    @pytest.mark.asyncio
    async def test_low_value_manager_to_verified(self, service):
        """≤30K: manager_approved → verified (帳本入帳)"""
        inv = _make_invoice(status="manager_approved", amount=Decimal("15000"))
        service.repo.get_by_id_for_update = AsyncMock(return_value=inv)
        service.repo.update_status = AsyncMock()
        service.repo.commit = AsyncMock()

        with patch.object(service, '_check_budget', new_callable=AsyncMock, return_value=None):
            with patch.object(service, '_notify_status_change', new_callable=AsyncMock):
                with patch.object(service, 'audit_update', new_callable=AsyncMock):
                    await service.approve(1)

        service.repo.update_status.assert_called_once_with(inv, "verified")
        service.ledger_service.record_from_expense.assert_called_once_with(inv)

    @pytest.mark.asyncio
    async def test_high_value_completes_after_manager(self, service):
        """>30K: manager_approved → verified。

        2026-08-17 owner「流程簡化」：財務層移除。
        原本這裡斷言 → finance_approved（不入帳），那是舊規則 ——
        改變的理由是每一層都是同一組人，第三段不產生控制效果。
        高額現在主管核准後直接終結**並入帳**。
        """
        inv = _make_invoice(status="manager_approved", amount=Decimal("50000"))
        service.repo.get_by_id_for_update = AsyncMock(return_value=inv)
        service.repo.update_status = AsyncMock()
        service.repo.commit = AsyncMock()

        with patch.object(service, '_check_budget', new_callable=AsyncMock, return_value=None):
            with patch.object(service, '_notify_status_change', new_callable=AsyncMock):
                with patch.object(service, 'audit_update', new_callable=AsyncMock):
                    await service.approve(1)

        service.repo.update_status.assert_called_once_with(inv, "verified")
        # 走到終態就要入帳 —— 這是流程簡化帶來的**行為改變**，不是測試寫錯：
        # 舊流程停在 finance_approved 所以不入帳，新流程直接完成。
        service.ledger_service.record_from_expense.assert_called_once()

    @pytest.mark.asyncio
    async def test_verified_cannot_approve(self, service):
        """已核准不可再審"""
        inv = _make_invoice(status="verified")
        service.repo.get_by_id_for_update = AsyncMock(return_value=inv)

        with pytest.raises(ValueError, match="不可進行審核"):
            await service.approve(1)

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self, service):
        """ID 不存在返回 None"""
        service.repo.get_by_id_for_update = AsyncMock(return_value=None)
        assert await service.approve(999) is None

    @pytest.mark.asyncio
    async def test_budget_warning_attached(self, service):
        """預算警告附加到 invoice 動態屬性"""
        inv = _make_invoice(status="manager_approved", amount=Decimal("15000"))
        service.repo.get_by_id_for_update = AsyncMock(return_value=inv)
        service.repo.update_status = AsyncMock()
        service.repo.commit = AsyncMock()

        with patch.object(service, '_check_budget', new_callable=AsyncMock, return_value="⚠️ 預算警告"):
            with patch.object(service, '_notify_status_change', new_callable=AsyncMock):
                with patch.object(service, 'audit_update', new_callable=AsyncMock):
                    result = await service.approve(1)

        assert result._budget_warning == "⚠️ 預算警告"


class TestReject:
    """駁回邏輯"""

    @pytest.mark.asyncio
    async def test_reject_pending(self, service):
        """pending 狀態可駁回"""
        inv = _make_invoice(status="pending")
        service.repo.get_by_id_for_update = AsyncMock(return_value=inv)
        service.repo.update_status = AsyncMock(return_value=inv)

        with patch.object(service, 'audit_update', new_callable=AsyncMock):
            result = await service.reject(1, reason="測試駁回")

        service.repo.update_status.assert_called_once_with(inv, "rejected", notes_append="[駁回] 測試駁回")

    @pytest.mark.asyncio
    async def test_reject_verified_raises(self, service):
        """已核准不可駁回"""
        inv = _make_invoice(status="verified")
        service.repo.get_by_id_for_update = AsyncMock(return_value=inv)

        with pytest.raises(ValueError, match="不可駁回"):
            await service.reject(1)


class TestDetermineNextApproval:
    """審核層級決策"""

    def test_all_paths(self):
        svc = ExpenseApprovalService.__new__(ExpenseApprovalService)
        # 低金額路徑
        assert svc._determine_next_approval("pending", Decimal("10000")) == "manager_approved"
        assert svc._determine_next_approval("manager_approved", Decimal("10000")) == "verified"
        # 高金額路徑
        assert svc._determine_next_approval("pending", Decimal("50000")) == "manager_approved"
        # 2026-08-17 流程簡化：財務層移除，主管核准後直接終結
        assert svc._determine_next_approval("manager_approved", Decimal("50000")) == "verified"
        assert svc._determine_next_approval("finance_approved", Decimal("50000")) == "verified"

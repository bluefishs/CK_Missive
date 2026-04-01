"""營運帳目服務 (Operational Account Service)

帳目 CRUD + 費用 CRUD + 預算檢查 + 自動編號

Version: 1.0.0
"""
import logging
from typing import Optional, List, Tuple
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.operational import OperationalAccount, OperationalExpense
from app.repositories.erp.operational_repository import (
    OperationalAccountRepository,
    OperationalExpenseRepository,
)
from app.schemas.erp.operational import (
    OperationalAccountCreate,
    OperationalAccountUpdate,
    OperationalAccountListRequest,
    OperationalAccountResponse,
    OperationalExpenseCreate,
    OperationalExpenseListRequest,
    OperationalExpenseResponse,
    OperationalAccountStatsResponse,
    ACCOUNT_CATEGORIES,
)
from app.services.audit_mixin import AuditableServiceMixin

logger = logging.getLogger(__name__)

# 預算警告門檻
BUDGET_WARNING_PCT = Decimal("80")
BUDGET_BLOCK_PCT = Decimal("100")


class OperationalAccountService(AuditableServiceMixin):
    """營運帳目服務"""

    AUDIT_TABLE = "operational_accounts"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.account_repo = OperationalAccountRepository(db)
        self.expense_repo = OperationalExpenseRepository(db)

    # ========================================================================
    # Account CRUD
    # ========================================================================

    async def list_accounts(
        self, params: OperationalAccountListRequest
    ) -> Tuple[List[OperationalAccountResponse], int]:
        """列出帳目 (含累計支出)"""
        items, total = await self.account_repo.list_filtered(params)
        results = []
        for acct in items:
            resp = self._to_account_response(acct)
            spent = await self.account_repo.get_total_spent(acct.id)
            resp.total_spent = spent
            if acct.budget_limit and acct.budget_limit > 0:
                resp.budget_usage_pct = (spent / acct.budget_limit * 100).quantize(Decimal("0.1"))
            results.append(resp)
        return results, total

    async def create_account(
        self, data: OperationalAccountCreate, user_id: Optional[int] = None
    ) -> OperationalAccountResponse:
        """建立帳目 (自動產生 account_code)"""
        if data.category not in ACCOUNT_CATEGORIES:
            raise ValueError(f"無效的類別: {data.category}, 允許: {list(ACCOUNT_CATEGORIES.keys())}")

        account_code = await self.account_repo.generate_code(data.fiscal_year, data.category)

        create_data = data.model_dump()
        create_data["account_code"] = account_code
        if data.owner_id is None and user_id:
            create_data["owner_id"] = user_id

        account = await self.account_repo.create(create_data)
        await self.db.commit()
        await self.audit_create(account.id, create_data, user_id=user_id)
        return self._to_account_response(account)

    async def get_account(self, account_id: int) -> Optional[OperationalAccountResponse]:
        """取得帳目詳情"""
        account = await self.account_repo.get_by_id(account_id)
        if not account:
            return None
        resp = self._to_account_response(account)
        spent = await self.account_repo.get_total_spent(account.id)
        resp.total_spent = spent
        if account.budget_limit and account.budget_limit > 0:
            resp.budget_usage_pct = (spent / account.budget_limit * 100).quantize(Decimal("0.1"))
        return resp

    async def update_account(
        self, account_id: int, data: OperationalAccountUpdate
    ) -> Optional[OperationalAccountResponse]:
        """更新帳目"""
        account = await self.account_repo.get_by_id(account_id)
        if not account:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "category" in update_data and update_data["category"] not in ACCOUNT_CATEGORIES:
            raise ValueError(f"無效的類別: {update_data['category']}")

        for key, value in update_data.items():
            setattr(account, key, value)

        await self.db.flush()
        await self.db.refresh(account)
        await self.db.commit()
        await self.audit_update(account_id, update_data)
        return self._to_account_response(account)

    async def delete_account(self, account_id: int) -> bool:
        """刪除帳目"""
        result = await self.account_repo.delete(account_id)
        if result:
            await self.db.commit()
            await self.audit_delete(account_id)
        return result

    # ========================================================================
    # Expense CRUD
    # ========================================================================

    async def list_expenses(
        self, params: OperationalExpenseListRequest
    ) -> Tuple[List[OperationalExpenseResponse], int]:
        """列出費用"""
        items, total = await self.expense_repo.list_filtered(params)
        return [OperationalExpenseResponse.model_validate(e) for e in items], total

    async def create_expense(
        self, data: OperationalExpenseCreate, user_id: Optional[int] = None
    ) -> OperationalExpenseResponse:
        """建立費用 (含預算檢查)"""
        # 驗證帳目存在
        account = await self.account_repo.get_by_id(data.account_id)
        if not account:
            raise ValueError(f"帳目 ID {data.account_id} 不存在")
        if account.status != "active":
            raise ValueError(f"帳目 {account.account_code} 非啟用狀態，無法新增費用")

        # 預算檢查
        budget_warning = await self._check_budget(account, data.amount)

        create_data = data.model_dump()
        create_data["created_by"] = user_id

        expense = await self.expense_repo.create(create_data)
        await self.db.commit()

        resp = OperationalExpenseResponse.model_validate(expense)
        if budget_warning:
            logger.warning("預算警告: account=%s, %s", account.account_code, budget_warning)
        return resp

    async def approve_expense(
        self, expense_id: int, approved_by: int
    ) -> Optional[OperationalExpenseResponse]:
        """核准費用 (含自動入帳)"""
        expense = await self.expense_repo.approve(expense_id, approved_by)
        if not expense:
            return None

        # 自動入帳至統一帳本
        try:
            from app.services.finance_ledger_service import FinanceLedgerService
            ledger_service = FinanceLedgerService(self.db)
            account = await self.account_repo.get_by_id(expense.account_id)
            await ledger_service.record_from_operational(
                expense_id=expense.id,
                account_code=account.account_code if account else "",
                amount=expense.amount,
                expense_date=expense.expense_date,
                description=expense.description,
                category=expense.category,
            )
        except Exception:
            logger.exception("營運費用自動入帳失敗: expense_id=%s", expense_id)

        # 審批通知
        try:
            from app.services.notification_service import NotificationService
            account = account or await self.account_repo.get_by_id(expense.account_id)
            acct_name = account.name if account else "營運帳目"
            await NotificationService.create_notification(
                db=self.db,
                notification_type="erp_approval",
                severity="info",
                title=f"費用審核通過 — {acct_name}",
                message=f"{expense.description} ${expense.amount:,.0f} 已核准入帳",
                source_table="operational_expenses",
                source_id=expense.id,
            )
        except Exception as e:
            logger.warning(f"審批通知失敗: {e}")

        await self.db.commit()
        return OperationalExpenseResponse.model_validate(expense)

    async def reject_expense(
        self, expense_id: int, reason: Optional[str] = None
    ) -> Optional[OperationalExpenseResponse]:
        """駁回費用"""
        expense = await self.expense_repo.reject(expense_id, reason)
        if not expense:
            return None
        await self.db.commit()
        return OperationalExpenseResponse.model_validate(expense)

    # ========================================================================
    # Stats
    # ========================================================================

    async def get_stats(
        self, fiscal_year: Optional[int] = None
    ) -> OperationalAccountStatsResponse:
        """取得統計數據"""
        raw = await self.account_repo.get_stats(fiscal_year)
        return OperationalAccountStatsResponse(**raw)

    # ========================================================================
    # Internal helpers
    # ========================================================================

    def _to_account_response(self, account: OperationalAccount) -> OperationalAccountResponse:
        """轉換帳目為回應"""
        resp = OperationalAccountResponse.model_validate(account)
        resp.category_label = ACCOUNT_CATEGORIES.get(account.category)
        return resp

    async def _check_budget(
        self, account: OperationalAccount, new_amount: Decimal
    ) -> Optional[str]:
        """預算檢查: >80% 警告, >100% 攔截"""
        if not account.budget_limit or account.budget_limit <= 0:
            return None

        current_spent = await self.account_repo.get_total_spent(account.id)
        projected = current_spent + new_amount
        usage_pct = projected / account.budget_limit * 100

        if usage_pct > BUDGET_BLOCK_PCT:
            raise ValueError(
                f"帳目 {account.account_code} 預算已超支: "
                f"累計 {projected:,.0f} / 預算 {account.budget_limit:,.0f} "
                f"({usage_pct:.1f}%)"
            )

        if usage_pct > BUDGET_WARNING_PCT:
            return (
                f"帳目 {account.account_code} 預算使用率 {usage_pct:.1f}%，"
                f"累計 {projected:,.0f} / 預算 {account.budget_limit:,.0f}"
            )

        return None

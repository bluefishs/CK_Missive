"""ERP 請款服務

Version: 2.0.0
- v2.0.0: 收款入帳改為同步 (直接呼叫 ledger_service)，保留 EventBus 通知
- v1.3.0: 收款確認改用 EventBus 解耦 (billing_paid → 帳本入帳)
- v1.2.0: create/delete 改用 Repository 方法 (合規修正)
- v1.1.0: Phase 5-6 收款確認自動寫入 Ledger
"""
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPBilling
from app.repositories.erp import ERPBillingRepository, ERPQuotationRepository
from app.schemas.erp import ERPBillingCreate, ERPBillingUpdate, ERPBillingResponse
from .finance_ledger import FinanceLedgerService
from app.services.audit_mixin import AuditableServiceMixin

logger = logging.getLogger(__name__)


class ERPBillingService(AuditableServiceMixin):
    """請款管理服務"""

    AUDIT_TABLE = "erp_billings"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ERPBillingRepository(db)
        self._quotation_repo = ERPQuotationRepository(db)
        self.ledger_service = FinanceLedgerService(db)

    async def create(self, data: ERPBillingCreate) -> ERPBillingResponse:
        """建立請款 (ADR-0013 Phase 2: 自動生成 billing_code + 併發 retry)"""
        from datetime import datetime
        from app.services.contract import CaseCodeService
        from app.services.coding_helpers import retry_on_code_conflict

        async def _create_op() -> ERPBilling:
            dump = data.model_dump()
            if not dump.get("billing_code"):
                code_svc = CaseCodeService(self.db)
                dump["billing_code"] = await code_svc.generate_billing_code(
                    year=datetime.now().year
                )
            # 2026-08-17：**必須 auto_commit=False**。
            # 這裡跑在 `retry_on_code_conflict` 的 SAVEPOINT 內，
            # 而 `BaseRepository.create` 預設 `auto_commit=True` 會直接 commit
            # → 外層交易被關掉 → `sp.commit()` 拋
            # `ResourceClosedError: This transaction is closed`
            # → 使用者看到「新增紀錄失敗」（owner 2026-08-17 於
            # /erp/quotations/152/accounts/receivable/create 回報）。
            #
            # 對照組：`asset_service` 用的 `create_asset` 只 flush、
            # 由外層自己 commit —— 那才是 savepoint 內該有的寫法。
            billing = await self.repo.create(dump, auto_commit=False)
            await self.audit_create(billing.id, dump)
            return billing

        billing = await retry_on_code_conflict(
            self.db, _create_op, unique_field="billing_code"
        )
        # savepoint commit 只是釋放 SAVEPOINT，**外層交易仍未落地** ——
        # 少了這一行會變成「不報錯但資料沒存進去」，比原本的錯誤更糟
        # （使用者以為成功了）。asset_service 的寫法就是這樣：
        # retry_on_code_conflict 之後自己 commit。
        await self.db.commit()
        return ERPBillingResponse.model_validate(billing)

    async def get_by_quotation(self, quotation_id: int) -> List[ERPBillingResponse]:
        """取得報價單所有請款"""
        items = await self.repo.get_by_quotation_id(quotation_id)
        return [ERPBillingResponse.model_validate(b) for b in items]

    async def update(self, billing_id: int, data: ERPBillingUpdate) -> Optional[ERPBillingResponse]:
        """更新請款 (含收款狀態) — 收款確認時自動入帳"""
        billing = await self.repo.get_by_id(billing_id)
        if not billing:
            return None

        old_status = billing.payment_status
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(billing, key, value)

        # 2026-08-16：「已收款」必須有金額。
        #
        # 入帳條件本來就要求 `billing.payment_amount`，但**存檔時沒有擋** ——
        # 於是可以存下「狀態說已付、金額是空的」這個矛盾狀態，
        # 而它不會報錯、不會入帳，只是安靜地讓帳本少一筆。
        # 實測當天有 2 筆（BL_2026_049/050）正是如此。
        #
        # 擋在 service 而不是 schema：金額與狀態可能分兩次請求送，
        # schema 只看得到單次 payload，看不到最終狀態。
        if billing.payment_status == "paid" and not billing.payment_amount:
            raise ValueError(
                "標記為「已收款」時必須填寫收款金額 —— "
                "沒有金額就無法入帳，帳本會少這一筆。"
                "若尚未收到款，請維持「待收款」。"
            )

        await self.db.flush()
        await self.db.refresh(billing)

        # v2.0.0: 收款確認 → 同步帳本入帳 (冪等：已有 entry 則跳過)
        new_status = billing.payment_status
        if new_status == "paid" and old_status != "paid" and billing.payment_amount:
            existing = await self.ledger_service.find_by_source("erp_billing", billing.id)
            if existing:
                logger.warning("帳本已有 erp_billing/%d 的 entry，跳過重複入帳", billing.id)
            else:
                case_code = await self._get_case_code(billing.erp_quotation_id)
                await self.ledger_service.record_from_billing(
                    billing_id=billing.id,
                    case_code=case_code,
                    payment_amount=billing.payment_amount,
                    payment_date=billing.payment_date,
                    billing_period=billing.billing_period,
                )
                logger.info(
                    "AR 同步入帳: 請款 #%d, 金額 %s, 案號 %s",
                    billing.id, billing.payment_amount, case_code,
                )

        await self.db.commit()
        await self.audit_update(billing_id, update_data)

        # EventBus 通知 (非關鍵路徑 — 用於通知推播，失敗不影響帳本)
        if new_status == "paid" and old_status != "paid":
            try:
                from app.core.event_bus import EventBus
                from app.core.domain_events import billing_paid
                bus = EventBus.get_instance()
                await bus.publish(billing_paid(
                    billing_id=billing.id,
                    amount=float(billing.payment_amount or 0),
                    case_code=await self._get_case_code(billing.erp_quotation_id),
                    payment_date=str(billing.payment_date) if billing.payment_date else None,
                    billing_period=billing.billing_period,
                ))
            except Exception as e:
                logger.debug("billing_paid event publish skipped: %s", e)

        return ERPBillingResponse.model_validate(billing)

    async def delete(self, billing_id: int) -> bool:
        """刪除請款 — 同步清理對應帳本 entries"""
        # 先清理帳本孤兒
        await self.ledger_service.delete_by_source("erp_billing", billing_id)
        result = await self.repo.delete(billing_id)
        if result:
            await self.audit_delete(billing_id)
        return result

    async def _get_case_code(self, quotation_id: int) -> str:
        """從報價單取得 case_code"""
        quotation = await self._quotation_repo.get_by_id(quotation_id)
        return quotation.case_code if quotation and quotation.case_code else "一般營運"

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Tuple
from decimal import Decimal

from app.extended.models.invoice import ExpenseInvoice, ExpenseInvoiceItem
from app.schemas.erp.expense import (
    ExpenseInvoiceCreate, ExpenseInvoiceUpdate, ExpenseInvoiceQuery,
    APPROVAL_THRESHOLD, APPROVAL_TRANSITIONS,
    BUDGET_WARNING_PCT, BUDGET_BLOCK_PCT,
)
from app.repositories.erp.expense_invoice_repository import ExpenseInvoiceRepository
from app.services.finance_ledger_service import FinanceLedgerService

import logging

logger = logging.getLogger(__name__)

class ExpenseInvoiceService:
    """費用報銷發票業務服務層"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ExpenseInvoiceRepository(db)
        self.ledger_service = FinanceLedgerService(db)

    async def create(self, data: ExpenseInvoiceCreate, user_id: Optional[int] = None) -> ExpenseInvoice:
        """建立報銷發票 (含重複檢查 + case_code 驗證)，狀態為 pending 待審核

        帳本記錄在 approve() 審核通過時才寫入，避免雙重記帳。
        """
        # 0. 驗證 case_code 對應專案存在 (Phase 13-2)
        if data.case_code:
            await self._validate_case_code(data.case_code)

        # 1. 檢查是否有重複發票
        is_duplicate = await self.repo.check_duplicate(data.inv_num)
        if is_duplicate:
            raise ValueError(f"發票號碼 {data.inv_num} 已存在，請確認是否重複報銷。")

        # 1.5 自動由 seller_ban 配對 vendor_id
        vendor_id = await self._resolve_vendor_by_ban(data.seller_ban) if data.seller_ban else None

        # 2. 建立 ExpenseInvoice 主檔 (status=pending，等待審核)
        invoice = ExpenseInvoice(
            inv_num=data.inv_num,
            date=data.date,
            amount=data.amount,
            tax_amount=data.tax_amount,
            buyer_ban=data.buyer_ban,
            seller_ban=data.seller_ban,
            case_code=data.case_code,
            category=data.category,
            source=data.source,
            notes=data.notes,
            user_id=user_id,
            status="pending",
            vendor_id=vendor_id,
            receipt_image_path=getattr(data, "receipt_image_path", None),
            # 多幣別 (Phase 5-4)
            currency=data.currency,
            original_amount=data.original_amount,
            exchange_rate=data.exchange_rate,
        )

        # 3. 建立 Items
        items = []
        if data.items:
            for item_in in data.items:
                items.append(ExpenseInvoiceItem(
                    item_name=item_in.item_name,
                    qty=item_in.qty,
                    unit_price=item_in.unit_price,
                    amount=item_in.amount
                ))

        return await self.repo.create_with_items(invoice, items)

    async def get_by_id(self, invoice_id: int) -> Optional[ExpenseInvoice]:
        """取得發票詳情"""
        return await self.repo.get_by_id(invoice_id)

    async def update(self, invoice_id: int, data: "ExpenseInvoiceUpdate") -> Optional[ExpenseInvoice]:
        """更新發票部分欄位"""
        invoice = await self.repo.get_by_id(invoice_id)
        if not invoice:
            return None
        update_data = data.model_dump(exclude_unset=True) if hasattr(data, 'model_dump') else data
        return await self.repo.update_fields(invoice, update_data)

    async def approve(self, invoice_id: int) -> Optional[ExpenseInvoice]:
        """多層審核推進 — 依金額門檻自動決定下一狀態

        ≤30K TWD: pending → manager_approved → verified (二級)
        >30K TWD: pending → manager_approved → finance_approved → verified (三級)
        僅 verified 狀態觸發帳本入帳。

        預算聯防：即將進入 verified 時檢查專案預算水位
        - >100%: 攔截審核 (需總經理介入)
        - >80%: 警告但放行 (附帶預警訊息)

        Returns:
            invoice: 更新後的 ExpenseInvoice (含 _budget_warning 動態屬性)
        """
        invoice = await self.repo.get_by_id(invoice_id)
        if not invoice:
            return None

        current = invoice.status
        if current in ("verified", "rejected"):
            raise ValueError(f"此發票狀態為「{current}」，不可進行審核操作")

        allowed = APPROVAL_TRANSITIONS.get(current, [])
        if "rejected" in allowed:
            allowed = [s for s in allowed if s != "rejected"]
        if not allowed:
            raise ValueError(f"狀態「{current}」無法進行審核推進")

        next_status = self._determine_next_approval(current, invoice.amount)

        if next_status not in APPROVAL_TRANSITIONS.get(current, []):
            raise ValueError(f"非法狀態流轉: {current} → {next_status}")

        # === 預算聯防控制 ===
        budget_warning: Optional[str] = None
        if next_status == "verified" and invoice.case_code:
            budget_warning = await self._check_budget(invoice.case_code, invoice.amount)

        await self.repo.update_status(invoice, next_status)

        # 僅最終 verified 才寫入帳本
        if next_status == "verified":
            await self.ledger_service.record_from_expense(invoice)

        await self.repo.commit()

        # 將預算警告附加為動態屬性，API 層可讀取
        invoice._budget_warning = budget_warning  # type: ignore[attr-defined]
        return invoice

    async def _resolve_vendor_by_ban(self, seller_ban: str) -> Optional[int]:
        """由賣方統編查找 partner_vendors.id (稅籍號碼 = vendor_code 慣例)"""
        from sqlalchemy import select
        from app.extended.models.core import PartnerVendor
        # vendor_code 通常就是統編
        stmt = select(PartnerVendor.id).where(PartnerVendor.vendor_code == seller_ban).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _validate_case_code(self, case_code: str) -> None:
        """驗證 case_code 對應的專案或報價存在

        檢查順序: ContractProject.project_code → PMCase.case_code → ERPQuotation.case_code
        任一匹配即通過，全部不匹配則拋出 ValueError。
        """
        from sqlalchemy import select, exists
        from app.extended.models.core import ContractProject

        # 1. 檢查 ContractProject
        stmt = select(exists().where(ContractProject.project_code == case_code))
        found = await self.db.scalar(stmt)
        if found:
            return

        # 2. 檢查 PMCase (soft match)
        try:
            from app.extended.models.pm import PMCase
            stmt2 = select(exists().where(PMCase.case_code == case_code))
            found2 = await self.db.scalar(stmt2)
            if found2:
                return
        except ImportError:
            pass

        # 3. 檢查 ERPQuotation
        try:
            from app.extended.models.erp import ERPQuotation
            stmt3 = select(exists().where(ERPQuotation.case_code == case_code))
            found3 = await self.db.scalar(stmt3)
            if found3:
                return
        except ImportError:
            pass

        raise ValueError(f"案號 {case_code} 不存在，請確認後再提交。")

    async def _check_budget(self, case_code: str, invoice_amount: Decimal) -> Optional[str]:
        """預算聯防 — 檢查專案預算水位

        Returns:
            None: 預算充足
            str: 預警訊息 (>80%) 或 raises ValueError (>100%)
        """
        from sqlalchemy import select
        from app.extended.models.erp import ERPQuotation

        # 1. 取得該專案的預算上限 (可能有多張報價單，取最大 budget_limit)
        stmt = (
            select(ERPQuotation.budget_limit)
            .where(ERPQuotation.case_code == case_code)
            .where(ERPQuotation.budget_limit.is_not(None))
            .order_by(ERPQuotation.budget_limit.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        budget_limit = result.scalar_one_or_none()

        if not budget_limit or budget_limit <= 0:
            return None  # 無預算設定，略過檢查

        budget = Decimal(str(budget_limit))
        amount = Decimal(str(invoice_amount)) if not isinstance(invoice_amount, Decimal) else invoice_amount

        # 2. 取得累計支出 (已入帳的 expense 總額)
        balance = await self.ledger_service.get_case_balance(case_code)
        cumulative_expense = Decimal(str(balance.get("expense", 0)))

        # 3. 預測核准後的支出總額
        projected = cumulative_expense + amount
        usage_pct = (projected / budget) * Decimal("100")

        logger.info(
            f"預算檢查 [{case_code}]: 累計支出={cumulative_expense}, "
            f"本筆={amount}, 預算={budget}, 預測使用率={usage_pct:.1f}%"
        )

        # 4. 判定
        if usage_pct > BUDGET_BLOCK_PCT:
            raise ValueError(
                f"預算超限！專案 {case_code} 累計支出將達 {projected:,.0f} 元 "
                f"(預算 {budget:,.0f} 元，使用率 {usage_pct:.1f}%)。"
                f"請聯繫總經理核准後再行操作。"
            )

        if usage_pct > BUDGET_WARNING_PCT:
            return (
                f"⚠️ 預算警告：專案 {case_code} 核准後累計支出將達 {projected:,.0f} 元 "
                f"(預算 {budget:,.0f} 元，使用率 {usage_pct:.1f}%)"
            )

        return None

    def _determine_next_approval(self, current_status: str, amount: Decimal) -> str:
        """根據當前狀態與金額決定下一審核狀態"""
        amount_val = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount
        is_high_value = amount_val > APPROVAL_THRESHOLD

        if current_status == "pending":
            return "manager_approved"
        elif current_status == "pending_receipt":
            return "pending"
        elif current_status == "manager_approved":
            return "finance_approved" if is_high_value else "verified"
        elif current_status == "finance_approved":
            return "verified"
        else:
            raise ValueError(f"狀態「{current_status}」無法推進審核")

    async def reject(self, invoice_id: int, reason: Optional[str] = None) -> Optional[ExpenseInvoice]:
        """駁回報銷 — 任何非終態階段皆可駁回"""
        invoice = await self.repo.get_by_id(invoice_id)
        if not invoice:
            return None
        if invoice.status in ("verified", "rejected"):
            raise ValueError(f"此發票狀態為「{invoice.status}」，不可駁回")

        allowed = APPROVAL_TRANSITIONS.get(invoice.status, [])
        if "rejected" not in allowed:
            raise ValueError(f"狀態「{invoice.status}」不允許駁回")

        notes_append = f"[駁回] {reason}" if reason else None
        return await self.repo.update_status(invoice, "rejected", notes_append=notes_append)

    def parse_qr_data(self, raw_qr: str) -> dict:
        """解析台灣電子發票 QR Code 資料

        QR 格式 (前 77 字元):
        - [0:10]  發票號碼 (2 英文 + 8 數字)
        - [10:17] 民國日期 (YYYMMDD)
        - [17:25] 隨機碼
        - [25:33] 買方統編 (8 碼)
        - [33:41] 賣方統編 (8 碼)
        - [41:49] 金額 hex (8 碼, 16 進位)
        """
        if len(raw_qr) < 49:
            raise ValueError("QR 資料格式不正確，長度不足")

        inv_num = raw_qr[0:10]
        date_str = raw_qr[10:17]  # 民國年 YYYMMDD
        buyer_ban = raw_qr[25:33]
        seller_ban = raw_qr[33:41]
        amount_hex = raw_qr[41:49]

        # 民國年轉西元
        from datetime import date as date_type
        roc_year = int(date_str[0:3])
        month = int(date_str[3:5])
        day = int(date_str[5:7])
        inv_date = date_type(roc_year + 1911, month, day)

        # 金額 hex → Decimal
        amount = Decimal(str(int(amount_hex, 16)))

        return {
            "inv_num": inv_num,
            "date": inv_date,
            "buyer_ban": buyer_ban,
            "seller_ban": seller_ban,
            "amount": amount,
            "source": "qr_scan",
            "raw_qr_data": raw_qr,
        }

    async def create_from_qr(
        self, raw_qr: str, case_code: Optional[str] = None,
        category: Optional[str] = None, user_id: Optional[int] = None,
    ) -> ExpenseInvoice:
        """從 QR Code 建立報銷發票"""
        parsed = self.parse_qr_data(raw_qr)

        data = ExpenseInvoiceCreate(
            inv_num=parsed["inv_num"],
            date=parsed["date"],
            amount=parsed["amount"],
            buyer_ban=parsed["buyer_ban"],
            seller_ban=parsed["seller_ban"],
            case_code=case_code,
            category=category,
            source="qr_scan",
        )
        return await self.create(data, user_id=user_id)

    async def attach_receipt(self, invoice_id: int, receipt_path: str) -> Optional[ExpenseInvoice]:
        """附加收據影像至發票 (不變更狀態)"""
        invoice = await self.repo.get_by_id(invoice_id)
        if not invoice:
            return None
        return await self.repo.update_fields(invoice, {"receipt_image_path": receipt_path})

    async def list_by_case(self, case_code: str, skip=0, limit=20) -> Tuple[List[ExpenseInvoice], int]:
        return await self.repo.find_by_case_code(case_code, skip, limit)

    async def query(self, params: ExpenseInvoiceQuery) -> Tuple[List[ExpenseInvoice], int]:
        return await self.repo.query(params)

    @staticmethod
    def get_approval_info(invoice: ExpenseInvoice) -> dict:
        """計算發票的審核層級資訊 (用於 Response 填充)"""
        status = invoice.status
        amount = Decimal(str(invoice.amount)) if invoice.amount else Decimal("0")
        is_high_value = amount > APPROVAL_THRESHOLD

        level_map = {
            "pending": "pending",
            "pending_receipt": "pending",
            "manager_approved": "manager",
            "finance_approved": "finance",
            "verified": "final",
            "rejected": None,
        }

        next_map: dict[str, Optional[str]] = {
            "pending": "manager",
            "pending_receipt": "manager",
            "manager_approved": "finance" if is_high_value else "final",
            "finance_approved": "final",
            "verified": None,
            "rejected": None,
        }

        return {
            "approval_level": level_map.get(status),
            "next_approval": next_map.get(status),
        }

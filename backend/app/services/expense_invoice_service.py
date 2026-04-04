"""
費用報銷發票服務 — CRUD + 組合層

審核工作流委派至 ExpenseApprovalService，
匯入/匯出委派至 ExpenseImportService。
本檔案僅保留 CRUD、查詢、以及向後相容的委派方法。

Version: 2.0.0 — refactored from monolithic 625L
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Tuple
from decimal import Decimal
from datetime import date, datetime as dt

from app.extended.models.invoice import ExpenseInvoice, ExpenseInvoiceItem
from app.schemas.erp.expense import ExpenseInvoiceCreate, ExpenseInvoiceUpdate, ExpenseInvoiceQuery
from app.repositories.erp.expense_invoice_repository import ExpenseInvoiceRepository
from app.services.finance_ledger_service import FinanceLedgerService
from app.services.expense_approval_service import ExpenseApprovalService
from app.services.expense_import_service import ExpenseImportService
from app.services.audit_mixin import AuditableServiceMixin

import logging

logger = logging.getLogger(__name__)


class ExpenseInvoiceService(AuditableServiceMixin):
    """費用報銷發票業務服務層 (Facade)"""

    AUDIT_TABLE = "expense_invoices"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ExpenseInvoiceRepository(db)
        self.ledger_service = FinanceLedgerService(db)
        self._approval = ExpenseApprovalService(db)
        self._import = ExpenseImportService(db)

    # ========================================================================
    # CRUD
    # ========================================================================

    async def create(self, data: ExpenseInvoiceCreate, user_id: Optional[int] = None) -> ExpenseInvoice:
        """建立報銷發票 (含重複檢查 + case_code 驗證)，狀態為 pending 待審核"""
        # 0. 驗證 case_code
        if data.case_code:
            await self._validate_case_code(data.case_code)

        # 1. 檢查是否有重複發票
        is_duplicate = await self.repo.check_duplicate(data.inv_num)
        if is_duplicate:
            raise ValueError(f"發票號碼 {data.inv_num} 已存在，請確認是否重複報銷。")

        # 1.5 自動由 seller_ban 配對 vendor_id
        vendor_id = await self._import._resolve_vendor_by_ban(data.seller_ban) if data.seller_ban else None

        # 2. 建立 ExpenseInvoice 主檔
        invoice = ExpenseInvoice(
            inv_num=data.inv_num,
            date=data.date,
            amount=Decimal(str(data.amount)) if data.amount else Decimal("0"),
            tax_amount=Decimal(str(data.tax_amount)) if data.tax_amount else Decimal("0"),
            buyer_ban=data.buyer_ban,
            seller_ban=data.seller_ban,
            case_code=data.case_code,
            category=data.category or "其他",
            notes=data.notes,
            currency=data.currency or "TWD",
            source=data.source or "manual",
            receipt_image_path=data.receipt_image_path,
            status="pending",
            user_id=user_id,
            vendor_id=vendor_id,
        )

        # attribution_type
        if hasattr(data, "attribution_type") and data.attribution_type:
            invoice.attribution_type = data.attribution_type

        self.db.add(invoice)

        # 3. 建立明細 (如有)
        if data.items:
            for item_data in data.items:
                item = ExpenseInvoiceItem(
                    description=item_data.description,
                    quantity=item_data.quantity or 1,
                    unit_price=Decimal(str(item_data.unit_price)) if item_data.unit_price else Decimal("0"),
                    amount=Decimal(str(item_data.amount)) if item_data.amount else Decimal("0"),
                )
                invoice.items.append(item)

        await self.db.commit()
        await self.db.refresh(invoice)
        await self.audit_create(invoice.id, data.model_dump() if hasattr(data, 'model_dump') else {})
        return invoice

    async def get_by_id(self, invoice_id: int) -> Optional[ExpenseInvoice]:
        """取得發票詳情"""
        return await self.repo.get_by_id(invoice_id)

    async def update(self, invoice_id: int, data: "ExpenseInvoiceUpdate") -> Optional[ExpenseInvoice]:
        """更新發票部分欄位"""
        invoice = await self.repo.get_by_id(invoice_id)
        if not invoice:
            return None
        update_data = data.model_dump(exclude_unset=True) if hasattr(data, 'model_dump') else data
        result = await self.repo.update_fields(invoice, update_data)
        if result:
            await self.audit_update(invoice_id, update_data)
        return result

    async def attach_receipt(self, invoice_id: int, receipt_path: str) -> Optional[ExpenseInvoice]:
        """附加收據影像至發票"""
        invoice = await self.repo.get_by_id(invoice_id)
        if not invoice:
            return None
        return await self.repo.update_fields(invoice, {"receipt_image_path": receipt_path})

    async def list_by_case(self, case_code: str, skip=0, limit=20) -> Tuple[List[ExpenseInvoice], int]:
        return await self.repo.find_by_case_code(case_code, skip, limit)

    async def query(self, params: ExpenseInvoiceQuery) -> Tuple[List[ExpenseInvoice], int]:
        return await self.repo.query(params)

    async def grouped_summary(self, attribution_type: Optional[str] = None) -> dict:
        """費用按歸屬分組彙總 — 專案/營運/未歸屬各自統計"""
        from sqlalchemy import select, func
        from app.extended.models.invoice import ExpenseInvoice as EI

        stmt = (
            select(
                EI.attribution_type, EI.case_code, EI.category,
                func.count(EI.id).label("count"),
                func.sum(EI.amount).label("total_amount"),
            )
            .group_by(EI.attribution_type, EI.case_code, EI.category)
            .order_by(func.sum(EI.amount).desc())
        )
        if attribution_type:
            stmt = stmt.where(EI.attribution_type == attribution_type)

        result = await self.db.execute(stmt)
        rows = result.all()

        group_map: dict = {}
        for row in rows:
            attr = row.attribution_type or "none"
            cc = (row.case_code or "__operational__") if attr == "operational" else (row.case_code or "__none__")
            key = f"{attr}:{cc}"

            if key not in group_map:
                group_map[key] = {
                    "group_key": key,
                    "group_label": cc if cc not in ("__operational__", "__none__") else ("營運支出" if attr == "operational" else "未歸屬"),
                    "attribution_type": attr,
                    "case_code": row.case_code,
                    "total_amount": 0,
                    "count": 0,
                    "_cat_map": {},
                }
            g = group_map[key]
            amt = float(row.total_amount or 0)
            g["total_amount"] += amt
            g["count"] += row.count
            cat = row.category or "其他"
            if cat not in g["_cat_map"]:
                g["_cat_map"][cat] = {"category": cat, "count": 0, "amount": 0}
            g["_cat_map"][cat]["count"] += row.count
            g["_cat_map"][cat]["amount"] += amt

        for g in group_map.values():
            g["categories"] = sorted(g.pop("_cat_map").values(), key=lambda c: c["amount"], reverse=True)

        # Enrich with project_code + case_name
        case_codes = [g["case_code"] for g in group_map.values() if g["case_code"]]
        if case_codes:
            from app.extended.models.pm import PMCase
            code_stmt = select(PMCase.case_code, PMCase.project_code, PMCase.case_name).where(
                PMCase.case_code.in_(case_codes)
            )
            code_result = await self.db.execute(code_stmt)
            code_map = {r.case_code: r for r in code_result.all()}
            for g in group_map.values():
                info = code_map.get(g["case_code"])
                if info:
                    g["project_code"] = info.project_code
                    g["group_label"] = f"{info.project_code or info.case_code} {info.case_name or ''}"

        groups = sorted(group_map.values(), key=lambda x: x["total_amount"], reverse=True)
        return {
            "groups": groups,
            "total_count": sum(g["count"] for g in groups),
            "total_amount": sum(g["total_amount"] for g in groups),
        }

    # ========================================================================
    # 委派：審核工作流
    # ========================================================================

    async def approve(self, invoice_id: int) -> Optional[ExpenseInvoice]:
        return await self._approval.approve(invoice_id)

    async def reject(self, invoice_id: int, reason: Optional[str] = None) -> Optional[ExpenseInvoice]:
        return await self._approval.reject(invoice_id, reason)

    @staticmethod
    def get_approval_info(invoice: ExpenseInvoice) -> dict:
        return ExpenseApprovalService.get_approval_info(invoice)

    # ========================================================================
    # 委派：匯入/匯出/QR
    # ========================================================================

    def parse_qr_data(self, raw_qr: str) -> dict:
        return self._import.parse_qr_data(raw_qr)

    async def create_from_qr(
        self, raw_qr: str, case_code: Optional[str] = None,
        category: Optional[str] = None, user_id: Optional[int] = None,
    ) -> ExpenseInvoice:
        """從 QR Code 建立報銷發票"""
        parsed = self._import.parse_qr_data(raw_qr)
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

    async def auto_link_einvoice(self, expense_id: int) -> Optional[dict]:
        return await self._import.auto_link_einvoice(expense_id)

    def generate_import_template(self) -> bytes:
        return self._import.generate_import_template()

    async def import_from_excel(self, file_bytes: bytes, user_id: Optional[int] = None) -> dict:
        return await self._import.import_from_excel(file_bytes, user_id)

    # ========================================================================
    # 內部輔助
    # ========================================================================

    async def _validate_case_code(self, case_code: str) -> None:
        """驗證 case_code 對應的專案或報價存在"""
        from app.repositories import ProjectRepository

        project_repo = ProjectRepository(self.db)
        if await project_repo.exists_by_project_code(case_code):
            return

        try:
            from sqlalchemy import select, exists
            from app.extended.models.pm import PMCase
            stmt2 = select(exists().where(PMCase.case_code == case_code))
            found2 = await self.db.scalar(stmt2)
            if found2:
                return
        except ImportError:
            pass

        try:
            from sqlalchemy import select, exists
            from app.extended.models.erp import ERPQuotation
            stmt3 = select(exists().where(ERPQuotation.case_code == case_code))
            found3 = await self.db.scalar(stmt3)
            if found3:
                return
        except ImportError:
            pass

        raise ValueError(f"案號 {case_code} 不存在，請確認後再提交。")

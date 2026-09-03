"""ERP 發票 Repository"""
import logging
from decimal import Decimal
from typing import Optional, List, Dict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPInvoice
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ERPInvoiceRepository(BaseRepository[ERPInvoice]):
    """發票資料存取"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, ERPInvoice)

    async def get_by_quotation_id(self, quotation_id: int) -> List[ERPInvoice]:
        """取得報價單所有發票"""
        query = (
            select(ERPInvoice)
            .where(ERPInvoice.erp_quotation_id == quotation_id)
            .order_by(ERPInvoice.invoice_date.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_invoice_number(self, invoice_number: str) -> Optional[ERPInvoice]:
        """依發票號碼查詢"""
        return await self.find_one_by(invoice_number=invoice_number)

    async def get_invoice_summary(
        self, invoice_type: Optional[str] = None, year: Optional[int] = None,
        skip: int = 0, limit: int = 50,
    ) -> tuple:
        """跨案件發票彙總 — 銷項/進項分類查詢"""
        from app.extended.models.erp import ERPQuotation

        query = (
            select(
                ERPInvoice,
                ERPQuotation.case_code,
                ERPQuotation.case_name,
                ERPQuotation.project_code,
            )
            .join(ERPQuotation, ERPInvoice.erp_quotation_id == ERPQuotation.id)
        )

        if invoice_type:
            query = query.where(ERPInvoice.invoice_type == invoice_type)
        if year:
            # 2026-09-04 金流複查：發票彙總是稅務用途，「年度」＝發票開立年度（invoice_date），不是報價單案件年度。
            # 此前用 ERPQuotation.year ⇒ 2026 年只算到 54 張 204 萬，而 2026 年實際開了 118 張 1,005 萬（FIELD_SEMANTICS）。
            query = query.where(func.extract('year', ERPInvoice.invoice_date) == year)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # 2026-08-29：分頁**前**的全量金額合計 —— 統計卡的分母。
        # 前端原本 reduce 當頁 items（limit 20）而發票實有 48 筆 ⇒
        # 三張卡都只算了 20/48，且不會報錯（同 client-accounts／ledger 家族）。
        sum_q = select(
            ERPInvoice.invoice_type,
            func.coalesce(func.sum(ERPInvoice.amount), 0),
        ).join(ERPQuotation, ERPInvoice.erp_quotation_id == ERPQuotation.id)
        if invoice_type:
            sum_q = sum_q.where(ERPInvoice.invoice_type == invoice_type)
        if year:
            sum_q = sum_q.where(func.extract('year', ERPInvoice.invoice_date) == year)
        sums = {"sales": Decimal("0"), "purchase": Decimal("0")}
        for itype, amt in (await self.db.execute(sum_q.group_by(ERPInvoice.invoice_type))).all():
            if itype in sums:
                sums[itype] = amt or Decimal("0")
        totals = {
            "sales": str(sums["sales"]),
            "purchase": str(sums["purchase"]),
            "net": str(sums["sales"] - sums["purchase"]),
        }

        # Results
        query = query.order_by(ERPInvoice.invoice_date.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        rows = result.all()

        items = []
        for inv, case_code, case_name, project_code in rows:
            items.append({
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_date": str(inv.invoice_date) if inv.invoice_date else None,
                "amount": str(inv.amount),
                "tax_amount": str(inv.tax_amount or 0),
                "invoice_type": inv.invoice_type,
                "status": inv.status,
                "description": inv.description,
                "case_code": case_code,
                "project_code": project_code,
                "case_name": case_name,
                "billing_id": inv.billing_id,
                "erp_quotation_id": inv.erp_quotation_id,
            })

        return items, total, totals

    async def get_counts_by_quotation_ids(
        self, quotation_ids: List[int]
    ) -> Dict[int, int]:
        """批次取得各報價單的發票數量"""
        if not quotation_ids:
            return {}
        query = (
            select(
                ERPInvoice.erp_quotation_id,
                func.count(ERPInvoice.id).label("cnt"),
            )
            .where(ERPInvoice.erp_quotation_id.in_(quotation_ids))
            .group_by(ERPInvoice.erp_quotation_id)
        )
        result = await self.db.execute(query)
        return {row.erp_quotation_id: row.cnt for row in result.all()}

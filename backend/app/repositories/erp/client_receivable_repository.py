"""ERP 委託單位應收 Repository

跨案件應收查詢：PartnerVendor ← PMCase.client_vendor_id → case_code → ERPQuotation → ERPBilling

Version: 1.0.0
Created: 2026-03-30
"""
import logging
from typing import Optional
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPQuotation, ERPBilling
from app.extended.models.pm import PMCase
from app.extended.models.core import PartnerVendor

logger = logging.getLogger(__name__)


class ClientReceivableRepository:
    """委託單位跨案件應收查詢"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_client_summary_list(
        self,
        year: Optional[int] = None,
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple:
        """跨案件委託單位應收彙總列表

        Join path:
          PartnerVendor ← PMCase.client_vendor_id
          → case_code → ERPQuotation → ERPBilling
        """
        # Subquery: billing aggregates per quotation
        billing_agg = (
            select(
                ERPQuotation.case_code,
                ERPQuotation.id.label("quotation_id"),
                func.coalesce(ERPQuotation.total_price, 0).label("contract_amount"),
                func.coalesce(func.sum(ERPBilling.billing_amount), 0).label("total_billed"),
                func.coalesce(func.sum(ERPBilling.payment_amount), 0).label("total_received"),
            )
            .outerjoin(ERPBilling, ERPBilling.erp_quotation_id == ERPQuotation.id)
            .group_by(ERPQuotation.case_code, ERPQuotation.id, ERPQuotation.total_price)
        ).subquery()

        # Main: join PMCase → PartnerVendor, aggregate by client
        query = (
            select(
                PMCase.client_vendor_id.label("vendor_id"),
                PartnerVendor.vendor_name,
                PartnerVendor.vendor_code,
                func.count(func.distinct(PMCase.case_code)).label("case_count"),
                func.coalesce(func.sum(billing_agg.c.contract_amount), 0).label("total_contract"),
                func.coalesce(func.sum(billing_agg.c.total_billed), 0).label("total_billed"),
                func.coalesce(func.sum(billing_agg.c.total_received), 0).label("total_received"),
            )
            .join(PartnerVendor, PMCase.client_vendor_id == PartnerVendor.id)
            .outerjoin(billing_agg, PMCase.case_code == billing_agg.c.case_code)
            .where(
                PMCase.client_vendor_id.isnot(None),
                PartnerVendor.vendor_type == "client",
            )
        )

        if year:
            query = query.where(PMCase.year == year)
        if keyword:
            query = query.where(PartnerVendor.vendor_name.ilike(f"%{keyword}%"))

        # Count: wrap grouped query as subquery
        grouped = query.group_by(
            PMCase.client_vendor_id, PartnerVendor.vendor_name, PartnerVendor.vendor_code
        ).subquery()
        total = await self.db.scalar(select(func.count()).select_from(grouped)) or 0

        # Results
        results_query = query.group_by(
            PMCase.client_vendor_id, PartnerVendor.vendor_name, PartnerVendor.vendor_code
        ).order_by(
            func.sum(billing_agg.c.contract_amount).desc()
        ).offset(skip).limit(limit)

        result = await self.db.execute(results_query)
        rows = result.all()

        items = []
        for r in rows:
            tc = Decimal(str(r.total_contract or 0))
            tb = Decimal(str(r.total_billed or 0))
            tr = Decimal(str(r.total_received or 0))
            items.append({
                "vendor_id": r.vendor_id,
                "vendor_name": r.vendor_name,
                "vendor_code": r.vendor_code,
                "case_count": r.case_count,
                "total_contract": str(tc),
                "total_billed": str(tb),
                "total_received": str(tr),
                "outstanding": str(tb - tr),
            })

        return items, total

    async def get_client_case_detail(
        self, vendor_id: int, year: Optional[int] = None
    ) -> Optional[dict]:
        """單一委託單位跨案件應收明細"""
        # Get vendor info
        vendor = (
            await self.db.execute(
                select(PartnerVendor).where(PartnerVendor.id == vendor_id)
            )
        ).scalars().first()
        if not vendor:
            return None

        # Get all PMCases for this client
        case_query = select(PMCase).where(PMCase.client_vendor_id == vendor_id)
        if year:
            case_query = case_query.where(PMCase.year == year)
        cases = (await self.db.execute(case_query)).scalars().all()

        if not cases:
            return {
                "vendor_id": vendor.id,
                "vendor_name": vendor.vendor_name,
                "vendor_code": vendor.vendor_code,
                "total_contract": "0",
                "total_billed": "0",
                "total_received": "0",
                "outstanding": "0",
                "cases": [],
            }

        case_codes = [c.case_code for c in cases if c.case_code]

        if not case_codes:
            return {
                "vendor_id": vendor.id,
                "vendor_name": vendor.vendor_name,
                "vendor_code": vendor.vendor_code,
                "total_contract": "0",
                "total_billed": "0",
                "total_received": "0",
                "outstanding": "0",
                "cases": [],
            }

        # Get quotations for these case_codes
        quotations = (
            await self.db.execute(
                select(ERPQuotation).where(ERPQuotation.case_code.in_(case_codes))
            )
        ).scalars().all()
        quot_map = {q.case_code: q for q in quotations}

        # Get all billings for these quotations
        quot_ids = [q.id for q in quotations]
        if quot_ids:
            billings = (
                await self.db.execute(
                    select(ERPBilling)
                    .where(ERPBilling.erp_quotation_id.in_(quot_ids))
                    .order_by(ERPBilling.billing_date)
                )
            ).scalars().all()
        else:
            billings = []

        # Group billings by quotation_id
        billing_map: dict[int, list] = {}
        for b in billings:
            billing_map.setdefault(b.erp_quotation_id, []).append(b)

        # Build case-level detail
        case_name_map = {c.case_code: c.case_name for c in cases if c.case_code}
        case_year_map = {c.case_code: c.year for c in cases if c.case_code}

        result_cases = []
        total_contract = Decimal("0")
        total_billed = Decimal("0")
        total_received = Decimal("0")

        for case_code in case_codes:
            quot = quot_map.get(case_code)
            if not quot:
                continue

            contract_amt = Decimal(str(quot.total_price or 0))
            case_billings = billing_map.get(quot.id, [])

            billed = sum(Decimal(str(b.billing_amount or 0)) for b in case_billings)
            received = sum(Decimal(str(b.payment_amount or 0)) for b in case_billings)

            total_contract += contract_amt
            total_billed += billed
            total_received += received

            result_cases.append({
                "erp_quotation_id": quot.id,
                "case_code": case_code,
                "case_name": quot.case_name or case_name_map.get(case_code),
                "year": quot.year or case_year_map.get(case_code),
                "quotation_status": quot.status,
                "contract_amount": str(contract_amt),
                "total_billed": str(billed),
                "total_received": str(received),
                "outstanding": str(billed - received),
                "items": [
                    {
                        "id": b.id,
                        "billing_period": b.billing_period,
                        "billing_date": str(b.billing_date) if b.billing_date else None,
                        "billing_amount": str(Decimal(str(b.billing_amount or 0))),
                        "payment_status": b.payment_status,
                        "payment_date": str(b.payment_date) if b.payment_date else None,
                        "payment_amount": str(Decimal(str(b.payment_amount or 0))),
                        "notes": b.notes,
                    }
                    for b in case_billings
                ],
            })

        return {
            "vendor_id": vendor.id,
            "vendor_name": vendor.vendor_name,
            "vendor_code": vendor.vendor_code,
            "total_contract": str(total_contract),
            "total_billed": str(total_billed),
            "total_received": str(total_received),
            "outstanding": str(total_billed - total_received),
            "cases": result_cases,
        }

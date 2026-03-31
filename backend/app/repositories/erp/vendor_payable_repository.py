"""ERP 廠商應付 Repository"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPVendorPayable, ERPQuotation
from app.extended.models.core import PartnerVendor
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ERPVendorPayableRepository(BaseRepository[ERPVendorPayable]):
    """廠商應付資料存取"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, ERPVendorPayable)

    async def get_by_quotation_id(self, quotation_id: int) -> List[ERPVendorPayable]:
        """取得報價單所有應付"""
        query = (
            select(ERPVendorPayable)
            .where(ERPVendorPayable.erp_quotation_id == quotation_id)
            .order_by(ERPVendorPayable.id.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_total_payable(self, quotation_id: int) -> Decimal:
        """取得報價單累計應付金額"""
        query = (
            select(func.coalesce(func.sum(ERPVendorPayable.payable_amount), 0))
            .where(ERPVendorPayable.erp_quotation_id == quotation_id)
        )
        result = await self.db.execute(query)
        return Decimal(str(result.scalar() or 0))

    async def get_total_paid(self, quotation_id: int) -> Decimal:
        """取得報價單累計已付金額"""
        query = (
            select(func.coalesce(func.sum(ERPVendorPayable.paid_amount), 0))
            .where(
                ERPVendorPayable.erp_quotation_id == quotation_id,
                ERPVendorPayable.paid_amount.isnot(None),
            )
        )
        result = await self.db.execute(query)
        return Decimal(str(result.scalar() or 0))

    async def get_aggregates_batch(
        self, quotation_ids: List[int],
    ) -> Dict[int, Dict[str, Any]]:
        """批次取得多筆報價的應付聚合 (消除 N+1)

        Returns:
            {quotation_id: {"total_payable": Decimal, "total_paid": Decimal}}
        """
        if not quotation_ids:
            return {}

        query = (
            select(
                ERPVendorPayable.erp_quotation_id,
                func.coalesce(func.sum(ERPVendorPayable.payable_amount), 0).label("payable"),
                func.coalesce(func.sum(ERPVendorPayable.paid_amount), 0).label("paid"),
            )
            .where(ERPVendorPayable.erp_quotation_id.in_(quotation_ids))
            .group_by(ERPVendorPayable.erp_quotation_id)
        )
        result = await self.db.execute(query)
        rows = result.all()

        agg: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            agg[row.erp_quotation_id] = {
                "total_payable": Decimal(str(row.payable)),
                "total_paid": Decimal(str(row.paid)),
            }
        return agg

    async def get_vendor_summary_list(
        self,
        vendor_type: str = "subcontractor",
        year: Optional[int] = None,
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """跨案件廠商應付彙總列表

        Uses vendor_name as primary grouping key to handle records
        where vendor_id is NULL (created with vendor_name only).
        """
        query = (
            select(
                ERPVendorPayable.vendor_id,
                ERPVendorPayable.vendor_name,
                func.count(func.distinct(ERPVendorPayable.erp_quotation_id)).label("case_count"),
                func.coalesce(func.sum(ERPVendorPayable.payable_amount), 0).label("total_payable"),
                func.coalesce(func.sum(ERPVendorPayable.paid_amount), 0).label("total_paid"),
            )
            .join(ERPQuotation, ERPVendorPayable.erp_quotation_id == ERPQuotation.id)
        )

        if year:
            query = query.where(ERPQuotation.year == year)
        if keyword:
            query = query.where(ERPVendorPayable.vendor_name.ilike(f"%{keyword}%"))

        # Filter by vendor_type via LEFT JOIN to PartnerVendor
        # Records without vendor_id are included (assumed to be subcontractors)
        if vendor_type:
            query = query.outerjoin(
                PartnerVendor, ERPVendorPayable.vendor_id == PartnerVendor.id
            ).where(
                or_(
                    PartnerVendor.vendor_type == vendor_type,
                    ERPVendorPayable.vendor_id.is_(None),
                )
            )

        group_cols = [ERPVendorPayable.vendor_name, ERPVendorPayable.vendor_id]

        # Count total vendors
        count_subq = query.group_by(*group_cols).subquery()
        count_query = select(func.count()).select_from(count_subq)
        total = await self.db.scalar(count_query) or 0

        # Paginated results
        query = (
            query.group_by(*group_cols)
            .order_by(func.sum(ERPVendorPayable.payable_amount).desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        rows = result.all()

        items = []
        for r in rows:
            tp = Decimal(str(r.total_payable or 0))
            pd = Decimal(str(r.total_paid or 0))
            items.append({
                "vendor_id": r.vendor_id or 0,
                "vendor_name": r.vendor_name,
                "vendor_code": None,  # Not available without vendor_id join
                "case_count": r.case_count,
                "total_payable": str(tp),
                "total_paid": str(pd),
                "outstanding": str(tp - pd),
            })
        return items, total

    async def get_vendor_case_detail(
        self, vendor_id: int, year: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """單一廠商跨案件應付明細"""
        # Get vendor info
        vendor_query = select(PartnerVendor).where(PartnerVendor.id == vendor_id)
        vendor = (await self.db.execute(vendor_query)).scalars().first()
        if not vendor:
            return None

        # Get all payables with quotation info
        query = (
            select(
                ERPVendorPayable,
                ERPQuotation.case_code,
                ERPQuotation.case_name,
                ERPQuotation.year,
                ERPQuotation.total_price,
                ERPQuotation.status.label("quotation_status"),
            )
            .join(ERPQuotation, ERPVendorPayable.erp_quotation_id == ERPQuotation.id)
            .where(ERPVendorPayable.vendor_id == vendor_id)
        )
        if year:
            query = query.where(ERPQuotation.year == year)
        query = query.order_by(ERPQuotation.case_code, ERPVendorPayable.id)

        result = await self.db.execute(query)
        rows = result.all()

        # Group by quotation
        cases_map: Dict[int, Dict[str, Any]] = {}
        for payable, case_code, case_name, q_year, total_price, quotation_status in rows:
            key = payable.erp_quotation_id
            if key not in cases_map:
                cases_map[key] = {
                    "erp_quotation_id": key,
                    "case_code": case_code,
                    "case_name": case_name,
                    "year": q_year,
                    "total_price": str(total_price or 0),
                    "quotation_status": quotation_status,
                    "payable_amount": Decimal("0"),
                    "paid_amount": Decimal("0"),
                    "items": [],
                }
            amt = Decimal(str(payable.payable_amount or 0))
            paid = Decimal(str(payable.paid_amount or 0))
            cases_map[key]["payable_amount"] += amt
            cases_map[key]["paid_amount"] += paid
            cases_map[key]["items"].append({
                "id": payable.id,
                "description": payable.description,
                "payable_amount": str(amt),
                "paid_amount": str(paid),
                "payment_status": payable.payment_status,
                "due_date": str(payable.due_date) if payable.due_date else None,
                "paid_date": str(payable.paid_date) if payable.paid_date else None,
                "invoice_number": payable.invoice_number,
                "notes": payable.notes,
            })

        cases = []
        total_payable = Decimal("0")
        total_paid = Decimal("0")
        for c in cases_map.values():
            c["outstanding"] = c["payable_amount"] - c["paid_amount"]
            if c["payable_amount"] > 0 and c["outstanding"] <= 0:
                c["payment_status"] = "paid"
            elif c["paid_amount"] > 0:
                c["payment_status"] = "partial"
            else:
                c["payment_status"] = "unpaid"
            # Convert Decimal to str for JSON serialization
            c["payable_amount"] = str(c["payable_amount"])
            c["paid_amount"] = str(c["paid_amount"])
            c["outstanding"] = str(c["outstanding"])
            total_payable += Decimal(c["payable_amount"])
            total_paid += Decimal(c["paid_amount"])
            cases.append(c)

        return {
            "vendor_id": vendor.id,
            "vendor_name": vendor.vendor_name,
            "vendor_code": vendor.vendor_code,
            "total_payable": str(total_payable),
            "total_paid": str(total_paid),
            "outstanding": str(total_payable - total_paid),
            "cases": cases,
        }

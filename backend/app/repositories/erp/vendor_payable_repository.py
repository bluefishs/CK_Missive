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
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        """跨案件廠商應付彙總列表

        ⚠️ 2026-08-27 owner：「**標準化 `/vendors` 為源頭**，
        `/erp/vendor-accounts` 對應」＋「如金粟科技工程顧問有限公司**重複**」。

        原本分組鍵是 `(vendor_name, vendor_id)` **兩個欄位一起** ——
        於是同一家廠商只要有些筆有 `vendor_id`、有些是 NULL，
        就會**分成兩列**。金粟就是這樣重複的（一列 id=12、一列 NULL）。

        ⇒ 改為**以 `vendor_id` 為分組主鍵**（`/vendors` 是源頭）；
        沒有 `vendor_id` 的才退回用 `vendor_name`，並且**不會**與
        有 id 的那些混在一起 —— 它們是「廠商檔裡還沒有這家」的另一群。

        ⚠️ 年度：owner「**篩選條件統一為西元年，且預設當年度**」。
        原本 `if year:` ⇒ **不給就不篩，所有年度混在一起算成一個總數**。
        實測 vendor_id=2 有 2025 兩筆已付、2026 四筆未付 ⇒
        「已付 100 萬」與「未付 300 萬」被加成一個數字，
        那正是 owner 說的「管理資訊不清晰」。
        ⇒ `year=None` 時預設**當年度**；要看全部必須明確傳 `year=0`。
        """
        from datetime import date as _date
        if year is None:
            year = _date.today().year        # 預設當年度
        elif year == 0:
            year = None                      # 明確要求「全部年度」
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

        # 以 vendor_id 為源頭；無 id 者才用名稱當鍵，且兩群不相混
        # （`COALESCE` 讓「有 id」永遠走 id，不會因名稱差異再分裂）
        vendor_key = func.coalesce(
            func.concat("id:", ERPVendorPayable.vendor_id),
            func.concat("name:", ERPVendorPayable.vendor_name),
        )
        group_cols = [vendor_key, ERPVendorPayable.vendor_id, ERPVendorPayable.vendor_name]

        # Count total vendors
        count_subq = query.group_by(*group_cols).subquery()
        count_query = select(func.count()).select_from(count_subq)
        total = await self.db.scalar(count_query) or 0

        # 2026-08-29（development-rules §2.6 ①）：統計卡的數字必須是**分頁前的全量**。
        # 前端原本用 `for (const item of items)` 逐筆累加 —— items 是**當頁**，
        # 於是廠商數一旦超過每頁筆數，三張卡就會靜靜少算而不報錯。
        # 現況 16 家、每頁 20 ⇒ 卡片**碰巧是對的**，但那是巧合不是設計；
        # 發票彙總卡就是同一個形狀（48 筆只算 20，少 74%）。
        #
        # 走 count_subq 同一條路 —— 篩選邏輯只有一份，不會有「兩個數字各自演化」。
        totals_row = (await self.db.execute(
            select(
                func.coalesce(func.sum(count_subq.c.total_payable), 0),
                func.coalesce(func.sum(count_subq.c.total_paid), 0),
            ).select_from(count_subq)
        )).first()
        _tp = Decimal(str((totals_row[0] if totals_row else 0) or 0))
        _pd = Decimal(str((totals_row[1] if totals_row else 0) or 0))
        totals = {
            "total_payable": str(_tp),
            "total_paid": str(_pd),
            "outstanding": str(_tp - _pd),
            "vendor_count": total,
        }

        # Paginated results
        query = (
            query.group_by(*group_cols)
            .order_by(func.sum(ERPVendorPayable.payable_amount).desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        rows = result.all()

        # 2026-09-04：以廠商名對主檔一次，補 id／內部代碼／統一編號（此前 vendor_code 一律 None）
        from app.extended.models.core import PartnerVendor as _PV
        _names = [(r.vendor_name or "").strip() for r in rows if r.vendor_name]
        vendor_lookup: dict = {}
        if _names:
            _vr = (await self.db.execute(select(_PV.id, _PV.vendor_name, _PV.vendor_code, _PV.tax_id).where(_PV.vendor_name.in_(_names)))).all()
            vendor_lookup = {(v.vendor_name or "").strip(): {"id": v.id, "vendor_code": v.vendor_code, "tax_id": v.tax_id} for v in _vr}
        items = []
        for r in rows:
            tp = Decimal(str(r.total_payable or 0))
            pd = Decimal(str(r.total_paid or 0))
            _v = vendor_lookup.get((r.vendor_name or "").strip(), {})
            items.append({
                "vendor_id": r.vendor_id or _v.get("id") or 0,
                "vendor_name": r.vendor_name,
                "vendor_code": _v.get("vendor_code"),
                "tax_id": _v.get("tax_id"),  # 2026-09-04：統一編號在 tax_id（此前存 vendor_code）
                "case_count": r.case_count,
                "total_payable": str(tp),
                "total_paid": str(pd),
                "outstanding": str(tp - pd),
            })
        return items, total, totals

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
                ERPQuotation.project_code,
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
        for payable, case_code, case_name, q_year, total_price, quotation_status, project_code in rows:
            key = payable.erp_quotation_id
            if key not in cases_map:
                cases_map[key] = {
                    "erp_quotation_id": key,
                    "case_code": case_code,
                    "project_code": project_code,
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
            "tax_id": vendor.tax_id,
            "total_payable": str(total_payable),
            "total_paid": str(total_paid),
            "outstanding": str(total_payable - total_paid),
            "cases": cases,
        }

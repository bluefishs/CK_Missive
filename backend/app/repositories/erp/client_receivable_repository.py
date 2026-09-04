"""ERP 委託單位應收 Repository

跨案件應收查詢，兩條腿（2026-08-28 owner 複查「工務局僅對應 1 案」後補齊）：

  腿 1（原有）：PartnerVendor ← PMCase.client_vendor_id → case_code → ERPQuotation → ERPBilling
  腿 2（新增）：ContractProject.client_agency（文字）→ case_code → ERPQuotation → ERPBilling
               —— 只取 case_code 沒有任何帶 FK 的 PM 案件的承攬案件，避免與腿 1 重複

為什麼需要腿 2：委託單位主檔是雙軌的 —— PM 案件掛 partner_vendors（FK），
承攬案件掛 government_agencies／文字欄 client_agency。只走腿 1 時，
工務局名下 7 案約 6,021 萬只看得到 1 案（5 案根本沒有 PM 案件）。
兩腿在 Python 端以名稱合併；名稱對不上 vendor 的以 vendor_id=None 列出
（不自動合併主檔 —— owner 2026-08-20 裁示 B8）。

Version: 2.0.0（1.0.0 Created: 2026-03-30）
"""
import logging
from typing import Optional
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPQuotation, ERPBilling
from app.extended.models.pm import PMCase
from app.extended.models.core import PartnerVendor, ContractProject

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
        # Subquery: billing aggregates per quotation (含未成案，以 case_code 聚合)
        billing_agg = (
            select(
                ERPQuotation.case_code,
                ERPQuotation.id.label("quotation_id"),
                ERPQuotation.project_code,
                func.coalesce(ERPQuotation.total_price, 0).label("contract_amount"),
                func.coalesce(func.sum(ERPBilling.billing_amount), 0).label("total_billed"),
                func.coalesce(func.sum(ERPBilling.payment_amount), 0).label("total_received"),
            )
            .outerjoin(ERPBilling, ERPBilling.erp_quotation_id == ERPQuotation.id)
            .where(ERPQuotation.deleted_at.is_(None))
            .group_by(ERPQuotation.case_code, ERPQuotation.id, ERPQuotation.project_code, ERPQuotation.total_price)
        )
        # 2026-09-04 金流複查：年度口徑統一為**報價單年**（FIELD_SEMANTICS）。此前 leg1 用 PM 案年、leg2 用承攬案年，
        # 與損益頁（報價單年）對不上——同一個 2026，委託單位頁少 563 萬（桃園案報價 2026、承攬案 2023）。
        # 年度篩選放在報價單聚合裡，兩腿不再各自用案件年。
        if year:
            billing_agg = billing_agg.where(ERPQuotation.year == year)
        billing_agg = billing_agg.subquery()

        # 2026-08-27 owner：「`/erp/client-accounts` **相同架構問題**」
        # ⇒ 與應付端同一套約定：`year=None` 預設**當年度**，
        #   要看全部年度必須明確傳 `year=0`。
        #
        # 原本 `if year:` ⇒ 不給就不篩，**所有年度混在一起算成一個總數**，
        # 而前端送來的還是**民國年**（115）而這裡比對西元（2026）
        # ⇒ 選了年度永遠是空的、不選則全部混在一起。兩種都不對，
        #   而兩邊各自用自己的紀年，沒有任何一方會報錯。
        from datetime import date as _date
        if year is None:
            year = _date.today().year
        elif year == 0:
            year = None

        # ── 腿 1：PM 案件 FK 路徑 ──
        # 2026-08-28：billing_agg 由 inner 改 outer join —— 有 FK 但還沒建
        # 報價單的案件原本整案消失（連 case_count 都不計），案量靜默蒸發。
        leg1 = (
            select(
                PMCase.client_vendor_id.label("vendor_id"),
                PartnerVendor.vendor_name,
                PartnerVendor.vendor_code,
                PartnerVendor.tax_id,
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
        # year 已在 billing_agg 內套用（報價單年）；沒有該年報價單的案子 total 為 0，由下方 items 過濾
        if keyword:
            leg1 = leg1.where(PartnerVendor.vendor_name.ilike(f"%{keyword}%"))
        leg1 = leg1.group_by(
            PMCase.client_vendor_id, PartnerVendor.vendor_name, PartnerVendor.vendor_code, PartnerVendor.tax_id
        )

        # ── 腿 2：承攬案件文字客戶路徑（case_code 不在腿 1 覆蓋範圍者）──
        covered_case_codes = select(PMCase.case_code).where(
            PMCase.client_vendor_id.isnot(None),
            PMCase.case_code.isnot(None),
        ).scalar_subquery()

        leg2 = (
            select(
                ContractProject.client_agency.label("client_name"),
                func.count(func.distinct(ContractProject.id)).label("case_count"),
                func.coalesce(func.sum(billing_agg.c.contract_amount), 0).label("total_contract"),
                func.coalesce(func.sum(billing_agg.c.total_billed), 0).label("total_billed"),
                func.coalesce(func.sum(billing_agg.c.total_received), 0).label("total_received"),
            )
            .outerjoin(billing_agg, ContractProject.case_code == billing_agg.c.case_code)
            .where(
                ContractProject.client_agency.isnot(None),
                ContractProject.client_agency != "",
                ContractProject.case_code.isnot(None),
                ~ContractProject.case_code.in_(covered_case_codes),
            )
            .group_by(ContractProject.client_agency)
        )
        if keyword:
            leg2 = leg2.where(ContractProject.client_agency.ilike(f"%{keyword}%"))

        leg1_rows = (await self.db.execute(leg1)).all()
        leg2_rows = (await self.db.execute(leg2)).all()

        # ── Python 端以名稱合併（不動主檔，只合併呈現）──
        items = []
        by_name: dict[str, dict] = {}
        for r in leg1_rows:
            row = {
                "vendor_id": r.vendor_id,
                "vendor_name": r.vendor_name,
                "vendor_code": r.vendor_code,
                "tax_id": r.tax_id,
                "case_count": int(r.case_count or 0),
                "_tc": Decimal(str(r.total_contract or 0)),
                "_tb": Decimal(str(r.total_billed or 0)),
                "_tr": Decimal(str(r.total_received or 0)),
            }
            items.append(row)
            by_name[(r.vendor_name or "").strip()] = row

        # 2026-09-04 owner「嘉義縣竹崎地政事務所無法點擊檢視細項」：leg2 只有名字，此前名稱對不上 leg1 就 vendor_id=None
        # ⇒ 沒有明細頁。改成拿名字去委託單位主檔對一次（主檔已補齊承攬案的委託單位名），對到就給 vendor_id。
        leg2_names = [(r.client_name or "").strip() for r in leg2_rows]
        name_to_vendor: dict[str, tuple] = {}
        if leg2_names:
            vrows = (await self.db.execute(
                select(PartnerVendor.id, PartnerVendor.vendor_name, PartnerVendor.vendor_code, PartnerVendor.tax_id)
                .where(func.btrim(PartnerVendor.vendor_name).in_(leg2_names))
            )).all()
            name_to_vendor = {(v.vendor_name or "").strip(): (v.id, v.vendor_code, v.tax_id) for v in vrows}
        for r in leg2_rows:
            name = (r.client_name or "").strip()
            existing = by_name.get(name)
            if existing is not None:
                existing["case_count"] += int(r.case_count or 0)
                existing["_tc"] += Decimal(str(r.total_contract or 0))
                existing["_tb"] += Decimal(str(r.total_billed or 0))
                existing["_tr"] += Decimal(str(r.total_received or 0))
            else:
                # 名稱對不上任何 partner_vendor —— 誠實列出（vendor_id=None），
                # 不自動建檔、不模糊比對（owner B8：重複判定屬人為填報要修正）
                vid, vcode, vtax = name_to_vendor.get(name, (None, None, None))
                items.append({
                    "vendor_id": vid,
                    "vendor_name": name,
                    "vendor_code": vcode,
                    "tax_id": vtax,
                    "case_count": int(r.case_count or 0),
                    "_tc": Decimal(str(r.total_contract or 0)),
                    "_tb": Decimal(str(r.total_billed or 0)),
                    "_tr": Decimal(str(r.total_received or 0)),
                })

        items.sort(key=lambda x: x["_tc"], reverse=True)
        total = len(items)

        # 2026-08-29（CK_Website 指出的計時炸彈）：統計卡若由前端加總
        # 「取回的那一頁」，資料超過 limit 時會**靜默少算而不報錯**。
        # 全體合計在分頁**之前**算好、由後端一次給 —— 卡的數字與分頁無關。
        totals = {
            "total_contract": str(sum((r["_tc"] for r in items), Decimal("0"))),
            "total_billed": str(sum((r["_tb"] for r in items), Decimal("0"))),
            "total_received": str(sum((r["_tr"] for r in items), Decimal("0"))),
            "outstanding": str(sum((r["_tb"] - r["_tr"] for r in items), Decimal("0"))),
        }

        page = items[skip: skip + limit]
        out = []
        for row in page:
            tc, tb, tr = row.pop("_tc"), row.pop("_tb"), row.pop("_tr")
            out.append({
                **row,
                "total_contract": str(tc),
                "total_billed": str(tb),
                "total_received": str(tr),
                "outstanding": str(tb - tr),
            })
        return out, total, totals

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

        case_codes = [c.case_code for c in cases if c.case_code]

        # ── 腿 2（2026-08-28）：名下只存在於承攬案件的 case ──
        # 與 get_client_summary_list 同一套判準；不加這一段的話，
        # 列表說 6 案、點進明細只剩 1 案 —— 兩層說法不同。
        covered_case_codes = select(PMCase.case_code).where(
            PMCase.client_vendor_id.isnot(None),
            PMCase.case_code.isnot(None),
        ).scalar_subquery()
        cp_query = select(ContractProject).where(
            ContractProject.client_agency == vendor.vendor_name,
            ContractProject.case_code.isnot(None),
            ~ContractProject.case_code.in_(covered_case_codes),
        )
        if year:
            cp_query = cp_query.where(ContractProject.year == year)
        contract_only = (await self.db.execute(cp_query)).scalars().all()

        cp_name_map = {cp.case_code: cp.project_name for cp in contract_only}
        cp_year_map = {cp.case_code: cp.year for cp in contract_only}
        case_codes += [cp.case_code for cp in contract_only]

        if not case_codes:
            return {
                "vendor_id": vendor.id,
                "vendor_name": vendor.vendor_name,
                "vendor_code": vendor.vendor_code,
            "tax_id": vendor.tax_id,
                "total_contract": "0",
                "total_billed": "0",
                "total_received": "0",
                "outstanding": "0",
                "cases": [],
            }

        # Get quotations for these case_codes (含未成案，以 case_code 為準)
        quotations = (
            await self.db.execute(
                select(ERPQuotation).where(
                    ERPQuotation.case_code.in_(case_codes),
                )
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
        case_name_map.update(cp_name_map)
        case_year_map = {c.case_code: c.year for c in cases if c.case_code}
        case_year_map.update(cp_year_map)

        result_cases = []
        total_contract = Decimal("0")
        total_billed = Decimal("0")
        total_received = Decimal("0")

        for case_code in case_codes:
            quot = quot_map.get(case_code)
            if not quot:
                # 2026-08-28：還沒建報價單的案不再整案消失 —— 列出零額列，
                # 讓「案存在但沒有報價單」與「案不存在」在畫面上分得開
                result_cases.append({
                    "erp_quotation_id": None,
                    "case_code": case_code,
                    "project_code": None,
                    "case_name": case_name_map.get(case_code),
                    "year": case_year_map.get(case_code),
                    "quotation_status": None,
                    "contract_amount": "0",
                    "total_billed": "0",
                    "total_received": "0",
                    "outstanding": "0",
                    "items": [],
                })
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
                "project_code": quot.project_code,
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

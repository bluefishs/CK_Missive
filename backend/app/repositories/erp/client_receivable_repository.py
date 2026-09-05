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

from sqlalchemy import select, func, or_, case as sa_case
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
        # 2026-09-05：金額＝承攬金額（議價→契約→報價總價，FIELD_SEMANTICS）。此前是 total_price（報價總價），
        # 卡片卻標「承攬金額（含稅）」⇒ 與 /erp/quotations 同名數字差 377 萬。承攬案主檔的兩個金額要 JOIN 才拿得到。
        awarded_expr = func.coalesce(
            func.nullif(ContractProject.winning_amount, 0),
            func.nullif(ContractProject.contract_amount, 0),
            ERPQuotation.total_price, 0,
        )
        billing_agg = (
            select(
                ERPQuotation.case_code,
                ERPQuotation.id.label("quotation_id"),
                ERPQuotation.project_code,
                awarded_expr.label("contract_amount"),
                func.coalesce(func.sum(ERPBilling.billing_amount), 0).label("total_billed"),
                func.coalesce(func.sum(ERPBilling.payment_amount), 0).label("total_received"),
            )
            .outerjoin(ERPBilling, ERPBilling.erp_quotation_id == ERPQuotation.id)
            .outerjoin(ContractProject, ContractProject.case_code == ERPQuotation.case_code)
            # 2026-09-05：只算成案報價單——未成案的報價總價不是應收，卻曾讓 2026 多出 1,271（CK2026_PM_02_075）
            .where(ERPQuotation.deleted_at.is_(None), ERPQuotation.project_code.isnot(None))
            .group_by(ERPQuotation.case_code, ERPQuotation.id, ERPQuotation.project_code, ERPQuotation.total_price,
                      ContractProject.winning_amount, ContractProject.contract_amount)
        )
        # 2026-09-05 owner「桃園 2026 應僅 2 件委辦案件」：09-04 把年度掛在這個報價單聚合上（報價單年），
        # 結果①案件數與案件清單沒跟著篩——桃園任何年度都 7 案；②`erp_quotations.year` 是補建那年，
        # 桃園 CK2023_01_01_001 的報價單 year=2026 ⇒ 2026 列進 2023 的案（09-04 說的「少 563 萬」正是這張）。
        # 裁示：年度＝案號年（PMCase.year／ContractProject.year，與案號 CK{年} 同值），套在**案件**上，金額跟案走。
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
                # 案件數＝已承攬（有成案報價單或 PM 狀態 contracted）；評估中的案不是「合作案件」
                func.count(func.distinct(sa_case(
                    (or_(billing_agg.c.case_code.isnot(None), PMCase.status == "contracted"), PMCase.case_code),
                    else_=None,
                ))).label("case_count"),
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
            leg1 = leg1.where(PMCase.year == year)
        if keyword:
            # 2026-09-05 owner「搜尋提示寫代碼＝統一編號」：提示改寫成統一編號，後端也真的用統編找
            leg1 = leg1.where(or_(PartnerVendor.vendor_name.ilike(f"%{keyword}%"), PartnerVendor.tax_id.ilike(f"%{keyword}%")))
        leg1 = leg1.group_by(
            PMCase.client_vendor_id, PartnerVendor.vendor_name, PartnerVendor.vendor_code, PartnerVendor.tax_id
        )

        # ── 腿 2：承攬案件文字客戶路徑（case_code 不在腿 1 覆蓋範圍者）──
        covered_case_codes = select(PMCase.case_code).where(
            PMCase.client_vendor_id.isnot(None),
            PMCase.case_code.isnot(None),
        ).scalar_subquery()

        # 2026-09-05 owner「桃園 1 案 64,800 另列一列」：腿 2 此前只用名稱快照分組，快照與主檔差一個字就另起一列。
        # 承攬案 09-04 起有主檔鍵 client_vendor_id ⇒ 先用鍵分組（鍵是關聯、名稱是快照），沒有鍵的才退回名稱。
        leg2 = (
            select(
                ContractProject.client_vendor_id.label("vendor_id"),
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
            .group_by(ContractProject.client_vendor_id, ContractProject.client_agency)
        )
        if year:
            leg2 = leg2.where(ContractProject.year == year)
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
        by_id: dict[int, dict] = {row["vendor_id"]: row for row in items if row.get("vendor_id") is not None}

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
        # 有鍵但腿 1 沒這家（該委託單位名下只有承攬案）⇒ 用主檔名稱建列，不用快照
        vid_rows = [r for r in leg2_rows if r.vendor_id is not None and r.vendor_id not in by_id]
        if vid_rows:
            vrows2 = (await self.db.execute(
                select(PartnerVendor.id, PartnerVendor.vendor_name, PartnerVendor.vendor_code, PartnerVendor.tax_id)
                .where(PartnerVendor.id.in_([r.vendor_id for r in vid_rows]))
            )).all()
            for v in vrows2:
                row = {"vendor_id": v.id, "vendor_name": v.vendor_name, "vendor_code": v.vendor_code, "tax_id": v.tax_id,
                       "case_count": 0, "_tc": Decimal("0"), "_tb": Decimal("0"), "_tr": Decimal("0")}
                items.append(row); by_id[v.id] = row; by_name[(v.vendor_name or "").strip()] = row
        for r in leg2_rows:
            name = (r.client_name or "").strip()
            existing = by_id.get(r.vendor_id) if r.vendor_id is not None else by_name.get(name)
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
            or_(ContractProject.client_vendor_id == vendor_id, ContractProject.client_agency == vendor.vendor_name),
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
        # 2026-09-05：排除 soft-delete；同案多張時成案那張優先（此前哪張贏由回傳順序決定）
        quotations = (
            await self.db.execute(
                select(ERPQuotation).where(
                    ERPQuotation.case_code.in_(case_codes),
                    ERPQuotation.deleted_at.is_(None),
                ).order_by(ERPQuotation.project_code.is_(None), ERPQuotation.id.desc())
            )
        ).scalars().all()
        quot_map: dict[str, ERPQuotation] = {}
        for q in quotations:
            quot_map.setdefault(q.case_code, q)
        # 承攬金額（議價→契約→報價總價）——與列表、/erp/quotations、/contract-cases 同一個算法
        cp_amt_rows = (await self.db.execute(
            select(ContractProject.case_code, ContractProject.winning_amount, ContractProject.contract_amount)
            .where(ContractProject.case_code.in_(case_codes))
        )).all()
        cp_amt_map = {r.case_code: (r.winning_amount, r.contract_amount) for r in cp_amt_rows}

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

            _w, _c = cp_amt_map.get(case_code, (None, None))
            contract_amt = Decimal(str((_w or 0) or (_c or 0) or (quot.total_price or 0)))
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
                "year": case_year_map.get(case_code) or quot.year,   # 年度＝案件年（09-05）
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

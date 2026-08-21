"""ERP 報價/成本服務 — 含損益即時計算

Version: 1.4.0
- v1.4.0: delete 改為軟刪除 (設定 deleted_at)
- v1.3.0: create/update/delete 改用 Repository 方法 (合規修正)
"""
import logging
from typing import Optional, Tuple, List
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPQuotation
from app.repositories.erp import (
    ERPQuotationRepository, ERPInvoiceRepository,
    ERPBillingRepository, ERPVendorPayableRepository,
)
from app.schemas.erp import (
    ERPQuotationCreate, ERPQuotationUpdate, ERPQuotationResponse,
    ERPQuotationListRequest, ERPProfitSummary, ERPProfitTrendItem,
)
from app.services.contract import CaseCodeService
from .finance_ledger import FinanceLedgerService
# 公司固定利潤率（公司留成，2026-08-18）——
# 純函式 compute_quotation_profit 不讀設定，由呼叫端取值後傳入。
from .company_profit import get_company_profit_rate
from app.services.audit_mixin import AuditableServiceMixin

logger = logging.getLogger(__name__)

ZERO = Decimal("0")


def compute_quotation_profit(
    total_price, tax_amount=0,
    outsourcing_fee=0, personnel_fee=0, overhead_fee=0, other_cost=0,
    company_profit_rate=0,
) -> dict:
    """統一利潤計算 — 全模組共用 (service/io/repository)

        營收       = 總價 − 稅額
        公司留成   = 營收 × company_profit_rate       ← 2026-08-18 新增這一層
        專案可用   = 營收 − 公司留成
        total_cost = outsourcing + personnel + overhead + other
        gross_profit = 專案可用 − total_cost
        gross_margin = gross_profit / 專案可用 × 100

    `company_profit_rate` 是 **0~1 的小數**（10% 傳 `Decimal("0.1")`），
    由呼叫端從 `services/erp/company_profit.get_company_profit_rate()` 取得。
    **刻意不在這裡讀設定表**：這支是純函式、被 io/repository/service 三處共用，
    加上 db session 會讓三個呼叫端都被迫改簽名，而純粹正是它的價值。

    ⚠️ 預設 0 ⇒ 不傳時行為與 08-18 之前**完全相同**。
    這件事很重要：比率一生效，每一張報價的毛利都會變，
    所以升級不得靠「忘記傳參數就自動套用」那種隱含行為。

    ⚠️ 分母是**專案可用**不是營收：公司留成已經不屬於專案可支配的錢，
    把它留在分母裡算出的毛利率會比真實情況低，
    而看的人會以為是成本偏高（歸因到錯的地方）。
    """
    tp = Decimal(str(total_price or 0))
    tax = Decimal(str(tax_amount or 0))
    out = Decimal(str(outsourcing_fee or 0))
    pers = Decimal(str(personnel_fee or 0))
    over = Decimal(str(overhead_fee or 0))
    other = Decimal(str(other_cost or 0))
    rate = Decimal(str(company_profit_rate or 0))

    total_cost = out + pers + over + other
    revenue = tp - tax

    # 公司留成。四捨五入到元 —— 對外的金額不該出現小數分位
    # （會與人手算的數字差一分而被當成系統算錯）。
    company_reserve = (revenue * rate).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ) if rate > ZERO else ZERO
    project_base = revenue - company_reserve

    gross_profit = project_base - total_cost

    gross_margin = None
    if project_base > ZERO:
        gross_margin = (gross_profit / project_base * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    return {
        "total_cost": total_cost,
        "gross_profit": gross_profit,
        "gross_margin": gross_margin,
        # 2026-08-18：把中間值一起回傳，否則毛利變小時看不出是被誰扣掉的。
        # 只給 gross_profit 的話，owner 設了 10% 之後看到的是
        # 「毛利莫名少了一截」，而查不到那一截去哪了。
        "company_profit_rate": rate,
        "company_reserve": company_reserve,
        "project_base": project_base,
        "revenue": revenue,
        # ⚠️ net_profit 與 gross_profit 是**同一個數字**（2026-08-15 查證）。
        # 報價詳情頁把「毛利」與「淨利」並排顯示，看的人會以為那是兩個指標。
        # 真正的淨利要再扣營運費用與稅，而那些資料在 operational_expenses
        # 與 finance_ledgers，這支函式看不到 —— 所以不是算錯，是**這一層算不出來**。
        # 保留欄位避免破壞既有消費端，但標明它不是淨利；UI 已改為不再單獨顯示。
        "net_profit": gross_profit,
        # 成本四欄未填時後端 schema 預設為 0（`Field(Decimal("0"))`），
        # 於是「沒填成本」與「成本真的是零」在資料裡完全無法分辨，
        # 毛利率會顯示 100%。實測 77 筆報價有 **37 筆**落在這裡，
        # 其中最大一筆收入 943 萬。
        # 這一層分不出來，但可以誠實說「沒有依據」，讓 UI 不要報一個假數字。
        "cost_declared": total_cost > ZERO,
    }


class ERPQuotationService(AuditableServiceMixin):
    """報價管理服務 — 損益計算核心"""

    AUDIT_TABLE = "erp_quotations"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ERPQuotationRepository(db)
        self.invoice_repo = ERPInvoiceRepository(db)
        self.billing_repo = ERPBillingRepository(db)
        self.payable_repo = ERPVendorPayableRepository(db)
        self.code_service = CaseCodeService(db)

    # =========================================================================
    # CRUD
    # =========================================================================

    async def generate_case_code(self, year: int, category: str = "01") -> str:
        """產生 ERP 案號"""
        return await self.code_service.generate_case_code("erp", year, category)

    async def create(self, data: ERPQuotationCreate, user_id: Optional[int] = None) -> ERPQuotationResponse:
        """建立報價 — case_code 未提供時自動產生，已有案號時驗證 PM 參照"""
        dump = data.model_dump()

        # 自動產生案號
        if not dump.get("case_code"):
            from datetime import date as _date
            year = dump.get("year") or _date.today().year
            category = "01"  # ERP 預設報價單
            dump["case_code"] = await self.code_service.generate_case_code(
                "erp", year, category,
            )
        else:
            # case_code 參照完整性驗證 — 確認 PM 案件存在
            await self._validate_case_code(dump["case_code"])

        dump["created_by"] = user_id
        quotation = await self.repo.create(dump)
        await self.audit_create(quotation.id, dump, user_id=user_id)
        return await self._to_response(quotation)

    async def get_detail(self, quotation_id: int) -> Optional[ERPQuotationResponse]:
        """取得報價詳情 (含計算欄位)"""
        quotation = await self.repo.get_by_id(quotation_id)
        if not quotation:
            return None
        return await self._to_response(quotation)

    async def update(self, quotation_id: int, data: ERPQuotationUpdate) -> Optional[ERPQuotationResponse]:
        """更新報價"""
        changes = data.model_dump(exclude_unset=True)
        quotation = await self.repo.update(quotation_id, changes)
        if not quotation:
            return None
        await self.audit_update(quotation_id, changes)
        return await self._to_response(quotation)

    async def delete(self, quotation_id: int) -> bool:
        """刪除報價 — 有已付帳單/應付的報價禁止刪除

        刪除時同步清理對應的 FinanceLedger entries，避免帳本孤兒。
        """
        # 防護：檢查是否有已付款的帳單或應付
        billings = await self.billing_repo.get_by_quotation_id(quotation_id)
        paid_billings = [b for b in billings if b.payment_status == "paid"]
        if paid_billings:
            raise ValueError(
                f"此報價有 {len(paid_billings)} 筆已收款帳單，無法刪除。"
                "請先在帳單中撤銷收款狀態。"
            )

        payables = await self.payable_repo.get_by_quotation_id(quotation_id)
        paid_payables = [p for p in payables if p.payment_status == "paid"]
        if paid_payables:
            raise ValueError(
                f"此報價有 {len(paid_payables)} 筆已付款的廠商應付，無法刪除。"
                "請先在應付帳款中撤銷付款狀態。"
            )

        # 軟刪除：設定 deleted_at 而非物理刪除
        quotation = await self.repo.get_by_id(quotation_id)
        if not quotation:
            return False

        quotation.deleted_at = datetime.now()
        await self.db.commit()
        await self.audit_delete(quotation_id)
        return True

    async def list_quotations(self, params: ERPQuotationListRequest) -> Tuple[List[ERPQuotationResponse], int]:
        """報價列表 — 使用批次聚合消除 N+1 查詢"""
        items, total = await self.repo.filter_quotations(
            year=params.year,
            status=params.status,
            case_code=params.case_code,
            search=params.search,
            skip=params.skip,
            limit=params.limit,
            sort_by=params.sort_by or "id",
            sort_order=params.sort_order.value if params.sort_order else "desc",
        )

        if not items:
            return [], total

        # 批次取得聚合數據 (2 queries instead of N*6)
        ids = [q.id for q in items]
        billing_agg = await self.billing_repo.get_aggregates_batch(ids)
        payable_agg = await self.payable_repo.get_aggregates_batch(ids)
        # invoice count 透過 billing count 估算或單獨批次查詢
        invoice_counts = await self._get_invoice_counts_batch(ids)
        # 整批取一次公司留成比率（值有 60 秒快取，但這裡連查詢都省掉）
        rate = await get_company_profit_rate(self.db)
        # 填報者姓名同樣整批取 —— 逐筆查會讓列表變成 N+1
        creator_names = await self._get_creator_names_batch([q.created_by for q in items])
        staff_names = await self._get_staff_names_batch([q.case_code for q in items])

        responses = []
        for item in items:
            b = billing_agg.get(item.id, {})
            p = payable_agg.get(item.id, {})
            responses.append(self._to_response_with_aggregates(
                item,
                creator_name=creator_names.get(item.created_by),
                staff_name=staff_names.get(item.case_code),
                billing_count=b.get("count", 0),
                total_billed=b.get("total_billed", ZERO),
                total_received=b.get("total_received", ZERO),
                total_payable=p.get("total_payable", ZERO),
                total_paid=p.get("total_paid", ZERO),
                invoice_count=invoice_counts.get(item.id, 0),
                company_profit_rate=rate,
            ))
        return responses, total


    async def _get_staff_names_batch(self, case_codes: List[str]) -> dict:
        """整批取每個 case_code 的承辦同仁姓名。

        owner 2026-08-21：「報價單也尚未對應承辦同仁」。

        資料本來就通 —— 承辦同仁掛在 `project_user_assignments.case_code` 上，
        而報價單也有 case_code；缺的只是把它帶出來。

        **不另建一套人員關聯**：邀標案件（`/pm/cases/:id?tab=staff`）看到的
        就是同一份，兩邊各自維護一份人員名單才是問題的開始。

        ADR-0025：以 canonical 人為準 —— 分身帳號不得顯示成另一個人。
        """
        codes = [c for c in {c for c in case_codes if c}]
        if not codes:
            return {}
        rows = (await self.db.execute(text("""
            SELECT pa.case_code,
                   string_agg(DISTINCT COALESCE(u.full_name, u.username), '、') AS names
              FROM project_user_assignments pa
              LEFT JOIN users au ON au.id = pa.user_id
              LEFT JOIN users u  ON u.id = COALESCE(au.canonical_user_id, au.id)
             WHERE pa.case_code = ANY(:cs)
               AND COALESCE(pa.status, 'active') <> 'inactive'
             GROUP BY pa.case_code
        """), {"cs": codes})).all()
        return {r[0]: r[1] for r in rows if r[1]}

    async def _get_creator_names_batch(self, user_ids: List[int]) -> dict:
        """一次取回填報者姓名（避免列表 N+1）。

        ⚠️ **不做 canonical 轉換**：填報者問的是「這筆資料是誰輸入的」，
        就是那個帳號本人；而同一頁的「服務人員」問的是案子窗口，
        那個才依 ADR-0025 收斂到 canonical。兩者在王駿穠身上會不同
        （aaronfly1978 業務身分 vs jujuiacc 管理帳號）。
        """
        ids = [i for i in set(user_ids or []) if i]
        if not ids:
            return {}
        from app.extended.models import User
        rows = (await self.db.execute(
            select(User.id, User.full_name, User.username).where(User.id.in_(ids))
        )).all()
        return {r[0]: (r[1] or r[2]) for r in rows}

    async def _get_invoice_counts_batch(self, quotation_ids: List[int]) -> dict:
        """批次取得發票數量 — 委派至 ERPInvoiceRepository"""
        return await self.invoice_repo.get_counts_by_quotation_ids(quotation_ids)

    def _to_response_with_aggregates(
        self,
        quotation: ERPQuotation,
        billing_count: int,
        total_billed: Decimal,
        total_received: Decimal,
        total_payable: Decimal,
        total_paid: Decimal,
        invoice_count: int,
        company_profit_rate=ZERO,
        staff_name: Optional[str] = None,
        creator_name: Optional[str] = None,
    ) -> ERPQuotationResponse:
        """轉換為回應格式 (使用預先批次聚合的數據，避免 N+1)

        `company_profit_rate` 由呼叫端整批取一次後傳入 —— 這支是 **sync**，
        不能在裡面 await；而就算能，每筆各查一次也是把一個
        「一天不會變一次」的值查 N 遍。
        """
        profit = self.compute_profit(quotation, company_profit_rate)

        budget_limit = quotation.budget_limit
        budget_usage_pct = None
        is_over_budget = False
        if budget_limit and budget_limit > ZERO:
            usage = profit["total_cost"] / budget_limit * 100
            budget_usage_pct = usage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            is_over_budget = profit["total_cost"] > budget_limit

        return ERPQuotationResponse(
            **{c.name: getattr(quotation, c.name) for c in quotation.__table__.columns},
            budget_usage_pct=budget_usage_pct,
            is_over_budget=is_over_budget,
            total_cost=profit["total_cost"],
            gross_profit=profit["gross_profit"],
            gross_margin=profit["gross_margin"],
            # 2026-08-18：這四欄必須手動接上 —— 這裡是**逐欄手寫**的 response，
            # 不是 `**profit`，所以 compute 算出來的新欄位不會自動流過來。
            # 漏接的症狀是「畫面永遠顯示 0%、而後端明明算對了」。
            company_profit_rate=profit["company_profit_rate"],
            company_reserve=profit["company_reserve"],
            project_base=profit["project_base"],
            revenue=profit["revenue"],
            net_profit=profit["net_profit"],
            cost_declared=profit["cost_declared"],
            # 列表不查實際成本：那要逐筆打 DB（N+1），而這個方法存在的理由
            # 正是消除 N+1（見 list_quotations 的批次聚合）。
            # 實際成本只在詳情頁計算；列表顯示的是報價單上的估列。
            created_by_name=creator_name,
            staff_name=staff_name,
            invoice_count=invoice_count,
            billing_count=billing_count,
            total_billed=total_billed,
            total_received=total_received,
            total_payable=total_payable,
            total_paid=total_paid,
        )

    async def _validate_case_code(self, case_code: str) -> None:
        """驗證 case_code 是否存在於 PM 系統 (參照完整性)"""
        try:
            from app.repositories.pm import PMCaseRepository
            pm_repo = PMCaseRepository(self.db)
            pm_case = await pm_repo.get_by_case_code(case_code)
            if not pm_case:
                logger.warning("ERP case_code '%s' 不存在於 PM 系統", case_code)
        except Exception:
            # PM 模組不可用時不阻擋 ERP 建案 (降級容錯)
            pass

    # =========================================================================
    # 損益計算
    # =========================================================================

    @staticmethod
    def compute_profit(quotation: ERPQuotation, company_profit_rate=ZERO) -> dict:
        """計算毛利/淨利 — 委派至模組級 compute_quotation_profit()

        `company_profit_rate` 由呼叫端從 `get_company_profit_rate(db)` 取得
        （0~1 小數）。**維持 staticmethod**：`quotation_service_io` 以類別呼叫它，
        改成實例方法會連帶改動匯出路徑，而那不是這次要動的東西。

        ⚠️ 預設 ZERO ⇒ 忘記傳的呼叫端行為與 08-18 之前相同（不扣公司留成）。
        那是刻意的降級方向：漏傳會少扣，而不是算出一個沒人預期的小數字。
        """
        return compute_quotation_profit(
            total_price=quotation.total_price,
            tax_amount=quotation.tax_amount,
            outsourcing_fee=quotation.outsourcing_fee,
            personnel_fee=quotation.personnel_fee,
            overhead_fee=quotation.overhead_fee,
            other_cost=quotation.other_cost,
            company_profit_rate=company_profit_rate,
        )

    # =========================================================================
    # PM 金額比對
    # =========================================================================

    async def get_pm_amount_check(self, case_code: Optional[str]) -> Optional[dict]:
        """比對 ERP total_price 與 PM contract_amount，並帶回委託單位名稱。

        2026-08-17 owner：「委託單位無同步顯示」。
        應收列表的 `counterparty` 原本是**硬編字串 `'委託單位'`**（欄位名被當成值），
        所以每一列都顯示那四個字而不是真實單位名 ——
        而名稱一直都在 `contract_projects.client_agency`（實測「嘉義縣竹崎地政事務所」）。

        委託單位在這裡一起查，**不另開一次往返**：這個方法本來就在查同一個
        case_code 的 PM 資料，多一個 join 比多一次呼叫便宜。
        """
        if not case_code:
            return None
        try:
            from app.extended.models.core import ContractProject
            from app.extended.models.pm import PMCase
            from sqlalchemy import select

            result = await self.db.execute(
                select(PMCase.contract_amount).where(PMCase.case_code == case_code)
            )
            pm_amount = result.scalar_one_or_none()

            # 委託單位：承攬案件的 client_agency 優先（那是成案後的正式對象），
            # 沒有才回退 PM 的 client_name。
            client_name = (await self.db.execute(
                select(ContractProject.client_agency)
                .where(ContractProject.case_code == case_code)
            )).scalar_one_or_none()
            if not client_name:
                client_name = (await self.db.execute(
                    select(PMCase.client_name).where(PMCase.case_code == case_code)
                )).scalar_one_or_none()

            # ⚠️ 原本 pm_amount 為 None 就整個 return None ——
            # 那會讓「有委託單位但沒填 PM 金額」的案件也拿不到單位名稱。
            # 兩件資訊各自獨立，不該互相綁死。
            # 專案類別（01 委辦招標／02 承攬報價）——
            # owner 2026-08-17：「若是標案應無報價明細 tab」。
            # 標案涉及多項程序、不易逐項填列成本，顯示一個填不了的分頁
            # 就是在要求對方做不可能的事（同「要求標案填成本」那個錯）。
            category = (await self.db.execute(
                select(ContractProject.category)
                .where(ContractProject.case_code == case_code)
            )).scalar_one_or_none()
            if not category:
                category = (await self.db.execute(
                    select(PMCase.category).where(PMCase.case_code == case_code)
                )).scalar_one_or_none()

            out: dict = {}
            if category:
                out["case_category"] = category
            if client_name:
                out["client_name"] = client_name
            if pm_amount is not None:
                quotation = await self.repo.get_by_case_code(case_code)
                erp_amount = Decimal(str(quotation.total_price or 0)) if quotation else ZERO
                pm_dec = Decimal(str(pm_amount or 0))
                out["pm_contract_amount"] = str(pm_dec)
                out["mismatch"] = abs(erp_amount - pm_dec) > Decimal("0.01")
            return out or None
        except Exception:
            return None

    # =========================================================================
    # 損益摘要
    # =========================================================================

    async def get_profit_summary(self, year: Optional[int] = None) -> ERPProfitSummary:
        """年度損益摘要 — 批次聚合消除 N+1"""
        items, _ = await self.repo.filter_quotations(
            year=year, skip=0, limit=9999,
        )

        total_revenue = ZERO
        total_cost = ZERO
        total_gross = ZERO

        # 批次取得請款聚合
        ids = [q.id for q in items]
        billing_agg = await self.billing_repo.get_aggregates_batch(ids) if ids else {}
        rate = await get_company_profit_rate(self.db)

        for q in items:
            profit = self.compute_profit(q, rate)
            price = Decimal(str(q.total_price or 0))
            tax = Decimal(str(q.tax_amount or 0))
            total_revenue += price - tax
            total_cost += profit["total_cost"]
            total_gross += profit["gross_profit"]

        total_billed = sum(
            (v.get("total_billed", ZERO) for v in billing_agg.values()), ZERO,
        )
        total_received = sum(
            (v.get("total_received", ZERO) for v in billing_agg.values()), ZERO,
        )

        avg_margin = None
        if total_revenue > ZERO:
            avg_margin = (total_gross / total_revenue * 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        return ERPProfitSummary(
            total_revenue=total_revenue,
            total_cost=total_cost,
            total_gross_profit=total_gross,
            avg_gross_margin=avg_margin,
            total_billed=total_billed,
            total_received=total_received,
            total_outstanding=total_billed - total_received,
            case_count=len(items),
        )

    # =========================================================================
    # 多年度損益趨勢
    # =========================================================================

    async def get_profit_trend(self) -> List[ERPProfitTrendItem]:
        """多年度損益趨勢 — SQL 聚合 (取代全表載入)"""
        rows = await self.repo.get_yearly_trend_sql()
        return [ERPProfitTrendItem(**row) for row in rows]

    # =========================================================================
    # IO 委派 (CSV/Excel 匯出入 — 委派至 quotation_service_io.py)
    # =========================================================================

    async def export_csv(self, year: Optional[int] = None) -> str:
        """匯出報價為 CSV 字串 (委派至 ERPQuotationIOService)"""
        from app.services.erp.quotation_service_io import ERPQuotationIOService
        return await ERPQuotationIOService(self.db).export_csv(year)

    async def export_excel(self, year: Optional[int] = None) -> bytes:
        """匯出報價為 Excel (委派至 ERPQuotationIOService)"""
        from app.services.erp.quotation_service_io import ERPQuotationIOService
        return await ERPQuotationIOService(self.db).export_excel(year)

    def generate_import_template(self) -> bytes:
        """產生匯入範本 Excel (委派至 ERPQuotationIOService)"""
        from app.services.erp.quotation_service_io import ERPQuotationIOService
        return ERPQuotationIOService.generate_import_template()

    async def import_from_excel(self, file_bytes: bytes, user_id: Optional[int] = None) -> dict:
        """匯入報價 Excel (委派至 ERPQuotationIOService)"""
        from app.services.erp.quotation_service_io import ERPQuotationIOService
        return await ERPQuotationIOService(self.db).import_from_excel(file_bytes, user_id)

    # =========================================================================
    # 轉換
    # =========================================================================

    async def _actual_cost(self, case_code: Optional[str], quotation_id: int) -> dict:
        """實際成本 —— 與報價單的「估列」是**兩件事**，不得混用。

        2026-08-15 owner：「報價單估列費用、實際成本、毛利皆由區分清楚不可混淆」。

        以**統一帳本**為準，不把三個來源相加 —— 帳本本來就是收攏應付與核銷的地方，
        相加會重複計算。但只報帳本會低估：目前 9 筆核銷只有 2 筆入帳、
        36 筆應付一筆都沒標記已付（見 `erp_data_integrity_audit` §2）。

        所以分成兩個數字：
        - `actual_cost`：已入帳（帳本 expense，有憑有據）
        - `pending_cost`：已發生但還沒入帳（核銷未入帳 ＋ 應付未付）

        把 pending 放在使用的當下，填報缺口才會被真正的人看到 ——
        而不是只出現在每週檢核裡。
        """
        from sqlalchemy import text as _sql

        actual = pending = ZERO
        if case_code:
            row = (await self.db.execute(_sql("""
                SELECT COALESCE(SUM(amount),0) FROM finance_ledgers
                WHERE entry_type='expense' AND case_code = :cc
            """), {"cc": case_code})).scalar()
            actual = Decimal(str(row or 0))

            row = (await self.db.execute(_sql("""
                SELECT COALESCE(SUM(e.amount),0) FROM expense_invoices e
                WHERE e.case_code = :cc
                  AND NOT EXISTS (SELECT 1 FROM finance_ledgers l
                                  WHERE l.source_type='expense_invoice' AND l.source_id=e.id)
            """), {"cc": case_code})).scalar()
            pending += Decimal(str(row or 0))

        row = (await self.db.execute(_sql("""
            SELECT COALESCE(SUM(COALESCE(payable_amount,0)),0) FROM erp_vendor_payables
            WHERE erp_quotation_id = :qid AND payment_status <> 'paid'
        """), {"qid": quotation_id})).scalar()
        pending += Decimal(str(row or 0))

        return {"actual_cost": actual, "pending_cost": pending}


    async def _to_response(self, quotation: ERPQuotation) -> ERPQuotationResponse:
        """轉換為回應格式 (含計算欄位 + 聚合)"""
        profit = self.compute_profit(
            quotation, await get_company_profit_rate(self.db)
        )

        invoices = await self.invoice_repo.get_by_quotation_id(quotation.id)
        total_billed = await self.billing_repo.get_total_billed(quotation.id)
        total_received = await self.billing_repo.get_total_received(quotation.id)
        total_payable = await self.payable_repo.get_total_payable(quotation.id)
        total_paid = await self.payable_repo.get_total_paid(quotation.id)
        billings = await self.billing_repo.get_by_quotation_id(quotation.id)
        actual = await self._actual_cost(quotation.case_code, quotation.id)

        # 預算警示計算
        budget_limit = quotation.budget_limit
        budget_usage_pct = None
        is_over_budget = False
        if budget_limit and budget_limit > ZERO:
            usage = profit["total_cost"] / budget_limit * 100
            budget_usage_pct = usage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            is_over_budget = profit["total_cost"] > budget_limit

        return ERPQuotationResponse(
            **{c.name: getattr(quotation, c.name) for c in quotation.__table__.columns},
            budget_usage_pct=budget_usage_pct,
            is_over_budget=is_over_budget,
            total_cost=profit["total_cost"],
            gross_profit=profit["gross_profit"],
            gross_margin=profit["gross_margin"],
            # 2026-08-18：這四欄必須手動接上 —— 這裡是**逐欄手寫**的 response，
            # 不是 `**profit`，所以 compute 算出來的新欄位不會自動流過來。
            # 漏接的症狀是「畫面永遠顯示 0%、而後端明明算對了」。
            company_profit_rate=profit["company_profit_rate"],
            company_reserve=profit["company_reserve"],
            project_base=profit["project_base"],
            revenue=profit["revenue"],
            net_profit=profit["net_profit"],
            cost_declared=profit["cost_declared"],
            actual_cost=actual["actual_cost"],
            pending_cost=actual["pending_cost"],
            # 單筆詳情：直接查一次（列表走 _get_creator_names_batch）
            created_by_name=(await self._get_creator_names_batch(
                [quotation.created_by])).get(quotation.created_by),
            staff_name=(await self._get_staff_names_batch(
                [quotation.case_code])).get(quotation.case_code),
            invoice_count=len(invoices),
            billing_count=len(billings),
            total_billed=total_billed,
            total_received=total_received,
            total_payable=total_payable,
            total_paid=total_paid,
        )

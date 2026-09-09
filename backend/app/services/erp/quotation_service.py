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
from app.services.audit.mixin import AuditableServiceMixin

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


async def narrow_scope_to_staff(db, accessible_case_codes, staff_user_id):
    """把「伺服器決定的身分範圍」再交集「使用者自選的承辦」。**列表與統計卡都走這一份。**

    - `staff_user_id` 為 None ⇒ 原樣回傳（不動範圍）。
    - 有值 ⇒ 承辦案號集合；若已有身分範圍則取交集；交集為空回 ``{"__none__"}``
      （讓 SQL `IN` 得到空結果，而不是 `IN ()` 的語法錯誤或「不篩＝全部」）。

    2026-09-09：此前只有 `list_quotations` 有這段、`get_profit_summary` 沒有 ⇒
    選了承辦之後列表 85 張、卡片仍是全公司 112 張的 2,149 萬。
    """
    if staff_user_id is None:
        return accessible_case_codes
    from app.repositories.erp.case_staff import case_codes_of_user
    mine = await case_codes_of_user(db, staff_user_id)
    return (
        mine if accessible_case_codes is None
        else (set(accessible_case_codes) & set(mine))
    ) or {"__none__"}


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

        # 2026-09-02：**這條路徑原本不給 QT 號**。給號邏輯只在 tender/case_creation.py
        # （從標案建案）那條路，而 /pm/cases「新增報價」走的是這裡 ⇒ 實測 257 張裡
        # 181 張 quotation_no 為空（owner 當日新建的「CCC」正是其中一張）。
        # 同一個欄位、兩條建立路徑、只有一條給號 —— 又一個「兩條路只認一條」。
        if not dump.get("quotation_no"):
            from datetime import date as _date
            dump["quotation_no"] = await self.code_service.generate_quotation_no(
                dump.get("year") or _date.today().year
            )
        dump.setdefault("revision", 1)
        if not dump.get("quote_kind"):
            from app.services.erp.quote_kind import infer_quote_kind
            dump["quote_kind"] = infer_quote_kind(dump.get("case_code"))

        dump["created_by"] = user_id
        quotation = await self.repo.create(dump)
        await self.audit_create(quotation.id, dump, user_id=user_id)
        # 成案即應收（2026-09-03）：直接建在已成案案號上、且有總額的報價單，也要有第一期
        try:
            from app.services.erp.billing_service import ERPBillingService
            await ERPBillingService(self.db).ensure_first_period(quotation.id, reason="新建報價單")
        except Exception as e:
            logger.error("成案即應收掛點失敗（不阻擋建立）quotation=%s: %s", quotation.id, e, exc_info=True)
        return await self._to_response(quotation)

    async def get_detail(self, quotation_id: int) -> Optional[ERPQuotationResponse]:
        """取得報價詳情 (含計算欄位)"""
        quotation = await self.repo.get_by_id(quotation_id)
        if not quotation:
            return None
        resp = await self._to_response(quotation)
        # 2026-09-09 owner：「問題錯誤如何標注與顯示」——列表有異常標註而詳情沒有，
        # 使用者點進去反而看不到哪裡不對。與列表同一份判準（finance_anomaly），失敗不阻擋詳情。
        try:
            from app.services.erp import finance_anomaly
            resp.anomalies = (await finance_anomaly.annotate(self.db, [quotation_id])).get(quotation_id, [])
        except Exception as e:  # noqa: BLE001
            logger.error("報價詳情異常標註失敗（不阻擋詳情）：%s", e, exc_info=True)
        return resp

    async def update(self, quotation_id: int, data: ERPQuotationUpdate) -> Optional[ERPQuotationResponse]:
        """更新報價"""
        changes = data.model_dump(exclude_unset=True)
        # 2026-09-03 全景覆盤 A3：已有請款的報價單不得直接改總價——請款額、發票額都對著它，
        # 改了就是三個地方三個數（weekly 104 ①）。要改走版次：revision+1 一起送才放行。
        if "total_price" in changes:
            from decimal import Decimal
            from sqlalchemy import select as _sel, func as _fn
            from app.extended.models.erp import ERPBilling
            cur = await self.repo.get_by_id(quotation_id)
            if cur is not None and cur.total_price is not None and changes["total_price"] is not None \
                    and Decimal(str(changes["total_price"])) != Decimal(str(cur.total_price)):
                n_bill = await self.db.scalar(_sel(_fn.count(ERPBilling.id)).where(ERPBilling.erp_quotation_id == quotation_id))
                if n_bill and int(changes.get("revision") or cur.revision or 1) <= int(cur.revision or 1):
                    raise ValueError(
                        f"此報價單已有 {n_bill} 筆請款，總價不可直接修改（請款額與發票額都對著它）。"
                        f"要調整請以新版次送出（revision {int(cur.revision or 1) + 1}），並同步調整請款。"
                    )
        quotation = await self.repo.update(quotation_id, changes)
        if not quotation:
            return None
        await self.audit_update(quotation_id, changes)
        # ⭐ 2026-09-08：切換「總價已含稅」之後，總價必須照新規則重算。
        # 只改旗標不重算的話，畫面上小計會說「即為總價」而 `total_price`
        # 還停在舊的 ×1.05 —— 而**兩個數字各自看都合理**，
        # 差異只在跨頁比總額時才浮出來（正是 09-04 那次兩頁兩個總額的形狀）。
        # 沒有工項的報價單不動（空明細＝尚未逐項拆，不是 0 元）。
        if "tax_included" in changes:
            try:
                from app.services.erp.quotation_items import QuotationItemService
                await QuotationItemService(self.db).recompute_totals(quotation_id)
            except ValueError:
                # 已有請款者會被 `_apply_totals` 那把鎖擋下 —— 要讓使用者看到原因，
                # 不是安靜地留下「旗標改了但金額沒動」的半套狀態。
                raise
            except Exception as e:  # noqa: BLE001
                logger.error("切換 tax_included 後重算總價失敗 quotation=%s: %s",
                             quotation_id, e, exc_info=True)
        # 成案即應收（2026-09-03）：補填總額或轉 confirmed 時，若還沒有請款就建第一期
        if "total_price" in changes or changes.get("status") == "confirmed":
            try:
                from app.services.erp.billing_service import ERPBillingService
                await ERPBillingService(self.db).ensure_first_period(quotation_id, reason="報價單更新")
            except Exception as e:
                logger.error("成案即應收掛點失敗（不阻擋更新）quotation=%s: %s", quotation_id, e, exc_info=True)
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

    async def _filter_kwargs(self, params: ERPQuotationListRequest, accessible_case_codes=None,
                             *, for_stats: bool = False) -> dict:
        """**列表與統計卡共用的篩選解析**（2026-09-09，weekly 133）——回 `repo.filter_quotations` 的關鍵字引數。

        此前列表在這裡解析十個條件、損益摘要只收四個 ⇒ 選了承辦／狀態／案號，卡片不跟。
        現在兩邊吃同一份 `ERPQuotationListRequest`，差別只有：
        * `for_stats=True` ⇒ `card` 不套（卡片是分母，點卡片篩列表時卡片不隨之歸零；`STATS_EXEMPT`）。
        * 關鍵字：`search`（本頁舊名）與 `keyword`（`CaseListFilters` 的統一名）**都認**，欄名統一是下一步。
        """
        accessible_case_codes = await narrow_scope_to_staff(
            self.db, accessible_case_codes, params.staff_user_id)

        anomaly_ids = None
        if params.anomaly:
            from app.services.erp import finance_anomaly
            anomaly_ids = await finance_anomaly.anomaly_ids(
                self.db, only_open=(params.anomaly == "open"))

        return dict(
            year=params.year,
            status=params.status,
            case_code=params.case_code,
            search=params.search or getattr(params, "keyword", None) or None,
            include_unawarded=params.include_unawarded,
            accessible_case_codes=accessible_case_codes,
            category=params.category,
            case_status=params.case_status,
            client_name=params.client_name,
            card=None if for_stats else params.card,
            anomaly_quotation_ids=anomaly_ids,
        )

    async def list_quotations(
        self,
        params: ERPQuotationListRequest,
        accessible_case_codes=None,
    ) -> Tuple[List[ERPQuotationResponse], int]:
        """報價列表 — 使用批次聚合消除 N+1 查詢。

        `accessible_case_codes`：**None ＝不限縮**（管理者或持有跨案查詢
        權限者）。由端點依登入身分算出來傳進來 —— 服務層不自己查身分，
        否則同一個服務在不同呼叫路徑會有不同的可見範圍。
        """
        # 2026-09-07 owner：「對應承辦同仁呈現對應資訊」。使用者自己選的承辦
        # **只能在可見範圍之內再縮小**——與 `accessible_case_codes` 取交集，
        # 不是覆蓋它（覆蓋就等於前端傳什麼就給什麼，RLS 形同虛設）。
        # 🛡️ 防呆（2026-09-08 owner：「包含 /erp/quotations 防呆管理機制」）：
        # `accessible_case_codes` 曾經被兩種形式餵進來 —— 集合，與**還沒執行的 SQL 述句**
        # （`RLSFilter.get_user_accessible_case_codes` 回的就是後者）。
        # 兩種形式在 `case_code.in_(...)` 都能用，所以一般情況看不出差別；
        # 但下面要做集合交集，對述句 `set()` 會 TypeError ⇒ **整個列表頁 500**。
        # 症狀只在「非管理員 ＋ 有選承辦同仁」時出現 —— 一天中大多數請求都是好的。
        # ⇒ 收在入口統一成集合：述句就地執行，其餘照舊。
        if accessible_case_codes is not None and not isinstance(
                accessible_case_codes, (set, frozenset, list, tuple)):
            try:
                rows = (await self.db.execute(accessible_case_codes)).all()
                accessible_case_codes = {r[0] for r in rows if r and r[0]}
                logger.warning(
                    "list_quotations 收到 SQL 述句形式的可見範圍，已就地執行為集合 —— "
                    "呼叫端應改回集合（見 endpoints/erp/quotations._quotation_scope）")
            except Exception as e:  # noqa: BLE001
                # 解不開就**限縮成空**而不是放行全部 —— 範圍守衛失效時，
                # 安全的失敗方向是「看不到」不是「全都看得到」。
                logger.error("可見範圍解析失敗，限縮為空：%s", e, exc_info=True)
                accessible_case_codes = set()

        items, total = await self.repo.filter_quotations(
            **(await self._filter_kwargs(params, accessible_case_codes)),
            skip=params.skip,
            limit=params.limit,
            sort_by=params.sort_by or "id",
            sort_order=params.sort_order.value if params.sort_order else "desc",
        )

        if not items:
            return [], total

        # 批次取得聚合數據 (2 queries instead of N*6)
        ids = [q.id for q in items]
        vendor_names = await self._get_vendor_names_batch(ids)
        case_amounts = await self._get_case_amounts_batch([q.case_code for q in items])
        contract_amounts = {k: v["contract"] for k, v in case_amounts.items() if v["contract"] is not None}
        billing_agg = await self.billing_repo.get_aggregates_batch(ids)
        payable_agg = await self.payable_repo.get_aggregates_batch(ids)
        # invoice count 透過 billing count 估算或單獨批次查詢
        invoice_counts = await self._get_invoice_counts_batch(ids)
        # 整批取一次公司留成比率（值有 60 秒快取，但這裡連查詢都省掉）
        rate = await get_company_profit_rate(self.db)
        # 填報者姓名同樣整批取 —— 逐筆查會讓列表變成 N+1
        creator_names = await self._get_creator_names_batch([q.created_by for q in items])
        staff_names = await self._get_staff_names_batch([q.case_code for q in items])
        # 客戶名也整批取（2026-09-03 列表加「客戶」欄；逐筆查會 N+1）
        client_names = await self._get_client_names_batch([q.case_code for q in items])

        # 異常標註（推導）——與上面的聚合同一個形狀：整批算一次，不逐筆查。
        # 失敗時記 error 並讓列表照常出來：異常標籤不見了是**看得出來的**降級，
        # 而整頁 500 會讓使用者連報價單都看不到。
        try:
            from app.services.erp import finance_anomaly
            anomaly_map = await finance_anomaly.annotate(self.db, ids)
        except Exception as e:  # noqa: BLE001
            logger.error("報價列表異常標註失敗（不阻擋列表）：%s", e, exc_info=True)
            anomaly_map = {}

        responses = []
        for item in items:
            b = billing_agg.get(item.id, {})
            p = payable_agg.get(item.id, {})
            resp = self._to_response_with_aggregates(
                item,
                creator_name=creator_names.get(item.created_by),
                staff_name=staff_names.get(item.case_code),
                client_name=client_names.get(item.case_code),
                billing_count=b.get("count", 0),
                total_billed=b.get("total_billed", ZERO),
                total_received=b.get("total_received", ZERO),
                total_payable=p.get("total_payable", ZERO),
                total_paid=p.get("total_paid", ZERO),
                invoice_count=invoice_counts.get(item.id, 0),
                company_profit_rate=rate,
                vendor_names=vendor_names.get(item.id),
                contract_amount=contract_amounts.get(item.case_code),
                winning_amount=case_amounts.get(item.case_code, {}).get("winning"),
            )
            resp.anomalies = anomaly_map.get(item.id, [])
            responses.append(resp)
        return responses, total

    async def _get_vendor_names_batch(self, quotation_ids: List[int]) -> dict:
        """quotation_id → 協力廠商名（應付上的廠商，去重、頓號分隔），一次查完。"""
        if not quotation_ids:
            return {}
        from sqlalchemy import text as _t
        rows = await self.db.execute(_t(
            "SELECT erp_quotation_id, string_agg(DISTINCT vendor_name, '、' ORDER BY vendor_name) "
            "FROM erp_vendor_payables WHERE erp_quotation_id = ANY(CAST(:ids AS int[])) AND vendor_name IS NOT NULL "
            "GROUP BY erp_quotation_id"
        ), {"ids": list(quotation_ids)})
        return {r[0]: r[1] for r in rows.all()}

    async def _get_contract_amounts_batch(self, case_codes: List[str]) -> dict:
        """case_code → 契約金額（contract_amount）。未成案沒有值。"""
        return {k: v["contract"] for k, v in (await self._get_case_amounts_batch(case_codes)).items() if v["contract"] is not None}

    async def _get_case_amounts_batch(self, case_codes: List[str]) -> dict:
        """case_code → {contract: 契約金額, winning: 議價金額, awarded: 承攬金額}。

        2026-09-04 晚 owner「/contract-cases/194 實際費用為議價而非契約金額」：
        契約金額＝成案時的報價（投標）金額；議價金額＝決標後實際承攬金額；
        **承攬金額＝COALESCE(NULLIF(議價,0), 契約)**，應收面（第一期請款、應收總額、統計卡）一律用它。
        """
        codes = [c for c in set(case_codes) if c]
        if not codes:
            return {}
        from sqlalchemy import text as _t
        from app.services.stats.finance import awarded_amount_case_only, winning_amount_expr
        # 2026-09-09：三個欄位的算式都從中心服務拿（L149）；此前 awarded 在 Python 端自己組第二份
        rows = await self.db.execute(_t(
            f"SELECT c.case_code, c.contract_amount, {winning_amount_expr('c')} AS winning, "
            f"{awarded_amount_case_only('c')} AS awarded "
            "FROM contract_projects c WHERE c.case_code = ANY(CAST(:codes AS text[]))"
        ), {"codes": codes})
        out = {}
        for r in rows.all():
            out[r[0]] = {"contract": r[1], "winning": r[2], "awarded": r[3]}
        return out


    async def _get_client_names_batch(self, case_codes: List[str]) -> dict:
        """case_code → 委託單位名。**主檔優先，快照只是回退。**

        ⚠️ 2026-09-07 owner：「委託單位『何明利』已修正為『汎宇藥業股份有限公司』，
        但檢索仍僅對應何明利」＋「即時刷新紀錄機制？」

        原本這裡只讀 `contract_projects.client_agency` 與 `pm_cases.client_name` ——
        那兩個是**建案當下抄下來的快照**。改了委託單位主檔，快照不會跟著動，
        於是列表與篩選下拉都還顯示舊名字，而**沒有任何地方會報錯**。

        ⇒ 有 `client_vendor_id`（鍵）時一律以主檔的名字為準。
        這就是「即時刷新」——改主檔一次，所有讀這條路徑的畫面立刻同步，
        不需要另外跑一支同步程式，也不會有「同步漏了幾筆」這種狀態。
        名稱是快照、鍵才是關聯（weekly 107 同族）。

        ⚠️ 快照仍留著且仍是回退值：沒有鍵的舊資料（純文字客戶）只有它。
        """
        codes = [c for c in set(case_codes) if c]
        if not codes:
            return {}
        from sqlalchemy import text as _t
        rows = await self.db.execute(_t(
            "SELECT x.cc, COALESCE(vc.vendor_name, vp.vendor_name, c.client_agency, p.client_name) AS name "
            "FROM unnest(CAST(:codes AS text[])) AS x(cc) "
            "LEFT JOIN contract_projects c ON c.case_code = x.cc "
            "LEFT JOIN pm_cases p ON p.case_code = x.cc "
            "LEFT JOIN partner_vendors vc ON vc.id = c.client_vendor_id "
            "LEFT JOIN partner_vendors vp ON vp.id = p.client_vendor_id"
        ), {"codes": codes})
        return {r[0]: r[1] for r in rows.fetchall() if r[1]}

    async def _get_staff_names_batch(self, case_codes: List[str]) -> dict:
        """整批取每個 case_code 的承辦同仁姓名。

        owner 2026-08-21：「報價單也尚未對應承辦同仁」。

        ⚠️ **2026-08-31 更正：原本這段寫「承辦同仁掛在
        `project_user_assignments.case_code` 上」—— 那句話只對一半。**

        `project_user_assignments` 有兩條綁法，而且是**互斥地**使用：
          · `case_code` —— 邀標／報價階段，還沒成案、沒有 project_id 可寫
          · `project_id` —— 成案之後從承攬案件那一側指派

        只比 `case_code` 的話，**成案後才指派的承辦全部查不到**。
        owner 回報 `/erp/quotations/541` 沒有承辦；實查該案
        （CK2026_GN_02_001）有承攬案件 id 200、也有指派 id 249，
        而那筆指派的 `case_code` 是空的、只綁 `project_id=200`。
        全庫實測 **7 張報價單**因此看不到承辦（168/170/171/172/175/389/541）。

        ⚠️ 這是**同族第七處**。2026-08-29 一天內修了四處
        （quotation_document／filing_gap／project_repository／
        get_user_accessible_project_ids），隔一輪又在 rls_filter 找到兩處，
        而這一處是 owner 從畫面上回報才發現的。
        ⇒ 「修完第一處要 grep 整個 repo」這件事，我到現在還沒做徹底。

        **不另建一套人員關聯**：邀標案件（`/pm/cases/:id?tab=staff`）看到的
        就是同一份，兩邊各自維護一份人員名單才是問題的開始。

        ADR-0025：以 canonical 人為準 —— 分身帳號不得顯示成另一個人。
        """
        # 2026-09-07：SQL 已搬到 `repositories/erp/case_staff.py`（唯一家）。
        # 留在這裡的只是委派 —— 同族此前有八份各自演化的實作，其中一半漏掉
        # `project_id` 那條綁法。要問承辦的人請 import 那一支，不要再抄一次。
        from app.repositories.erp.case_staff import staff_names_by_case_code
        return await staff_names_by_case_code(self.db, case_codes)

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
        client_name: Optional[str] = None,
        creator_name: Optional[str] = None,
        vendor_names: Optional[str] = None,
        contract_amount=None,
        winning_amount=None,
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
            vendor_names=vendor_names,
            contract_amount=contract_amount,
            winning_amount=winning_amount,
            staff_name=staff_name,
            client_name=client_name,
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
            # 2026-09-05：詳情頁也要「承攬金額（含稅）」——把承攬案的契約金額／議價金額帶回（列表路徑另有批次版）
            from sqlalchemy import text as _txt
            from app.services.stats.finance import winning_amount_expr
            amt_row = (await self.db.execute(_txt(
                f"SELECT c.contract_amount, {winning_amount_expr('c')} FROM contract_projects c WHERE c.case_code = :c LIMIT 1"
            ), {"c": case_code})).first()
            if amt_row is not None:
                if amt_row[0] is not None:
                    out["contract_amount"] = amt_row[0]
                if amt_row[1] is not None:
                    out["winning_amount"] = amt_row[1]
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

    async def get_client_options(self, year: Optional[int] = None, category: Optional[str] = None,
                                 accessible_case_codes=None) -> list[dict]:
        """委託單位篩選的選項＝**案件實際的客戶**，不是主檔的 vendor_type=client。

        2026-09-04 owner「委託單位篩選無法正確檢索案件」：選項此前取自主檔 client 型，但
        ①大有國際／秋森萬在主檔是 subcontractor 型卻也是三個承攬案的委託單位 ⇒ 下拉沒有它們；
        ②張啟良／張啓良（異體字）／張啟良建築師三筆主檔並存，選到不對的那筆就 0 筆。
        取案件真有的名字，選了必然找得到。
        """
        # 2026-09-04 晚 owner「下拉篩選對應仍有錯誤」：選項若不跟年度／類別走，178 家裡 84 家在頁面預設 2026 下
        # 選了就是空表——選項數字說有 2 筆、列表 0 筆。選項必須與列表**同一個範圍**（§2.6 ①：卡片與選項都是分母）。
        from sqlalchemy import text as _text
        scope = "q.deleted_at IS NULL"
        params: dict = {}
        if year:
            scope += " AND q.case_code LIKE :yr"
            params["yr"] = f"CK{int(year)}_%"
        if category in ("01", "02"):
            scope += " AND q.case_code ~ :cat"
            params["cat"] = r"^CK\d{4}_(PM_)?" + category + "_"
        # ⭐ 2026-09-08 owner：「相關下拉選單…防呆機制」。
        # 選項也要跟身分範圍走 —— 否則業務同仁的下拉列出全公司 178 家委託單位，
        # 選了任何一家都是空表（他的案裡沒有那一家），
        # 而畫面上只會顯示「查無資料」，看不出是權限範圍造成的。
        if accessible_case_codes is not None:
            codes = list(accessible_case_codes) or ["__none__"]
            scope += " AND q.case_code = ANY(:codes)"
            params["codes"] = codes
        sql = """
            SELECT name, SUM(n)::int AS n FROM (
              -- 2026-09-07：名字一律**主檔優先**（`COALESCE(主檔, 快照)`），與列表同一套。
              -- 兩邊不一致的後果是：下拉列出舊名、列表顯示新名 ⇒ 選了就是空表，
              -- 而不會有任何錯誤訊息（owner 09-07 回報「檢索仍僅對應何明利」）。
              SELECT btrim(COALESCE(vc.vendor_name, c.client_agency)) AS name, count(DISTINCT q.id) AS n
              FROM contract_projects c JOIN erp_quotations q ON q.case_code = c.case_code AND __SCOPE__
              LEFT JOIN partner_vendors vc ON vc.id = c.client_vendor_id
              WHERE COALESCE(vc.vendor_name, c.client_agency) IS NOT NULL
                AND btrim(COALESCE(vc.vendor_name, c.client_agency)) <> '' GROUP BY 1
              UNION ALL
              SELECT btrim(COALESCE(vp.vendor_name, p.client_name)), count(DISTINCT q.id)
              FROM pm_cases p JOIN erp_quotations q ON q.case_code = p.case_code AND __SCOPE__
              JOIN contract_projects c ON c.case_code = p.case_code
              LEFT JOIN partner_vendors vp ON vp.id = p.client_vendor_id
              WHERE COALESCE(vp.vendor_name, p.client_name) IS NOT NULL
                AND btrim(COALESCE(vp.vendor_name, p.client_name)) <> ''
                AND NOT EXISTS (SELECT 1 FROM contract_projects c2 WHERE c2.case_code = p.case_code AND btrim(c2.client_agency) = btrim(p.client_name))
              GROUP BY 1
            ) t GROUP BY name ORDER BY name
        """.replace("__SCOPE__", scope)
        rows = (await self.db.execute(_text(sql), params)).all()
        return [{"name": r.name, "count": r.n} for r in rows]

    async def get_profit_summary(
        self, params: Optional[ERPQuotationListRequest] = None, *,
        year: Optional[int] = None, search: Optional[str] = None,
        category: Optional[str] = None, client_name: Optional[str] = None,
        accessible_case_codes=None, staff_user_id: Optional[int] = None,
    ) -> ERPProfitSummary:
        """年度損益摘要 — 批次聚合消除 N+1（與列表同一組條件：年度／關鍵字／類別／委託單位，統計卡是列表的分母）

        ⭐ 2026-09-08 owner 圈出：列表只有 3 案，而「承攬金額」卡寫著 108,108,873。

        原因是**列表限縮了身分範圍、統計卡沒有** —— 卡片走這一支，
        而這一支從來不知道「誰在看」。於是業務同仁看到的是
        「我的 3 個案」配上「全公司的一億」，兩個數字放在同一個畫面上互相矛盾。

        ⚠️ 這與 §2.6 ①「卡片的分母不隨自己的篩選變動」**不衝突**：
        身分範圍不是使用者的篩選，它是這個人看得到的全部 ——
        分母可以不隨勾選變，但不能超出他看得到的範圍。
        """
        # 2026-09-09 owner：選了承辦「邱元宏」，列表 85 張而卡片 2,149 萬（全公司 112 張）——
        # 列表用 `narrow_scope_to_staff` 交集承辦案號，這裡此前沒有。同一份 helper，不再各寫一份。
        if params is None:  # 舊呼叫形狀（關鍵字引數）——組成同一份 schema，走同一條解析
            params = ERPQuotationListRequest(
                year=year, search=search or None, category=category or None,
                client_name=client_name or None, staff_user_id=staff_user_id)
        items, _ = await self.repo.filter_quotations(
            **(await self._filter_kwargs(params, accessible_case_codes, for_stats=True)),
            skip=0, limit=9999,
        )

        total_revenue = ZERO
        total_awarded = ZERO
        total_cost = ZERO
        total_gross = ZERO

        # 批次取得請款聚合
        ids = [q.id for q in items]
        billing_agg = await self.billing_repo.get_aggregates_batch(ids) if ids else {}
        rate = await get_company_profit_rate(self.db)
        payable_agg = await self.payable_repo.get_aggregates_batch(ids) if ids else {}
        total_payable = sum((v.get("total_payable", ZERO) for v in payable_agg.values()), ZERO)

        awarded_map = await self._get_case_amounts_batch([q.case_code for q in items])
        for q in items:
            profit = self.compute_profit(q, rate)
            price = Decimal(str(q.total_price or 0))
            tax = Decimal(str(q.tax_amount or 0))
            # 2026-09-04 晚：有議價金額的案，應收以承攬金額為準（含稅）；未稅＝承攬金額 − 依同比例換算的稅
            amounts = awarded_map.get(q.case_code) or {}
            winning = amounts.get("winning")
            if winning is not None and price > 0:
                w = Decimal(str(winning))
                total_revenue += w - (tax * w / price).quantize(Decimal("1"))
            else:
                total_revenue += price - tax
            # 2026-09-05 owner「是否皆以含稅呈現」：應收總額（含稅）＝承攬金額（議價→契約→報價總價），
            # 與 /contract-cases 的承攬金額合計是同一個算法 ⇒ 兩頁數字相等。winning 是 Float，先整數化去 .5 雜訊。
            awarded = amounts.get("awarded")
            total_awarded += Decimal(str(awarded)) if awarded is not None else price
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

        # 兩頁同一種進位：先加總再四捨五入（逐列進位會與承攬案頁差 1）
        total_awarded = total_awarded.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return ERPProfitSummary(
            total_revenue=total_revenue,
            total_awarded=total_awarded,
            total_cost=total_cost,
            total_gross_profit=total_gross,
            avg_gross_margin=avg_margin,
            total_billed=total_billed,
            total_received=total_received,
            # 2026-09-09：應收未收＝承攬金額－已收款（不是已請款－已收款）。
            # 已請款改成只認有請款日期的請款單後，兩者才分得開：佔位是應收、不是已請款。
            total_outstanding=total_awarded - total_received,
            total_payable=total_payable,
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

        from app.services.stats.finance import payable_amount_agg
        # 未付應付＝應付合計片段（中心服務）＋ payment_status 條件；SUM 本來就略過 NULL，結果與舊寫法相同
        row = (await self.db.execute(_sql(
            f"SELECT {payable_amount_agg('p')} FROM erp_vendor_payables p "
            "WHERE p.erp_quotation_id = :qid AND p.payment_status <> 'paid'"
        ), {"qid": quotation_id})).scalar()
        pending += Decimal(str(row or 0))

        return {"actual_cost": actual, "pending_cost": pending}


    async def _to_response(self, quotation: ERPQuotation) -> ERPQuotationResponse:
        """轉換為回應格式 (含計算欄位 + 聚合)"""
        profit = self.compute_profit(
            quotation, await get_company_profit_rate(self.db)
        )

        invoices = await self.invoice_repo.get_by_quotation_id(quotation.id)
        # 客戶名：承攬案優先、回退 PM 案（與 quotation_document 同規則）
        from sqlalchemy import text as _t
        client_name = await self.db.scalar(_t(
            "SELECT COALESCE(c.client_agency, p.client_name) FROM (SELECT :cc AS cc) x "
            "LEFT JOIN contract_projects c ON c.case_code=x.cc LEFT JOIN pm_cases p ON p.case_code=x.cc LIMIT 1"
        ), {"cc": quotation.case_code})
        total_billed = await self.billing_repo.get_total_billed(quotation.id)
        total_received = await self.billing_repo.get_total_received(quotation.id)
        total_payable = await self.payable_repo.get_total_payable(quotation.id)
        total_paid = await self.payable_repo.get_total_paid(quotation.id)
        billings = await self.billing_repo.get_by_quotation_id(quotation.id)
        actual = await self._actual_cost(quotation.case_code, quotation.id)
        # 2026-09-05：詳情頁也要「承攬金額（含稅）」——帶承攬案的契約金額／議價金額（列表路徑用同一支批次）
        case_amt = (await self._get_case_amounts_batch([quotation.case_code])).get(quotation.case_code) or {}

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
            client_name=client_name,
            total_billed=total_billed,
            total_received=total_received,
            total_payable=total_payable,
            total_paid=total_paid,
            contract_amount=case_amt.get("contract"),
            winning_amount=case_amt.get("winning"),
        )

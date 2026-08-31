"""ERP 報價 Repository"""
import logging
from typing import Optional, List, Tuple

from typing import Dict, Any
from decimal import Decimal

from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPQuotation
from app.repositories.base_repository import BaseRepository
from app.repositories.sort_utils import resolve_sort_column

logger = logging.getLogger(__name__)


class ERPQuotationRepository(BaseRepository[ERPQuotation]):
    """報價/成本主檔資料存取"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, ERPQuotation)

    async def get_by_case_code(self, case_code: str) -> Optional[ERPQuotation]:
        """依案號查詢 (取最新一筆, 排除軟刪除)"""
        query = (
            select(ERPQuotation)
            .where(ERPQuotation.case_code == case_code)
            .where(ERPQuotation.deleted_at.is_(None))
            .order_by(ERPQuotation.id.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_max_case_code_by_prefix(self, prefix: str) -> Optional[str]:
        """取得指定前綴的最大案號"""
        query = (
            select(func.max(ERPQuotation.case_code))
            .where(ERPQuotation.case_code.like(f"{prefix}%"))
        )
        result = await self.db.execute(query)
        return result.scalar()

    async def exists_by_case_code(self, case_code: str) -> bool:
        """檢查案號是否存在 (排除軟刪除)"""
        query = select(func.count(ERPQuotation.id)).where(
            ERPQuotation.case_code == case_code,
            ERPQuotation.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def get_lookup_by_case_code(self, case_code: str) -> Optional[Dict[str, Any]]:
        """跨模組查詢用 — 依 case_code 回傳案號的摘要資訊 (含毛利計算)"""
        return await self._get_lookup(ERPQuotation.case_code == case_code)

    async def get_lookup_by_project_code(
        self, project_code: str
    ) -> Optional[Dict[str, Any]]:
        """跨模組查詢用 — 依 project_code（成案編號）查同一份報價。

        2026-07-29 補：承攬案件詳情頁「財務紀錄」已傳 `case_code || project_code`
        （意圖 fallback），但查詢層原本只比對 `case_code` 欄位 → fallback 從未成立。
        實測 71 筆報價中 **49 筆兩碼不同值**，故對「無 case_code 但有 project_code」
        的案件必然查不到（半接通）。
        """
        return await self._get_lookup(ERPQuotation.project_code == project_code)

    async def _get_lookup(self, where_clause) -> Optional[Dict[str, Any]]:
        """跨模組摘要查詢單一實作（毛利計算只有一份，避免 case/project 兩路漂移）。"""
        query = select(
            ERPQuotation.id, ERPQuotation.case_name, ERPQuotation.status,
            ERPQuotation.total_price,
            ERPQuotation.outsourcing_fee, ERPQuotation.personnel_fee,
            ERPQuotation.overhead_fee, ERPQuotation.other_cost,
            ERPQuotation.tax_amount,
        ).where(where_clause)
        row = (await self.db.execute(query)).first()
        if not row:
            return None
        total_cost = (
            (row.outsourcing_fee or 0)
            + (row.personnel_fee or 0)
            + (row.overhead_fee or 0)
            + (row.other_cost or 0)
        )
        revenue = (row.total_price or 0) - (row.tax_amount or 0)
        gross_profit = revenue - total_cost

        # 2026-08-27 owner：「以利掌握公司專案資金管理」。
        #
        # 在此之前這裡只回**合約總價與毛利** —— 那是「這個案子談成多少」，
        # 回答不了「**收了多少、付了多少、還有多少沒收**」。
        # 承攬案件的「財務紀錄」分頁因此看不到任何實際金流。
        #
        # ⚠️ 請款與應付**掛在報價單**（只有 `erp_quotation_id`），
        # 不是掛在專案 ⇒ 這裡以 `row.id`（報價單 id）聚合是正確的路徑；
        # 若改用 project_code 會查不到而**回 0 不是報錯**。
        cash = (await self.db.execute(text("""
            SELECT
              COALESCE((SELECT SUM(billing_amount) FROM erp_billings
                         WHERE erp_quotation_id = :qid), 0)                 AS billed,
              COALESCE((SELECT SUM(payment_amount) FROM erp_billings
                         WHERE erp_quotation_id = :qid
                           AND payment_status = 'paid'), 0)                 AS received,
              COALESCE((SELECT SUM(payable_amount) FROM erp_vendor_payables
                         WHERE erp_quotation_id = :qid), 0)                 AS payable,
              COALESCE((SELECT SUM(paid_amount) FROM erp_vendor_payables
                         WHERE erp_quotation_id = :qid
                           AND payment_status = 'paid'), 0)                 AS paid
        """), {"qid": row.id})).one()

        return {
            "id": row.id,
            "case_name": row.case_name,
            "status": row.status,
            "total_price": str(row.total_price) if row.total_price else "0",
            "gross_profit": str(gross_profit),
            # 實際金流 —— 與上面的「合約總價／毛利」是**兩件事**：
            # 那是談定的，這是真的進出的。
            "billed_total": str(cash.billed),      # 已開立請款
            "received_total": str(cash.received),  # 已收款
            "unreceived": str(cash.billed - cash.received),
            "payable_total": str(cash.payable),    # 應付
            "paid_total": str(cash.paid),          # 已付
            "unpaid": str(cash.payable - cash.paid),
        }

    async def filter_quotations(
        self,
        year: Optional[int] = None,
        status: Optional[str] = None,
        case_code: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "id",
        sort_order: str = "desc",
        include_unawarded: bool = False,
        accessible_case_codes=None,
    ) -> Tuple[List[ERPQuotation], int]:
        """篩選報價列表。

        Args:
            include_unawarded: 是否納入未成案（無 contract_project）的報價單。
                預設 False —— owner 2026-08-31：「應改以成案案件為主，
                未成案承攬案件報價單參考價值低」。實測 257 張裡 93 張未成案，
                其中 90 張狀態是 confirmed 卻從未成案。
            accessible_case_codes: 可見範圍。**None ＝不限縮**（管理者或持有
                跨案查詢權限者）；給子查詢／清單則限縮到那些 case_code。
                ⚠️ 範圍由**呼叫端依身分**決定，不由請求參數決定 ——
                否則前端傳什麼就給什麼，等於沒有 RLS。
        """
        query = select(ERPQuotation).where(ERPQuotation.deleted_at.is_(None))
        count_query = select(func.count(ERPQuotation.id)).where(ERPQuotation.deleted_at.is_(None))

        conditions = []
        if year is not None:
            conditions.append(ERPQuotation.year == year)
        if status:
            conditions.append(ERPQuotation.status == status)
        if case_code:
            conditions.append(ERPQuotation.case_code == case_code)
        if search:
            conditions.append(or_(
                ERPQuotation.case_code.ilike(f"%{search}%"),
                ERPQuotation.case_name.ilike(f"%{search}%"),
            ))

        # 成案主軸：只留有承攬案件的報價單
        if not include_unawarded:
            from app.extended.models.core import ContractProject
            conditions.append(
                ERPQuotation.case_code.in_(
                    select(ContractProject.case_code).where(
                        ContractProject.case_code.isnot(None)
                    )
                )
            )

        # 可見範圍（None ＝ 不限縮）
        if accessible_case_codes is not None:
            conditions.append(ERPQuotation.case_code.in_(accessible_case_codes))

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        sort_col = resolve_sort_column(ERPQuotation, sort_by, ERPQuotation.id)
        if sort_order == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total

    async def get_yearly_trend_sql(self) -> list:
        """多年度損益趨勢 — 純 SQL 聚合 (取代 limit=9999 全表載入)"""
        query = (
            select(
                ERPQuotation.year,
                func.count(ERPQuotation.id).label("case_count"),
                func.coalesce(func.sum(ERPQuotation.total_price), 0).label("sum_price"),
                func.coalesce(func.sum(ERPQuotation.tax_amount), 0).label("sum_tax"),
                func.coalesce(func.sum(ERPQuotation.outsourcing_fee), 0).label("sum_out"),
                func.coalesce(func.sum(ERPQuotation.personnel_fee), 0).label("sum_pers"),
                func.coalesce(func.sum(ERPQuotation.overhead_fee), 0).label("sum_over"),
                func.coalesce(func.sum(ERPQuotation.other_cost), 0).label("sum_other"),
            )
            .where(ERPQuotation.year.isnot(None))
            .where(ERPQuotation.deleted_at.is_(None))
            .group_by(ERPQuotation.year)
            .order_by(ERPQuotation.year)
        )
        result = await self.db.execute(query)
        # 公司留成比率整批取一次（2026-08-18）。年度趨勢是逐年聚合後才算毛利，
        # 所以留成也是對「該年度營收總額」扣一次 —— 與逐案扣再加總的結果相同
        # （比率固定，乘法可分配），差異只在四捨五入的分位。
        from app.services.erp.company_profit import get_company_profit_rate
        rate = await get_company_profit_rate(self.db)
        rows = []
        for r in result.all():
            from app.services.erp.quotation_service import compute_quotation_profit
            profit = compute_quotation_profit(
                total_price=r.sum_price, tax_amount=r.sum_tax,
                outsourcing_fee=r.sum_out, personnel_fee=r.sum_pers,
                overhead_fee=r.sum_over, other_cost=r.sum_other,
                company_profit_rate=rate,
            )
            rows.append({
                "year": r.year,
                "revenue": Decimal(str(r.sum_price)) - Decimal(str(r.sum_tax)),
                "cost": profit["total_cost"],
                "gross_profit": profit["gross_profit"],
                "gross_margin": profit["gross_margin"],
                "case_count": r.case_count,
            })
        return rows

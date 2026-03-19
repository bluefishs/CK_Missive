"""ERP 報價 Repository"""
import logging
from typing import Optional, List, Tuple

from typing import Dict, Any
from decimal import Decimal

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPQuotation
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ERPQuotationRepository(BaseRepository[ERPQuotation]):
    """報價/成本主檔資料存取"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, ERPQuotation)

    async def get_by_case_code(self, case_code: str) -> Optional[ERPQuotation]:
        """依案號查詢 (取最新一筆)"""
        query = (
            select(ERPQuotation)
            .where(ERPQuotation.case_code == case_code)
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
        """檢查案號是否存在"""
        query = select(func.count(ERPQuotation.id)).where(ERPQuotation.case_code == case_code)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def get_lookup_by_case_code(self, case_code: str) -> Optional[Dict[str, Any]]:
        """跨模組查詢用 — 回傳案號的摘要資訊 (含毛利計算)"""
        query = select(
            ERPQuotation.id, ERPQuotation.case_name, ERPQuotation.status,
            ERPQuotation.total_price,
            ERPQuotation.outsourcing_fee, ERPQuotation.personnel_fee,
            ERPQuotation.overhead_fee, ERPQuotation.other_cost,
            ERPQuotation.tax_amount,
        ).where(ERPQuotation.case_code == case_code)
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
        return {
            "id": row.id,
            "case_name": row.case_name,
            "status": row.status,
            "total_price": str(row.total_price) if row.total_price else "0",
            "gross_profit": str(gross_profit),
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
    ) -> Tuple[List[ERPQuotation], int]:
        """篩選報價列表"""
        query = select(ERPQuotation)
        count_query = select(func.count(ERPQuotation.id))

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

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        sort_col = getattr(ERPQuotation, sort_by, ERPQuotation.id)
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
            .group_by(ERPQuotation.year)
            .order_by(ERPQuotation.year)
        )
        result = await self.db.execute(query)
        rows = []
        for r in result.all():
            revenue = Decimal(str(r.sum_price)) - Decimal(str(r.sum_tax))
            cost = (
                Decimal(str(r.sum_out)) + Decimal(str(r.sum_pers))
                + Decimal(str(r.sum_over)) + Decimal(str(r.sum_other))
            )
            gross = revenue - cost
            margin = None
            if revenue > 0:
                from decimal import ROUND_HALF_UP
                margin = (gross / revenue * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            rows.append({
                "year": r.year,
                "revenue": revenue,
                "cost": cost,
                "gross_profit": gross,
                "gross_margin": margin,
                "case_count": r.case_count,
            })
        return rows

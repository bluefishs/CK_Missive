"""PM 案件 Repository"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy import Integer, case, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.pm import PMCase
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class PMCaseRepository(BaseRepository[PMCase]):
    """案件主檔資料存取"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, PMCase)

    async def get_by_case_code(self, case_code: str) -> Optional[PMCase]:
        """依案號查詢"""
        return await self.find_one_by(case_code=case_code)

    async def get_max_case_code_by_prefix(self, prefix: str) -> Optional[str]:
        """取得指定前綴的最大案號"""
        query = (
            select(func.max(PMCase.case_code))
            .where(PMCase.case_code.like(f"{prefix}%"))
        )
        result = await self.db.execute(query)
        return result.scalar()

    async def exists_by_case_code(self, case_code: str) -> bool:
        """檢查案號是否存在"""
        query = select(func.count(PMCase.id)).where(PMCase.case_code == case_code)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def get_lookup_by_case_code(self, case_code: str) -> Optional[Dict[str, Any]]:
        """跨模組查詢用 — 回傳案號的摘要資訊"""
        query = select(
            PMCase.id, PMCase.case_name, PMCase.status, PMCase.progress
        ).where(PMCase.case_code == case_code)
        row = (await self.db.execute(query)).first()
        if not row:
            return None
        return {
            "id": row.id,
            "case_name": row.case_name,
            "status": row.status,
            "progress": row.progress,
        }

    async def filter_cases(
        self,
        year: Optional[int] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        client_name: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "id",
        sort_order: str = "desc",
    ) -> Tuple[List[PMCase], int]:
        """篩選案件列表"""
        query = select(PMCase)
        count_query = select(func.count(PMCase.id))

        conditions = []
        if year is not None:
            conditions.append(PMCase.year == year)
        if status:
            conditions.append(PMCase.status == status)
        if category:
            conditions.append(PMCase.category == category)
        if client_name:
            conditions.append(PMCase.client_name.ilike(f"%{client_name}%"))
        if search:
            conditions.append(or_(
                PMCase.case_code.ilike(f"%{search}%"),
                PMCase.case_name.ilike(f"%{search}%"),
                PMCase.client_name.ilike(f"%{search}%"),
            ))

        if conditions:
            from sqlalchemy import and_
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # 排序
        sort_col = getattr(PMCase, sort_by, PMCase.id)
        if sort_order == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        # 分頁
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total

    async def get_summary(
        self, year: Optional[int] = None
    ) -> Dict[str, Any]:
        """取得案件統計摘要"""
        base = select(PMCase)
        if year is not None:
            base = base.where(PMCase.year == year)

        # 總數
        total_q = select(func.count(PMCase.id))
        if year is not None:
            total_q = total_q.where(PMCase.year == year)
        total = (await self.db.execute(total_q)).scalar() or 0

        # 依狀態分組
        status_q = (
            select(PMCase.status, func.count(PMCase.id))
            .group_by(PMCase.status)
        )
        if year is not None:
            status_q = status_q.where(PMCase.year == year)
        status_result = await self.db.execute(status_q)
        by_status = {row[0] or "unknown": row[1] for row in status_result.all()}

        # 合約總額
        amount_q = select(func.sum(PMCase.contract_amount))
        if year is not None:
            amount_q = amount_q.where(PMCase.year == year)
        total_amount = (await self.db.execute(amount_q)).scalar()

        return {
            "total_cases": total,
            "by_status": by_status,
            "total_contract_amount": total_amount,
        }

    async def get_yearly_trend_sql(self) -> List[Dict[str, Any]]:
        """多年度趨勢 — 純 SQL 聚合 (取代 limit=9999 全表載入)"""
        query = (
            select(
                PMCase.year,
                func.count(PMCase.id).label("case_count"),
                func.coalesce(func.sum(PMCase.contract_amount), 0).label("total_contract"),
                func.sum(
                    case((PMCase.status == "closed", 1), else_=0)
                ).label("closed_count"),
                func.sum(
                    case((PMCase.status == "in_progress", 1), else_=0)
                ).label("in_progress_count"),
                func.coalesce(func.avg(PMCase.progress), 0).label("avg_progress"),
            )
            .where(PMCase.year.isnot(None))
            .group_by(PMCase.year)
            .order_by(PMCase.year)
        )
        result = await self.db.execute(query)
        return [
            {
                "year": row.year,
                "case_count": row.case_count,
                "total_contract": Decimal(str(row.total_contract)),
                "closed_count": int(row.closed_count or 0),
                "in_progress_count": int(row.in_progress_count or 0),
                "avg_progress": round(float(row.avg_progress)),
            }
            for row in result.all()
        ]

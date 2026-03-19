"""ERP 請款 Repository"""
import logging
from typing import Any, Dict, List
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPBilling
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ERPBillingRepository(BaseRepository[ERPBilling]):
    """請款資料存取"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, ERPBilling)

    async def get_by_quotation_id(self, quotation_id: int) -> List[ERPBilling]:
        """取得報價單所有請款"""
        query = (
            select(ERPBilling)
            .where(ERPBilling.erp_quotation_id == quotation_id)
            .order_by(ERPBilling.billing_date.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_total_billed(self, quotation_id: int) -> Decimal:
        """取得報價單累計請款金額"""
        query = (
            select(func.coalesce(func.sum(ERPBilling.billing_amount), 0))
            .where(ERPBilling.erp_quotation_id == quotation_id)
        )
        result = await self.db.execute(query)
        return Decimal(str(result.scalar() or 0))

    async def get_total_received(self, quotation_id: int) -> Decimal:
        """取得報價單累計收款金額"""
        query = (
            select(func.coalesce(func.sum(ERPBilling.payment_amount), 0))
            .where(
                ERPBilling.erp_quotation_id == quotation_id,
                ERPBilling.payment_amount.isnot(None),
            )
        )
        result = await self.db.execute(query)
        return Decimal(str(result.scalar() or 0))

    async def get_aggregates_batch(
        self, quotation_ids: List[int],
    ) -> Dict[int, Dict[str, Any]]:
        """批次取得多筆報價的請款聚合 (消除 N+1)

        Returns:
            {quotation_id: {"count": int, "total_billed": Decimal, "total_received": Decimal}}
        """
        if not quotation_ids:
            return {}

        query = (
            select(
                ERPBilling.erp_quotation_id,
                func.count(ERPBilling.id).label("cnt"),
                func.coalesce(func.sum(ERPBilling.billing_amount), 0).label("billed"),
                func.coalesce(func.sum(ERPBilling.payment_amount), 0).label("received"),
            )
            .where(ERPBilling.erp_quotation_id.in_(quotation_ids))
            .group_by(ERPBilling.erp_quotation_id)
        )
        result = await self.db.execute(query)
        rows = result.all()

        agg: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            agg[row.erp_quotation_id] = {
                "count": row.cnt,
                "total_billed": Decimal(str(row.billed)),
                "total_received": Decimal(str(row.received)),
            }
        return agg

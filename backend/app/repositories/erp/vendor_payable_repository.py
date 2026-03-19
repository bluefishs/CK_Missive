"""ERP 廠商應付 Repository"""
import logging
from typing import Any, Dict, List
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPVendorPayable
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

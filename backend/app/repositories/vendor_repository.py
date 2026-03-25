"""
VendorRepository - 廠商資料存取層

提供廠商相關的資料庫查詢操作，包含：
- 廠商特定查詢方法
- 專案關聯查詢
- 統計方法
- 關聯檢查

版本: 1.0.0
建立日期: 2026-01-28
"""

import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc

from app.repositories.base_repository import BaseRepository
from app.extended.models import (
    PartnerVendor,
    project_vendor_association,
    ContractProject,
)

logger = logging.getLogger(__name__)


class VendorRepository(BaseRepository[PartnerVendor]):
    """
    廠商資料存取層

    繼承 BaseRepository 並擴展廠商特定的查詢方法。

    Example:
        vendor_repo = VendorRepository(db)

        # 基本查詢
        vendor = await vendor_repo.get_by_id(1)

        # 廠商特定查詢
        filtered = await vendor_repo.filter_vendors(search='建設')
        stats = await vendor_repo.get_vendor_statistics()
    """

    SEARCH_FIELDS = ['vendor_name', 'vendor_code']

    def __init__(self, db: AsyncSession):
        """初始化廠商 Repository"""
        super().__init__(db, PartnerVendor)

    # =========================================================================
    # 廠商特定查詢方法
    # =========================================================================

    async def get_by_code(self, vendor_code: str) -> Optional[PartnerVendor]:
        """根據統一編號取得廠商"""
        return await self.find_one_by(vendor_code=vendor_code)

    async def get_by_name(self, vendor_name: str) -> Optional[PartnerVendor]:
        """根據廠商名稱取得廠商"""
        return await self.find_one_by(vendor_name=vendor_name)

    async def filter_vendors(
        self,
        search: Optional[str] = None,
        vendor_type: Optional[str] = None,
        business_type: Optional[str] = None,
        rating: Optional[int] = None,
        sort_by: str = 'vendor_name',
        sort_order: str = 'asc',
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[PartnerVendor], int]:
        """
        篩選廠商列表

        Returns:
            (廠商列表, 總筆數)
        """
        query = select(PartnerVendor)
        count_query = select(func.count(PartnerVendor.id))
        filters = []

        if vendor_type:
            filters.append(PartnerVendor.vendor_type == vendor_type)

        if search:
            search_conditions = [
                getattr(PartnerVendor, field).ilike(f"%{search}%")
                for field in self.SEARCH_FIELDS
                if hasattr(PartnerVendor, field)
            ]
            if search_conditions:
                filters.append(or_(*search_conditions))

        if business_type:
            filters.append(PartnerVendor.business_type == business_type)

        if rating is not None:
            filters.append(PartnerVendor.rating == rating)

        if filters:
            combined = and_(*filters)
            query = query.where(combined)
            count_query = count_query.where(combined)

        # 排序
        sort_column = getattr(PartnerVendor, sort_by, PartnerVendor.vendor_name)
        order_fn = asc if sort_order == 'asc' else desc
        query = query.order_by(order_fn(sort_column))

        # 分頁
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total

    # =========================================================================
    # 關聯查詢
    # =========================================================================

    async def check_vendor_associations(self, vendor_id: int) -> Dict[str, int]:
        """
        檢查廠商的關聯使用情況

        Returns:
            各關聯類型的使用數量
        """
        # 專案關聯
        project_count_result = await self.db.execute(
            select(func.count())
            .select_from(project_vendor_association)
            .where(project_vendor_association.c.vendor_id == vendor_id)
        )
        project_count = project_count_result.scalar() or 0

        return {
            "project_count": project_count,
            "total": project_count,
        }

    # =========================================================================
    # 統計方法
    # =========================================================================

    async def get_financial_summary(self, vendor_id: int) -> Dict[str, Any]:
        """
        廠商財務彙總 — 跨模組 JOIN 查詢應付/報銷/帳本

        Args:
            vendor_id: 廠商 ID

        Returns:
            包含應付帳款、報銷發票、帳本彙總的字典
        """
        from app.extended.models.erp import ERPVendorPayable
        from app.extended.models.invoice import ExpenseInvoice
        from app.extended.models.finance import FinanceLedger

        # 1. 應付帳款彙總
        payable_stmt = select(
            func.coalesce(func.sum(ERPVendorPayable.payable_amount), 0).label("total_payable"),
            func.coalesce(func.sum(ERPVendorPayable.paid_amount), 0).label("total_paid"),
            func.count(ERPVendorPayable.id).label("payable_count"),
        ).where(ERPVendorPayable.vendor_id == vendor_id)
        payable_row = (await self.db.execute(payable_stmt)).one()

        # 2. 報銷發票彙總 (透過 vendor_id)
        expense_stmt = select(
            func.coalesce(func.sum(ExpenseInvoice.amount), 0).label("total_expenses"),
            func.count(ExpenseInvoice.id).label("expense_count"),
        ).where(
            ExpenseInvoice.vendor_id == vendor_id,
            ExpenseInvoice.status != "rejected",
        )
        expense_row = (await self.db.execute(expense_stmt)).one()

        # 3. 帳本彙總 (直接 vendor_id)
        ledger_stmt = select(
            func.coalesce(func.sum(FinanceLedger.amount), 0).label("ledger_total"),
            func.count(FinanceLedger.id).label("ledger_count"),
        ).where(
            FinanceLedger.vendor_id == vendor_id,
            FinanceLedger.entry_type == "expense",
        )
        ledger_row = (await self.db.execute(ledger_stmt)).one()

        total_payable = Decimal(str(payable_row.total_payable))
        total_paid = Decimal(str(payable_row.total_paid))

        return {
            "total_payable": total_payable,
            "total_paid": total_paid,
            "pending_payable": total_payable - total_paid,
            "payable_count": payable_row.payable_count,
            "total_expenses": Decimal(str(expense_row.total_expenses)),
            "expense_count": expense_row.expense_count,
            "ledger_expense_total": Decimal(str(ledger_row.ledger_total)),
            "ledger_entry_count": ledger_row.ledger_count,
        }

    async def get_vendor_statistics(self) -> Dict[str, Any]:
        """取得廠商統計資訊"""
        # 總數
        total_result = await self.db.execute(
            select(func.count(PartnerVendor.id))
        )
        total = total_result.scalar() or 0

        # 按營業類型統計
        type_result = await self.db.execute(
            select(
                PartnerVendor.business_type,
                func.count(PartnerVendor.id)
            )
            .group_by(PartnerVendor.business_type)
            .order_by(func.count(PartnerVendor.id).desc())
        )
        by_type = [
            {"type": row[0] or "未分類", "count": row[1]}
            for row in type_result.all()
        ]

        return {
            "total": total,
            "by_type": by_type,
        }

    async def get_id_by_vendor_code(self, vendor_code: str) -> Optional[int]:
        """依 vendor_code (統編) 查詢廠商 ID"""
        result = await self.db.execute(
            select(PartnerVendor.id)
            .where(PartnerVendor.vendor_code == vendor_code)
            .limit(1)
        )
        return result.scalar_one_or_none()

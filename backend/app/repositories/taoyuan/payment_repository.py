"""
PaymentRepository - 契金管控資料存取層

提供契金管控的 CRUD 操作和特定查詢方法。

@version 1.0.0
@date 2026-01-28
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from ..base_repository import BaseRepository
from app.extended.models import (
    TaoyuanContractPayment,
    TaoyuanDispatchOrder,
    ContractProject,
)

logger = logging.getLogger(__name__)


class PaymentRepository(BaseRepository[TaoyuanContractPayment]):
    """
    契金管控資料存取層

    繼承 BaseRepository 並提供契金管控特定的查詢方法
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, TaoyuanContractPayment)

    # =========================================================================
    # 查詢方法
    # =========================================================================

    async def get_with_dispatch(
        self, payment_id: int
    ) -> Optional[TaoyuanContractPayment]:
        """
        取得契金記錄及其關聯的派工單

        Args:
            payment_id: 契金記錄 ID

        Returns:
            契金記錄（含派工單）或 None
        """
        query = (
            select(TaoyuanContractPayment)
            .options(selectinload(TaoyuanContractPayment.dispatch_order))
            .where(TaoyuanContractPayment.id == payment_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_dispatch_order(
        self, dispatch_order_id: int
    ) -> Optional[TaoyuanContractPayment]:
        """
        取得派工單的契金記錄

        Args:
            dispatch_order_id: 派工單 ID

        Returns:
            契金記錄或 None
        """
        return await self.find_one_by(dispatch_order_id=dispatch_order_id)

    async def filter_payments(
        self,
        dispatch_order_id: Optional[int] = None,
        contract_project_id: Optional[int] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[TaoyuanContractPayment], int]:
        """
        篩選契金記錄列表

        Args:
            dispatch_order_id: 派工單 ID
            contract_project_id: 承攬案件 ID
            page: 頁碼
            limit: 每頁筆數

        Returns:
            (契金記錄列表, 總筆數)
        """
        query = select(TaoyuanContractPayment).options(
            selectinload(TaoyuanContractPayment.dispatch_order)
        )

        if dispatch_order_id:
            query = query.where(
                TaoyuanContractPayment.dispatch_order_id == dispatch_order_id
            )
        elif contract_project_id:
            query = query.join(TaoyuanDispatchOrder).where(
                TaoyuanDispatchOrder.contract_project_id == contract_project_id
            )

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 分頁
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_contract_project(
        self, contract_project_id: int
    ) -> List[TaoyuanContractPayment]:
        """
        取得承攬案件下的所有契金記錄

        Args:
            contract_project_id: 承攬案件 ID

        Returns:
            契金記錄列表（按派工單號排序）
        """
        query = (
            select(TaoyuanContractPayment)
            .options(selectinload(TaoyuanContractPayment.dispatch_order))
            .join(TaoyuanDispatchOrder)
            .where(TaoyuanDispatchOrder.contract_project_id == contract_project_id)
            .order_by(TaoyuanDispatchOrder.dispatch_no)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # 累進計算
    # =========================================================================

    async def calculate_cumulative_payment(
        self,
        contract_project_id: int,
        current_dispatch_id: int,
    ) -> Tuple[float, float]:
        """
        計算累進派工金額和剩餘金額

        Args:
            contract_project_id: 承攬案件 ID
            current_dispatch_id: 當前派工單 ID

        Returns:
            (累進金額, 剩餘金額)
        """
        # 從承攬案件動態取得總預算
        budget_result = await self.db.execute(
            select(ContractProject.winning_amount, ContractProject.contract_amount)
            .where(ContractProject.id == contract_project_id)
        )
        budget_row = budget_result.first()
        total_budget = float(budget_row[0] or budget_row[1] or 0) if budget_row else 0

        # 查詢所有相同承攬案件的契金記錄
        all_payments = await self.get_by_contract_project(contract_project_id)

        # 計算累進金額
        cumulative = 0.0
        for payment in all_payments:
            cumulative += float(payment.current_amount or 0)
            if payment.dispatch_order_id == current_dispatch_id:
                break

        remaining = total_budget - cumulative
        return cumulative, remaining

    async def update_cumulative_amounts(
        self, contract_project_id: int
    ) -> int:
        """
        更新承攬案件下所有契金記錄的累進金額

        Args:
            contract_project_id: 承攬案件 ID

        Returns:
            更新的記錄數
        """
        payments = await self.get_by_contract_project(contract_project_id)
        updated_count = 0

        for payment in payments:
            cumulative, remaining = await self.calculate_cumulative_payment(
                contract_project_id, payment.dispatch_order_id
            )

            if (payment.cumulative_amount != cumulative or
                payment.remaining_amount != remaining):
                payment.cumulative_amount = cumulative
                payment.remaining_amount = remaining
                updated_count += 1

        if updated_count > 0:
            await self.db.commit()

        return updated_count

    # =========================================================================
    # 統計方法
    # =========================================================================

    async def get_project_summary(
        self, contract_project_id: int
    ) -> Dict[str, Any]:
        """
        取得承攬案件的契金彙總

        Args:
            contract_project_id: 承攬案件 ID

        Returns:
            彙總資料字典
        """
        # 取得預算
        budget_result = await self.db.execute(
            select(
                ContractProject.winning_amount,
                ContractProject.contract_amount,
                ContractProject.project_name,
            )
            .where(ContractProject.id == contract_project_id)
        )
        budget_row = budget_result.first()

        if not budget_row:
            return {
                "total_budget": 0,
                "total_payment": 0,
                "remaining": 0,
                "payment_count": 0,
            }

        total_budget = float(budget_row[0] or budget_row[1] or 0)
        project_name = budget_row[2]

        # 計算總支付金額
        sum_result = await self.db.execute(
            select(func.sum(TaoyuanContractPayment.current_amount))
            .join(TaoyuanDispatchOrder)
            .where(TaoyuanDispatchOrder.contract_project_id == contract_project_id)
        )
        total_payment = float(sum_result.scalar() or 0)

        # 計算記錄數
        count_result = await self.db.execute(
            select(func.count(TaoyuanContractPayment.id))
            .join(TaoyuanDispatchOrder)
            .where(TaoyuanDispatchOrder.contract_project_id == contract_project_id)
        )
        payment_count = count_result.scalar() or 0

        return {
            "project_name": project_name,
            "total_budget": total_budget,
            "total_payment": total_payment,
            "remaining": total_budget - total_payment,
            "payment_count": payment_count,
            "usage_percentage": (total_payment / total_budget * 100) if total_budget > 0 else 0,
        }

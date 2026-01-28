"""
TaoyuanStatisticsService - 桃園派工統計服務

提供桃園派工系統的綜合統計資料。

@version 1.0.0
@date 2026-01-28
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.repositories.taoyuan import (
    DispatchOrderRepository,
    TaoyuanProjectRepository,
    PaymentRepository,
)
from app.extended.models import (
    TaoyuanDispatchOrder,
    TaoyuanProject,
    TaoyuanContractPayment,
    ContractProject,
)

logger = logging.getLogger(__name__)


class TaoyuanStatisticsService:
    """
    桃園派工統計服務

    職責:
    - 綜合統計資料計算
    - 儀表板資料彙整
    - 進度追蹤
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dispatch_repo = DispatchOrderRepository(db)
        self.project_repo = TaoyuanProjectRepository(db)
        self.payment_repo = PaymentRepository(db)

    # =========================================================================
    # 綜合統計
    # =========================================================================

    async def get_overview_statistics(
        self, contract_project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        取得總覽統計

        Args:
            contract_project_id: 承攬案件 ID（可選）

        Returns:
            統計資料字典
        """
        # 派工單統計
        dispatch_stats = await self.dispatch_repo.get_statistics(contract_project_id)

        # 專案統計
        project_stats = await self.project_repo.get_statistics(contract_project_id)

        # 契金彙總
        payment_summary = {}
        if contract_project_id:
            payment_summary = await self.payment_repo.get_project_summary(
                contract_project_id
            )

        return {
            'dispatch': dispatch_stats,
            'project': project_stats,
            'payment': payment_summary,
            'generated_at': datetime.now().isoformat(),
        }

    async def get_dispatch_summary(
        self, contract_project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        取得派工單彙總

        Args:
            contract_project_id: 承攬案件 ID（可選）

        Returns:
            彙總資料
        """
        base_condition = (
            TaoyuanDispatchOrder.contract_project_id == contract_project_id
            if contract_project_id else True
        )

        # 總數
        total_query = select(func.count(TaoyuanDispatchOrder.id)).where(base_condition)
        total = (await self.db.execute(total_query)).scalar() or 0

        # 本月新增
        today = date.today()
        month_start = date(today.year, today.month, 1)
        this_month_query = select(func.count(TaoyuanDispatchOrder.id)).where(
            and_(
                base_condition,
                TaoyuanDispatchOrder.created_at >= month_start,
            )
        )
        this_month = (await self.db.execute(this_month_query)).scalar() or 0

        # 按作業類別統計
        work_type_query = (
            select(
                TaoyuanDispatchOrder.work_type,
                func.count(TaoyuanDispatchOrder.id),
            )
            .where(base_condition)
            .group_by(TaoyuanDispatchOrder.work_type)
        )
        result = await self.db.execute(work_type_query)
        by_work_type = [
            {'work_type': row[0] or '未分類', 'count': row[1]}
            for row in result.fetchall()
        ]

        # 逾期統計（履約期限已過但狀態非完成）
        overdue_query = select(func.count(TaoyuanDispatchOrder.id)).where(
            and_(
                base_condition,
                TaoyuanDispatchOrder.deadline < today,
            )
        )
        overdue = (await self.db.execute(overdue_query)).scalar() or 0

        return {
            'total': total,
            'this_month': this_month,
            'by_work_type': by_work_type,
            'overdue': overdue,
        }

    async def get_project_summary(
        self, contract_project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        取得專案彙總

        Args:
            contract_project_id: 承攬案件 ID（可選）

        Returns:
            彙總資料
        """
        base_condition = (
            TaoyuanProject.contract_project_id == contract_project_id
            if contract_project_id else True
        )

        # 總數
        total_query = select(func.count(TaoyuanProject.id)).where(base_condition)
        total = (await self.db.execute(total_query)).scalar() or 0

        # 按狀態統計
        status_query = (
            select(
                TaoyuanProject.status,
                func.count(TaoyuanProject.id),
            )
            .where(base_condition)
            .group_by(TaoyuanProject.status)
        )
        result = await self.db.execute(status_query)
        by_status = [
            {'status': row[0] or '未設定', 'count': row[1]}
            for row in result.fetchall()
        ]

        return {
            'total': total,
            'by_status': by_status,
        }

    async def get_payment_summary(
        self, contract_project_id: int
    ) -> Dict[str, Any]:
        """
        取得契金彙總

        Args:
            contract_project_id: 承攬案件 ID

        Returns:
            彙總資料
        """
        return await self.payment_repo.get_project_summary(contract_project_id)

    # =========================================================================
    # 進度追蹤
    # =========================================================================

    async def get_deadline_tracking(
        self, contract_project_id: Optional[int] = None,
        days_ahead: int = 30,
    ) -> Dict[str, Any]:
        """
        取得履約期限追蹤

        Args:
            contract_project_id: 承攬案件 ID（可選）
            days_ahead: 預警天數

        Returns:
            期限追蹤資料
        """
        today = date.today()
        warning_date = date.fromordinal(today.toordinal() + days_ahead)

        base_condition = (
            TaoyuanDispatchOrder.contract_project_id == contract_project_id
            if contract_project_id else True
        )

        # 已逾期
        overdue_query = (
            select(TaoyuanDispatchOrder)
            .where(
                and_(
                    base_condition,
                    TaoyuanDispatchOrder.deadline < today,
                )
            )
            .order_by(TaoyuanDispatchOrder.deadline.asc())
            .limit(10)
        )
        overdue_result = await self.db.execute(overdue_query)
        overdue_items = [
            {
                'id': item.id,
                'dispatch_no': item.dispatch_no,
                'project_name': item.project_name,
                'deadline': item.deadline.isoformat() if item.deadline else None,
                'days_overdue': (today - item.deadline).days if item.deadline else 0,
            }
            for item in overdue_result.scalars().all()
        ]

        # 即將到期
        upcoming_query = (
            select(TaoyuanDispatchOrder)
            .where(
                and_(
                    base_condition,
                    TaoyuanDispatchOrder.deadline >= today,
                    TaoyuanDispatchOrder.deadline <= warning_date,
                )
            )
            .order_by(TaoyuanDispatchOrder.deadline.asc())
            .limit(10)
        )
        upcoming_result = await self.db.execute(upcoming_query)
        upcoming_items = [
            {
                'id': item.id,
                'dispatch_no': item.dispatch_no,
                'project_name': item.project_name,
                'deadline': item.deadline.isoformat() if item.deadline else None,
                'days_remaining': (item.deadline - today).days if item.deadline else 0,
            }
            for item in upcoming_result.scalars().all()
        ]

        return {
            'overdue': {
                'count': len(overdue_items),
                'items': overdue_items,
            },
            'upcoming': {
                'count': len(upcoming_items),
                'items': upcoming_items,
            },
            'tracking_date': today.isoformat(),
            'warning_days': days_ahead,
        }

    # =========================================================================
    # 主控表報
    # =========================================================================

    async def get_master_control_report(
        self, contract_project_id: int
    ) -> Dict[str, Any]:
        """
        取得主控表報

        Args:
            contract_project_id: 承攬案件 ID

        Returns:
            主控表報資料
        """
        # 取得承攬案件資訊
        project_query = select(ContractProject).where(
            ContractProject.id == contract_project_id
        )
        project_result = await self.db.execute(project_query)
        project = project_result.scalar_one_or_none()

        if not project:
            return {'error': '承攬案件不存在'}

        # 取得統計資料
        overview = await self.get_overview_statistics(contract_project_id)
        dispatch_summary = await self.get_dispatch_summary(contract_project_id)
        project_summary = await self.get_project_summary(contract_project_id)
        deadline_tracking = await self.get_deadline_tracking(contract_project_id)

        return {
            'contract_project': {
                'id': project.id,
                'project_name': project.project_name,
                'project_code': project.project_code,
                'winning_amount': float(project.winning_amount or 0),
                'contract_amount': float(project.contract_amount or 0),
            },
            'overview': overview,
            'dispatch_summary': dispatch_summary,
            'project_summary': project_summary,
            'deadline_tracking': deadline_tracking,
            'generated_at': datetime.now().isoformat(),
        }

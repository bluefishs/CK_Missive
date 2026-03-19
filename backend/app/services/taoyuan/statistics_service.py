"""
TaoyuanStatisticsService - 桃園派工統計服務

提供桃園派工系統的綜合統計資料。

@version 2.0.0
@date 2026-03-18
@update 重構：直接 DB 查詢遷移至 TaoyuanStatisticsRepository
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.taoyuan import (
    DispatchOrderRepository,
    TaoyuanProjectRepository,
    PaymentRepository,
    TaoyuanStatisticsRepository,
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
        self.statistics_repo = TaoyuanStatisticsRepository(db)

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
        today = date.today()
        month_start = date(today.year, today.month, 1)

        total = await self.statistics_repo.count_dispatches(contract_project_id)
        this_month = await self.statistics_repo.count_dispatches_since(
            month_start, contract_project_id
        )
        work_type_counts = await self.statistics_repo.get_dispatch_counts_by_work_type(
            contract_project_id
        )
        overdue = await self.statistics_repo.count_overdue_dispatches(
            today, contract_project_id
        )

        return {
            'total': total,
            'this_month': this_month,
            'by_work_type': [
                {'work_type': item.work_type, 'count': item.count}
                for item in work_type_counts
            ],
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
        total = await self.statistics_repo.count_projects(contract_project_id)
        status_counts = await self.statistics_repo.get_project_counts_by_status(
            contract_project_id
        )

        return {
            'total': total,
            'by_status': [
                {'status': item.status, 'count': item.count}
                for item in status_counts
            ],
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

        overdue_items = await self.statistics_repo.get_overdue_dispatches(
            today, contract_project_id
        )
        upcoming_items = await self.statistics_repo.get_upcoming_deadline_dispatches(
            today, warning_date, contract_project_id
        )

        return {
            'overdue': {
                'count': len(overdue_items),
                'items': [
                    {
                        'id': item.id,
                        'dispatch_no': item.dispatch_no,
                        'project_name': item.project_name,
                        'deadline': item.deadline,
                        'days_overdue': item.days_overdue,
                    }
                    for item in overdue_items
                ],
            },
            'upcoming': {
                'count': len(upcoming_items),
                'items': [
                    {
                        'id': item.id,
                        'dispatch_no': item.dispatch_no,
                        'project_name': item.project_name,
                        'deadline': item.deadline,
                        'days_remaining': item.days_remaining,
                    }
                    for item in upcoming_items
                ],
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
        project_info = await self.statistics_repo.get_contract_project_info(
            contract_project_id
        )

        if not project_info:
            return {'error': '承攬案件不存在'}

        # 取得統計資料
        overview = await self.get_overview_statistics(contract_project_id)
        dispatch_summary = await self.get_dispatch_summary(contract_project_id)
        project_summary = await self.get_project_summary(contract_project_id)
        deadline_tracking = await self.get_deadline_tracking(contract_project_id)

        return {
            'contract_project': {
                'id': project_info.id,
                'project_name': project_info.project_name,
                'project_code': project_info.project_code,
                'winning_amount': project_info.winning_amount,
                'contract_amount': project_info.contract_amount,
            },
            'overview': overview,
            'dispatch_summary': dispatch_summary,
            'project_summary': project_summary,
            'deadline_tracking': deadline_tracking,
            'generated_at': datetime.now().isoformat(),
        }

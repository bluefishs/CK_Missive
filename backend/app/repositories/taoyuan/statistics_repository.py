"""
TaoyuanStatisticsRepository - 桃園派工統計資料存取層

提供桃園派工系統的統計查詢方法，將直接 DB 查詢從 Service 層分離。

@version 1.0.0
@date 2026-03-18
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.extended.models import (
    TaoyuanDispatchOrder,
    TaoyuanProject,
    ContractProject,
)

logger = logging.getLogger(__name__)


# =========================================================================
# 回傳型別定義
# =========================================================================


@dataclass
class WorkTypeCount:
    """作業類別統計"""
    work_type: str
    count: int


@dataclass
class StatusCount:
    """狀態統計"""
    status: str
    count: int


@dataclass
class OverdueDispatchItem:
    """逾期派工單項目"""
    id: int
    dispatch_no: Optional[str]
    project_name: Optional[str]
    deadline: Optional[str]
    days_overdue: int


@dataclass
class UpcomingDispatchItem:
    """即將到期派工單項目"""
    id: int
    dispatch_no: Optional[str]
    project_name: Optional[str]
    deadline: Optional[str]
    days_remaining: int


@dataclass
class ContractProjectInfo:
    """承攬案件資訊"""
    id: int
    project_name: Optional[str]
    project_code: Optional[str]
    winning_amount: float
    contract_amount: float


class TaoyuanStatisticsRepository:
    """
    桃園派工統計資料存取層

    職責:
    - 派工單彙總查詢 (總數, 本月新增, 按類別, 逾期)
    - 專案彙總查詢 (總數, 按狀態)
    - 履約期限追蹤查詢 (逾期/即將到期)
    - 承攬案件資訊查詢
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # 派工單統計查詢
    # =========================================================================

    async def count_dispatches(
        self, contract_project_id: Optional[int] = None
    ) -> int:
        """取得派工單總數"""
        condition = self._dispatch_base_condition(contract_project_id)
        query = select(func.count(TaoyuanDispatchOrder.id)).where(condition)
        return (await self.db.execute(query)).scalar() or 0

    async def count_dispatches_since(
        self,
        since_date: date,
        contract_project_id: Optional[int] = None,
    ) -> int:
        """取得指定日期後新增的派工單數"""
        condition = self._dispatch_base_condition(contract_project_id)
        query = select(func.count(TaoyuanDispatchOrder.id)).where(
            and_(
                condition,
                TaoyuanDispatchOrder.created_at >= since_date,
            )
        )
        return (await self.db.execute(query)).scalar() or 0

    async def get_dispatch_counts_by_work_type(
        self, contract_project_id: Optional[int] = None
    ) -> List[WorkTypeCount]:
        """按作業類別統計派工單"""
        condition = self._dispatch_base_condition(contract_project_id)
        query = (
            select(
                TaoyuanDispatchOrder.work_type,
                func.count(TaoyuanDispatchOrder.id),
            )
            .where(condition)
            .group_by(TaoyuanDispatchOrder.work_type)
        )
        result = await self.db.execute(query)
        return [
            WorkTypeCount(work_type=row[0] or '未分類', count=row[1])
            for row in result.fetchall()
        ]

    async def count_overdue_dispatches(
        self,
        as_of: date,
        contract_project_id: Optional[int] = None,
    ) -> int:
        """取得逾期派工單數量"""
        condition = self._dispatch_base_condition(contract_project_id)
        query = select(func.count(TaoyuanDispatchOrder.id)).where(
            and_(
                condition,
                TaoyuanDispatchOrder.deadline < as_of,
            )
        )
        return (await self.db.execute(query)).scalar() or 0

    # =========================================================================
    # 專案統計查詢
    # =========================================================================

    async def count_projects(
        self, contract_project_id: Optional[int] = None
    ) -> int:
        """取得專案總數"""
        condition = self._project_base_condition(contract_project_id)
        query = select(func.count(TaoyuanProject.id)).where(condition)
        return (await self.db.execute(query)).scalar() or 0

    async def get_project_counts_by_status(
        self, contract_project_id: Optional[int] = None
    ) -> List[StatusCount]:
        """按狀態統計專案"""
        condition = self._project_base_condition(contract_project_id)
        query = (
            select(
                TaoyuanProject.status,
                func.count(TaoyuanProject.id),
            )
            .where(condition)
            .group_by(TaoyuanProject.status)
        )
        result = await self.db.execute(query)
        return [
            StatusCount(status=row[0] or '未設定', count=row[1])
            for row in result.fetchall()
        ]

    # =========================================================================
    # 履約期限追蹤查詢
    # =========================================================================

    async def get_overdue_dispatches(
        self,
        as_of: date,
        contract_project_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[OverdueDispatchItem]:
        """取得逾期派工單列表"""
        condition = self._dispatch_base_condition(contract_project_id)
        query = (
            select(TaoyuanDispatchOrder)
            .where(
                and_(
                    condition,
                    TaoyuanDispatchOrder.deadline < as_of,
                )
            )
            .order_by(TaoyuanDispatchOrder.deadline.asc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return [
            OverdueDispatchItem(
                id=item.id,
                dispatch_no=item.dispatch_no,
                project_name=item.project_name,
                deadline=item.deadline.isoformat() if item.deadline else None,
                days_overdue=(as_of - item.deadline).days if item.deadline else 0,
            )
            for item in result.scalars().all()
        ]

    async def get_upcoming_deadline_dispatches(
        self,
        start_date: date,
        end_date: date,
        contract_project_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[UpcomingDispatchItem]:
        """取得即將到期的派工單列表"""
        condition = self._dispatch_base_condition(contract_project_id)
        query = (
            select(TaoyuanDispatchOrder)
            .where(
                and_(
                    condition,
                    TaoyuanDispatchOrder.deadline >= start_date,
                    TaoyuanDispatchOrder.deadline <= end_date,
                )
            )
            .order_by(TaoyuanDispatchOrder.deadline.asc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return [
            UpcomingDispatchItem(
                id=item.id,
                dispatch_no=item.dispatch_no,
                project_name=item.project_name,
                deadline=item.deadline.isoformat() if item.deadline else None,
                days_remaining=(item.deadline - start_date).days if item.deadline else 0,
            )
            for item in result.scalars().all()
        ]

    # =========================================================================
    # 承攬案件查詢
    # =========================================================================

    async def get_contract_project_info(
        self, contract_project_id: int
    ) -> Optional[ContractProjectInfo]:
        """取得承攬案件基本資訊"""
        query = select(ContractProject).where(
            ContractProject.id == contract_project_id
        )
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()

        if not project:
            return None

        return ContractProjectInfo(
            id=project.id,
            project_name=project.project_name,
            project_code=project.project_code,
            winning_amount=float(project.winning_amount or 0),
            contract_amount=float(project.contract_amount or 0),
        )

    # =========================================================================
    # 私有方法
    # =========================================================================

    @staticmethod
    def _dispatch_base_condition(contract_project_id: Optional[int] = None):
        """建立派工單基礎篩選條件"""
        if contract_project_id:
            return TaoyuanDispatchOrder.contract_project_id == contract_project_id
        return True

    @staticmethod
    def _project_base_condition(contract_project_id: Optional[int] = None):
        """建立專案基礎篩選條件"""
        if contract_project_id:
            return TaoyuanProject.contract_project_id == contract_project_id
        return True

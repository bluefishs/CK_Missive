"""
DocumentStatisticsService - 公文統計業務邏輯層

提供公文統計相關的業務邏輯處理。

@version 2.0.0
@date 2026-01-28
@updated 2026-03-23 — 全面遷移至 Repository 層 (A2)
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, and_, extract

from app.repositories.document_stats_repository import DocumentStatsRepository
from app.extended.models import OfficialDocument, ContractProject, GovernmentAgency

logger = logging.getLogger(__name__)


class DocumentStatisticsService:
    """
    公文統計業務邏輯服務

    職責:
    - 公文統計計算
    - 下拉選項查詢
    - 發文字號生成
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DocumentStatsRepository(db)
        self._project_repo: Optional["ProjectRepository"] = None
        self._agency_repo: Optional["AgencyRepository"] = None

    # =========================================================================
    # 統計方法
    # =========================================================================

    async def get_overall_statistics(self) -> Dict[str, Any]:
        """取得公文整體統計"""
        stats = await self.repository.get_statistics()
        current_year_send = await self.repository.get_current_year_send_count()
        delivery_stats = await self.repository.get_delivery_method_statistics()

        return {
            'success': True,
            'total': stats['total'],
            'total_documents': stats['total'],
            'send': stats['by_type'].get('發文', 0),
            'send_count': stats['by_type'].get('發文', 0),
            'receive': stats['by_type'].get('收文', 0),
            'receive_count': stats['by_type'].get('收文', 0),
            'current_year_count': sum(stats['by_month'].values()),
            'current_year_send_count': current_year_send,
            'delivery_method_stats': delivery_stats,
        }

    async def get_filtered_statistics(
        self,
        doc_number: Optional[str] = None,
        keyword: Optional[str] = None,
        doc_type: Optional[str] = None,
        year: Optional[int] = None,
        sender: Optional[str] = None,
        receiver: Optional[str] = None,
        delivery_method: Optional[str] = None,
        doc_date_from: Optional[date] = None,
        doc_date_to: Optional[date] = None,
        contract_case: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        取得篩選後的統計資料

        安全性修正 (v2.0.0): 使用 SQLAlchemy ORM 取代動態 SQL 字串拼接
        """
        conditions = self._build_filter_conditions(
            doc_number=doc_number, keyword=keyword, doc_type=doc_type,
            year=year, sender=sender, receiver=receiver,
            delivery_method=delivery_method,
            doc_date_from=doc_date_from, doc_date_to=doc_date_to,
            contract_case=contract_case,
        )
        counts = await self.repository.get_filtered_counts(conditions)

        return {
            'success': True,
            'total': counts['total'],
            'send_count': counts['send_count'],
            'receive_count': counts['receive_count'],
            'filters_applied': bool(conditions),
        }

    # =========================================================================
    # 下拉選項查詢
    # =========================================================================

    async def get_contract_projects_dropdown(
        self,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """取得承攬案件下拉選項"""
        from app.repositories import ProjectRepository
        if self._project_repo is None:
            self._project_repo = ProjectRepository(self.db)
        return await self._project_repo.get_for_dropdown(search=search, limit=limit)

    async def get_agencies_dropdown(
        self,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """取得政府機關下拉選項"""
        from app.repositories import AgencyRepository
        if self._agency_repo is None:
            self._agency_repo = AgencyRepository(self.db)
        return await self._agency_repo.get_for_dropdown(search=search, limit=limit)

    async def get_document_years(self) -> List[int]:
        """取得文檔年度列表"""
        return await self.repository.get_document_years()

    # =========================================================================
    # 發文字號生成
    # =========================================================================

    async def get_next_send_number(
        self,
        prefix: Optional[str] = None,
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        """取得下一個發文字號"""
        if prefix is None:
            prefix = '乾坤測字第'
        current_year = year or datetime.now().year
        roc_year = current_year - 1911

        year_pattern = f"{prefix}{roc_year}%"
        prefix_len = len(prefix)
        year_len = len(str(roc_year))
        substr_start = prefix_len + year_len + 1

        max_sequence = await self.repository.get_next_send_sequence(
            year_pattern, substr_start
        )
        next_sequence = max_sequence + 1
        full_number = f"{prefix}{roc_year}{next_sequence:07d}號"

        return {
            'full_number': full_number,
            'year': current_year,
            'roc_year': roc_year,
            'sequence_number': next_sequence,
            'previous_max': max_sequence,
            'prefix': prefix,
        }

    # =========================================================================
    # 趨勢與效率 (從 endpoint 層提升)
    # =========================================================================

    async def get_trends(self, months: int = 12) -> List[Dict[str, Any]]:
        """取得過去 N 個月收發文趨勢"""
        from dateutil.relativedelta import relativedelta

        today = date.today()
        since = (today - relativedelta(months=months - 1)).replace(day=1)
        rows = await self.repository.get_monthly_trends(since)

        month_map = {
            f"{r['year']}-{r['month']:02d}": {
                'month': f"{r['year']}-{r['month']:02d}",
                'received': r['received'],
                'sent': r['sent'],
            }
            for r in rows
        }

        trends: List[Dict[str, Any]] = []
        cursor = since
        while cursor <= today:
            key = f"{cursor.year}-{cursor.month:02d}"
            trends.append(month_map.get(key, {'month': key, 'received': 0, 'sent': 0}))
            cursor = cursor + relativedelta(months=1)
        return trends

    async def get_efficiency(self) -> Dict[str, Any]:
        """取得公文處理效率統計 (狀態分布 + 逾期)"""
        status_distribution = await self.repository.get_status_distribution()
        total = await self.repository.count()
        overdue_count = await self.repository.get_overdue_count()
        overdue_rate = round(overdue_count / total, 3) if total > 0 else 0.0

        return {
            'status_distribution': status_distribution,
            'overdue_count': overdue_count,
            'overdue_rate': overdue_rate,
            'total': total,
        }

    # =========================================================================
    # 內部工具
    # =========================================================================

    @staticmethod
    def _build_filter_conditions(
        doc_number: Optional[str] = None,
        keyword: Optional[str] = None,
        doc_type: Optional[str] = None,
        year: Optional[int] = None,
        sender: Optional[str] = None,
        receiver: Optional[str] = None,
        delivery_method: Optional[str] = None,
        doc_date_from: Optional[date] = None,
        doc_date_to: Optional[date] = None,
        contract_case: Optional[str] = None,
    ) -> list:
        """建構 ORM 篩選條件列表"""
        from sqlalchemy import select as sa_select
        conditions: list = []

        if doc_number:
            conditions.append(OfficialDocument.doc_number.ilike(f"%{doc_number}%"))
        if keyword:
            conditions.append(or_(
                OfficialDocument.subject.ilike(f"%{keyword}%"),
                OfficialDocument.content.ilike(f"%{keyword}%"),
                OfficialDocument.notes.ilike(f"%{keyword}%")
            ))
        if doc_type:
            conditions.append(OfficialDocument.doc_type == doc_type)
        if year:
            conditions.append(extract('year', OfficialDocument.doc_date) == year)
        if sender:
            conditions.append(OfficialDocument.sender.ilike(f"%{sender}%"))
        if receiver:
            conditions.append(OfficialDocument.receiver.ilike(f"%{receiver}%"))
        if delivery_method:
            conditions.append(OfficialDocument.delivery_method == delivery_method)
        if doc_date_from:
            conditions.append(OfficialDocument.doc_date >= doc_date_from)
        if doc_date_to:
            conditions.append(OfficialDocument.doc_date <= doc_date_to)
        if contract_case:
            project_subquery = sa_select(ContractProject.id).where(
                or_(
                    ContractProject.project_name.ilike(f"%{contract_case}%"),
                    ContractProject.project_code.ilike(f"%{contract_case}%")
                )
            )
            conditions.append(OfficialDocument.contract_project_id.in_(project_subquery))

        return conditions

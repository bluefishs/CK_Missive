"""
DocumentStatsRepository - 公文統計資料存取層

從 DocumentRepository 提取，專注於統計查詢操作。

版本: 2.0.0
建立日期: 2026-03-10
更新日期: 2026-03-23 — 補完 8 個缺失方法 (A2)
提取自: document_repository.py
"""

from typing import Dict, Any, List, Optional
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Integer, select, func, or_, and_, extract, case

from app.repositories.base_repository import BaseRepository
from app.extended.models import OfficialDocument, DocumentCalendarEvent


class DocumentStatsRepository(BaseRepository[OfficialDocument]):
    """公文統計專用 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, OfficialDocument)

    async def get_statistics(self) -> Dict[str, Any]:
        """
        取得公文統計資料

        Returns:
            統計資料字典，包含：
            - total: 總數
            - by_type: 依類型統計
            - by_status: 依狀態統計
            - by_month: 依月份統計（當年度）
        """
        total = await self.count()
        type_stats = await self._get_grouped_count('doc_type')
        status_stats = await self._get_grouped_count('status')
        current_year = date.today().year
        month_stats = await self._get_monthly_count(current_year)

        return {
            "total": total,
            "by_type": type_stats,
            "by_status": status_stats,
            "by_month": month_stats,
            "year": current_year,
        }

    async def get_type_statistics(self) -> Dict[str, int]:
        """取得依類型統計"""
        return await self._get_grouped_count('doc_type')

    async def get_status_statistics(self) -> Dict[str, int]:
        """取得依狀態統計"""
        return await self._get_grouped_count('status')

    async def get_yearly_statistics(self, year: int) -> Dict[str, Any]:
        """取得年度統計"""
        query = select(func.count(OfficialDocument.id)).where(
            or_(
                extract('year', OfficialDocument.doc_date) == year,
                extract('year', OfficialDocument.receive_date) == year
            )
        )
        total = (await self.db.execute(query)).scalar() or 0
        month_stats = await self._get_monthly_count(year)
        type_stats = await self._get_grouped_count_with_year('doc_type', year)

        return {
            "year": year,
            "total": total,
            "by_month": month_stats,
            "by_type": type_stats,
        }

    async def get_pending_count(self) -> int:
        """取得待處理公文數量"""
        return await self.count_by(status='待處理')

    async def get_unlinked_count(self) -> int:
        """取得未關聯專案的公文數量"""
        query = select(func.count(OfficialDocument.id)).where(
            OfficialDocument.contract_project_id.is_(None)
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _get_grouped_count(self, field_name: str) -> Dict[str, int]:
        """取得依欄位分組的計數"""
        field = getattr(OfficialDocument, field_name)
        query = (
            select(field, func.count(OfficialDocument.id))
            .group_by(field)
        )
        result = await self.db.execute(query)

        stats = {}
        for value, count in result.fetchall():
            key = value if value else '(未設定)'
            stats[key] = count
        return stats

    async def _get_grouped_count_with_year(
        self,
        field_name: str,
        year: int
    ) -> Dict[str, int]:
        """取得指定年度依欄位分組的計數"""
        field = getattr(OfficialDocument, field_name)
        query = (
            select(field, func.count(OfficialDocument.id))
            .where(
                or_(
                    extract('year', OfficialDocument.doc_date) == year,
                    extract('year', OfficialDocument.receive_date) == year
                )
            )
            .group_by(field)
        )
        result = await self.db.execute(query)

        stats = {}
        for value, count in result.fetchall():
            key = value if value else '(未設定)'
            stats[key] = count
        return stats

    async def _get_monthly_count(self, year: int) -> Dict[int, int]:
        """取得指定年度的月份統計"""
        query = (
            select(
                extract('month', OfficialDocument.doc_date).label('month'),
                func.count(OfficialDocument.id)
            )
            .where(extract('year', OfficialDocument.doc_date) == year)
            .group_by(extract('month', OfficialDocument.doc_date))
        )
        result = await self.db.execute(query)

        stats = {i: 0 for i in range(1, 13)}
        for month, count in result.fetchall():
            if month:
                stats[int(month)] = count
        return stats

    # =========================================================================
    # v2.0.0 新增方法 — 從 Service/Endpoint 提取 (A2)
    # =========================================================================

    async def get_current_year_send_count(self, year: Optional[int] = None) -> int:
        """取得指定年度（預設當年）發文數"""
        target_year = year or date.today().year
        query = select(func.count(OfficialDocument.id)).where(
            and_(
                OfficialDocument.category == '發文',
                extract('year', OfficialDocument.doc_date) == target_year,
            )
        )
        return (await self.db.execute(query)).scalar() or 0

    async def get_delivery_method_statistics(self) -> Dict[str, int]:
        """取得發文形式統計 (電子交換/紙本郵寄/電子+紙本)"""
        methods = ['電子交換', '紙本郵寄', '電子+紙本']
        keys = ['electronic', 'paper', 'both']
        result: Dict[str, int] = {}
        for key, method in zip(keys, methods):
            query = select(func.count(OfficialDocument.id)).where(
                and_(
                    OfficialDocument.category == '發文',
                    OfficialDocument.delivery_method == method,
                )
            )
            result[key] = (await self.db.execute(query)).scalar() or 0
        return result

    async def get_filtered_counts(
        self,
        conditions: list,
    ) -> Dict[str, int]:
        """
        取得篩選後的收發文計數

        Args:
            conditions: SQLAlchemy WHERE 條件列表

        Returns:
            {'total': int, 'send_count': int, 'receive_count': int}
        """
        base_filter = and_(*conditions) if conditions else True

        total_q = select(func.count(OfficialDocument.id)).where(base_filter)
        total = (await self.db.execute(total_q)).scalar() or 0

        send_q = select(func.count(OfficialDocument.id)).where(
            and_(base_filter, OfficialDocument.category == '發文')
        )
        send_count = (await self.db.execute(send_q)).scalar() or 0

        recv_q = select(func.count(OfficialDocument.id)).where(
            and_(base_filter, OfficialDocument.category == '收文')
        )
        receive_count = (await self.db.execute(recv_q)).scalar() or 0

        return {'total': total, 'send_count': send_count, 'receive_count': receive_count}

    async def get_document_years(self) -> List[int]:
        """取得所有文檔年度列表"""
        query = (
            select(extract('year', OfficialDocument.doc_date).label('year'))
            .where(OfficialDocument.doc_date.isnot(None))
            .distinct()
            .order_by(extract('year', OfficialDocument.doc_date).desc())
        )
        result = await self.db.execute(query)
        return [int(row.year) for row in result.all() if row.year]

    async def get_next_send_sequence(
        self, year_pattern: str, substr_start: int
    ) -> int:
        """
        取得指定年度最大發文流水號

        Args:
            year_pattern: LIKE 樣式，如 '乾坤測字第115%'
            substr_start: substring 起始位置

        Returns:
            最大流水號 (0 表示尚無資料)
        """
        query = (
            select(
                func.max(
                    func.cast(
                        func.substring(
                            OfficialDocument.doc_number, substr_start, 7
                        ),
                        Integer,
                    )
                ).label("max_seq")
            )
            .where(OfficialDocument.doc_number.ilike(year_pattern))
            .where(
                or_(
                    OfficialDocument.category == '發文',
                    OfficialDocument.doc_type == '發文',
                )
            )
        )
        result = await self.db.execute(query)
        row = result.fetchone()
        return row[0] if row and row[0] else 0

    async def get_monthly_trends(self, since: date) -> List[Dict[str, Any]]:
        """
        取得自指定日期起每月收發文趨勢

        Args:
            since: 起始日期

        Returns:
            [{'year': int, 'month': int, 'received': int, 'sent': int}, ...]
        """
        year_col = extract('year', OfficialDocument.doc_date)
        month_col = extract('month', OfficialDocument.doc_date)

        query = (
            select(
                year_col.label('year'),
                month_col.label('month'),
                func.sum(
                    case((OfficialDocument.category == '收文', 1), else_=0)
                ).label('received'),
                func.sum(
                    case((OfficialDocument.category == '發文', 1), else_=0)
                ).label('sent'),
            )
            .where(
                and_(
                    OfficialDocument.doc_date.isnot(None),
                    OfficialDocument.doc_date >= since,
                )
            )
            .group_by(year_col, month_col)
            .order_by(year_col.asc(), month_col.asc())
        )
        result = await self.db.execute(query)
        return [
            {
                'year': int(row.year),
                'month': int(row.month),
                'received': int(row.received or 0),
                'sent': int(row.sent or 0),
            }
            for row in result.all()
        ]

    async def get_status_distribution(self) -> List[Dict[str, Any]]:
        """取得公文狀態分布"""
        query = (
            select(
                OfficialDocument.status,
                func.count(OfficialDocument.id).label('count'),
            )
            .where(OfficialDocument.status.isnot(None))
            .group_by(OfficialDocument.status)
            .order_by(func.count(OfficialDocument.id).desc())
        )
        result = await self.db.execute(query)
        return [
            {'status': row.status, 'count': int(row.count)}
            for row in result.all()
        ]

    # =========================================================================
    # 流水號查詢 — 供 DocumentSerialNumberService 使用 (B3)
    # =========================================================================

    async def get_max_auto_serial(self, pattern: str) -> Optional[str]:
        """取得符合 pattern 的最大 auto_serial 值"""
        query = select(func.max(OfficialDocument.auto_serial)).where(
            OfficialDocument.auto_serial.like(pattern)
        )
        return (await self.db.execute(query)).scalar()

    async def count_by_serial_pattern(self, pattern: str) -> int:
        """取得符合 pattern 的 auto_serial 筆數"""
        query = select(func.count(OfficialDocument.id)).where(
            OfficialDocument.auto_serial.like(pattern)
        )
        return (await self.db.execute(query)).scalar() or 0

    async def get_overdue_count(self) -> int:
        """取得逾期公文數量 (未結案且行事曆事件已過期)"""
        now = datetime.now()
        query = (
            select(func.count(func.distinct(OfficialDocument.id)))
            .join(
                DocumentCalendarEvent,
                DocumentCalendarEvent.document_id == OfficialDocument.id,
            )
            .where(
                and_(
                    OfficialDocument.status != '已結案',
                    DocumentCalendarEvent.end_date.isnot(None),
                    DocumentCalendarEvent.end_date < now,
                    DocumentCalendarEvent.status != 'completed',
                )
            )
        )
        return (await self.db.execute(query)).scalar() or 0

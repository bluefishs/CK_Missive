"""
DocumentStatisticsService - 公文統計業務邏輯層

提供公文統計相關的業務邏輯處理。

@version 1.0.0
@date 2026-01-28
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, or_, and_, extract

from app.repositories import DocumentRepository
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
        self.repository = DocumentRepository(db)

    # =========================================================================
    # 統計方法
    # =========================================================================

    async def get_overall_statistics(self) -> Dict[str, Any]:
        """
        取得公文整體統計

        Returns:
            統計資料字典
        """
        # 使用 Repository 取得基礎統計
        stats = await self.repository.get_statistics()

        # 補充額外統計
        current_year = date.today().year

        # 本年度發文數
        current_year_send_query = select(func.count(OfficialDocument.id)).where(
            and_(
                OfficialDocument.category == '發文',
                extract('year', OfficialDocument.doc_date) == current_year
            )
        )
        current_year_send = (await self.db.execute(current_year_send_query)).scalar() or 0

        # 發文形式統計
        delivery_stats = await self._get_delivery_method_statistics()

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

        Returns:
            篩選統計資料
        """
        conditions = []
        params = {}

        if doc_number:
            conditions.append("doc_number ILIKE :doc_number")
            params["doc_number"] = f"%{doc_number}%"

        if keyword:
            conditions.append("""
                (subject ILIKE :keyword
                 OR content ILIKE :keyword OR notes ILIKE :keyword)
            """)
            params["keyword"] = f"%{keyword}%"

        if doc_type:
            conditions.append("doc_type = :doc_type")
            params["doc_type"] = doc_type

        if year:
            conditions.append("EXTRACT(YEAR FROM doc_date) = :year")
            params["year"] = year

        if sender:
            conditions.append("sender ILIKE :sender")
            params["sender"] = f"%{sender}%"

        if receiver:
            conditions.append("receiver ILIKE :receiver")
            params["receiver"] = f"%{receiver}%"

        if delivery_method:
            conditions.append("delivery_method = :delivery_method")
            params["delivery_method"] = delivery_method

        if doc_date_from:
            conditions.append("doc_date >= :doc_date_from")
            params["doc_date_from"] = doc_date_from

        if doc_date_to:
            conditions.append("doc_date <= :doc_date_to")
            params["doc_date_to"] = doc_date_to

        if contract_case:
            conditions.append("""
                contract_project_id IN (
                    SELECT id FROM contract_projects
                    WHERE project_name ILIKE :contract_case OR project_code ILIKE :contract_case
                )
            """)
            params["contract_case"] = f"%{contract_case}%"

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 總數查詢
        total_query = f"SELECT COUNT(*) FROM documents WHERE {where_clause}"
        total_result = await self.db.execute(text(total_query), params)
        total = total_result.scalar() or 0

        # 發文數查詢
        send_query = f"SELECT COUNT(*) FROM documents WHERE {where_clause} AND category = '發文'"
        send_result = await self.db.execute(text(send_query), params)
        send_count = send_result.scalar() or 0

        # 收文數查詢
        receive_query = f"SELECT COUNT(*) FROM documents WHERE {where_clause} AND category = '收文'"
        receive_result = await self.db.execute(text(receive_query), params)
        receive_count = receive_result.scalar() or 0

        return {
            'success': True,
            'total': total,
            'send_count': send_count,
            'receive_count': receive_count,
            'filters_applied': bool(conditions),
        }

    async def _get_delivery_method_statistics(self) -> Dict[str, int]:
        """取得發文形式統計"""
        electronic_query = select(func.count(OfficialDocument.id)).where(
            and_(
                OfficialDocument.category == '發文',
                OfficialDocument.delivery_method == '電子交換'
            )
        )
        paper_query = select(func.count(OfficialDocument.id)).where(
            and_(
                OfficialDocument.category == '發文',
                OfficialDocument.delivery_method == '紙本郵寄'
            )
        )
        both_query = select(func.count(OfficialDocument.id)).where(
            and_(
                OfficialDocument.category == '發文',
                OfficialDocument.delivery_method == '電子+紙本'
            )
        )

        electronic = (await self.db.execute(electronic_query)).scalar() or 0
        paper = (await self.db.execute(paper_query)).scalar() or 0
        both = (await self.db.execute(both_query)).scalar() or 0

        return {
            'electronic': electronic,
            'paper': paper,
            'both': both,
        }

    # =========================================================================
    # 下拉選項查詢
    # =========================================================================

    async def get_contract_projects_dropdown(
        self,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        取得承攬案件下拉選項

        Args:
            search: 搜尋關鍵字
            limit: 筆數上限

        Returns:
            選項列表
        """
        query = select(
            ContractProject.id,
            ContractProject.project_name,
            ContractProject.year,
            ContractProject.category
        )

        if search:
            query = query.where(
                or_(
                    ContractProject.project_name.ilike(f"%{search}%"),
                    ContractProject.project_code.ilike(f"%{search}%"),
                    ContractProject.client_agency.ilike(f"%{search}%")
                )
            )

        query = query.order_by(
            ContractProject.year.desc(),
            ContractProject.project_name.asc()
        ).limit(limit)

        result = await self.db.execute(query)
        projects = result.all()

        return [
            {
                "value": p.project_name,
                "label": f"{p.project_name} ({p.year}年)",
                "id": p.id,
                "year": p.year,
                "category": p.category
            }
            for p in projects
        ]

    async def get_agencies_dropdown(
        self,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        取得政府機關下拉選項

        Args:
            search: 搜尋關鍵字
            limit: 筆數上限

        Returns:
            選項列表
        """
        query = select(
            GovernmentAgency.id,
            GovernmentAgency.agency_name,
            GovernmentAgency.agency_code,
            GovernmentAgency.agency_short_name
        ).where(
            GovernmentAgency.agency_name.isnot(None),
            GovernmentAgency.agency_name != ''
        )

        if search:
            query = query.where(
                or_(
                    GovernmentAgency.agency_name.ilike(f"%{search}%"),
                    GovernmentAgency.agency_short_name.ilike(f"%{search}%")
                )
            )

        query = query.order_by(GovernmentAgency.agency_name).limit(limit)

        result = await self.db.execute(query)
        agencies = result.all()

        return [
            {
                "value": a.agency_name,
                "label": a.agency_name,
                "id": a.id,
                "agency_code": a.agency_code or "",
                "agency_short_name": a.agency_short_name or ""
            }
            for a in agencies
        ]

    async def get_document_years(self) -> List[int]:
        """
        取得文檔年度列表

        Returns:
            年度列表
        """
        query = (
            select(extract('year', OfficialDocument.doc_date).label('year'))
            .where(OfficialDocument.doc_date.isnot(None))
            .distinct()
            .order_by(extract('year', OfficialDocument.doc_date).desc())
        )

        result = await self.db.execute(query)
        return [int(row.year) for row in result.all() if row.year]

    # =========================================================================
    # 發文字號生成
    # =========================================================================

    async def get_next_send_number(
        self,
        prefix: Optional[str] = None,
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        取得下一個發文字號

        Args:
            prefix: 字號前綴（預設：乾坤測字第）
            year: 年度（預設當年）

        Returns:
            字號資訊
        """
        # 處理預設值
        if prefix is None:
            prefix = '乾坤測字第'
        current_year = year or datetime.now().year
        roc_year = current_year - 1911

        # 查詢該民國年度的最大流水號
        year_pattern = f"{prefix}{roc_year}%"

        prefix_len = len(prefix)
        year_len = len(str(roc_year))

        raw_query = text(f"""
            SELECT MAX(
                CAST(
                    SUBSTRING(doc_number, {prefix_len + year_len + 1}, 7)
                    AS INTEGER
                )
            ) as max_seq
            FROM documents
            WHERE doc_number LIKE :pattern
            AND (category = '發文' OR doc_type = '發文')
        """)

        max_seq_result = await self.db.execute(raw_query, {"pattern": year_pattern})
        row = max_seq_result.fetchone()
        max_sequence = row[0] if row and row[0] else 0

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

"""
AgencyRepository - 機關資料存取層

提供機關（政府機關/民間企業）相關的資料庫查詢操作，包含：
- 機關特定查詢方法
- 公文關聯查詢
- 統計方法
- 智慧匹配支援

版本: 1.0.0
建立日期: 2026-01-26
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc

from app.repositories.base_repository import BaseRepository
from app.extended.models import (
    GovernmentAgency,
    OfficialDocument,
)

logger = logging.getLogger(__name__)


class AgencyRepository(BaseRepository[GovernmentAgency]):
    """
    機關資料存取層

    繼承 BaseRepository 並擴展機關特定的查詢方法。

    Example:
        agency_repo = AgencyRepository(db)

        # 基本查詢
        agency = await agency_repo.get_by_id(1)

        # 機關特定查詢
        by_type = await agency_repo.get_by_type('政府機關')
        with_stats = await agency_repo.get_with_document_stats(1)
    """

    # 搜尋欄位設定
    SEARCH_FIELDS = ['agency_name', 'agency_short_name', 'agency_code']

    def __init__(self, db: AsyncSession):
        """
        初始化機關 Repository

        Args:
            db: AsyncSession 資料庫連線
        """
        super().__init__(db, GovernmentAgency)

    # =========================================================================
    # 機關特定查詢方法
    # =========================================================================

    async def get_by_name(self, name: str) -> Optional[GovernmentAgency]:
        """
        根據機關名稱取得機關

        Args:
            name: 機關名稱

        Returns:
            機關實體，若不存在則返回 None
        """
        return await self.find_one_by(agency_name=name)

    async def get_by_short_name(self, short_name: str) -> Optional[GovernmentAgency]:
        """
        根據機關簡稱取得機關

        Args:
            short_name: 機關簡稱

        Returns:
            機關實體，若不存在則返回 None
        """
        return await self.find_one_by(agency_short_name=short_name)

    async def get_by_code(self, code: str) -> Optional[GovernmentAgency]:
        """
        根據機關代碼取得機關

        Args:
            code: 機關代碼

        Returns:
            機關實體，若不存在則返回 None
        """
        return await self.find_one_by(agency_code=code)

    async def get_by_type(
        self,
        agency_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[GovernmentAgency]:
        """
        根據機關類型取得機關列表

        Args:
            agency_type: 機關類型 (政府機關, 民間企業, 其他單位)
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            機關列表
        """
        query = (
            select(GovernmentAgency)
            .where(GovernmentAgency.agency_type == agency_type)
            .order_by(GovernmentAgency.agency_name)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_government_agencies(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[GovernmentAgency]:
        """
        取得政府機關列表

        Args:
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            政府機關列表
        """
        return await self.get_by_type('政府機關', skip, limit)

    async def get_private_companies(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[GovernmentAgency]:
        """
        取得民間企業列表

        Args:
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            民間企業列表
        """
        return await self.get_by_type('民間企業', skip, limit)

    # =========================================================================
    # 公文關聯查詢
    # =========================================================================

    async def get_sent_documents(
        self,
        agency_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[OfficialDocument]:
        """
        取得機關的發文列表

        Args:
            agency_id: 機關 ID
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            發文列表
        """
        query = (
            select(OfficialDocument)
            .where(OfficialDocument.sender_agency_id == agency_id)
            .order_by(desc(OfficialDocument.doc_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_received_documents(
        self,
        agency_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[OfficialDocument]:
        """
        取得機關的收文列表

        Args:
            agency_id: 機關 ID
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            收文列表
        """
        query = (
            select(OfficialDocument)
            .where(OfficialDocument.receiver_agency_id == agency_id)
            .order_by(desc(OfficialDocument.doc_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_all_documents(
        self,
        agency_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[OfficialDocument]:
        """
        取得機關的所有相關公文（發文+收文）

        Args:
            agency_id: 機關 ID
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            公文列表
        """
        query = (
            select(OfficialDocument)
            .where(
                or_(
                    OfficialDocument.sender_agency_id == agency_id,
                    OfficialDocument.receiver_agency_id == agency_id
                )
            )
            .order_by(desc(OfficialDocument.doc_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_document_counts(self, agency_id: int) -> Dict[str, int]:
        """
        取得機關的公文統計

        Args:
            agency_id: 機關 ID

        Returns:
            {'sent': 發文數, 'received': 收文數, 'total': 總數}
        """
        # 發文數
        sent_query = select(func.count(OfficialDocument.id)).where(
            OfficialDocument.sender_agency_id == agency_id
        )
        sent_count = (await self.db.execute(sent_query)).scalar() or 0

        # 收文數
        received_query = select(func.count(OfficialDocument.id)).where(
            OfficialDocument.receiver_agency_id == agency_id
        )
        received_count = (await self.db.execute(received_query)).scalar() or 0

        return {
            "sent": sent_count,
            "received": received_count,
            "total": sent_count + received_count,
        }

    async def get_with_document_stats(
        self,
        agency_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        取得機關資料含公文統計

        Args:
            agency_id: 機關 ID

        Returns:
            機關資料（含統計），若不存在則返回 None
        """
        agency = await self.get_by_id(agency_id)
        if not agency:
            return None

        doc_counts = await self.get_document_counts(agency_id)

        # 最後活動日期
        last_activity_query = (
            select(func.max(OfficialDocument.doc_date))
            .where(
                or_(
                    OfficialDocument.sender_agency_id == agency_id,
                    OfficialDocument.receiver_agency_id == agency_id
                )
            )
        )
        last_activity = (await self.db.execute(last_activity_query)).scalar()

        return {
            "id": agency.id,
            "agency_name": agency.agency_name,
            "agency_short_name": agency.agency_short_name,
            "agency_code": agency.agency_code,
            "agency_type": agency.agency_type,
            "contact_person": agency.contact_person,
            "phone": agency.phone,
            "email": agency.email,
            "address": agency.address,
            "created_at": agency.created_at,
            "updated_at": agency.updated_at,
            "document_stats": doc_counts,
            "last_activity": last_activity,
        }

    async def has_related_documents(self, agency_id: int) -> bool:
        """
        檢查機關是否有關聯公文

        Args:
            agency_id: 機關 ID

        Returns:
            是否有關聯公文
        """
        query = select(func.count(OfficialDocument.id)).where(
            or_(
                OfficialDocument.sender_agency_id == agency_id,
                OfficialDocument.receiver_agency_id == agency_id
            )
        )
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    # =========================================================================
    # 統計方法
    # =========================================================================

    async def get_statistics(self) -> Dict[str, Any]:
        """
        取得機關統計資料

        Returns:
            統計資料字典
        """
        # 總數
        total = await self.count()

        # 依類型統計
        type_stats = await self._get_grouped_count('agency_type')

        # 有公文往來的機關數
        active_count = await self._get_active_agency_count()

        return {
            "total": total,
            "by_type": type_stats,
            "active_count": active_count,
        }

    async def get_type_statistics(self) -> Dict[str, int]:
        """
        取得依類型統計

        Returns:
            {類型: 數量} 字典
        """
        return await self._get_grouped_count('agency_type')

    async def get_top_agencies_by_documents(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        取得公文往來最多的機關

        Args:
            limit: 回傳數量限制

        Returns:
            機關列表（含公文數量）
        """
        # 計算每個機關的公文數量（發文+收文）
        # 使用子查詢
        sent_subq = (
            select(
                OfficialDocument.sender_agency_id.label('agency_id'),
                func.count(OfficialDocument.id).label('count')
            )
            .where(OfficialDocument.sender_agency_id.isnot(None))
            .group_by(OfficialDocument.sender_agency_id)
            .subquery()
        )

        received_subq = (
            select(
                OfficialDocument.receiver_agency_id.label('agency_id'),
                func.count(OfficialDocument.id).label('count')
            )
            .where(OfficialDocument.receiver_agency_id.isnot(None))
            .group_by(OfficialDocument.receiver_agency_id)
            .subquery()
        )

        # 組合查詢
        query = (
            select(
                GovernmentAgency.id,
                GovernmentAgency.agency_name,
                GovernmentAgency.agency_type,
                func.coalesce(sent_subq.c.count, 0).label('sent_count'),
                func.coalesce(received_subq.c.count, 0).label('received_count'),
                (
                    func.coalesce(sent_subq.c.count, 0) +
                    func.coalesce(received_subq.c.count, 0)
                ).label('total_count')
            )
            .outerjoin(sent_subq, GovernmentAgency.id == sent_subq.c.agency_id)
            .outerjoin(received_subq, GovernmentAgency.id == received_subq.c.agency_id)
            .order_by(desc('total_count'))
            .limit(limit)
        )

        result = await self.db.execute(query)

        return [
            {
                "id": row.id,
                "agency_name": row.agency_name,
                "agency_type": row.agency_type,
                "sent_count": row.sent_count,
                "received_count": row.received_count,
                "total_count": row.total_count,
            }
            for row in result.fetchall()
            if row.total_count > 0
        ]

    async def _get_grouped_count(self, field_name: str) -> Dict[str, int]:
        """
        取得依欄位分組的計數

        Args:
            field_name: 欄位名稱

        Returns:
            {欄位值: 數量} 字典
        """
        field = getattr(GovernmentAgency, field_name)
        query = (
            select(field, func.count(GovernmentAgency.id))
            .group_by(field)
        )
        result = await self.db.execute(query)

        stats = {}
        for value, count in result.fetchall():
            key = value if value else '(未設定)'
            stats[key] = count
        return stats

    async def _get_active_agency_count(self) -> int:
        """
        取得有公文往來的機關數量

        Returns:
            有公文往來的機關數量
        """
        # 發文機關
        sender_ids = select(OfficialDocument.sender_agency_id).where(
            OfficialDocument.sender_agency_id.isnot(None)
        ).distinct()

        # 收文機關
        receiver_ids = select(OfficialDocument.receiver_agency_id).where(
            OfficialDocument.receiver_agency_id.isnot(None)
        ).distinct()

        # 聯集計數
        query = (
            select(func.count(func.distinct(GovernmentAgency.id)))
            .where(
                or_(
                    GovernmentAgency.id.in_(sender_ids),
                    GovernmentAgency.id.in_(receiver_ids)
                )
            )
        )

        result = await self.db.execute(query)
        return result.scalar() or 0

    # =========================================================================
    # 智慧匹配支援
    # =========================================================================

    async def find_by_name_pattern(
        self,
        pattern: str,
        limit: int = 10
    ) -> List[GovernmentAgency]:
        """
        根據名稱模式搜尋機關

        Args:
            pattern: 搜尋模式（支援模糊匹配）
            limit: 回傳數量限制

        Returns:
            符合的機關列表
        """
        search_pattern = f"%{pattern}%"
        query = (
            select(GovernmentAgency)
            .where(
                or_(
                    GovernmentAgency.agency_name.ilike(search_pattern),
                    GovernmentAgency.agency_short_name.ilike(search_pattern),
                    GovernmentAgency.agency_code.ilike(search_pattern)
                )
            )
            .order_by(GovernmentAgency.agency_name)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def match_agency(self, text: str) -> Optional[GovernmentAgency]:
        """
        智慧匹配機關

        匹配優先順序：
        1. 完全匹配機關代碼
        2. 完全匹配機關名稱
        3. 完全匹配機關簡稱
        4. 機關名稱包含在文字中

        Args:
            text: 搜尋文字

        Returns:
            匹配的機關，若無則返回 None
        """
        if not text or not text.strip():
            return None

        text = text.strip()

        # 1. 完全匹配機關代碼
        agency = await self.get_by_code(text)
        if agency:
            return agency

        # 2. 完全匹配機關名稱
        agency = await self.get_by_name(text)
        if agency:
            return agency

        # 3. 完全匹配機關簡稱
        agency = await self.get_by_short_name(text)
        if agency:
            return agency

        # 4. 機關名稱包含在文字中
        all_agencies = await self.get_all(limit=1000)  # 取得所有機關
        for agency in all_agencies:
            if agency.agency_name and agency.agency_name in text:
                return agency
            if agency.agency_short_name and agency.agency_short_name in text:
                return agency

        return None

    async def suggest_agencies(
        self,
        text: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        根據文字建議可能的機關

        Args:
            text: 搜尋文字
            limit: 回傳數量限制

        Returns:
            建議的機關列表
        """
        if not text or len(text) < 2:
            return []

        agencies = await self.find_by_name_pattern(text, limit)

        return [
            {
                "id": a.id,
                "agency_name": a.agency_name,
                "agency_code": a.agency_code,
                "agency_short_name": a.agency_short_name,
                "agency_type": a.agency_type,
            }
            for a in agencies
        ]

    # =========================================================================
    # 未關聯分析
    # =========================================================================

    async def get_unassociated_summary(self) -> Dict[str, Any]:
        """
        取得未關聯機關的公文統計

        Returns:
            未關聯統計資料
        """
        # 總公文數
        total_docs = (await self.db.execute(
            select(func.count(OfficialDocument.id))
        )).scalar() or 0

        # 無發文機關關聯數
        no_sender = (await self.db.execute(
            select(func.count(OfficialDocument.id)).where(
                and_(
                    OfficialDocument.sender_agency_id.is_(None),
                    OfficialDocument.sender.isnot(None),
                    OfficialDocument.sender != ''
                )
            )
        )).scalar() or 0

        # 無受文機關關聯數
        no_receiver = (await self.db.execute(
            select(func.count(OfficialDocument.id)).where(
                and_(
                    OfficialDocument.receiver_agency_id.is_(None),
                    OfficialDocument.receiver.isnot(None),
                    OfficialDocument.receiver != ''
                )
            )
        )).scalar() or 0

        # 已關聯統計
        has_sender = (await self.db.execute(
            select(func.count(OfficialDocument.id)).where(
                OfficialDocument.sender_agency_id.isnot(None)
            )
        )).scalar() or 0

        has_receiver = (await self.db.execute(
            select(func.count(OfficialDocument.id)).where(
                OfficialDocument.receiver_agency_id.isnot(None)
            )
        )).scalar() or 0

        return {
            "total_documents": total_docs,
            "sender_associated": has_sender,
            "sender_unassociated": no_sender,
            "receiver_associated": has_receiver,
            "receiver_unassociated": no_receiver,
            "association_rate": {
                "sender": round(has_sender / total_docs * 100, 1) if total_docs > 0 else 0,
                "receiver": round(has_receiver / total_docs * 100, 1) if total_docs > 0 else 0,
            }
        }

    # =========================================================================
    # 進階篩選
    # =========================================================================

    async def filter_agencies(
        self,
        agency_type: Optional[str] = None,
        search: Optional[str] = None,
        has_documents: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = 'agency_name',
        sort_order: str = 'asc'
    ) -> Tuple[List[GovernmentAgency], int]:
        """
        進階篩選機關

        Args:
            agency_type: 機關類型
            search: 搜尋關鍵字
            has_documents: 是否有公文往來
            skip: 跳過筆數
            limit: 取得筆數
            sort_by: 排序欄位
            sort_order: 排序方向

        Returns:
            (機關列表, 總數) 元組
        """
        query = select(GovernmentAgency)
        conditions = []

        # 類型篩選
        if agency_type:
            conditions.append(GovernmentAgency.agency_type == agency_type)

        # 搜尋條件
        if search:
            search_pattern = f"%{search}%"
            search_conditions = [
                getattr(GovernmentAgency, field).ilike(search_pattern)
                for field in self.SEARCH_FIELDS
                if hasattr(GovernmentAgency, field)
            ]
            if search_conditions:
                conditions.append(or_(*search_conditions))

        # 有公文往來篩選
        if has_documents is not None:
            sender_ids = select(OfficialDocument.sender_agency_id).where(
                OfficialDocument.sender_agency_id.isnot(None)
            ).distinct()
            receiver_ids = select(OfficialDocument.receiver_agency_id).where(
                OfficialDocument.receiver_agency_id.isnot(None)
            ).distinct()

            if has_documents:
                conditions.append(
                    or_(
                        GovernmentAgency.id.in_(sender_ids),
                        GovernmentAgency.id.in_(receiver_ids)
                    )
                )
            else:
                conditions.append(
                    and_(
                        GovernmentAgency.id.notin_(sender_ids),
                        GovernmentAgency.id.notin_(receiver_ids)
                    )
                )

        if conditions:
            query = query.where(and_(*conditions))

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 排序
        sort_column = getattr(GovernmentAgency, sort_by, GovernmentAgency.agency_name)
        if sort_order.lower() == 'desc':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # 分頁
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        agencies = list(result.scalars().all())

        return agencies, total

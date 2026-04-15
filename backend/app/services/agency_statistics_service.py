"""
機關統計服務

從 AgencyService 拆分，負責機關統計相關功能。

版本: 1.0.0
更新日期: 2026-03-10
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, case

from app.repositories import AgencyRepository
from app.services.base import StatisticsHelper
from app.extended.models import GovernmentAgency, OfficialDocument

logger = logging.getLogger(__name__)


class AgencyStatisticsService:
    """
    機關統計服務

    負責機關列表含統計資料查詢、分類統計等。

    Example:
        service = AgencyStatisticsService(db)
        stats = await service.get_agency_statistics()
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = AgencyRepository(db)
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def _normalize_category(agency_type: Optional[str]) -> str:
        """將機關類型標準化為三大分類"""
        if not agency_type:
            return '其他單位'
        if agency_type == '政府機關':
            return '政府機關'
        if agency_type == '民間企業':
            return '民間企業'
        return '其他單位'

    async def get_agencies_with_stats(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        取得機關列表含統計資料

        Args:
            skip: 跳過筆數
            limit: 取得筆數
            search: 搜尋關鍵字
            category: 機關分類篩選 (政府機關/民間企業/其他單位)

        Returns:
            含統計資料的機關列表
        """
        query = select(GovernmentAgency)

        if search:
            query = query.where(
                or_(
                    GovernmentAgency.agency_name.ilike(f"%{search}%"),
                    GovernmentAgency.agency_short_name.ilike(f"%{search}%"),
                )
            )

        if category:
            if category == '政府機關':
                query = query.where(GovernmentAgency.agency_type == '政府機關')
            elif category == '民間企業':
                query = query.where(GovernmentAgency.agency_type == '民間企業')
            elif category == '其他單位':
                query = query.where(
                    or_(
                        GovernmentAgency.agency_type.is_(None),
                        GovernmentAgency.agency_type == '',
                        GovernmentAgency.agency_type == '其他單位',
                        GovernmentAgency.agency_type == '其他機關',
                        GovernmentAgency.agency_type == '社會團體',
                        GovernmentAgency.agency_type == '教育機構',
                    )
                )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        agencies_result = await self.db.execute(
            query.order_by(
                desc(func.coalesce(GovernmentAgency.updated_at, GovernmentAgency.created_at))
            ).offset(skip).limit(limit)
        )
        agencies = agencies_result.scalars().all()

        agencies_with_stats = await self._batch_calculate_agency_stats(agencies)

        return {
            "agencies": agencies_with_stats,
            "total": total,
            "returned": len(agencies_with_stats),
        }

    async def _batch_calculate_agency_stats(
        self,
        agencies: List[GovernmentAgency],
    ) -> List[Dict[str, Any]]:
        """批次計算所有機關統計（單一 GROUP BY 查詢取代每機關 3 次查詢）"""
        if not agencies:
            return []

        agency_ids = [a.id for a in agencies]

        stats_query = (
            select(
                GovernmentAgency.id.label("agency_id"),
                func.count(
                    case((OfficialDocument.sender_agency_id == GovernmentAgency.id, OfficialDocument.id))
                ).label("sent_count"),
                func.count(
                    case((OfficialDocument.receiver_agency_id == GovernmentAgency.id, OfficialDocument.id))
                ).label("received_count"),
                func.max(OfficialDocument.doc_date).label("last_activity"),
            )
            .outerjoin(
                OfficialDocument,
                or_(
                    OfficialDocument.sender_agency_id == GovernmentAgency.id,
                    OfficialDocument.receiver_agency_id == GovernmentAgency.id,
                ),
            )
            .where(GovernmentAgency.id.in_(agency_ids))
            .group_by(GovernmentAgency.id)
        )

        result = await self.db.execute(stats_query)
        stats_map = {}
        for row in result.all():
            stats_map[row.agency_id] = {
                "sent_count": row.sent_count or 0,
                "received_count": row.received_count or 0,
                "last_activity": row.last_activity,
            }

        agencies_with_stats = []
        for agency in agencies:
            stats = stats_map.get(agency.id, {"sent_count": 0, "received_count": 0, "last_activity": None})
            normalized_category = self._normalize_category(agency.agency_type)
            agencies_with_stats.append({
                "id": agency.id,
                "agency_name": agency.agency_name,
                "agency_short_name": agency.agency_short_name,
                "agency_code": agency.agency_code,
                "agency_type": agency.agency_type,
                "category": normalized_category,
                "contact_person": agency.contact_person,
                "phone": agency.phone,
                "email": agency.email,
                "address": agency.address,
                "document_count": stats["sent_count"] + stats["received_count"],
                "sent_count": stats["sent_count"],
                "received_count": stats["received_count"],
                "last_activity": stats["last_activity"],
                "created_at": agency.created_at,
                "updated_at": agency.updated_at,
            })

        return agencies_with_stats

    async def get_agency_statistics(self) -> Dict[str, Any]:
        """
        取得機關統計資料

        Returns:
            統計資料字典
        """
        try:
            basic_stats = await StatisticsHelper.get_basic_stats(self.db, GovernmentAgency)
            total_agencies = basic_stats.get("total", 0)

            grouped_stats = await StatisticsHelper.get_grouped_stats(
                self.db, GovernmentAgency, 'agency_type'
            )

            category_counts: Dict[str, int] = {}
            for agency_type, count in grouped_stats.items():
                original_type = None if agency_type == 'null' else agency_type
                category = self._normalize_category(original_type)
                category_counts[category] = category_counts.get(category, 0) + count

            category_order = ['政府機關', '民間企業', '其他單位']
            categories = []
            for cat in category_order:
                cnt = category_counts.get(cat, 0)
                if cnt > 0:
                    categories.append({
                        'category': cat,
                        'count': cnt,
                        'percentage': round((cnt / total_agencies * 100), 1) if total_agencies > 0 else 0,
                    })

            data_quality = await self._get_data_quality()

            return {
                "total_agencies": total_agencies,
                "categories": categories,
                "data_quality": data_quality,
            }
        except Exception as e:
            self.logger.error(f"取得機關統計資料失敗: {e}", exc_info=True)
            return {"total_agencies": 0, "categories": [], "data_quality": None}

    async def _get_data_quality(self) -> Dict[str, Any]:
        """取得資料品質統計：agency_code 缺失依 source 分類"""
        query = (
            select(
                func.coalesce(GovernmentAgency.source, "manual").label("source"),
                func.count(GovernmentAgency.id).label("missing_count"),
            )
            .where(
                or_(
                    GovernmentAgency.agency_code.is_(None),
                    GovernmentAgency.agency_code == "",
                )
            )
            .group_by(func.coalesce(GovernmentAgency.source, "manual"))
        )
        result = await self.db.execute(query)
        missing_by_source: Dict[str, int] = {}
        total_missing = 0
        for row in result.all():
            missing_by_source[row.source] = row.missing_count
            total_missing += row.missing_count
        return {
            "missing_agency_code": total_missing,
            "missing_by_source": missing_by_source,
        }

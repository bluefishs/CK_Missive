"""
機關服務層 - 繼承 BaseService 實現標準 CRUD

使用泛型基類減少重複代碼，提供統一的資料庫操作介面。
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_

from app.services.base_service import BaseService
from app.extended.models import GovernmentAgency, OfficialDocument
from app.schemas.agency import AgencyCreate, AgencyUpdate

logger = logging.getLogger(__name__)


class AgencyService(BaseService[GovernmentAgency, AgencyCreate, AgencyUpdate]):
    """
    機關服務 - 繼承 BaseService

    提供機關相關的 CRUD 操作和業務邏輯。
    """

    def __init__(self):
        """初始化機關服務"""
        super().__init__(GovernmentAgency, "機關")

    # =========================================================================
    # 覆寫方法 - 加入業務邏輯
    # =========================================================================

    async def create(
        self,
        db: AsyncSession,
        data: AgencyCreate
    ) -> GovernmentAgency:
        """
        建立機關 - 加入名稱重複檢查

        Args:
            db: 資料庫 session
            data: 建立資料

        Returns:
            新建的機關

        Raises:
            ValueError: 機關名稱已存在
        """
        # 檢查機關名稱是否重複
        existing = await self.get_by_field(db, "agency_name", data.agency_name)
        if existing:
            raise ValueError(f"機關名稱已存在: {data.agency_name}")

        return await super().create(db, data)

    async def delete(
        self,
        db: AsyncSession,
        agency_id: int
    ) -> bool:
        """
        刪除機關 - 檢查是否有關聯公文

        Args:
            db: 資料庫 session
            agency_id: 機關 ID

        Returns:
            是否刪除成功

        Raises:
            ValueError: 機關仍有關聯公文
        """
        # 檢查是否有關聯公文
        usage_query = select(func.count(OfficialDocument.id)).where(
            or_(
                OfficialDocument.sender_agency_id == agency_id,
                OfficialDocument.receiver_agency_id == agency_id
            )
        )
        result = await db.execute(usage_query)
        usage_count = result.scalar_one()

        if usage_count > 0:
            raise ValueError(f"無法刪除，尚有 {usage_count} 筆公文與此機關關聯")

        return await super().delete(db, agency_id)

    # =========================================================================
    # 擴充方法 - 業務特定功能
    # =========================================================================

    async def get_agency_by_name(
        self,
        db: AsyncSession,
        name: str
    ) -> Optional[GovernmentAgency]:
        """
        依名稱取得機關

        Args:
            db: 資料庫 session
            name: 機關名稱

        Returns:
            機關或 None
        """
        return await self.get_by_field(db, "agency_name", name)

    async def get_agencies_with_search(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        取得機關列表（含搜尋）

        Args:
            db: 資料庫 session
            skip: 跳過筆數
            limit: 取得筆數
            search: 搜尋關鍵字

        Returns:
            機關列表（字典格式）
        """
        query = select(GovernmentAgency)

        # 搜尋條件 - 支援名稱和簡稱
        if search:
            search_filter = or_(
                GovernmentAgency.agency_name.ilike(f"%{search}%"),
                GovernmentAgency.agency_short_name.ilike(f"%{search}%")
            )
            query = query.where(search_filter)

        query = query.order_by(GovernmentAgency.agency_name).offset(skip).limit(limit)
        result = await db.execute(query)
        agencies = result.scalars().all()

        # 轉換為字典格式
        return [
            {
                "id": agency.id,
                "agency_name": agency.agency_name,
                "agency_short_name": agency.agency_short_name,
                "agency_code": agency.agency_code,
                "agency_type": agency.agency_type,
                "contact_person": agency.contact_person,
                "phone": agency.phone,
                "email": agency.email,
                "address": agency.address,
                "notes": agency.notes,
                "created_at": agency.created_at,
                "updated_at": agency.updated_at
            }
            for agency in agencies
        ]

    async def get_total_with_search(
        self,
        db: AsyncSession,
        search: Optional[str] = None
    ) -> int:
        """
        取得機關總數（含搜尋條件）

        Args:
            db: 資料庫 session
            search: 搜尋關鍵字

        Returns:
            符合條件的機關總數
        """
        query = select(func.count(GovernmentAgency.id))

        if search:
            search_filter = or_(
                GovernmentAgency.agency_name.ilike(f"%{search}%"),
                GovernmentAgency.agency_short_name.ilike(f"%{search}%")
            )
            query = query.where(search_filter)

        result = await db.execute(query)
        return result.scalar() or 0

    async def get_agencies_with_stats(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        取得機關列表含統計資料

        Args:
            db: 資料庫 session
            skip: 跳過筆數
            limit: 取得筆數
            search: 搜尋關鍵字

        Returns:
            含統計資料的機關列表
        """
        query = select(GovernmentAgency)

        if search:
            query = query.where(
                or_(
                    GovernmentAgency.agency_name.ilike(f"%{search}%"),
                    GovernmentAgency.agency_short_name.ilike(f"%{search}%")
                )
            )

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        # 取得分頁資料
        agencies_result = await db.execute(
            query.order_by(
                desc(func.coalesce(GovernmentAgency.updated_at, GovernmentAgency.created_at))
            ).offset(skip).limit(limit)
        )
        agencies = agencies_result.scalars().all()

        # 計算各機關統計
        agencies_with_stats = [
            await self._calculate_agency_stats(db, agency)
            for agency in agencies
        ]

        return {
            "agencies": agencies_with_stats,
            "total": total,
            "returned": len(agencies_with_stats)
        }

    async def _calculate_agency_stats(
        self,
        db: AsyncSession,
        agency: GovernmentAgency
    ) -> Dict[str, Any]:
        """
        計算單一機關的統計資料

        Args:
            db: 資料庫 session
            agency: 機關實體

        Returns:
            含統計資料的機關字典
        """
        # 發送/接收公文數
        sent_count = (await db.execute(
            select(func.count()).where(OfficialDocument.sender_agency_id == agency.id)
        )).scalar() or 0

        received_count = (await db.execute(
            select(func.count()).where(OfficialDocument.receiver_agency_id == agency.id)
        )).scalar() or 0

        # 最後活動日期
        last_activity = (await db.execute(
            select(func.max(OfficialDocument.doc_date)).where(
                or_(
                    OfficialDocument.sender_agency_id == agency.id,
                    OfficialDocument.receiver_agency_id == agency.id
                )
            )
        )).scalar_one_or_none()

        # 標準化分類
        normalized_category = self._normalize_category(agency.agency_type)

        return {
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
            "document_count": sent_count + received_count,
            "sent_count": sent_count,
            "received_count": received_count,
            "last_activity": last_activity,
            "created_at": agency.created_at,
            "updated_at": agency.updated_at
        }

    async def get_agency_statistics(
        self,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        取得機關統計資料

        Args:
            db: 資料庫 session

        Returns:
            統計資料字典
        """
        try:
            # 總數
            total_agencies = await self.get_count(db)

            # 依類型統計
            agencies = (await db.execute(
                select(GovernmentAgency.agency_type)
            )).scalars().all()

            category_counts: Dict[str, int] = {}
            for agency_type in agencies:
                category = self._normalize_category(agency_type)
                category_counts[category] = category_counts.get(category, 0) + 1

            # 依照指定順序排序
            category_order = ['政府機關', '民間企業', '其他單位']
            categories = []
            for cat in category_order:
                cnt = category_counts.get(cat, 0)
                if cnt > 0:
                    categories.append({
                        'category': cat,
                        'count': cnt,
                        'percentage': round((cnt / total_agencies * 100), 1) if total_agencies > 0 else 0
                    })

            return {
                "total_agencies": total_agencies,
                "categories": categories
            }
        except Exception as e:
            logger.error(f"取得機關統計資料失敗: {e}", exc_info=True)
            return {
                "total_agencies": 0,
                "categories": []
            }

    def _normalize_category(self, agency_type: Optional[str]) -> str:
        """
        將機關類型標準化為三大分類

        Args:
            agency_type: 原始機關類型

        Returns:
            標準化分類：政府機關、民間企業、其他單位
        """
        if not agency_type:
            return '其他單位'
        if agency_type == '政府機關':
            return '政府機關'
        if agency_type == '民間企業':
            return '民間企業'
        return '其他單位'

    def _categorize_agency(self, agency_name: str) -> str:
        """
        根據機關名稱推斷分類（備用方法）

        Args:
            agency_name: 機關名稱

        Returns:
            推斷的分類
        """
        name = (agency_name or "").lower()
        if any(k in name for k in ['政府', '市政', '縣政', '部', '局', '署', '處']):
            return '政府機關'
        if any(k in name for k in ['公司', '企業', '集團']):
            return '民間企業'
        return '其他單位'

    # =========================================================================
    # 向後相容方法 (逐步淘汰)
    # =========================================================================

    async def get_agency(self, db: AsyncSession, agency_id: int) -> Optional[GovernmentAgency]:
        """@deprecated 使用 get_by_id"""
        return await self.get_by_id(db, agency_id)

    async def get_agencies(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[GovernmentAgency]:
        """@deprecated 使用 get_list"""
        return await self.get_list(db, skip=skip, limit=limit)

    async def create_agency(self, db: AsyncSession, agency: AgencyCreate) -> GovernmentAgency:
        """@deprecated 使用 create"""
        return await self.create(db, agency)

    async def update_agency(self, db: AsyncSession, agency_id: int, agency_update: AgencyUpdate) -> Optional[GovernmentAgency]:
        """@deprecated 使用 update"""
        return await self.update(db, agency_id, agency_update)

    async def delete_agency(self, db: AsyncSession, agency_id: int) -> bool:
        """@deprecated 使用 delete"""
        return await self.delete(db, agency_id)

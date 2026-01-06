"""
Service layer for Government Agency operations (Refactored)
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_

from app.extended.models import GovernmentAgency, OfficialDocument
from app.schemas.agency import AgencyCreate, AgencyUpdate

logger = logging.getLogger(__name__)

class AgencyService:
    async def get_agency(self, db: AsyncSession, agency_id: int) -> Optional[GovernmentAgency]:
        result = await db.execute(select(GovernmentAgency).where(GovernmentAgency.id == agency_id))
        return result.scalar_one_or_none()

    async def get_agencies(self, db: AsyncSession, skip: int, limit: int) -> List[GovernmentAgency]:
        result = await db.execute(select(GovernmentAgency).order_by(GovernmentAgency.agency_name).offset(skip).limit(limit))
        return result.scalars().all()

    async def create_agency(self, db: AsyncSession, agency: AgencyCreate) -> GovernmentAgency:
        existing = await self.get_agency_by_name(db, agency.agency_name)
        if existing:
            raise ValueError(f"機關名稱已存在: {agency.agency_name}")
        db_agency = GovernmentAgency(**agency.dict())
        db.add(db_agency)
        await db.commit()
        await db.refresh(db_agency)
        return db_agency

    async def update_agency(self, db: AsyncSession, agency_id: int, agency_update: AgencyUpdate) -> Optional[GovernmentAgency]:
        db_agency = await self.get_agency(db, agency_id)
        if not db_agency: return None
        update_data = agency_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_agency, key, value)
        await db.commit()
        await db.refresh(db_agency)
        return db_agency

    async def delete_agency(self, db: AsyncSession, agency_id: int) -> bool:
        usage_count = (await db.execute(select(func.count(OfficialDocument.id)).where((OfficialDocument.sender_agency_id == agency_id) | (OfficialDocument.receiver_agency_id == agency_id)))).scalar_one()
        if usage_count > 0:
            raise ValueError(f"無法刪除，尚有 {usage_count} 筆公文與此機關關聯。")
        db_agency = await self.get_agency(db, agency_id)
        if not db_agency: return False
        await db.delete(db_agency)
        await db.commit()
        return True

    async def get_agency_by_name(self, db: AsyncSession, name: str) -> Optional[GovernmentAgency]:
        result = await db.execute(select(GovernmentAgency).where(GovernmentAgency.agency_name == name))
        return result.scalar_one_or_none()

    async def get_agencies_with_stats(self, db: AsyncSession, skip: int, limit: int, search: Optional[str]) -> Dict[str, Any]:
        query = select(GovernmentAgency)
        if search:
            # 支援搜尋機關名稱和簡稱
            query = query.where(
                or_(
                    GovernmentAgency.agency_name.ilike(f"%{search}%"),
                    GovernmentAgency.agency_short_name.ilike(f"%{search}%")
                )
            )
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()
        agencies_result = await db.execute(query.order_by(desc(func.coalesce(GovernmentAgency.updated_at, GovernmentAgency.created_at))).offset(skip).limit(limit))
        agencies = agencies_result.scalars().all()
        agencies_with_stats = [await self._calculate_agency_stats(db, agency) for agency in agencies]
        return {"agencies": agencies_with_stats, "total": total, "returned": len(agencies_with_stats)}

    async def _calculate_agency_stats(self, db: AsyncSession, agency: GovernmentAgency) -> Dict[str, Any]:
        sent_count = (await db.execute(select(func.count()).where(OfficialDocument.sender_agency_id == agency.id))).scalar() or 0
        received_count = (await db.execute(select(func.count()).where(OfficialDocument.receiver_agency_id == agency.id))).scalar() or 0
        # 標準化分類（將 agency_type 映射到三大分類）
        normalized_category = self._normalize_category(agency.agency_type)
        return {
            "id": agency.id,
            "agency_name": agency.agency_name,
            "agency_short_name": agency.agency_short_name,  # 機關簡稱
            "agency_code": agency.agency_code,
            "agency_type": agency.agency_type,
            "category": normalized_category,  # 標準化分類（政府機關、民間企業、其他單位）
            "contact_person": agency.contact_person,
            "phone": agency.phone,
            "address": agency.address,
            "email": agency.email,
            "document_count": sent_count + received_count,
            "sent_count": sent_count,
            "received_count": received_count,
            "last_activity": (await db.execute(select(func.max(OfficialDocument.doc_date)).where((OfficialDocument.sender_agency_id == agency.id) | (OfficialDocument.receiver_agency_id == agency.id)))).scalar_one_or_none(),
            "created_at": agency.created_at,
            "updated_at": agency.updated_at
        }

    async def get_agency_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """取得機關統計資料（使用資料庫 agency_type 欄位）"""
        total_agencies = (await db.execute(select(func.count(GovernmentAgency.id)))).scalar_one()

        # 直接從資料庫查詢 agency_type 分組統計
        agencies = (await db.execute(select(GovernmentAgency.agency_type))).scalars().all()
        category_counts = {}
        for agency_type in agencies:
            # 將 NULL 或舊分類映射到新三大分類
            category = self._normalize_category(agency_type)
            category_counts[category] = category_counts.get(category, 0) + 1

        # 依照指定順序排序：政府機關、民間企業、其他單位
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

        return {"total_agencies": total_agencies, "categories": categories}

    def _normalize_category(self, agency_type: Optional[str]) -> str:
        """將機關類型標準化為三大分類：政府機關、民間企業、其他單位"""
        if not agency_type:
            return '其他單位'
        if agency_type == '政府機關':
            return '政府機關'
        if agency_type == '民間企業':
            return '民間企業'
        # 其他機關、社會團體、教育機構 等舊分類 → 其他單位
        return '其他單位'

    def _categorize_agency(self, agency_name: str) -> str:
        """根據機關名稱推斷分類（備用方法，當 agency_type 為空時使用）"""
        name = (agency_name or "").lower()
        if any(k in name for k in ['政府', '市政', '縣政', '部', '局', '署', '處']): return '政府機關'
        if any(k in name for k in ['公司', '企業', '集團']): return '民間企業'
        return '其他單位'

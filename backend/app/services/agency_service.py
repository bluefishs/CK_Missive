"""
Service layer for Government Agency operations (Refactored)
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

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
        if search: query = query.where(GovernmentAgency.agency_name.ilike(f"%{search}%"))
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()
        agencies_result = await db.execute(query.order_by(desc(func.coalesce(GovernmentAgency.updated_at, GovernmentAgency.created_at))).offset(skip).limit(limit))
        agencies = agencies_result.scalars().all()
        agencies_with_stats = [await self._calculate_agency_stats(db, agency) for agency in agencies]
        return {"agencies": agencies_with_stats, "total": total, "returned": len(agencies_with_stats)}

    async def _calculate_agency_stats(self, db: AsyncSession, agency: GovernmentAgency) -> Dict[str, Any]:
        sent_count = (await db.execute(select(func.count()).where(OfficialDocument.sender_agency_id == agency.id))).scalar() or 0
        received_count = (await db.execute(select(func.count()).where(OfficialDocument.receiver_agency_id == agency.id))).scalar() or 0
        return {
            "id": agency.id,
            "agency_name": agency.agency_name,  # 修復：使用正確的欄位名稱
            "agency_code": agency.agency_code,
            "agency_type": agency.agency_type,
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
        total_agencies = (await db.execute(select(func.count(GovernmentAgency.id)))).scalar_one()
        agencies = (await db.execute(select(GovernmentAgency.agency_name))).scalars().all()
        category_counts = {}
        for name in agencies:
            category = self._categorize_agency(name)
            category_counts[category] = category_counts.get(category, 0) + 1
        categories = [{'category': cat, 'count': cnt, 'percentage': round((cnt / total_agencies * 100), 1) if total_agencies > 0 else 0} for cat, cnt in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)]
        return {"total_agencies": total_agencies, "categories": categories}

    def _categorize_agency(self, agency_name: str) -> str:
        name = (agency_name or "").lower()
        if any(k in name for k in ['政府', '市政', '縣政', '部', '局', '署', '處']): return '政府機關'
        if any(k in name for k in ['公司', '企業', '集團']): return '民間企業'
        if any(k in name for k in ['大學', '學院', '學校']): return '教育機構'
        return '其他機關'

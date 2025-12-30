"""
Service layer for Partner Vendor operations (with total count)
"""
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.extended.models import PartnerVendor, project_vendor_association
from app.schemas.vendor import VendorCreate, VendorUpdate

logger = logging.getLogger(__name__)

class VendorService:
    """協力廠商相關的資料庫操作服務"""

    async def get_vendor(self, db: AsyncSession, vendor_id: int) -> Optional[PartnerVendor]:
        result = await db.execute(select(PartnerVendor).where(PartnerVendor.id == vendor_id))
        return result.scalar_one_or_none()

    async def get_vendors(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[dict]:
        result = await db.execute(select(PartnerVendor).order_by(PartnerVendor.vendor_name).offset(skip).limit(limit))
        vendors = result.scalars().all()

        # 轉換為字典格式以便序列化
        return [
            {
                "id": vendor.id,
                "vendor_name": vendor.vendor_name,
                "vendor_code": vendor.vendor_code,
                "contact_person": vendor.contact_person,
                "phone": vendor.phone,
                "address": vendor.address,
                "email": vendor.email,
                "business_type": vendor.business_type,
                "rating": vendor.rating,
                "created_at": vendor.created_at,
                "updated_at": vendor.updated_at
            }
            for vendor in vendors
        ]

    async def get_total_vendors(self, db: AsyncSession) -> int:
        """ 獲取廠商總數 """
        result = await db.execute(select(func.count(PartnerVendor.id)))
        return result.scalar() or 0

    async def create_vendor(self, db: AsyncSession, vendor: VendorCreate) -> PartnerVendor:
        if vendor.vendor_code:
            existing = (await db.execute(select(PartnerVendor).where(PartnerVendor.vendor_code == vendor.vendor_code))).scalar_one_or_none()
            if existing:
                raise ValueError(f"廠商統一編號 {vendor.vendor_code} 已存在")
        db_vendor = PartnerVendor(**vendor.dict())
        db.add(db_vendor)
        await db.commit()
        await db.refresh(db_vendor)
        return db_vendor

    async def update_vendor(self, db: AsyncSession, vendor_id: int, vendor_update: VendorUpdate) -> Optional[PartnerVendor]:
        db_vendor = await self.get_vendor(db, vendor_id)
        if not db_vendor:
            return None
        update_data = vendor_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_vendor, key, value)
        await db.commit()
        await db.refresh(db_vendor)
        return db_vendor

    async def delete_vendor(self, db: AsyncSession, vendor_id: int) -> bool:
        usage_query = select(func.count(project_vendor_association.c.project_id)).where(
            project_vendor_association.c.vendor_id == vendor_id
        )
        usage_count = (await db.execute(usage_query)).scalar_one()
        if usage_count > 0:
            raise ValueError(f"無法刪除，此廠商仍與 {usage_count} 個專案關聯。")

        db_vendor = await self.get_vendor(db, vendor_id)
        if not db_vendor:
            return False
        await db.delete(db_vendor)
        await db.commit()
        return True

    async def get_vendor_statistics(self, db: AsyncSession) -> dict:
        try:
            total_vendors = await self.get_total_vendors(db)
            type_result = await db.execute(
                select(PartnerVendor.business_type, func.count(PartnerVendor.id))
                .group_by(PartnerVendor.business_type)
                .order_by(PartnerVendor.business_type)
            )
            type_stats = [
                {"business_type": row[0] or "未分類", "count": row[1]}
                for row in type_result.fetchall()
            ]
            rating_result = await db.execute(
                select(func.avg(PartnerVendor.rating)).where(PartnerVendor.rating.isnot(None))
            )
            avg_rating = rating_result.scalar()
            avg_rating = round(float(avg_rating), 2) if avg_rating else 0.0

            return {
                "total_vendors": total_vendors,
                "business_types": type_stats,
                "average_rating": avg_rating
            }
        except Exception as e:
            logger.error(f"取得廠商統計資料失敗: {e}", exc_info=True)
            return {
                "total_vendors": 0,
                "business_types": [],
                "average_rating": 0.0
            }
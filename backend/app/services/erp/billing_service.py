"""ERP 請款服務

Version: 1.0.0
"""
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPBilling
from app.repositories.erp import ERPBillingRepository
from app.schemas.erp import ERPBillingCreate, ERPBillingUpdate, ERPBillingResponse

logger = logging.getLogger(__name__)


class ERPBillingService:
    """請款管理服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ERPBillingRepository(db)

    async def create(self, data: ERPBillingCreate) -> ERPBillingResponse:
        """建立請款"""
        billing = ERPBilling(**data.model_dump())
        self.db.add(billing)
        await self.db.flush()
        await self.db.refresh(billing)
        await self.db.commit()
        return ERPBillingResponse.model_validate(billing)

    async def get_by_quotation(self, quotation_id: int) -> List[ERPBillingResponse]:
        """取得報價單所有請款"""
        items = await self.repo.get_by_quotation_id(quotation_id)
        return [ERPBillingResponse.model_validate(b) for b in items]

    async def update(self, billing_id: int, data: ERPBillingUpdate) -> Optional[ERPBillingResponse]:
        """更新請款 (含收款狀態)"""
        billing = await self.repo.get_by_id(billing_id)
        if not billing:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(billing, key, value)

        await self.db.flush()
        await self.db.refresh(billing)
        await self.db.commit()
        return ERPBillingResponse.model_validate(billing)

    async def delete(self, billing_id: int) -> bool:
        """刪除請款"""
        billing = await self.repo.get_by_id(billing_id)
        if not billing:
            return False
        await self.db.delete(billing)
        await self.db.commit()
        return True

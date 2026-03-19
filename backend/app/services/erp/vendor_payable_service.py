"""ERP 廠商應付服務

Version: 1.0.0
"""
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPVendorPayable
from app.repositories.erp import ERPVendorPayableRepository
from app.schemas.erp import ERPVendorPayableCreate, ERPVendorPayableUpdate, ERPVendorPayableResponse

logger = logging.getLogger(__name__)


class ERPVendorPayableService:
    """廠商應付管理服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ERPVendorPayableRepository(db)

    async def create(self, data: ERPVendorPayableCreate) -> ERPVendorPayableResponse:
        """建立廠商應付"""
        payable = ERPVendorPayable(**data.model_dump())
        self.db.add(payable)
        await self.db.flush()
        await self.db.refresh(payable)
        await self.db.commit()
        return ERPVendorPayableResponse.model_validate(payable)

    async def get_by_quotation(self, quotation_id: int) -> List[ERPVendorPayableResponse]:
        """取得報價單所有應付"""
        items = await self.repo.get_by_quotation_id(quotation_id)
        return [ERPVendorPayableResponse.model_validate(p) for p in items]

    async def update(self, payable_id: int, data: ERPVendorPayableUpdate) -> Optional[ERPVendorPayableResponse]:
        """更新廠商應付"""
        payable = await self.repo.get_by_id(payable_id)
        if not payable:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(payable, key, value)

        await self.db.flush()
        await self.db.refresh(payable)
        await self.db.commit()
        return ERPVendorPayableResponse.model_validate(payable)

    async def delete(self, payable_id: int) -> bool:
        """刪除廠商應付"""
        payable = await self.repo.get_by_id(payable_id)
        if not payable:
            return False
        await self.db.delete(payable)
        await self.db.commit()
        return True

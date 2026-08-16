"""報價明細 API（POST-only）—— 線上報價單

2026-08-16 owner：「線上報價單機制」。
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth
from app.db.database import get_async_db
from app.extended.models import User
from app.schemas.common import SuccessResponse
from app.services.erp.quotation_items import QuotationItemService

logger = logging.getLogger(__name__)
router = APIRouter()


class QuotationItemIn(BaseModel):
    item_name: str = Field("", max_length=200, description="工項名稱（空白列會被略過）")
    spec: Optional[str] = Field(None, max_length=300)
    unit: Optional[str] = Field(None, max_length=20)
    qty: float = Field(1, ge=0)
    unit_price: float = Field(0, ge=0)
    sort_order: int = 0
    notes: Optional[str] = None


class QuotationIdRequest(BaseModel):
    quotation_id: int = Field(..., ge=1)


class ReplaceItemsRequest(QuotationIdRequest):
    items: list[QuotationItemIn] = Field(default_factory=list)


@router.post("/detail", response_model=SuccessResponse)
async def quotation_detail(
    req: QuotationIdRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """線上報價單內容（逐項 + 小計 + 稅 + 總計）。"""
    try:
        data = await QuotationItemService(db).summary(req.quotation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SuccessResponse(data=data)


@router.post("/replace", response_model=SuccessResponse)
async def replace_items(
    req: ReplaceItemsRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """整批取代明細，並由小計加總回寫報價總價。

    ⚠️ 明細為空時**不會**把 total_price 歸零 ——
    空明細代表「還沒逐項拆」，不代表「這張報價是 0 元」。
    既有 55 張有總價但沒明細的報價不得被清掉。
    """
    try:
        result = await QuotationItemService(db).replace_items(
            req.quotation_id, [i.model_dump() for i in req.items],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await db.commit()
    return SuccessResponse(data=result)

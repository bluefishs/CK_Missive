# -*- coding: utf-8 -*-
"""我的專案統整 —— 個人儀表板核心卡（2026-09-03）。

POST /api/erp/my-summary：以登入者為承辦的案件／請款統整。只看自己的，不需要 reports 權限：
承辦看自己的待收與逾期是稽催機制的一部分，不是報表。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_db, require_auth
from app.extended.models import User
from app.schemas.common import SuccessResponse
from app.schemas.erp.my_summary import MyErpSummary
from app.services.erp.my_summary_service import get_my_summary

router = APIRouter()


@router.post("", summary="我的專案統整（承辦視角）")
async def my_summary(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
) -> SuccessResponse:
    data = await get_my_summary(db, current_user.id)
    return SuccessResponse(data=MyErpSummary(**data).model_dump())

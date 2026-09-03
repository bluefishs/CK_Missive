# -*- coding: utf-8 -*-
"""我的專案統整（個人儀表板）回應形狀。⚠️ 與 `frontend/src/types/erp.ts` 的 `MyErpSummary` 是一組契約。"""
from typing import List, Optional

from pydantic import BaseModel, Field


class MyOverdueItem(BaseModel):
    billing_id: int
    quotation_id: int
    case_code: Optional[str] = None
    case_name: Optional[str] = None
    billing_period: Optional[str] = None
    amount: int = 0
    billing_date: Optional[str] = None
    days_overdue: int = 0


class MyErpSummary(BaseModel):
    cases_active: int = 0
    cases_closed: int = 0
    quotes_unawarded: int = Field(0, description="我承辦、尚未成案的報價單")
    pending_count: int = 0
    pending_amount: int = 0
    overdue_count: int = 0
    overdue_amount: int = 0
    overdue_30_count: int = Field(0, description="逾期超過 30 天（夜間吹哨者的 critical 門檻）")
    received_ytd: int = Field(0, description="今年已收")
    no_billing: int = Field(0, description="我的成案有金額卻無請款——自動第一期沒接到")
    overdue_items: List[MyOverdueItem] = []

# -*- coding: utf-8 -*-
"""金流異常判讀的請求 schema（唯一來源；endpoints 不得本地定義 BaseModel，weekly 59）。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AnomalyListRequest(BaseModel):
    #: 只列還沒有人判讀的（待處理清單）。預設 False ＝連已判讀的一起列，
    #: 因為「已判讀」不代表數字變正常了。
    only_open: bool = False
    codes: Optional[list[str]] = None
    year: Optional[int] = Field(None, description="案件年度（西元，見 §2.5）")


class AnomalyAckRequest(BaseModel):
    quotation_id: int
    anomaly_type: str
    #: 必填且不得只是空白 —— 沒有原因的判讀等於把問題藏起來。
    reason: str = Field(..., min_length=2, max_length=500)


class AnomalyUnackRequest(BaseModel):
    quotation_id: int
    anomaly_type: str

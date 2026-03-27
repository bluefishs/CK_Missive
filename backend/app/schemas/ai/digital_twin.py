# -*- coding: utf-8 -*-
"""
Digital Twin (數位分身) 請求/回應 Schema

SSOT - 從 endpoints/ai/digital_twin.py 遷移至此。

Version: 1.0.0
Created: 2026-03-23
"""

from pydantic import BaseModel, Field


class DigitalTwinQueryRequest(BaseModel):
    """數位分身查詢請求"""

    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None
    context: dict | None = None


class DelegateAutoRequest(BaseModel):
    """跨域自動委派請求 (E-6 Federation Query)"""

    intent: str = Field(..., min_length=1, max_length=4096)
    context: dict | None = None
    timeout: float = Field(default=30.0, ge=1.0, le=120.0)


class TaskApprovalRequest(BaseModel):
    """任務審批請求 (V-2.1 Human Approval Gate)"""

    approved_by: str = Field(default="", max_length=100)


class TaskRejectionRequest(BaseModel):
    """任務拒絕請求 (V-2.1 Human Approval Gate)"""

    rejected_by: str = Field(default="", max_length=100)
    reason: str = Field(default="", max_length=500)

"""電子發票同步相關 Schemas"""
from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict, model_validator
import datetime
from typing import Optional
from decimal import Decimal

# v6.10.1 (2026-05-20): 日期防呆 SSOT helper
from app.schemas.common import validate_date_ordering


class EInvoiceSyncRequest(BaseModel):
    """手動觸發同步請求"""
    start_date: Optional[datetime.date] = Field(None, description="查詢起始日期 (預設前 3 天)")
    end_date: Optional[datetime.date] = Field(None, description="查詢結束日期 (預設今天)")

    @model_validator(mode="after")
    def _check_date_order(self):
        validate_date_ordering(self.start_date, self.end_date)
        return self


class EInvoiceSyncLogResponse(BaseModel):
    """同步批次記錄回應"""
    id: int
    buyer_ban: str
    query_start: datetime.date
    query_end: datetime.date
    status: str
    total_fetched: int
    new_imported: int
    skipped_duplicate: int
    detail_fetched: int
    error_message: Optional[str] = None
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EInvoiceSyncLogQuery(BaseModel):
    """同步記錄查詢"""
    skip: int = 0
    limit: int = Field(default=10, le=50)


class ReceiptUploadRequest(BaseModel):
    """收據上傳關聯請求"""
    invoice_id: int = Field(..., description="發票 ID")
    case_code: Optional[str] = Field(None, max_length=50, description="案號")
    category: Optional[str] = Field(None, max_length=50, description="費用分類")


class PendingReceiptQuery(BaseModel):
    """待核銷清單查詢"""
    skip: int = 0
    limit: int = Field(default=20, le=100)

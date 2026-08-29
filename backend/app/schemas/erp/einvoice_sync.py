"""電子發票同步相關 Schemas"""
from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict, model_validator
import datetime
from typing import Optional
from decimal import Decimal

# v6.10.1 (2026-05-20): 日期防呆 SSOT helper
from app.schemas.common import PaginatedResponse, validate_date_ordering
from app.schemas.erp.expense import ExpenseInvoiceResponse


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

# ─────────────────────────────────────────────────────────────────────────
# 待核銷清單回應 —— **統計卡的全量合計必須進 schema**（型別 SSOT，規範 §3）
#
# ⚠️ 2026-08-29 自我更正：我第一版是在端點裡拼裸 dict 回傳
# `{**resp.model_dump(), "totals": {...}}` —— 那**繞過了 response schema**：
#   ① 該欄位對 OpenAPI 不可見（前端無從產生型別）
#   ② 前端只能用 inline cast 補償，後端改名不會產生任何編譯錯誤
# ⇒ 契約在前後端各宣告一次，靠巧合一致而非結構保證。
# 這正是我同一天在別處強制的那條規範，自己卻違反了。
class PendingReceiptTotals(BaseModel):
    """待核銷清單的**分頁前**合計（development-rules §2.6 ①）。

    ⚠️ `pending_amount` 刻意用 **str** 傳送：金額是 Decimal，
    JSON number 會有浮點誤差。前端負責 `Number(...)` 轉換。
    """

    pending_amount: str = Field(..., description="待核銷發票金額合計（全量，非當頁）")


class PendingReceiptListResponse(PaginatedResponse[ExpenseInvoiceResponse]):
    """待核銷清單回應：分頁項目 + 全量合計。

    卡片「待核銷發票」讀 `pagination.total`、「待核銷金額」讀
    `totals.pending_amount` —— 兩者同源同條件，不會一個當頁一個全量。
    """

    totals: PendingReceiptTotals = Field(..., description="分頁前的全量合計")

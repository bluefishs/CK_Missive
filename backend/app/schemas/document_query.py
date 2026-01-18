"""
Pydantic schemas for Document Query Operations
公文查詢相關的統一 Schema 定義

包含：
- 下拉選項查詢 (Dropdown Query)
- 搜尋請求 (Search Request)
- 審計日誌查詢 (Audit Log Query)
- 匯出請求 (Export Request)
"""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.common import PaginationMeta, PaginationParams


# =============================================================================
# 下拉選項查詢 Schema
# =============================================================================

class DropdownQuery(BaseModel):
    """下拉選項查詢參數"""
    search: Optional[str] = Field(None, description="搜尋關鍵字")
    limit: int = Field(default=100, ge=1, le=1000, description="限制筆數")


class AgencyDropdownQuery(DropdownQuery):
    """機關下拉選項查詢參數"""
    agency_type: Optional[str] = Field(None, description="機關類型")


# =============================================================================
# 搜尋請求 Schema
# =============================================================================

class OptimizedSearchRequest(BaseModel):
    """優化搜尋請求"""
    keyword: str = Field(..., min_length=1, description="搜尋關鍵字")
    category: Optional[str] = Field(None, description="收發文分類 (send/receive)")
    delivery_method: Optional[str] = Field(None, description="發文形式")
    year: Optional[int] = Field(None, description="年度")
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=100, description="每頁筆數")


class SearchSuggestionRequest(BaseModel):
    """搜尋建議請求"""
    prefix: str = Field(..., min_length=2, description="輸入前綴")
    limit: int = Field(default=10, ge=1, le=20, description="建議數量上限")


# =============================================================================
# 審計日誌 Schema
# =============================================================================

class AuditLogQuery(BaseModel):
    """審計日誌查詢參數"""
    document_id: Optional[int] = Field(None, description="公文 ID")
    table_name: Optional[str] = Field(None, description="表格名稱")
    action: Optional[str] = Field(None, description="操作類型 (CREATE/UPDATE/DELETE)")
    user_id: Optional[int] = Field(None, description="操作者 ID")
    is_critical: Optional[bool] = Field(None, description="是否為關鍵欄位變更")
    date_from: Optional[str] = Field(None, description="起始日期 (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="結束日期 (YYYY-MM-DD)")
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=100, description="每頁筆數")


class AuditLogItem(BaseModel):
    """審計日誌項目"""
    id: int
    table_name: str
    record_id: int
    action: str
    changes: Optional[str] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    source: Optional[str] = None
    is_critical: bool = False
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    """審計日誌查詢回應"""
    success: bool = True
    items: List[AuditLogItem] = []
    pagination: PaginationMeta


# =============================================================================
# 專案公文查詢 Schema
# =============================================================================

class ProjectDocumentsQuery(BaseModel):
    """專案關聯公文查詢參數"""
    project_id: int = Field(..., description="專案 ID")
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=50, ge=1, le=100, description="每頁筆數")


# =============================================================================
# 匯出請求 Schema
# =============================================================================

class DocumentExportQuery(BaseModel):
    """公文匯出查詢參數 (CSV)"""
    document_ids: Optional[List[int]] = Field(None, description="指定匯出的公文ID列表，若為空則匯出全部")
    category: Optional[str] = Field(None, description="類別篩選 (收文/發文)")
    year: Optional[int] = Field(None, description="年度篩選")
    format: str = Field(default="csv", description="匯出格式 (csv)")


class ExcelExportRequest(BaseModel):
    """Excel 匯出請求"""
    document_ids: Optional[List[int]] = Field(None, description="指定匯出的公文 ID 列表")
    category: Optional[str] = Field(None, description="類別篩選 (收文/發文)")
    year: Optional[int] = Field(None, description="年度篩選")
    keyword: Optional[str] = Field(None, description="關鍵字搜尋")
    status: Optional[str] = Field(None, description="狀態篩選")
    contract_case: Optional[str] = Field(None, description="承攬案件篩選")
    sender: Optional[str] = Field(None, description="發文單位篩選")
    receiver: Optional[str] = Field(None, description="受文單位篩選")

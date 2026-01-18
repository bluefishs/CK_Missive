"""
Pydantic schemas for Document Numbers
發文字號管理相關的統一 Schema 定義

注意：document_numbers 端點已棄用，請改用 documents_enhanced
此 Schema 僅供向後相容使用
"""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# 發文字號項目 Schema
# =============================================================================

class DocumentNumberItem(BaseModel):
    """發文字號項目"""
    id: int
    doc_prefix: str = ""
    year: int
    sequence_number: int = 0
    full_number: str
    subject: str = ""
    contract_case: str = ""
    contract_case_id: Optional[int] = None
    receiver: str = ""
    doc_date: Optional[str] = None
    status: str = "draft"
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentNumberListResponse(BaseModel):
    """發文字號列表回應"""
    items: List[DocumentNumberItem]
    total: int
    page: int
    limit: int
    total_pages: int


# =============================================================================
# 查詢請求 Schema
# =============================================================================

class DocumentNumberQueryRequest(BaseModel):
    """發文字號查詢請求 (POST-only)"""
    page: int = Field(default=1, ge=1, description="頁數")
    limit: int = Field(default=20, ge=1, le=100, description="每頁筆數")
    year: Optional[int] = Field(default=None, description="年度篩選")
    status: Optional[str] = Field(default=None, description="狀態篩選")
    keyword: Optional[str] = Field(default=None, description="關鍵字搜尋")
    sort_by: str = Field(default="doc_date", description="排序欄位")
    sort_order: str = Field(default="desc", description="排序方向")


# =============================================================================
# 統計相關 Schema
# =============================================================================

class YearlyStats(BaseModel):
    """年度統計"""
    year: int
    count: int


class YearRange(BaseModel):
    """年度範圍"""
    min_year: Optional[int] = None
    max_year: Optional[int] = None


class DocumentNumberStats(BaseModel):
    """發文字號統計"""
    total_count: int
    draft_count: int
    sent_count: int
    archived_count: int
    max_sequence: int
    year_range: YearRange
    yearly_stats: List[YearlyStats]


# =============================================================================
# 字號生成 Schema
# =============================================================================

class NextNumberRequest(BaseModel):
    """下一個字號請求"""
    prefix: Optional[str] = Field(default=None, description="文號前綴")
    year: Optional[int] = Field(default=None, description="指定年度")


class NextNumberResponse(BaseModel):
    """下一個字號回應"""
    full_number: str
    year: int
    roc_year: int
    sequence_number: int
    previous_max: int
    prefix: str


# =============================================================================
# CRUD 請求 Schema
# =============================================================================

class DocumentNumberCreateRequest(BaseModel):
    """建立發文字號請求"""
    subject: str = Field(..., min_length=1, description="公文主旨")
    receiver: str = Field(..., min_length=1, description="受文單位")
    contract_case_id: Optional[int] = Field(default=None, description="承攬案件 ID")
    doc_date: Optional[str] = Field(default=None, description="發文日期")
    status: str = Field(default="draft", description="狀態")


class DocumentNumberUpdateRequest(BaseModel):
    """更新發文字號請求"""
    subject: Optional[str] = Field(default=None, description="公文主旨")
    receiver: Optional[str] = Field(default=None, description="受文單位")
    contract_case_id: Optional[int] = Field(default=None, description="承攬案件 ID")
    doc_date: Optional[str] = Field(default=None, description="發文日期")
    status: Optional[str] = Field(default=None, description="狀態")

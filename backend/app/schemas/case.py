"""
Pydantic schemas for Case Management
案件管理相關的統一 Schema 定義
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.common import PaginationMeta, SortOrder


# =============================================================================
# 案件查詢 Schema
# =============================================================================

class CaseListQuery(BaseModel):
    """案件列表查詢參數"""
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=100, description="每頁筆數")
    status: Optional[str] = Field(None, description="狀態篩選")
    search: Optional[str] = Field(None, description="搜尋關鍵字")
    sort_by: str = Field(default="id", description="排序欄位")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="排序方向")


# =============================================================================
# 案件回應 Schema
# =============================================================================

class CaseResponse(BaseModel):
    """案件回應格式"""
    id: int
    case_number: str
    case_name: str
    description: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CaseListResponse(BaseModel):
    """案件列表回應格式"""
    success: bool = True
    items: List[CaseResponse] = []
    pagination: PaginationMeta

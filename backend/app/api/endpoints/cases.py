"""
案件管理 API 端點 (非同步化)

@version 2.0.0 - 統一回應格式
@date 2026-01-12
"""
from fastapi import APIRouter, Query, Depends, Body, status
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.core.dependencies import require_auth
from app.core.exceptions import NotFoundException
from app.schemas.common import PaginationMeta, DeleteResponse, SortOrder
from app.extended.models import User

router = APIRouter()


# ============================================================================
# 查詢參數 Schema
# ============================================================================

class CaseListQuery(BaseModel):
    """案件列表查詢參數"""
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=100, description="每頁筆數")
    status: Optional[str] = Field(None, description="狀態篩選")
    search: Optional[str] = Field(None, description="搜尋關鍵字")
    sort_by: str = Field(default="id", description="排序欄位")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="排序方向")


class CaseResponse(BaseModel):
    """案件回應格式"""
    id: int
    case_number: str
    case_name: str
    description: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None


class CaseListResponse(BaseModel):
    """案件列表回應格式"""
    success: bool = True
    items: list[CaseResponse]
    pagination: PaginationMeta


# ============================================================================
# API 端點
# ============================================================================

@router.post("/list", response_model=CaseListResponse, summary="查詢案件列表")
async def get_cases(
    query: CaseListQuery = Body(default=CaseListQuery()),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """
    查詢案件列表（POST-only 資安機制）

    目前為模擬資料，待實作完整 CRUD
    """
    # 模擬資料
    items = [
        CaseResponse(
            id=1,
            case_number="CASE-2025-001",
            case_name="測試案件",
            status="active",
            created_at=datetime.now()
        )
    ]
    total = 1

    return CaseListResponse(
        items=items,
        pagination=PaginationMeta.create(
            total=total,
            page=query.page,
            limit=query.limit
        )
    )


@router.post("/{case_id}/detail", response_model=CaseResponse, summary="取得案件詳情")
async def get_case(
    case_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """取得案件詳細資訊（POST-only 資安機制）"""
    # 模擬資料 - 實際應查詢資料庫
    if case_id != 1:
        raise NotFoundException(resource="案件", resource_id=case_id)

    return CaseResponse(
        id=case_id,
        case_number="CASE-2025-001",
        case_name="測試案件",
        description="案件描述...",
        status="active"
    )


@router.post(
    "",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立新案件"
)
async def create_case(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """建立新案件（POST-only 資安機制）"""
    # 模擬建立 - 實際應寫入資料庫
    return CaseResponse(
        id=2,
        case_number="CASE-2025-002",
        case_name="新案件",
        status="active",
        created_at=datetime.now()
    )

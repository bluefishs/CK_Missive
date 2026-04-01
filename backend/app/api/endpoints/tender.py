"""
標案檢索 API 端點 (POST-only)

提供政府電子採購網標案搜尋、詳情查詢、廠商搜尋、智能推薦。

Version: 1.0.0
"""
from typing import Optional, List
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends

from app.services.tender_search_service import TenderSearchService
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/tender", tags=["標案檢索"])


# ============================================================================
# Schemas
# ============================================================================

class TenderSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100, description="搜尋關鍵字")
    page: int = Field(1, ge=1, le=100)
    category: Optional[str] = Field(None, description="分類: 工程/勞務/財物")


class TenderDetailRequest(BaseModel):
    unit_id: str = Field(..., description="機關代碼")
    job_number: str = Field(..., description="標案案號")


class TenderCompanySearchRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=100)
    page: int = Field(1, ge=1, le=100)


class TenderRecommendRequest(BaseModel):
    keywords: Optional[List[str]] = Field(None, description="自訂關鍵字 (空=使用預設)")
    page: int = Field(1, ge=1)


# ============================================================================
# Dependencies
# ============================================================================

def get_tender_service() -> TenderSearchService:
    """取得標案搜尋服務 (含 Redis 快取)"""
    try:
        from app.core.redis_client import get_redis_client
        redis = get_redis_client()
    except Exception:
        redis = None
    return TenderSearchService(redis_client=redis)


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/search")
async def search_tenders(
    req: TenderSearchRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """搜尋標案 (依標題關鍵字)"""
    result = await service.search_by_title(
        query=req.query, page=req.page, category=req.category,
    )
    return SuccessResponse(data=result)


@router.post("/detail")
async def get_tender_detail(
    req: TenderDetailRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """取得標案詳情 (含歷次公告)"""
    result = await service.get_tender_detail(
        unit_id=req.unit_id, job_number=req.job_number,
    )
    if not result:
        return SuccessResponse(data=None, message="查無此標案")
    return SuccessResponse(data=result)


@router.post("/search-company")
async def search_by_company(
    req: TenderCompanySearchRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """依廠商名稱搜尋得標紀錄"""
    result = await service.search_by_company(
        company_name=req.company_name, page=req.page,
    )
    return SuccessResponse(data=result)


@router.post("/recommend")
async def recommend_tenders(
    req: TenderRecommendRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """智能推薦 — 依乾坤核心業務關鍵字推薦相關標案"""
    result = await service.recommend_tenders(
        keywords=req.keywords, page=req.page,
    )
    return SuccessResponse(data=result)

"""
標案圖譜 + 建案 API — graph / create-case
"""
from typing import Optional
from pydantic import BaseModel, Field

import logging
from fastapi import APIRouter, Depends, HTTPException

from app.services.tender_search_service import TenderSearchService
from app.schemas.common import SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class TenderGraphRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100)
    max_tenders: int = Field(20, ge=1, le=50)


class TenderCreateCaseRequest(BaseModel):
    """從標案建立 PM Case"""
    unit_id: str = Field(..., description="機關代碼")
    job_number: str = Field(..., description="標案案號")
    title: str = Field(..., description="標案名稱")
    unit_name: str = Field("", description="招標機關名稱")
    budget: Optional[str] = Field(None, description="預算金額")
    category: Optional[str] = Field(None, description="分類")


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

@router.post("/graph")
async def get_tender_graph(
    req: TenderGraphRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """標案知識圖譜 — DB 優先 + API 補充"""
    # 先從 DB 建圖
    db_graph = None
    try:
        from app.db.database import AsyncSessionFromDB
        from app.services.tender_cache_service import build_graph_from_db
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            db_graph = await build_graph_from_db(db, req.query, req.max_tenders)
    except Exception:
        pass

    if db_graph and db_graph.get("stats", {}).get("tenders", 0) >= 5:
        return SuccessResponse(data=db_graph)

    # DB 不足 → 回退 API
    result = await service.build_tender_graph(
        query=req.query, max_tenders=req.max_tenders,
    )
    return SuccessResponse(data=result)


@router.post("/create-case")
async def create_case_from_tender(
    req: TenderCreateCaseRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """從標案一鍵建立 PM Case + ERP Quotation"""
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.database import get_async_db as get_db
    from app.services.case_code_service import CaseCodeService
    from app.extended.models.pm import PMCase
    from app.extended.models.erp import ERPQuotation
    from app.db.database import AsyncSessionLocal
    import re
    from datetime import date

    async with AsyncSessionLocal() as db:
        # 防呆：檢查是否已建過此標案
        from sqlalchemy import select as sa_select
        existing = (await db.execute(
            sa_select(PMCase).where(
                PMCase.notes.ilike(f"%{req.job_number}%")
            )
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"此標案已建案: {existing.case_code} ({existing.case_name[:30]})"
            )

        code_service = CaseCodeService(db)

        # 解析預算金額
        budget_amount = 0
        if req.budget:
            nums = re.sub(r'[^\d.]', '', req.budget.replace(',', ''))
            budget_amount = int(float(nums)) if nums else 0

        year = date.today().year

        # 產生案號
        case_code = await code_service.generate_case_code("pm", year, "01")

        # 查找或建立委託單位 (招標機關)
        client_vendor_id = None
        if req.unit_name:
            from app.extended.models.core import PartnerVendor
            from sqlalchemy import select as sa_select
            existing_client = (await db.execute(
                sa_select(PartnerVendor).where(
                    PartnerVendor.vendor_name == req.unit_name,
                    PartnerVendor.vendor_type == 'client',
                )
            )).scalar_one_or_none()
            if existing_client:
                client_vendor_id = existing_client.id
            else:
                new_client = PartnerVendor(
                    vendor_name=req.unit_name,
                    vendor_type='client',
                    notes=f"[標案自動建立] {req.job_number}",
                )
                db.add(new_client)
                await db.flush()
                client_vendor_id = new_client.id

        # 建立 PM Case
        pm_case = PMCase(
            case_code=case_code,
            case_name=req.title,
            year=year,
            status="bidding",
            contract_amount=budget_amount if budget_amount > 0 else None,
            client_vendor_id=client_vendor_id,
            notes=f"來源: 政府標案 {req.job_number} ({req.unit_name})",
        )
        db.add(pm_case)
        await db.flush()

        # 邀標階段不建立 ERP Quotation — 等確認投標後再建
        await db.commit()

        return SuccessResponse(data={
            "case_code": case_code,
            "pm_case_id": pm_case.id,
            "message": f"已建立案件 {case_code}",
        })

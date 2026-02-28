"""
AI 分析結果持久化端點

提供公文 AI 分析結果的查詢、觸發與統計。

@version 1.0.0
@date 2026-02-28
"""

import logging

from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.core.dependencies import require_auth, require_admin
from app.core.exceptions import NotFoundException
from app.extended.models import User
from app.services.ai.document_analysis_service import DocumentAnalysisService
from app.schemas.ai import (
    DocumentAIAnalysisResponse,
    DocumentAIAnalysisBatchRequest,
    DocumentAIAnalysisBatchResponse,
    DocumentAIAnalysisStatsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["AI Analysis"])


def _get_service(db: AsyncSession = Depends(get_async_db)) -> DocumentAnalysisService:
    return DocumentAnalysisService(db)


@router.post(
    "/{document_id}",
    response_model=DocumentAIAnalysisResponse,
    summary="取得公文 AI 分析結果",
)
async def get_document_analysis(
    document_id: int,
    service: DocumentAnalysisService = Depends(_get_service),
    current_user: User = Depends(require_auth()),
):
    """
    取得指定公文的 AI 分析結果。
    若尚未分析則回傳 404。
    """
    analysis = await service.get_analysis(document_id)
    if not analysis:
        raise NotFoundException(resource="AI 分析結果", resource_id=document_id)
    return analysis


@router.post(
    "/{document_id}/analyze",
    response_model=DocumentAIAnalysisResponse,
    summary="觸發公文 AI 分析",
)
async def trigger_document_analysis(
    document_id: int,
    force: bool = Body(default=False, embed=True),
    service: DocumentAnalysisService = Depends(_get_service),
    current_user: User = Depends(require_auth()),
):
    """
    觸發 AI 分析（摘要 + 分類 + 關鍵字），結果存入資料庫。
    若已存在非過期結果且 force=false，直接回傳快取。
    """
    return await service.get_or_analyze(document_id, force=force)


@router.post(
    "/batch",
    response_model=DocumentAIAnalysisBatchResponse,
    summary="批次 AI 分析",
)
async def batch_analyze(
    request: DocumentAIAnalysisBatchRequest = Body(
        default=DocumentAIAnalysisBatchRequest()
    ),
    service: DocumentAnalysisService = Depends(_get_service),
    current_user: User = Depends(require_admin()),
):
    """
    批次分析無結果或已過期的公文（需管理員權限）。
    """
    counts = await service.batch_analyze(
        limit=request.limit, force=request.force
    )
    return DocumentAIAnalysisBatchResponse(
        success=True,
        processed=counts["processed"],
        success_count=counts["success"],
        error_count=counts["error"],
        skip_count=counts["skip"],
        message=f"批次分析完成：{counts['success']}/{counts['processed']} 成功",
    )


@router.post(
    "/stats",
    response_model=DocumentAIAnalysisStatsResponse,
    summary="AI 分析覆蓋率統計",
)
async def get_analysis_stats(
    service: DocumentAnalysisService = Depends(_get_service),
    current_user: User = Depends(require_auth()),
):
    """取得 AI 分析覆蓋率統計。"""
    stats = await service.get_analysis_stats()
    return DocumentAIAnalysisStatsResponse(**stats)

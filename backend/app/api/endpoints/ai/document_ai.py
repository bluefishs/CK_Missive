"""
公文 AI API 端點

Version: 1.0.0
Created: 2026-02-04

端點:
- POST /ai/document/summary - 生成公文摘要
- POST /ai/document/classify - 分類建議
- POST /ai/document/keywords - 關鍵字提取
- POST /ai/agency/match - AI 機關匹配
- GET /ai/health - AI 服務健康檢查
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.ai.document_ai_service import (
    DocumentAIService,
    get_document_ai_service,
)
from app.services.ai.ai_config import get_ai_config

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class SummaryRequest(BaseModel):
    """摘要生成請求"""

    subject: str = Field(..., description="公文主旨")
    content: Optional[str] = Field(None, description="公文內容")
    sender: Optional[str] = Field(None, description="發文機關")
    max_length: int = Field(100, ge=20, le=500, description="摘要最大長度")


class SummaryResponse(BaseModel):
    """摘要生成回應"""

    summary: str
    confidence: float
    source: str


class ClassifyRequest(BaseModel):
    """分類建議請求"""

    subject: str = Field(..., description="公文主旨")
    content: Optional[str] = Field(None, description="公文內容")
    sender: Optional[str] = Field(None, description="發文機關")


class ClassifyResponse(BaseModel):
    """分類建議回應"""

    doc_type: str
    category: str
    doc_type_confidence: float
    category_confidence: float
    reasoning: Optional[str] = None
    source: str


class KeywordsRequest(BaseModel):
    """關鍵字提取請求"""

    subject: str = Field(..., description="公文主旨")
    content: Optional[str] = Field(None, description="公文內容")
    max_keywords: int = Field(5, ge=1, le=10, description="最大關鍵字數量")


class KeywordsResponse(BaseModel):
    """關鍵字提取回應"""

    keywords: List[str]
    confidence: float
    source: str


class AgencyCandidate(BaseModel):
    """機關候選項"""

    id: int
    name: str
    short_name: Optional[str] = None


class AgencyMatchRequest(BaseModel):
    """機關匹配請求"""

    agency_name: str = Field(..., description="輸入的機關名稱")
    candidates: Optional[List[AgencyCandidate]] = Field(
        None, description="候選機關列表"
    )


class AgencyMatchResult(BaseModel):
    """匹配結果"""

    id: int
    name: str
    score: float


class AgencyMatchResponse(BaseModel):
    """機關匹配回應"""

    best_match: Optional[AgencyMatchResult] = None
    alternatives: List[AgencyMatchResult] = []
    is_new: bool
    reasoning: Optional[str] = None
    source: str


class HealthResponse(BaseModel):
    """健康檢查回應"""

    groq: Dict[str, Any]
    ollama: Dict[str, Any]


class AIConfigResponse(BaseModel):
    """AI 配置回應"""

    enabled: bool = Field(description="AI 功能是否啟用")
    providers: Dict[str, Any] = Field(description="可用的 AI 提供者")
    rate_limit: Dict[str, int] = Field(description="速率限制設定")
    cache: Dict[str, Any] = Field(description="快取設定")
    features: Dict[str, Dict[str, Any]] = Field(description="各功能的配置")


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/document/summary", response_model=SummaryResponse)
async def generate_summary(
    request: SummaryRequest,
    service: DocumentAIService = Depends(get_document_ai_service),
) -> SummaryResponse:
    """
    生成公文摘要

    根據公文主旨和內容，使用 AI 生成簡潔的摘要。
    """
    logger.info(f"生成摘要: {request.subject[:50]}...")

    result = await service.generate_summary(
        subject=request.subject,
        content=request.content,
        sender=request.sender,
        max_length=request.max_length,
    )

    return SummaryResponse(**result)


@router.post("/document/classify", response_model=ClassifyResponse)
async def suggest_classification(
    request: ClassifyRequest,
    service: DocumentAIService = Depends(get_document_ai_service),
) -> ClassifyResponse:
    """
    建議公文分類

    根據公文資訊，AI 建議公文類型和收發類別。
    """
    logger.info(f"分類建議: {request.subject[:50]}...")

    result = await service.suggest_classification(
        subject=request.subject,
        content=request.content,
        sender=request.sender,
    )

    return ClassifyResponse(**result)


@router.post("/document/keywords", response_model=KeywordsResponse)
async def extract_keywords(
    request: KeywordsRequest,
    service: DocumentAIService = Depends(get_document_ai_service),
) -> KeywordsResponse:
    """
    提取公文關鍵字

    從公文中提取重要的關鍵字，用於搜尋和分類。
    """
    logger.info(f"提取關鍵字: {request.subject[:50]}...")

    result = await service.extract_keywords(
        subject=request.subject,
        content=request.content,
        max_keywords=request.max_keywords,
    )

    return KeywordsResponse(**result)


@router.post("/agency/match", response_model=AgencyMatchResponse)
async def match_agency(
    request: AgencyMatchRequest,
    service: DocumentAIService = Depends(get_document_ai_service),
) -> AgencyMatchResponse:
    """
    AI 機關匹配

    使用 AI 強化機關名稱匹配，支援簡稱、別稱識別。
    """
    logger.info(f"機關匹配: {request.agency_name}")

    # 轉換候選列表格式
    candidates = None
    if request.candidates:
        candidates = [
            {"id": c.id, "name": c.name, "short_name": c.short_name}
            for c in request.candidates
        ]

    result = await service.match_agency_enhanced(
        agency_name=request.agency_name,
        candidates=candidates,
    )

    # 轉換回應格式
    best_match = None
    if result.get("best_match"):
        best_match = AgencyMatchResult(**result["best_match"])

    return AgencyMatchResponse(
        best_match=best_match,
        alternatives=[],
        is_new=result.get("is_new", True),
        reasoning=result.get("reasoning"),
        source=result.get("source", "unknown"),
    )


@router.get("/health", response_model=HealthResponse)
async def check_ai_health(
    service: DocumentAIService = Depends(get_document_ai_service),
) -> HealthResponse:
    """
    AI 服務健康檢查

    檢查 Groq API 和 Ollama 的可用性。
    """
    logger.info("AI 健康檢查")

    result = await service.check_health()

    return HealthResponse(**result)


@router.get("/config", response_model=AIConfigResponse)
async def get_ai_config_endpoint() -> AIConfigResponse:
    """
    取得 AI 服務配置

    回傳目前 AI 服務的配置設定，供前端使用。
    實現 Feature Flag 模式，前端可根據此配置動態調整 UI。
    """
    config = get_ai_config()

    return AIConfigResponse(
        enabled=config.enabled,
        providers={
            "groq": {
                "name": "Groq",
                "description": "主要 AI 服務（雲端）",
                "priority": 1,
                "model": config.groq_model,
                "available": bool(config.groq_api_key),
            },
            "ollama": {
                "name": "Ollama",
                "description": "本地 AI 備援服務",
                "priority": 2,
                "model": config.ollama_model,
                "url": config.ollama_base_url,
            },
        },
        rate_limit={
            "max_requests": config.rate_limit_requests,
            "window_seconds": config.rate_limit_window,
        },
        cache={
            "enabled": config.cache_enabled,
            "ttl_summary": config.cache_ttl_summary,
            "ttl_classify": config.cache_ttl_classify,
            "ttl_keywords": config.cache_ttl_keywords,
        },
        features={
            "summary": {
                "max_tokens": config.summary_max_tokens,
                "default_max_length": 100,
            },
            "classify": {
                "max_tokens": config.classify_max_tokens,
                "confidence_threshold": 0.7,
            },
            "keywords": {
                "max_tokens": config.keywords_max_tokens,
                "default_max_keywords": 5,
            },
            "agency_match": {
                "score_threshold": 0.7,
                "max_alternatives": 3,
            },
        },
    )

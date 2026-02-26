"""
公文 AI API 端點

Version: 2.1.0
Created: 2026-02-04
Updated: 2026-02-08 - 新增串流摘要 SSE 端點

端點:
- POST /ai/document/summary - 生成公文摘要
- POST /ai/document/summary/stream - 串流生成公文摘要 (SSE) (v2.1.0 新增)
- POST /ai/document/classify - 分類建議
- POST /ai/document/keywords - 關鍵字提取
- POST /ai/document/natural-search - 自然語言公文搜尋 (v1.1.0 新增)
- POST /ai/document/parse-intent - 意圖解析（僅解析不搜尋）(v2.1.0 新增)
- POST /ai/agency/match - AI 機關匹配
- POST /ai/health - AI 服務健康檢查
"""

import json
import logging
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.core.dependencies import get_async_db, optional_auth
from app.services.ai.document_ai_service import (
    DocumentAIService,
    get_document_ai_service,
)
from app.services.ai.ai_config import get_ai_config
from app.services.audit_service import AuditService
from app.schemas.ai import (
    ParseIntentRequest,
    ParseIntentResponse,
    NaturalSearchRequest,
    NaturalSearchResponse,
    ParsedSearchIntent,
    SummaryRequest,
    SummaryResponse,
    ClassifyRequest,
    ClassifyResponse,
    KeywordsRequest,
    KeywordsExtractResponse,
    AgencyCandidate,
    AgencyMatchRequest,
    AgencyMatchResult,
    AgencyMatchResponse,
    HealthResponse,
    AIConfigResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/document/summary", response_model=SummaryResponse)
async def generate_summary(
    request: SummaryRequest,
    service: DocumentAIService = Depends(get_document_ai_service),
    current_user=Depends(optional_auth()),
) -> SummaryResponse:
    """
    生成公文摘要

    根據公文主旨和內容，使用 AI 生成簡潔的摘要。
    """
    logger.info(f"生成摘要: {request.subject[:50]}...")
    start_time = time.time()

    result = await service.generate_summary(
        subject=request.subject,
        content=request.content,
        sender=request.sender,
        max_length=request.max_length,
    )

    latency_ms = (time.time() - start_time) * 1000
    user_id = getattr(current_user, "id", None) if current_user else None
    user_name = getattr(current_user, "email", None) if current_user else None
    await AuditService.log_ai_event(
        event_type="AI_SUMMARY_GENERATED",
        feature="summary",
        input_text=request.subject,
        user_id=user_id,
        user_name=user_name,
        source_provider=result.get("source", "unknown"),
        latency_ms=latency_ms,
    )

    return SummaryResponse(**result)


@router.post("/document/summary/stream")
async def stream_summary(
    request: SummaryRequest,
    service: DocumentAIService = Depends(get_document_ai_service),
    current_user=Depends(optional_auth()),
) -> StreamingResponse:
    """
    串流生成公文摘要 (SSE)

    使用 Server-Sent Events 逐字回傳 AI 生成的摘要，
    降低使用者感知延遲。

    SSE 格式:
        data: {"token": "字", "done": false}
        data: {"token": "", "done": true}
    """
    logger.info(f"串流生成摘要: {request.subject[:50]}...")

    async def event_generator():
        start_time_ms = time.time()
        try:
            async for token in service.stream_summary(
                subject=request.subject,
                content=request.content,
                sender=request.sender,
                max_length=request.max_length,
            ):
                data = json.dumps(
                    {"token": token, "done": False}, ensure_ascii=False
                )
                yield f"data: {data}\n\n"

            # 串流完成
            yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"

            # 記錄審計日誌
            latency_ms = (time.time() - start_time_ms) * 1000
            user_id = (
                getattr(current_user, "id", None) if current_user else None
            )
            user_name = (
                getattr(current_user, "email", None) if current_user else None
            )
            await AuditService.log_ai_event(
                event_type="AI_SUMMARY_STREAMED",
                feature="summary_stream",
                input_text=request.subject,
                user_id=user_id,
                user_name=user_name,
                source_provider="ai",
                latency_ms=latency_ms,
            )
        except RuntimeError as e:
            # 速率限制
            error_data = json.dumps(
                {"token": "", "done": True, "error": str(e)},
                ensure_ascii=False,
            )
            yield f"data: {error_data}\n\n"
        except Exception as e:
            logger.error(f"串流摘要失敗: {e}")
            error_data = json.dumps(
                {"token": "", "done": True, "error": str(e)},
                ensure_ascii=False,
            )
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/document/classify", response_model=ClassifyResponse)
async def suggest_classification(
    request: ClassifyRequest,
    service: DocumentAIService = Depends(get_document_ai_service),
    current_user=Depends(optional_auth()),
) -> ClassifyResponse:
    """
    建議公文分類

    根據公文資訊，AI 建議公文類型和收發類別。
    """
    logger.info(f"分類建議: {request.subject[:50]}...")
    start_time = time.time()

    result = await service.suggest_classification(
        subject=request.subject,
        content=request.content,
        sender=request.sender,
    )

    latency_ms = (time.time() - start_time) * 1000
    user_id = getattr(current_user, "id", None) if current_user else None
    user_name = getattr(current_user, "email", None) if current_user else None
    await AuditService.log_ai_event(
        event_type="AI_CLASSIFY_SUGGESTED",
        feature="classify",
        input_text=request.subject,
        user_id=user_id,
        user_name=user_name,
        source_provider=result.get("source", "unknown"),
        latency_ms=latency_ms,
    )

    return ClassifyResponse(**result)


@router.post("/document/keywords", response_model=KeywordsExtractResponse)
async def extract_keywords(
    request: KeywordsRequest,
    service: DocumentAIService = Depends(get_document_ai_service),
    current_user=Depends(optional_auth()),
) -> KeywordsExtractResponse:
    """
    提取公文關鍵字

    從公文中提取重要的關鍵字，用於搜尋和分類。
    """
    logger.info(f"提取關鍵字: {request.subject[:50]}...")
    start_time = time.time()

    result = await service.extract_keywords(
        subject=request.subject,
        content=request.content,
        max_keywords=request.max_keywords,
    )

    latency_ms = (time.time() - start_time) * 1000
    user_id = getattr(current_user, "id", None) if current_user else None
    user_name = getattr(current_user, "email", None) if current_user else None
    await AuditService.log_ai_event(
        event_type="AI_KEYWORDS_EXTRACTED",
        feature="keywords",
        input_text=request.subject,
        user_id=user_id,
        user_name=user_name,
        source_provider=result.get("source", "unknown"),
        latency_ms=latency_ms,
    )

    return KeywordsExtractResponse(**result)


@router.post("/document/natural-search", response_model=NaturalSearchResponse)
async def natural_search_documents(
    request: NaturalSearchRequest,
    db: AsyncSession = Depends(get_async_db),
    service: DocumentAIService = Depends(get_document_ai_service),
    current_user=Depends(optional_auth()),
) -> NaturalSearchResponse:
    """
    自然語言公文搜尋

    使用 AI 解析自然語言查詢，搜尋相關公文並返回結果（含附件資訊）。
    支援權限過濾：非管理員僅能搜尋自己可存取的公文。

    範例查詢:
    - "找桃園市政府上個月的公文"
    - "有截止日的待處理公文"
    - "中壢區相關的會勘通知"
    """
    logger.info(f"自然語言搜尋: {request.query[:50]}...")

    start_time = time.time()
    try:
        result = await service.natural_search(
            db=db, request=request, current_user=current_user
        )

        latency_ms = (time.time() - start_time) * 1000
        user_id = getattr(current_user, "id", None) if current_user else None
        user_name = getattr(current_user, "email", None) if current_user else None
        await AuditService.log_ai_event(
            event_type="AI_SEARCH_EXECUTED",
            feature="search",
            input_text=request.query,
            user_id=user_id,
            user_name=user_name,
            source_provider=result.source,
            latency_ms=latency_ms,
            details={"results_count": result.total},
        )

        return result
    except RuntimeError as e:
        # 速率限制錯誤 → 429
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        logger.error(f"自然語言搜尋失敗: {type(e).__name__}: {e}", exc_info=True)
        latency_ms = (time.time() - start_time) * 1000
        user_id = getattr(current_user, "id", None) if current_user else None
        await AuditService.log_ai_event(
            event_type="AI_SEARCH_EXECUTED",
            feature="search",
            input_text=request.query,
            user_id=user_id,
            source_provider="error",
            latency_ms=latency_ms,
            success=False,
            error=f"{type(e).__name__}: {e}",
        )
        return NaturalSearchResponse(
            success=False,
            query=request.query,
            parsed_intent=ParsedSearchIntent(keywords=[request.query], confidence=0.0),
            results=[],
            total=0,
            source="error",
            error=f"{type(e).__name__}: {e}",
        )


@router.post("/document/parse-intent", response_model=ParseIntentResponse)
async def parse_search_intent(
    request: ParseIntentRequest,
    service: DocumentAIService = Depends(get_document_ai_service),
    db: AsyncSession = Depends(get_async_db),
) -> ParseIntentResponse:
    """
    解析搜尋意圖（僅解析，不執行搜尋）

    使用三層架構（規則→向量→LLM）將自然語言查詢解析為結構化搜尋條件，
    供前端填充傳統篩選器使用。

    範例查詢:
    - "找桃園市政府上個月的公文" → sender=桃園市政府, date_from/date_to
    - "待處理的會勘通知" → status=待處理, doc_type=會勘通知單
    """
    logger.info(f"意圖解析: {request.query[:50]}...")

    try:
        parsed_intent, intent_source = await service.parse_search_intent(request.query, db=db)
        return ParseIntentResponse(
            success=True,
            query=request.query,
            parsed_intent=parsed_intent,
            source=intent_source,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        logger.error(f"意圖解析失敗: {type(e).__name__}: {e}", exc_info=True)
        return ParseIntentResponse(
            success=False,
            query=request.query,
            parsed_intent=ParsedSearchIntent(keywords=[request.query], confidence=0.0),
            source="error",
            error="意圖解析暫時無法使用，請稍後再試",
        )


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
    start_time = time.time()

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

    latency_ms = (time.time() - start_time) * 1000
    await AuditService.log_ai_event(
        event_type="AI_AGENCY_MATCHED",
        feature="agency_match",
        input_text=request.agency_name,
        source_provider=result.get("source", "unknown"),
        latency_ms=latency_ms,
        details={"is_new": result.get("is_new", True)},
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


@router.post("/health", response_model=HealthResponse)
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


@router.post("/config", response_model=AIConfigResponse)
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
                "confidence_threshold": config.agency_match_threshold,
            },
            "keywords": {
                "max_tokens": config.keywords_max_tokens,
                "default_max_keywords": 5,
            },
            "agency_match": {
                "score_threshold": config.agency_match_threshold,
                "max_alternatives": 3,
            },
        },
    )

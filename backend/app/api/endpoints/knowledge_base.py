"""知識庫瀏覽器 API

提供知識地圖、ADR、架構圖的瀏覽功能，以及向量搜尋。

@version 2.0.0
@date 2026-03-19
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.database import get_async_db
from app.schemas.knowledge_base import (
    AdrListResponse,
    DiagramListResponse,
    FileContentResponse,
    FileRequest,
    KBEmbedResponse,
    KBSearchRequest,
    KBSearchResponse,
    KBSearchResult,
    KBStatsResponse,
    TreeResponse,
)
from app.services.system.knowledge_base_service import KnowledgeBaseService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/tree", response_model=TreeResponse)
async def get_knowledge_tree(
    _admin: dict = Depends(require_admin()),
) -> TreeResponse:
    """取得知識地圖目錄結構。"""
    return TreeResponse(success=True, sections=KnowledgeBaseService().build_tree())


@router.post("/file", response_model=FileContentResponse)
async def get_file_content(
    req: FileRequest,
    _admin: dict = Depends(require_admin()),
) -> FileContentResponse:
    """讀取知識庫檔案內容。"""
    content, filename = KnowledgeBaseService().read_file(req.path)
    return FileContentResponse(success=True, content=content, filename=filename)


@router.post("/adr/list", response_model=AdrListResponse)
async def list_adrs(
    _admin: dict = Depends(require_admin()),
) -> AdrListResponse:
    """列出所有 ADR 文件。"""
    return AdrListResponse(success=True, items=KnowledgeBaseService().list_adrs())


@router.post("/diagrams/list", response_model=DiagramListResponse)
async def list_diagrams(
    _admin: dict = Depends(require_admin()),
) -> DiagramListResponse:
    """列出所有架構圖文件。"""
    return DiagramListResponse(success=True, items=KnowledgeBaseService().list_diagrams())


@router.post("/search", response_model=KBSearchResponse)
async def search_knowledge_base(
    req: KBSearchRequest,
    _admin: dict = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
) -> KBSearchResponse:
    """混合搜尋知識庫內容：向量搜尋優先，文字搜尋兜底。"""
    from app.services.kb_embedding_service import KBEmbeddingService

    # 向量搜尋優先
    vector_results = await KBEmbeddingService(db).search(req.query, limit=req.limit)
    if vector_results:
        results = [
            KBSearchResult(
                file_path=r["file_path"], filename=r["filename"],
                excerpt=r["content"][:500], line_number=0, relevance_score=r["score"],
            )
            for r in vector_results
        ]
        return KBSearchResponse(success=True, results=results, total=len(results), search_mode="vector")

    # 兜底：檔案系統文字搜尋（委派 service）
    results, total = KnowledgeBaseService().text_search(req.query, req.limit)
    return KBSearchResponse(success=True, results=results, total=total, search_mode="text")


@router.post("/embed", response_model=KBEmbedResponse)
async def trigger_kb_embedding(
    _admin: dict = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
) -> KBEmbedResponse:
    """觸發知識庫 Embedding 管線（掃描 docs/ → 分段 → 向量化）。"""
    from app.services.kb_embedding_service import KBEmbeddingService

    kb_service = KBEmbeddingService(db)
    try:
        stats = await kb_service.scan_and_embed()
    except Exception:
        logger.exception("KB embedding 管線失敗")
        raise HTTPException(status_code=500, detail="Embedding 管線執行失敗")

    return KBEmbedResponse(success=True, **stats)


@router.post("/code-wiki/module")
async def get_module_wiki(
    request: Request,
    _admin: dict = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """生成模組 Wiki (Gemma 4)"""
    body = await request.json()
    module_name = body.get("module_name", "")
    if not module_name:
        return JSONResponse({"success": False, "error": "缺少 module_name"})

    from app.services.ai.misc.code_wiki_generator import CodeWikiGenerator

    svc = CodeWikiGenerator(db)
    result = await svc.generate_module_wiki(module_name)
    return JSONResponse({"success": True, "data": result})


@router.post("/code-wiki/overview")
async def get_code_wiki_overview(
    request: Request,
    _admin: dict = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """程式碼 Wiki 總覽"""
    body = await request.json()
    limit = body.get("limit", 50)
    if not isinstance(limit, int) or limit < 1:
        limit = 50
    limit = min(limit, 200)

    from app.services.ai.misc.code_wiki_generator import CodeWikiGenerator

    svc = CodeWikiGenerator(db)
    result = await svc.generate_overview(limit=limit)
    return JSONResponse({"success": True, "data": result})


@router.post("/stats", response_model=KBStatsResponse)
async def get_kb_stats(
    _admin: dict = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
) -> KBStatsResponse:
    """取得知識庫 Embedding 統計資訊。"""
    from app.services.kb_embedding_service import KBEmbeddingService

    kb_service = KBEmbeddingService(db)
    stats = await kb_service.get_stats()
    return KBStatsResponse(success=True, **stats)


@router.post("/summarize-card")
async def summarize_knowledge_card(
    request: Request,
    _admin: dict = Depends(require_admin()),
):
    """Gemma 4 生成知識卡片摘要"""
    body = await request.json()
    content = body.get("content", "")
    title = body.get("title", "")

    if not content and not title:
        return JSONResponse({"success": False, "error": "缺少 content 或 title"})

    from app.core.ai_connector import get_ai_connector

    ai = get_ai_connector()
    prompt = (
        f"為以下知識卡片生成 2-3 句摘要：\n\n"
        f"標題: {title}\n內容:\n{content[:1000]}\n\n"
        "摘要:"
    )
    try:
        summary = await ai.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
            task_type="summary",
        )
        return JSONResponse({"success": True, "summary": summary})
    except Exception as e:
        logger.error("summarize_knowledge_card failed: %s", e, exc_info=True)
        return JSONResponse({"success": False, "error": "摘要生成失敗，請稍後再試"})

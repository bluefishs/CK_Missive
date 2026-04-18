"""
LLM Wiki API 端點

提供 wiki 的 CRUD、搜尋、lint、index 重建等操作。
"""
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import require_admin, require_auth, get_async_db
from app.services.wiki_service import get_wiki_service
from sqlalchemy.ext.asyncio import AsyncSession

# 整組需登入（Wiki 為內部知識庫）；寫端點額外 require_admin 於單端點（見下方）
router = APIRouter(prefix="/wiki", tags=["wiki"], dependencies=[Depends(require_auth())])


# ── Request / Response schemas ──

class IngestEntityRequest(BaseModel):
    name: str
    entity_type: str
    description: str
    sources: List[str] = []
    tags: List[str] = []
    related_entities: List[str] = []
    confidence: str = "medium"


class IngestSourceRequest(BaseModel):
    title: str
    source_type: str
    summary: str
    key_points: List[str] = []
    entities_mentioned: List[str] = []
    source_id: Optional[str] = None
    tags: List[str] = []


class SaveSynthesisRequest(BaseModel):
    title: str
    content_md: str
    sources: List[str] = []
    tags: List[str] = []


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


# ── Endpoints ──

@router.post("/ingest/entity")
async def ingest_entity(req: IngestEntityRequest, _admin=Depends(require_admin())):
    """攝入實體到 wiki（Admin 限定）"""
    svc = get_wiki_service()
    result = await svc.ingest_entity(
        name=req.name,
        entity_type=req.entity_type,
        description=req.description,
        sources=req.sources,
        tags=req.tags,
        related_entities=req.related_entities,
        confidence=req.confidence,
    )
    await svc.rebuild_index()
    return {"success": True, "data": result}


@router.post("/ingest/source")
async def ingest_source(req: IngestSourceRequest, _admin=Depends(require_admin())):
    """攝入來源摘要到 wiki（Admin 限定）"""
    svc = get_wiki_service()
    result = await svc.ingest_source(
        title=req.title,
        source_type=req.source_type,
        summary=req.summary,
        key_points=req.key_points,
        entities_mentioned=req.entities_mentioned,
        source_id=req.source_id,
        tags=req.tags,
    )
    await svc.rebuild_index()
    return {"success": True, "data": result}


@router.post("/synthesis")
async def save_synthesis(req: SaveSynthesisRequest, _admin=Depends(require_admin())):
    """儲存綜合分析到 wiki（Admin 限定）"""
    svc = get_wiki_service()
    result = await svc.save_synthesis(
        title=req.title,
        content_md=req.content_md,
        sources=req.sources,
        tags=req.tags,
    )
    await svc.rebuild_index()
    return {"success": True, "data": result}


@router.post("/search")
async def search_wiki(req: SearchRequest):
    """搜尋 wiki 頁面"""
    svc = get_wiki_service()
    results = await svc.search_wiki(req.query, limit=req.limit)
    return {"success": True, "data": results, "total": len(results)}


@router.post("/page")
async def read_page(page_path: str):
    """讀取指定 wiki 頁面"""
    svc = get_wiki_service()
    content = await svc.read_page(page_path)
    if content is None:
        return {"success": False, "error": "Page not found"}
    return {"success": True, "data": {"path": page_path, "content": content}}


@router.post("/lint")
async def lint_wiki(_admin=Depends(require_admin())):
    """Wiki 健康檢查（Admin 限定）"""
    svc = get_wiki_service()
    result = await svc.lint()
    return {"success": True, "data": result}


@router.post("/rebuild-index")
async def rebuild_index(_admin=Depends(require_admin())):
    """重建 wiki 索引（Admin 限定）"""
    svc = get_wiki_service()
    counts = await svc.rebuild_index()
    return {"success": True, "data": counts}


@router.post("/stats")
async def wiki_stats():
    """Wiki 統計"""
    svc = get_wiki_service()
    return {"success": True, "data": svc.get_stats()}


@router.post("/graph")
async def wiki_graph():
    """Wiki 頁面圖譜 — nodes + edges，供 force-graph 視覺化"""
    svc = get_wiki_service()
    result = await svc.get_graph()
    return {"success": True, "data": result}


@router.post("/coverage")
async def wiki_coverage(
    db: AsyncSession = Depends(get_async_db),
):
    """Wiki ↔ KG 交叉比對 — 列出覆蓋差異 (exact/fuzzy/wiki-only/kg-only)"""
    from app.services.wiki_coverage_service import WikiCoverageService
    svc = WikiCoverageService(db)
    result = await svc.compare()
    return {"success": True, "data": result}


@router.post("/compile")
async def compile_wiki(
    min_doc_count: int = 5,
    mode: str = "incremental",
    _admin=Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """從公文/案件 DB 編譯 wiki 內容 (Admin 限定)

    Args:
        min_doc_count: 最低公文數門檻
        mode: "incremental" (預設，只編譯有新公文的) 或 "full" (全量重編)
    """
    from app.services.wiki_compiler import WikiCompiler
    compiler = WikiCompiler(db)
    if mode == "full":
        result = await compiler.compile_all(min_doc_count=min_doc_count)
    else:
        result = await compiler.compile_incremental(min_doc_count=min_doc_count)
    return {"success": True, "data": result}

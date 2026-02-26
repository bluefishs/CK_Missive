"""
知識圖譜查詢 API 端點

提供正規化實體的搜尋、鄰居、詳情、時間軸、排名、
入圖管線、統計等功能。

Version: 1.0.0
Created: 2026-02-24
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth, require_admin, get_async_db
from app.extended.models import User
from app.services.ai.graph_query_service import GraphQueryService
from app.services.ai.graph_ingestion_pipeline import GraphIngestionPipeline
from app.services.ai.canonical_entity_service import CanonicalEntityService
from app.schemas.knowledge_graph import (
    KGEntitySearchRequest,
    KGEntitySearchResponse,
    KGNeighborsRequest,
    KGNeighborsResponse,
    KGShortestPathRequest,
    KGShortestPathResponse,
    KGEntityDetailRequest,
    KGEntityDetailResponse,
    KGTimelineRequest,
    KGTimelineResponse,
    KGTopEntitiesRequest,
    KGTopEntitiesResponse,
    KGGraphStatsResponse,
    KGIngestRequest,
    KGIngestResponse,
    KGMergeEntitiesRequest,
    KGMergeEntitiesResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# 端點
# ============================================================================

@router.post("/graph/entity/search", response_model=KGEntitySearchResponse)
async def search_entities(
    request: KGEntitySearchRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """搜尋正規化實體"""
    svc = GraphQueryService(db)
    results = await svc.search_entities(
        query=request.query,
        entity_type=request.entity_type,
        limit=request.limit,
    )
    return {"success": True, "results": results, "total": len(results)}


@router.post("/graph/entity/neighbors", response_model=KGNeighborsResponse)
async def get_entity_neighbors(
    request: KGNeighborsRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """取得實體的 K 跳鄰居"""
    svc = GraphQueryService(db)
    result = await svc.get_neighbors(
        entity_id=request.entity_id,
        max_hops=request.max_hops,
        limit=request.limit,
    )
    return {"success": True, **result}


@router.post("/graph/entity/shortest-path", response_model=KGShortestPathResponse)
async def find_shortest_path(
    request: KGShortestPathRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """查詢兩實體間的最短路徑"""
    svc = GraphQueryService(db)
    result = await svc.find_shortest_path(
        source_id=request.source_id,
        target_id=request.target_id,
        max_hops=request.max_hops,
    )
    if not result:
        return {"success": True, "found": False, "depth": 0, "path": [], "relations": []}
    return {"success": True, **result}


@router.post("/graph/entity/detail", response_model=KGEntityDetailResponse)
async def get_entity_detail(
    request: KGEntityDetailRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """取得實體詳情（含別名、公文、關係）"""
    svc = GraphQueryService(db)
    detail = await svc.get_entity_detail(request.entity_id)
    if not detail:
        raise HTTPException(status_code=404, detail="實體不存在")
    return {"success": True, **detail}


@router.post("/graph/entity/timeline", response_model=KGTimelineResponse)
async def get_entity_timeline(
    request: KGTimelineRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """取得實體的關係時間軸"""
    svc = GraphQueryService(db)
    timeline = await svc.get_entity_timeline(request.entity_id)
    return {"success": True, "entity_id": request.entity_id, "timeline": timeline}


@router.post("/graph/entity/top", response_model=KGTopEntitiesResponse)
async def get_top_entities(
    request: KGTopEntitiesRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """高頻實體排名"""
    svc = GraphQueryService(db)
    results = await svc.get_top_entities(
        entity_type=request.entity_type,
        sort_by=request.sort_by,
        limit=request.limit,
    )
    return {"success": True, "entities": results}


@router.post("/graph/stats", response_model=KGGraphStatsResponse)
async def get_graph_stats(
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """圖譜統計"""
    svc = GraphQueryService(db)
    stats = await svc.get_graph_stats()
    return {"success": True, **stats}


@router.post("/graph/ingest", response_model=KGIngestResponse)
async def ingest_documents(
    request: KGIngestRequest,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    觸發公文入圖管線。
    - document_id 指定時：入圖單篇公文
    - document_id 為空時：批次入圖（背景任務）
    """
    pipeline = GraphIngestionPipeline(db)

    if request.document_id:
        result = await pipeline.ingest_document(
            document_id=request.document_id,
            force=request.force,
        )
        await db.commit()
        return {"success": True, **result}

    # 批次入圖
    result = await pipeline.batch_ingest(limit=request.limit, force=request.force)
    return {"success": True, **result}


@router.post("/graph/admin/merge-entities", response_model=KGMergeEntitiesResponse)
async def merge_entities(
    request: KGMergeEntitiesRequest,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """手動合併兩個正規化實體"""
    svc = CanonicalEntityService(db)
    try:
        result = await svc.merge_entities(
            keep_id=request.keep_id,
            merge_id=request.merge_id,
        )
        await db.commit()
        return {
            "success": True,
            "message": f"已合併至: {result.canonical_name}",
            "entity_id": result.id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

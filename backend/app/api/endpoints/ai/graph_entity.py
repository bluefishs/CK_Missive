"""
知識圖譜實體查詢 API 端點

提供正規化實體的搜尋、鄰居、詳情、時間軸、排名、
統計、DB Schema 等功能。

Refactored from: graph_query.py
Version: 1.0.0
Created: 2026-03-30
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth, get_async_db
from app.extended.models import User
from app.services.ai.graph_query_service import GraphQueryService
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
    KGTimelineAggregateRequest,
    KGTimelineAggregateResponse,
    KGTopEntitiesRequest,
    KGTopEntitiesResponse,
    KGEntityGraphRequest,
    KGEntityGraphResponse,
    KGGraphStatsResponse,
    KGDbSchemaResponse,
    KGDbGraphResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# KG 實體查詢端點
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


@router.post("/graph/timeline/aggregate", response_model=KGTimelineAggregateResponse)
async def get_timeline_aggregate(
    request: KGTimelineAggregateRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """跨實體時序聚合：按月/季/年統計關係數量趨勢"""
    svc = GraphQueryService(db)
    result = await svc.get_timeline_aggregate(
        relation_type=request.relation_type,
        entity_type=request.entity_type,
        granularity=request.granularity,
    )
    return {"success": True, **result}


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


@router.post("/graph/entity/graph", response_model=KGEntityGraphResponse)
async def get_entity_graph(
    request: KGEntityGraphRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """以實體為中心的公文知識圖譜（排除 code entities）"""
    svc = GraphQueryService(db)
    result = await svc.get_entity_graph(
        entity_types=request.entity_types,
        min_mentions=request.min_mentions,
        limit=request.limit,
        year=request.year,
        collapse_agency=request.collapse_agency,
    )
    return {"success": True, **result}


@router.post("/graph/stats", response_model=KGGraphStatsResponse)
async def get_graph_stats(
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """圖譜統計"""
    svc = GraphQueryService(db)
    stats = await svc.get_graph_stats()
    return {"success": True, **stats}


@router.post("/graph/db-schema", response_model=KGDbSchemaResponse)
async def get_db_schema(
    current_user: User = Depends(require_auth()),
):
    """
    取得完整資料庫 Schema 反射結果。

    回傳所有資料表的欄位、型別、主鍵、外鍵、索引、唯一約束。
    結果會快取 10 分鐘。
    """
    from app.services.ai.schema_reflector import SchemaReflectorService

    try:
        schema = await SchemaReflectorService.get_full_schema_async()
        return KGDbSchemaResponse(success=True, tables=schema.get("tables", []))
    except Exception as e:
        logger.error("資料庫 Schema 反射失敗: %s", e, exc_info=True)
        return KGDbSchemaResponse(success=False, error="Schema 反射失敗，請稍後再試")


@router.post("/graph/db-graph", response_model=KGDbGraphResponse)
async def get_db_graph(
    current_user: User = Depends(require_auth()),
):
    """
    取得資料庫 ER 圖譜資料（nodes + edges 格式）。

    nodes = 資料表, edges = 外鍵關聯。
    相容前端 ExternalGraphData 格式。
    """
    from app.services.ai.schema_reflector import SchemaReflectorService

    try:
        graph = await SchemaReflectorService.get_graph_data_async()
        return KGDbGraphResponse(
            success=True,
            nodes=graph.get("nodes", []),
            edges=graph.get("edges", []),
        )
    except Exception as e:
        logger.error("資料庫 ER 圖譜產生失敗: %s", e, exc_info=True)
        return KGDbGraphResponse(success=False, error="ER 圖譜產生失敗，請稍後再試")

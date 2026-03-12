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
    KGEntityGraphRequest,
    KGEntityGraphResponse,
    KGGraphStatsResponse,
    KGIngestRequest,
    KGIngestResponse,
    KGMergeEntitiesRequest,
    KGMergeEntitiesResponse,
    KGCodeWikiRequest,
    KGCodeWikiResponse,
    KGCodeGraphIngestRequest,
    KGCodeGraphIngestResponse,
    KGCycleDetectionResponse,
    KGArchitectureAnalysisResponse,
    KGJsonImportRequest,
    KGJsonImportResponse,
    KGModuleOverviewResponse,
    KGDbSchemaResponse,
    KGDbGraphResponse,
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


@router.post("/graph/code-wiki", response_model=KGCodeWikiResponse)
async def get_code_wiki_graph(
    request: KGCodeWikiRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """取得 Code Wiki 代碼圖譜（nodes + edges）"""
    svc = GraphQueryService(db)
    result = await svc.get_code_wiki_graph(
        entity_types=request.entity_types,
        module_prefix=request.module_prefix,
        limit=request.limit,
    )
    return {"success": True, **result}


@router.post("/graph/module-overview", response_model=KGModuleOverviewResponse)
async def get_module_overview(
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    取得模組架構概覽。

    按架構層（core/api/services/repository 等）分組模組統計，
    以及所有資料表的 ERD 摘要資訊。
    """
    svc = GraphQueryService(db)
    try:
        result = await svc.get_module_overview()
        return {"success": True, **result}
    except Exception as e:
        logger.error("模組架構概覽查詢失敗: %s", e, exc_info=True)
        return KGModuleOverviewResponse(success=False)


@router.post("/graph/admin/code-ingest", response_model=KGCodeGraphIngestResponse)
async def ingest_code_graph(
    request: KGCodeGraphIngestRequest,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    觸發 Code Graph 代碼圖譜入圖。

    掃描後端 Python 原始碼（AST）及 DB Schema，
    將模組/類別/函數/資料表及其關聯寫入知識圖譜。

    🔒 權限要求: Admin
    """
    import os
    from pathlib import Path
    from app.services.ai.code_graph_service import CodeGraphIngestionService

    # graph_query.py 位於 backend/app/api/endpoints/ai/ → parents[4] = backend/
    project_root = Path(__file__).resolve().parents[5]
    backend_app_dir = project_root / "backend" / "app"
    frontend_src_dir = project_root / "frontend" / "src" if request.include_frontend else None

    # 建構同步 DB URL（schema reflection 用）
    db_url = None
    if request.include_schema:
        async_url = os.environ.get("DATABASE_URL", "")
        if async_url:
            db_url = async_url.replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql")
        if not db_url:
            db_host = os.environ.get("POSTGRES_HOST", "localhost")
            db_port = os.environ.get("POSTGRES_HOST_PORT", os.environ.get("POSTGRES_PORT", "5434"))
            db_user = os.environ.get("POSTGRES_USER", "ck_user")
            db_pass = os.environ.get("POSTGRES_PASSWORD", "")
            db_name = os.environ.get("POSTGRES_DB", "ck_documents")
            db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    svc = CodeGraphIngestionService(db)
    try:
        result = await svc.ingest(
            backend_app_dir=backend_app_dir,
            db_url=db_url,
            clean=request.clean,
            incremental=request.incremental,
            frontend_src_dir=frontend_src_dir,
        )
        await db.commit()
        skipped = result.get("skipped", 0)
        ts_modules = result.get("ts_modules", 0)
        ts_components = result.get("ts_components", 0)
        ts_hooks = result.get("ts_hooks", 0)
        msg_parts = [
            f"代碼圖譜入圖完成: {result.get('modules', 0)} 模組, "
            f"{result.get('classes', 0)} 類別, "
            f"{result.get('functions', 0)} 函數, "
            f"{result.get('tables', 0)} 表",
        ]
        if ts_modules > 0:
            msg_parts.append(f", {ts_modules} TS模組, {ts_components} 元件, {ts_hooks} Hook")
        if skipped > 0:
            msg_parts.append(f"（跳過 {skipped} 個未變更檔案）")
        return KGCodeGraphIngestResponse(
            success=True,
            message="".join(msg_parts),
            modules=result.get("modules", 0),
            classes=result.get("classes", 0),
            functions=result.get("functions", 0),
            tables=result.get("tables", 0),
            ts_modules=ts_modules,
            ts_components=ts_components,
            ts_hooks=ts_hooks,
            relations=result.get("relations", 0),
            errors=result.get("errors", 0),
            skipped=skipped,
            elapsed_seconds=result.get("elapsed_s", 0.0),
        )
    except Exception as e:
        logger.error("代碼圖譜入圖失敗: %s", e, exc_info=True)
        return KGCodeGraphIngestResponse(
            success=False,
            message="入圖失敗，請查看系統日誌了解詳情",
        )


@router.post("/graph/admin/cycle-detection", response_model=KGCycleDetectionResponse)
async def detect_import_cycles(
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    偵測模組間的循環匯入依賴。

    基於已入圖的 imports 關聯，使用 DFS 找出所有循環路徑。

    🔒 權限要求: Admin
    """
    from app.services.ai.code_graph_service import CodeGraphIngestionService

    svc = CodeGraphIngestionService(db)
    try:
        result = await svc.detect_import_cycles()
        return KGCycleDetectionResponse(success=True, **result)
    except Exception as e:
        logger.error("循環依賴偵測失敗: %s", e, exc_info=True)
        return KGCycleDetectionResponse(
            success=False,
            total_modules=0,
            total_import_edges=0,
            cycles_found=0,
        )


@router.post("/graph/admin/architecture-analysis", response_model=KGArchitectureAnalysisResponse)
async def analyze_architecture(
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    分析代碼架構，產出以下洞察：

    - 高耦合模組（出向依賴最多）
    - 樞紐模組（被匯入最多）
    - 大型模組（行數最多）
    - 孤立模組（無入向匯入）
    - 巨型類別（方法數最多）
    """
    from app.services.ai.code_graph_service import CodeGraphIngestionService

    svc = CodeGraphIngestionService(db)
    try:
        result = await svc.analyze_architecture()
        return KGArchitectureAnalysisResponse(success=True, **result)
    except Exception as e:
        logger.error("架構分析失敗: %s", e, exc_info=True)
        return KGArchitectureAnalysisResponse(success=False)


@router.post("/graph/admin/json-import", response_model=KGJsonImportResponse)
async def import_json_graph(
    request: KGJsonImportRequest,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    匯入本地 GitNexus 產生的 knowledge_graph.json。

    支援 Local-First 架構：開發者本地執行 generate-code-graph.py 產生
    JSON 檔案，透過此端點匯入知識圖譜資料庫。

    🔒 權限要求: Admin
    """
    from pathlib import Path
    from app.services.ai.code_graph_service import CodeGraphIngestionService

    project_root = Path(__file__).resolve().parents[5]
    json_path = (project_root / request.file_path).resolve()

    # 路徑穿越防護：確保 resolved 路徑在專案根目錄內
    if not json_path.is_relative_to(project_root):
        return KGJsonImportResponse(
            success=False,
            message="無效的檔案路徑",
            nodes_imported=0,
            edges_imported=0,
            elapsed_seconds=0.0,
        )

    svc = CodeGraphIngestionService(db)
    try:
        result = await svc.ingest_from_json(
            file_path=json_path,
            clean=request.clean,
        )
        return KGJsonImportResponse(
            success=True,
            message=result.get("message", ""),
            nodes_imported=result.get("nodes_imported", 0),
            edges_imported=result.get("edges_imported", 0),
            elapsed_seconds=result.get("elapsed_seconds", 0.0),
        )
    except Exception as e:
        logger.error("JSON 圖譜匯入失敗: %s", e, exc_info=True)
        return KGJsonImportResponse(
            success=False,
            message="匯入失敗，請查看系統日誌了解詳情",
        )


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
        logger.error("實體合併失敗: %s", e)
        raise HTTPException(status_code=400, detail="操作失敗，請稍後再試")


@router.post("/graph/module-mappings")
async def get_module_mappings(
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    取得動態模組映射 — 基於 site_navigation_items 已啟用的導覽項目

    前端代碼圖譜的模組視圖會根據此 API 判斷哪些模組應顯示。
    回傳 { enabled_keys: [...], disabled_keys: [...] }
    """
    from app.repositories.navigation_repository import NavigationRepository

    repo = NavigationRepository(db)
    try:
        root_items = await repo.get_root_items()

        enabled_keys: list[str] = []
        disabled_keys: list[str] = []

        async def collect_keys(items: list) -> None:
            for item in items:
                key = item.key
                if item.is_visible and item.is_enabled:
                    enabled_keys.append(key)
                else:
                    disabled_keys.append(key)
                children = await repo.get_children(item.id)
                if children:
                    await collect_keys(children)

        await collect_keys(root_items)

        return {
            "success": True,
            "enabled_keys": enabled_keys,
            "disabled_keys": disabled_keys,
            "total": len(enabled_keys) + len(disabled_keys),
        }
    except Exception as e:
        logger.error("模組映射查詢失敗: %s", e)
        return {"success": False, "enabled_keys": [], "disabled_keys": []}

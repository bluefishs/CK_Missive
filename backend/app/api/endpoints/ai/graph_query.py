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
    UnifiedGraphSearchRequest,
    UnifiedGraphSearchResponse,
    UnifiedGraphResult,
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


@router.post("/graph/skill-evolution")
async def get_skill_evolution_tree(
    current_user: User = Depends(require_auth()),
):
    """
    取得技能演化樹資料

    返回系統所有技能節點、演化路徑、融合關係，
    供前端渲染互動式技能演化視覺化。
    """
    from app.services.skill_evolution_service import build_skill_tree
    return build_skill_tree()


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


@router.post("/graph/unified-search", response_model=UnifiedGraphSearchResponse)
async def unified_graph_search(
    request: UnifiedGraphSearchRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """跨圖譜統一搜尋 — 同時搜尋知識圖譜 + 代碼圖譜 + 資料庫圖譜"""
    import asyncio

    query = request.query.strip()
    query_lower = query.lower()
    results: list[UnifiedGraphResult] = []
    sources_queried: list[str] = []

    async def search_kg() -> list[UnifiedGraphResult]:
        svc = GraphQueryService(db)
        entities = await svc.search_entities(query=query, limit=request.limit_per_graph)
        return [
            UnifiedGraphResult(
                source="kg",
                entity_type=e.get("entity_type", "unknown"),
                name=e.get("canonical_name", ""),
                description=e.get("description", "") or "",
                relevance=float(e.get("mention_count", 1)),
            )
            for e in entities
        ]

    async def search_code() -> list[UnifiedGraphResult]:
        from sqlalchemy import select, func
        from app.extended.models.knowledge_graph import CanonicalEntity
        from app.core.constants import CODE_ENTITY_TYPES
        import re

        escaped = re.sub(r'([%_\\])', r'\\\1', query)
        stmt = (
            select(CanonicalEntity.canonical_name, CanonicalEntity.entity_type, CanonicalEntity.description)
            .where(CanonicalEntity.entity_type.in_(CODE_ENTITY_TYPES))
            .where(CanonicalEntity.canonical_name.ilike(f"%{escaped}%"))
            .order_by(CanonicalEntity.mention_count.desc())
            .limit(request.limit_per_graph)
        )
        rows = (await db.execute(stmt)).all()
        return [
            UnifiedGraphResult(
                source="code",
                entity_type=row[1],
                name=row[0],
                description=(row[2] if isinstance(row[2], str) else "") or "",
            )
            for row in rows
        ]

    async def search_db() -> list[UnifiedGraphResult]:
        from app.services.ai.schema_reflector import SchemaReflectorService

        schema = await SchemaReflectorService.get_full_schema_async()
        hits: list[UnifiedGraphResult] = []
        for table in schema.get("tables", []):
            table_name = table.get("name", "")
            if query_lower in table_name.lower():
                cols = [c["name"] for c in table.get("columns", [])[:5]]
                hits.append(UnifiedGraphResult(
                    source="db", entity_type="db_table", name=table_name,
                    description=f"columns: {', '.join(cols)}",
                ))
                if len(hits) >= request.limit_per_graph:
                    break
            else:
                for col in table.get("columns", []):
                    if query_lower in col["name"].lower():
                        hits.append(UnifiedGraphResult(
                            source="db", entity_type="db_column",
                            name=f"{table_name}.{col['name']}",
                            description=f"type: {col.get('type', 'unknown')}",
                        ))
                        if len(hits) >= request.limit_per_graph:
                            break
                if len(hits) >= request.limit_per_graph:
                    break
        return hits

    tasks = []
    if request.include_kg:
        tasks.append(("kg", search_kg()))
        sources_queried.append("kg")
    if request.include_code:
        tasks.append(("code", search_code()))
        sources_queried.append("code")
    if request.include_db:
        tasks.append(("db", search_db()))
        sources_queried.append("db")

    gathered = await asyncio.gather(
        *[t[1] for t in tasks], return_exceptions=True,
    )

    for (source, _), result in zip(tasks, gathered):
        if isinstance(result, Exception):
            logger.warning("unified-search %s failed: %s", source, result)
        else:
            results.extend(result)

    return UnifiedGraphSearchResponse(
        success=True,
        results=results,
        total=len(results),
        sources_queried=sources_queried,
    )


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


# ============================================================================
# Skills Capability Map（靜態圖譜）
# ============================================================================

@router.post("/graph/skills-map")
async def get_skills_capability_map(
    current_user: User = Depends(require_auth()),
):
    """
    回傳乾坤智能體能力圖譜 — 3 層階層式架構。

    Level 1: 能力分層 (5 層)
    Level 2: 核心能力 (10 個, 含成熟度 ★1-5)
    Level 3: 具體技能/工具 + 演進方向

    節點與邊為靜態定義，不需資料庫查詢。
    mention_count 編碼成熟度: ★N × 20
    """

    # -- 節點色彩定義 --
    C_LAYER      = "#434343"   # 深灰 — 能力分層
    C_CAPABILITY = "#1890ff"   # 藍   — 核心能力
    C_SKILL      = "#52c41a"   # 綠   — 具體技能
    C_FUTURE     = "#ff85c0"   # 粉   — 演進方向

    nodes = [
        # ================================================================
        # Level 1: 能力分層 (5 層)
        # ================================================================
        {"id": "layer:input",   "label": "感知層 Input",   "type": "layer", "color": C_LAYER, "mention_count": 30},
        {"id": "layer:think",   "label": "認知層 Think",   "type": "layer", "color": C_LAYER, "mention_count": 30},
        {"id": "layer:know",    "label": "知識層 Know",    "type": "layer", "color": C_LAYER, "mention_count": 30},
        {"id": "layer:execute", "label": "行動層 Execute", "type": "layer", "color": C_LAYER, "mention_count": 30},
        {"id": "layer:learn",   "label": "學習層 Learn",   "type": "layer", "color": C_LAYER, "mention_count": 30},

        # ================================================================
        # Level 2: 核心能力 (10 個, ★ = maturity)
        # ================================================================
        # ★5 成熟 (mention_count=100)
        {"id": "cap:crud",       "label": "公文CRUD ★★★★★",    "type": "capability", "color": C_CAPABILITY, "mention_count": 100},
        {"id": "cap:agent",      "label": "Agent問答 ★★★★★",   "type": "capability", "color": C_CAPABILITY, "mention_count": 100},
        {"id": "cap:rag",        "label": "RAG檢索 ★★★★★",    "type": "capability", "color": C_CAPABILITY, "mention_count": 100},
        # ★4 穩定 (mention_count=80)
        {"id": "cap:kg",         "label": "知識圖譜 ★★★★",     "type": "capability", "color": C_CAPABILITY, "mention_count": 80},
        {"id": "cap:learning",   "label": "自我學習 ★★★★",     "type": "capability", "color": C_CAPABILITY, "mention_count": 80},
        # ★3 可用 (mention_count=60)
        {"id": "cap:voice",      "label": "語音辨識 ★★★",      "type": "capability", "color": C_CAPABILITY, "mention_count": 60},
        {"id": "cap:ocr",        "label": "影像OCR ★★★",       "type": "capability", "color": C_CAPABILITY, "mention_count": 60},
        {"id": "cap:discovery",  "label": "工具發現 ★★★",      "type": "capability", "color": C_CAPABILITY, "mention_count": 60},
        # ★2 實驗 (mention_count=40)
        {"id": "cap:nim",        "label": "NIM推理 ★★",        "type": "capability", "color": C_CAPABILITY, "mention_count": 40},
        {"id": "cap:federation", "label": "聯邦查詢 ★★",       "type": "capability", "color": C_CAPABILITY, "mention_count": 40},

        # ================================================================
        # Level 3a: 具體技能 (15 個)
        # ================================================================
        {"id": "skill:ner",           "label": "NER 實體提取",       "type": "skill", "color": C_SKILL, "mention_count": 15},
        {"id": "skill:entity_norm",   "label": "實體正規化",         "type": "skill", "color": C_SKILL, "mention_count": 12},
        {"id": "skill:graph_rag",     "label": "Graph-RAG",         "type": "skill", "color": C_SKILL, "mention_count": 14},
        {"id": "skill:pattern_learn", "label": "模式學習",           "type": "skill", "color": C_SKILL, "mention_count": 12},
        {"id": "skill:self_eval",     "label": "自我評分",           "type": "skill", "color": C_SKILL, "mention_count": 10},
        {"id": "skill:evolution",     "label": "自動進化",           "type": "skill", "color": C_SKILL, "mention_count": 10},
        {"id": "skill:cross_session", "label": "跨會話記憶",         "type": "skill", "color": C_SKILL, "mention_count": 11},
        {"id": "skill:whisper",       "label": "Whisper 轉錄",      "type": "skill", "color": C_SKILL, "mention_count": 8},
        {"id": "skill:tesseract",     "label": "Tesseract OCR",     "type": "skill", "color": C_SKILL, "mention_count": 8},
        {"id": "skill:tool_suggest",  "label": "工具自動推薦",       "type": "skill", "color": C_SKILL, "mention_count": 9},
        {"id": "skill:upsert",        "label": "圖譜入圖管線",       "type": "skill", "color": C_SKILL, "mention_count": 12},
        {"id": "skill:matrix",        "label": "公文配對矩陣",       "type": "skill", "color": C_SKILL, "mention_count": 10},
        {"id": "skill:auto_link",     "label": "實體自動連結",       "type": "skill", "color": C_SKILL, "mention_count": 11},
        {"id": "skill:bm25",          "label": "BM25 混合搜尋",     "type": "skill", "color": C_SKILL, "mention_count": 13},
        {"id": "skill:chunking",      "label": "文件分段",           "type": "skill", "color": C_SKILL, "mention_count": 11},

        # ================================================================
        # Level 3b: 演進方向 (6 個)
        # ================================================================
        {"id": "future:multimodal",    "label": "多模態RAG",         "type": "future", "color": C_FUTURE, "mention_count": 20},
        {"id": "future:causal",        "label": "因果推理",           "type": "future", "color": C_FUTURE, "mention_count": 20},
        {"id": "future:proactive",     "label": "主動式學習",         "type": "future", "color": C_FUTURE, "mention_count": 20},
        {"id": "future:voice_stream",  "label": "即時語音串流",       "type": "future", "color": C_FUTURE, "mention_count": 20},
        {"id": "future:table_ocr",     "label": "表格辨識",           "type": "future", "color": C_FUTURE, "mention_count": 20},
        {"id": "future:cross_org",     "label": "跨組織聯邦",         "type": "future", "color": C_FUTURE, "mention_count": 20},
    ]

    edges = [
        # ================================================================
        # Layer → Capability (contains) — 灰色
        # ================================================================
        {"source": "layer:input",   "target": "cap:crud",       "type": "contains",    "label": "包含"},
        {"source": "layer:input",   "target": "cap:voice",      "type": "contains",    "label": "包含"},
        {"source": "layer:input",   "target": "cap:ocr",        "type": "contains",    "label": "包含"},
        {"source": "layer:think",   "target": "cap:agent",      "type": "contains",    "label": "包含"},
        {"source": "layer:think",   "target": "cap:rag",        "type": "contains",    "label": "包含"},
        {"source": "layer:think",   "target": "cap:nim",        "type": "contains",    "label": "包含"},
        {"source": "layer:know",    "target": "cap:kg",         "type": "contains",    "label": "包含"},
        {"source": "layer:know",    "target": "cap:discovery",  "type": "contains",    "label": "包含"},
        {"source": "layer:execute", "target": "cap:crud",       "type": "contains",    "label": "包含"},
        {"source": "layer:execute", "target": "cap:federation", "type": "contains",    "label": "包含"},
        {"source": "layer:learn",   "target": "cap:learning",   "type": "contains",    "label": "包含"},

        # ================================================================
        # Capability → Skill (implements) — 藍色
        # ================================================================
        {"source": "cap:rag",       "target": "skill:bm25",          "type": "implements", "label": "實現"},
        {"source": "cap:rag",       "target": "skill:chunking",      "type": "implements", "label": "實現"},
        {"source": "cap:rag",       "target": "skill:graph_rag",     "type": "implements", "label": "實現"},
        {"source": "cap:kg",        "target": "skill:ner",           "type": "implements", "label": "實現"},
        {"source": "cap:kg",        "target": "skill:entity_norm",   "type": "implements", "label": "實現"},
        {"source": "cap:kg",        "target": "skill:upsert",        "type": "implements", "label": "實現"},
        {"source": "cap:kg",        "target": "skill:auto_link",     "type": "implements", "label": "實現"},
        {"source": "cap:learning",  "target": "skill:pattern_learn", "type": "implements", "label": "實現"},
        {"source": "cap:learning",  "target": "skill:self_eval",     "type": "implements", "label": "實現"},
        {"source": "cap:learning",  "target": "skill:evolution",     "type": "implements", "label": "實現"},
        {"source": "cap:learning",  "target": "skill:cross_session", "type": "implements", "label": "實現"},
        {"source": "cap:voice",     "target": "skill:whisper",       "type": "implements", "label": "實現"},
        {"source": "cap:ocr",       "target": "skill:tesseract",     "type": "implements", "label": "實現"},
        {"source": "cap:discovery", "target": "skill:tool_suggest",  "type": "implements", "label": "實現"},
        {"source": "cap:crud",      "target": "skill:matrix",        "type": "implements", "label": "實現"},

        # ================================================================
        # Capability → Capability (depends_on) — 紅色
        # ================================================================
        {"source": "cap:agent",      "target": "cap:rag",        "type": "depends_on", "label": "依賴"},
        {"source": "cap:agent",      "target": "cap:kg",         "type": "depends_on", "label": "依賴"},
        {"source": "cap:agent",      "target": "cap:discovery",  "type": "depends_on", "label": "依賴"},
        {"source": "cap:rag",        "target": "cap:crud",       "type": "depends_on", "label": "依賴"},
        {"source": "cap:nim",        "target": "cap:rag",        "type": "depends_on", "label": "依賴"},
        {"source": "cap:federation", "target": "cap:agent",      "type": "depends_on", "label": "依賴"},

        # ================================================================
        # Capability ← Capability (enhances) — 綠色
        # ================================================================
        {"source": "cap:learning",   "target": "cap:agent",      "type": "enhances",   "label": "強化"},
        {"source": "cap:kg",         "target": "cap:rag",        "type": "enhances",   "label": "強化"},
        {"source": "cap:discovery",  "target": "cap:agent",      "type": "enhances",   "label": "強化"},
        {"source": "cap:voice",      "target": "cap:crud",       "type": "enhances",   "label": "強化"},
        {"source": "cap:ocr",        "target": "cap:crud",       "type": "enhances",   "label": "強化"},

        # ================================================================
        # Skill → Skill (feeds) — 橘色
        # ================================================================
        {"source": "skill:ner",           "target": "skill:entity_norm",   "type": "feeds",      "label": "資料流"},
        {"source": "skill:entity_norm",   "target": "skill:upsert",       "type": "feeds",      "label": "資料流"},
        {"source": "skill:upsert",        "target": "skill:auto_link",    "type": "feeds",      "label": "資料流"},
        {"source": "skill:chunking",      "target": "skill:bm25",         "type": "feeds",      "label": "資料流"},
        {"source": "skill:self_eval",     "target": "skill:evolution",    "type": "feeds",      "label": "資料流"},
        {"source": "skill:pattern_learn", "target": "skill:cross_session","type": "feeds",      "label": "資料流"},
        {"source": "skill:ner",           "target": "skill:graph_rag",    "type": "feeds",      "label": "資料流"},
        {"source": "skill:auto_link",     "target": "skill:matrix",       "type": "feeds",      "label": "資料流"},

        # ================================================================
        # Skill + Skill (integrates) — 紫色
        # ================================================================
        {"source": "skill:graph_rag",     "target": "skill:bm25",         "type": "integrates", "label": "整合"},
        {"source": "skill:graph_rag",     "target": "skill:upsert",       "type": "integrates", "label": "整合"},
        {"source": "skill:cross_session", "target": "skill:tool_suggest", "type": "integrates", "label": "整合"},

        # ================================================================
        # Current → Future (evolves_to) — 粉色
        # ================================================================
        {"source": "cap:rag",        "target": "future:multimodal",   "type": "evolves_to", "label": "演進"},
        {"source": "cap:agent",      "target": "future:causal",       "type": "evolves_to", "label": "演進"},
        {"source": "cap:learning",   "target": "future:proactive",    "type": "evolves_to", "label": "演進"},
        {"source": "cap:voice",      "target": "future:voice_stream", "type": "evolves_to", "label": "演進"},
        {"source": "cap:ocr",        "target": "future:table_ocr",    "type": "evolves_to", "label": "演進"},
        {"source": "cap:federation", "target": "future:cross_org",    "type": "evolves_to", "label": "演進"},

        # ================================================================
        # Cross-layer connections (enhances / feeds / depends_on)
        # ================================================================
        # Skills enhancing capabilities they don't directly belong to
        {"source": "skill:bm25",          "target": "cap:agent",      "type": "enhances",   "label": "強化"},
        {"source": "skill:cross_session", "target": "cap:agent",      "type": "enhances",   "label": "強化"},
        {"source": "skill:tool_suggest",  "target": "cap:agent",      "type": "enhances",   "label": "強化"},
        {"source": "skill:entity_norm",   "target": "cap:rag",        "type": "enhances",   "label": "強化"},

        # Future nodes feeding back
        {"source": "future:multimodal",   "target": "future:table_ocr",    "type": "integrates", "label": "整合"},
        {"source": "future:proactive",    "target": "future:causal",       "type": "depends_on", "label": "依賴"},
        {"source": "future:cross_org",    "target": "future:voice_stream", "type": "integrates", "label": "整合"},
    ]

    return {
        "success": True,
        "nodes": nodes,
        "edges": edges,
    }


# ============================================================================
# NemoClaw: Agent 能力自覺 + 鏡像回饋
# ============================================================================

@router.post("/agent/capability-profile")
async def get_agent_capability_profile(
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Agent 能力自覺 — 分析最近 7 天各領域的表現。

    返回每個領域的平均分數、查詢數、趨勢，
    以及識別出的強項和弱項領域。
    """
    from app.services.ai.agent_capability_tracker import get_capability_profile

    try:
        profile = await get_capability_profile(db)
        return {"success": True, **profile}
    except Exception as e:
        logger.error("能力剖面查詢失敗: %s", e, exc_info=True)
        return {
            "success": False,
            "domains": {},
            "strengths": [],
            "weaknesses": [],
            "overall_score": 0.0,
            "total_queries": 0,
        }


@router.post("/agent/mirror-report")
async def get_agent_mirror_report(
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Agent 鏡像回饋 — 生成自我觀察報告。

    統計今日查詢、學習記錄、能力剖面，
    並用 LLM 生成一段自然語言的自我觀察。
    """
    from app.core.ai_connector import get_ai_connector
    from app.services.ai.agent_mirror_feedback import generate_mirror_report

    try:
        ai_connector = get_ai_connector()
    except Exception:
        ai_connector = None

    try:
        report = await generate_mirror_report(db, ai_connector)
        return {"success": True, **report}
    except Exception as e:
        logger.error("鏡像回饋報告生成失敗: %s", e, exc_info=True)
        return {
            "success": False,
            "summary": "",
            "stats": {},
            "learnings": [],
            "strengths": [],
            "weaknesses": [],
        }


# ============================================================================
# NemoClaw Stage 1B: Agent Self-Profile
# ============================================================================


@router.post("/agent/self-profile")
async def get_agent_self_profile(
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Agent 自我檔案 — 我是誰、我擅長什麼。

    從 DB 統計查詢總數、常用領域、常用工具、平均分數、
    學習記錄數，並產生一段個性描述。
    """
    from app.services.ai.agent_self_profile import get_self_profile

    try:
        profile = await get_self_profile(db)
        return {"success": True, **profile}
    except Exception as e:
        logger.error("Agent 自我檔案查詢失敗: %s", e, exc_info=True)
        return {
            "success": False,
            "identity": "乾坤",
            "total_queries": 0,
            "top_domains": [],
            "favorite_tools": [],
            "avg_score": 0.0,
            "learnings_count": 0,
            "conversation_summaries": 0,
            "personality_hint": "系統資料暫時無法存取",
        }


# ============================================================================
# NemoClaw Stage 2: Proactive Alerts (deadline-focused)
# ============================================================================


@router.post("/agent/proactive-alerts")
async def get_agent_proactive_alerts(
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Agent 主動提醒 — 即將到期公文 + 系統健康 + 未讀通知。

    專為 Agent 問答注入上下文設計，與 ai_stats 的
    proactive/alerts 端點互補（後者側重案件逾期與品質）。
    """
    from app.services.ai.agent_proactive_scanner import scan_agent_alerts

    try:
        alerts = await scan_agent_alerts(db)
        return {"success": True, **alerts}
    except Exception as e:
        logger.error("Agent 主動提醒掃描失敗: %s", e, exc_info=True)
        return {
            "success": False,
            "deadline_alerts": [],
            "health_issues": [],
            "unread_notifications": 0,
            "total_alerts": 0,
        }

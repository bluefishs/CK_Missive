"""
知識圖譜管理操作 API 端點

提供入圖管線、代碼圖譜入圖、循環偵測、架構分析、
JSON 匯入、實體合併等管理功能。

Refactored from: graph_query.py
Version: 1.0.0
Created: 2026-03-30
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin, get_async_db
from app.extended.models import User
from app.services.ai.graph_ingestion_pipeline import GraphIngestionPipeline
from app.services.ai.canonical_entity_service import CanonicalEntityService
from app.schemas.knowledge_graph import (
    KGIngestRequest,
    KGIngestResponse,
    KGMergeEntitiesRequest,
    KGMergeEntitiesResponse,
    KGCodeGraphIngestRequest,
    KGCodeGraphIngestResponse,
    KGCycleDetectionResponse,
    KGArchitectureAnalysisResponse,
    KGJsonImportRequest,
    KGJsonImportResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# 管理操作端點
# ============================================================================

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

    # 動態偵測專案根目錄（相容 PM2 + Docker + 直接執行）
    _this_file = Path(__file__).resolve()
    # 往上找直到找到包含 backend/ 和 frontend/ 的目錄
    project_root = _this_file.parents[5]  # 預設: backend/app/api/endpoints/ai/ → 5 層
    for i in range(3, 7):
        candidate = _this_file.parents[i]
        if (candidate / "backend" / "app").is_dir():
            project_root = candidate
            break
    backend_app_dir = project_root / "backend" / "app"
    frontend_src_dir = project_root / "frontend" / "src" if request.include_frontend else None
    logger.info(f"Code-graph ingest: project_root={project_root}, backend_app={backend_app_dir} (exists={backend_app_dir.is_dir()})")

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


@router.post("/graph/admin/diff-impact")
async def analyze_diff_impact(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin()),
):
    """
    分析 git diff 的影響範圍。

    基於知識圖譜中的程式碼實體，找出變更檔案關聯的實體
    及其下游依賴者，產出影響報告。

    🔒 權限要求: Admin
    """
    from app.services.ai.diff_impact_analyzer import DiffImpactAnalyzer

    analyzer = DiffImpactAnalyzer(db)
    try:
        result = await analyzer.analyze_diff()
        return {"success": True, "data": result}
    except Exception as e:
        logger.error("Diff impact analysis failed: %s", e, exc_info=True)
        return {"success": False, "data": {"error": str(e)}}


@router.post("/graph/admin/centrality")
async def centrality_analysis(
    top_n: int = 20,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    God Node 中心性分析：找出圖譜中度數最高的樞紐實體。

    回傳 top-N 高中心性實體、平均度數、耦合風險實體列表。

    Args:
        top_n: 回傳前 N 個樞紐實體 (預設 20)

    🔒 權限要求: Admin
    """
    from app.services.ai.graph_statistics_service import GraphStatisticsService

    svc = GraphStatisticsService(db)
    try:
        result = await svc.centrality_analysis(top_n=top_n)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error("Centrality analysis failed: %s", e, exc_info=True)
        return {"success": False, "data": {"error": str(e)}}


@router.post("/graph/admin/export-obsidian")
async def export_obsidian_vault(
    entity_types: list[str] | None = None,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Export knowledge graph as Obsidian Markdown vault (ZIP download).

    Generates one .md file per CanonicalEntity with [[wiki links]]
    for automatic Obsidian graph connection.

    Args:
        entity_types: Optional list of entity types to include (None = all)

    🔒 權限要求: Admin
    """
    import shutil
    import tempfile

    from fastapi.responses import StreamingResponse
    from app.services.ai.obsidian_exporter import export_vault

    tmpdir = tempfile.mkdtemp(prefix="obsidian_vault_")
    try:
        result = await export_vault(db, tmpdir, entity_types=entity_types)

        if result["files_created"] == 0:
            import json
            return StreamingResponse(
                iter([json.dumps({"success": True, "message": "No entities to export", **result}).encode()]),
                media_type="application/json",
            )

        # Create ZIP archive
        zip_path = shutil.make_archive(
            base_name=tmpdir + "_archive",
            format="zip",
            root_dir=tmpdir,
        )

        def iter_file():
            with open(zip_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
            # Cleanup temp files after streaming
            import os
            try:
                os.remove(zip_path)
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass

        return StreamingResponse(
            iter_file(),
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=obsidian_vault.zip",
            },
        )
    except Exception as e:
        logger.error("Obsidian vault export failed: %s", e, exc_info=True)
        # Cleanup on error
        import shutil as sh
        sh.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=500, detail="Export failed")


@router.post("/graph/admin/code-check")
async def code_graph_check(
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Code Graph 快速檢查（dry-run）。

    不執行入圖，僅統計來源檔案數量與目前圖譜實體數量。

    🔒 權限要求: Admin
    """
    from pathlib import Path
    from sqlalchemy import func, select
    from app.extended.models import CanonicalEntity, EntityRelationship

    # 偵測專案根目錄
    _this_file = Path(__file__).resolve()
    project_root = _this_file.parents[5]
    for i in range(3, 7):
        candidate = _this_file.parents[i]
        if (candidate / "backend" / "app").is_dir():
            project_root = candidate
            break

    backend_app = project_root / "backend" / "app"
    frontend_src = project_root / "frontend" / "src"

    py_files = len(list(backend_app.rglob("*.py"))) if backend_app.is_dir() else 0
    ts_files = 0
    if frontend_src.is_dir():
        ts_files = len(list(frontend_src.rglob("*.ts"))) + len(list(frontend_src.rglob("*.tsx")))

    # 查詢 DB 實體統計
    stmt = (
        select(CanonicalEntity.entity_type, func.count())
        .group_by(CanonicalEntity.entity_type)
    )
    rows = (await db.execute(stmt)).all()
    entity_counts_by_type = {r[0]: r[1] for r in rows}
    total_entities = sum(entity_counts_by_type.values())

    rel_count = (await db.execute(select(func.count()).select_from(EntityRelationship))).scalar() or 0

    return {
        "success": True,
        "py_files": py_files,
        "ts_files": ts_files,
        "entity_counts_by_type": entity_counts_by_type,
        "total_entities": total_entities,
        "total_relations": rel_count,
    }


@router.post("/graph/admin/relation-types")
async def list_relation_types(
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    列舉圖譜中所有關係類型，按 code_graph / knowledge_graph 分組。

    🔒 權限要求: Admin
    """
    from sqlalchemy import distinct, select
    from app.extended.models import EntityRelationship
    from app.core.constants import CODE_ENTITY_TYPES

    # Code graph 常見關係前綴/類型
    _CODE_RELATION_PREFIXES = ("imports", "defines", "calls", "inherits", "has_column", "has_endpoint")

    stmt = select(distinct(EntityRelationship.relation_type))
    rows = (await db.execute(stmt)).all()

    code_graph_types = []
    knowledge_graph_types = []
    for (rel_type,) in rows:
        if any(rel_type.startswith(p) for p in _CODE_RELATION_PREFIXES):
            code_graph_types.append(rel_type)
        else:
            knowledge_graph_types.append(rel_type)

    return {
        "success": True,
        "code_graph": sorted(code_graph_types),
        "knowledge_graph": sorted(knowledge_graph_types),
        "total_types": len(code_graph_types) + len(knowledge_graph_types),
    }


@router.post("/graph/admin/federation-health")
async def federation_health(
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Federation 健康狀態：各來源專案的實體與關係數量。

    回傳每個 source_project 的 entity_count / relation_count，
    以及 federation_ready 旗標（至少 2 個專案有實體時為 True）。

    🔒 權限要求: Admin
    """
    from sqlalchemy import func, select
    from app.extended.models import CanonicalEntity, EntityRelationship

    # Entity counts per source_project
    entity_stmt = (
        select(
            CanonicalEntity.source_project,
            func.count().label("entity_count"),
        )
        .group_by(CanonicalEntity.source_project)
    )
    entity_rows = (await db.execute(entity_stmt)).all()

    # Relation counts per source_project
    rel_stmt = (
        select(
            EntityRelationship.source_project,
            func.count().label("relation_count"),
        )
        .group_by(EntityRelationship.source_project)
    )
    rel_rows = (await db.execute(rel_stmt)).all()

    # Build per-project dict
    rel_map = {r[0]: r[1] for r in rel_rows}
    projects = {}
    total_entities = 0
    for row in entity_rows:
        proj_name = row[0]
        e_count = row[1]
        projects[proj_name] = {
            "entity_count": e_count,
            "relation_count": rel_map.get(proj_name, 0),
        }
        total_entities += e_count

    return {
        "projects": projects,
        "total_entities": total_entities,
        "federation_ready": len(projects) >= 2,
    }


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


@router.post("/graph/admin/verify-entity", summary="實體置信度升級")
async def verify_entity(
    request: Request,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    將實體或關係的 confidence_level 從 extracted/inferred → verified。
    用於用戶確認 Agent 答案正確後，提升引用實體的置信度。
    """
    from app.extended.models.knowledge_graph import CanonicalEntity, EntityRelationship
    from sqlalchemy import update

    body = await request.json()
    entity_ids = body.get("entity_ids", [])
    relationship_ids = body.get("relationship_ids", [])

    updated = 0

    if entity_ids:
        # CanonicalEntity 目前沒有 confidence_level，改為增加 mention_count
        result = await db.execute(
            update(CanonicalEntity)
            .where(CanonicalEntity.id.in_(entity_ids))
            .values(mention_count=CanonicalEntity.mention_count + 5)  # 驗證加權
        )
        updated += result.rowcount

    if relationship_ids:
        result = await db.execute(
            update(EntityRelationship)
            .where(EntityRelationship.id.in_(relationship_ids))
            .where(EntityRelationship.confidence_level != "verified")
            .values(confidence_level="verified")
        )
        updated += result.rowcount

    await db.commit()

    return {
        "success": True,
        "message": f"已驗證 {updated} 個實體/關係",
        "updated": updated,
    }


@router.post("/graph/admin/erp-ingest", summary="手動觸發 ERP 圖譜入圖")
async def trigger_erp_graph_ingest(
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    手動觸發 ERP 圖譜入圖。

    掃描 ERP 表 (quotation/expense/asset/vendor) → canonical_entities，
    自動建立 case_code 跨圖橋接。
    """
    from app.services.ai.erp_graph_ingest import ErpGraphIngestService

    service = ErpGraphIngestService(db)
    stats = await service.ingest_all()
    return {
        "success": True,
        "message": f"ERP 入圖完成: {stats['entities']} 實體, {stats['relations']} 關係, {stats['cross_graph_bridges']} 橋接",
        **stats,
    }

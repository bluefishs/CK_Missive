"""
Code Graph 管理操作 API 端點

提供代碼圖譜入圖、循環偵測、架構分析、JSON 匯入、快速檢查等功能。

Refactored from: graph_admin.py
Version: 1.0.0
Created: 2026-04-09
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin, get_async_db
from app.extended.models import User
from app.schemas.knowledge_graph import (
    KGCodeGraphIngestRequest,
    KGCodeGraphIngestResponse,
    KGCycleDetectionResponse,
    KGArchitectureAnalysisResponse,
    KGJsonImportRequest,
    KGJsonImportResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


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

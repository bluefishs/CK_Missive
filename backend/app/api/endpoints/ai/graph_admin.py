"""
知識圖譜管理操作 API 端點

提供入圖管線、實體合併、中心性分析、Obsidian 匯出、
Federation 健康、ERP 入圖等管理功能。

Code Graph 相關端點已拆分至 graph_admin_code.py。

Refactored from: graph_query.py
Version: 1.1.0
Created: 2026-03-30
Updated: 2026-04-09 - 拆分 Code Graph 端點至 graph_admin_code.py
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
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

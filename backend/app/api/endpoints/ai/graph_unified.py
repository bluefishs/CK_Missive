"""
跨圖譜統一搜尋 API 端點

提供 Code Wiki、模組概覽、統一搜尋、模組映射、
智慧搜尋、ERP 圖譜網路、案件流程鏈等功能。

Skills 能力圖譜與技能演化樹已拆分至 graph_skills_map.py。

Refactored from: graph_query.py
Version: 1.1.0
Created: 2026-03-30
Updated: 2026-04-09 - 拆分 skills-map/skill-evolution 至 graph_skills_map.py
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth, get_async_db
from app.extended.models import User
from app.services.ai.graph.graph_query_service import GraphQueryService
from app.schemas.knowledge_graph import (
    UnifiedGraphSearchRequest,
    UnifiedGraphSearchResponse,
    UnifiedGraphResult,
    KGCodeWikiRequest,
    KGCodeWikiResponse,
    KGModuleOverviewResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# 跨圖譜搜尋與能力圖譜端點
# ============================================================================

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


@router.post("/graph/unified-search", response_model=UnifiedGraphSearchResponse)
async def unified_graph_search(
    request: UnifiedGraphSearchRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """跨圖譜統一搜尋 — 同時搜尋 7 大圖譜 (KG + Code + DB + ERP + Tender)"""
    import asyncio

    query = request.query.strip()
    query_lower = query.lower()
    results: list[UnifiedGraphResult] = []
    sources_queried: list[str] = []

    # 每個並行 DB task 必須用獨立 session（避免 asyncpg "another operation in progress"）
    from app.db.database import run_with_fresh_session

    async def search_kg() -> list[UnifiedGraphResult]:
        async def _q(fresh_db):
            svc = GraphQueryService(fresh_db)
            return await svc.search_entities(query=query, limit=request.limit_per_graph)
        entities = await run_with_fresh_session(_q)
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
        rows = await run_with_fresh_session(lambda s: s.execute(stmt))
        rows = rows.all()
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
        from app.services.ai.graph.schema_reflector import SchemaReflectorService

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

    async def search_erp() -> list[UnifiedGraphResult]:
        """搜尋 ERP 圖譜 (KG-7)"""
        from sqlalchemy import select
        from app.extended.models.knowledge_graph import CanonicalEntity
        from app.services.ai.graph.erp_graph_types import ERP_ENTITY_TYPES
        import re

        escaped = re.sub(r'([%_\\])', r'\\\1', query)
        stmt = (
            select(CanonicalEntity.canonical_name, CanonicalEntity.entity_type,
                   CanonicalEntity.description, CanonicalEntity.external_id)
            .where(CanonicalEntity.entity_type.in_(ERP_ENTITY_TYPES))
            .where(CanonicalEntity.canonical_name.ilike(f"%{escaped}%"))
            .order_by(CanonicalEntity.mention_count.desc())
            .limit(request.limit_per_graph)
        )
        rows = await run_with_fresh_session(lambda s: s.execute(stmt))
        rows = rows.all()
        return [
            UnifiedGraphResult(
                source="erp",
                entity_type=row[1],
                name=row[0],
                description=(row[2] if isinstance(row[2], str) else "") or "",
                relevance=1.0,
            )
            for row in rows
        ]

    async def search_tender() -> list[UnifiedGraphResult]:
        """搜尋標案圖譜 (KG-5)"""
        from sqlalchemy import select
        from app.extended.models.tender_cache import TenderRecord
        import re

        escaped = re.sub(r'([%_\\])', r'\\\1', query)
        stmt = (
            select(TenderRecord.title, TenderRecord.unit_name,
                   TenderRecord.budget, TenderRecord.job_number)
            .where(TenderRecord.title.ilike(f"%{escaped}%"))
            .order_by(TenderRecord.announce_date.desc().nullslast())
            .limit(request.limit_per_graph)
        )
        rows = await run_with_fresh_session(lambda s: s.execute(stmt))
        rows = rows.all()
        return [
            UnifiedGraphResult(
                source="tender",
                entity_type="tender_record",
                name=row[0] or "",
                description=f"機關: {row[1] or '?'} | 預算: {row[2] or '?'} | {row[3] or ''}",
                relevance=1.0,
            )
            for row in rows
        ]

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
    if request.include_erp:
        tasks.append(("erp", search_erp()))
        sources_queried.append("erp")
    if request.include_tender:
        tasks.append(("tender", search_tender()))
        sources_queried.append("tender")

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


@router.post("/graph/smart-search")
async def smart_graph_search(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    """自然語言知識圖譜搜尋 (Gemma 4 powered)"""
    body = await request.json()
    question = body.get("question", "")
    if not question:
        return JSONResponse({"success": False, "error": "缺少 question"})

    svc = GraphQueryService(db)
    try:
        result = await svc.smart_graph_search(question, limit=20)
    except Exception as e:
        logger.error("smart_graph_search failed: %s", e, exc_info=True)
        return JSONResponse({"success": False, "error": str(e)})
    return JSONResponse(
        {"success": True, "data": result},
        media_type="application/json; charset=utf-8",
    )


@router.post("/graph/erp-network", summary="ERP 財務圖譜關係網路")
async def get_erp_graph_network(
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """ERP 實體關係網路 — nodes + links for force-directed graph"""
    from sqlalchemy import select as sa_select
    from app.extended.models.knowledge_graph import CanonicalEntity, EntityRelationship
    from app.services.ai.graph.erp_graph_types import ERP_ENTITY_TYPES

    ent_rows = (await db.execute(
        sa_select(CanonicalEntity.id, CanonicalEntity.canonical_name,
                  CanonicalEntity.entity_type, CanonicalEntity.external_id)
        .where(CanonicalEntity.entity_type.in_(ERP_ENTITY_TYPES))
        .order_by(CanonicalEntity.mention_count.desc())
        .limit(150)
    )).all()

    id_set = {r[0] for r in ent_rows}
    nodes = [{"id": str(r[0]), "name": r[1], "type": r[2]} for r in ent_rows]

    links = []
    if id_set:
        rel_rows = (await db.execute(
            sa_select(EntityRelationship.source_entity_id, EntityRelationship.target_entity_id,
                      EntityRelationship.relation_type)
            .where(EntityRelationship.source_entity_id.in_(id_set))
            .where(EntityRelationship.target_entity_id.in_(id_set))
            .limit(500)
        )).all()
        links = [{"source": str(r[0]), "target": str(r[1]), "relation": r[2]} for r in rel_rows]

    return JSONResponse(
        {"success": True, "data": {"nodes": nodes, "links": links}},
        media_type="application/json; charset=utf-8",
    )


@router.post("/graph/case-flow", summary="案件全流程鏈查詢")
async def get_case_flow(
    request: Request,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    以 case_code 為樞紐查詢完整業務鏈路:
    tender -> pm_case -> quotation -> invoice -> billing -> vendor_payable -> expense
    """
    body = await request.json()
    case_code = body.get("case_code", "").strip()
    if not case_code:
        return JSONResponse(
            {"success": False, "error": "case_code is required"},
            status_code=400,
        )

    from app.services.ai.domain.case_flow_tracker import CaseFlowTracker
    tracker = CaseFlowTracker(db)
    flow = await tracker.get_full_flow(case_code)
    return JSONResponse(
        {"success": True, "data": flow},
        media_type="application/json; charset=utf-8",
    )

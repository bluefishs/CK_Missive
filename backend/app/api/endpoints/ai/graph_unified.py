"""
跨圖譜統一搜尋與能力圖譜 API 端點

提供技能演化樹、Code Wiki、模組概覽、統一搜尋、
模組映射、能力圖譜等功能。

Refactored from: graph_query.py
Version: 1.0.0
Created: 2026-03-30
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth, get_async_db
from app.extended.models import User
from app.services.ai.graph_query_service import GraphQueryService
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

    async def search_erp() -> list[UnifiedGraphResult]:
        """搜尋 ERP 圖譜 (KG-7)"""
        from sqlalchemy import select
        from app.extended.models.knowledge_graph import CanonicalEntity
        from app.services.ai.erp_graph_types import ERP_ENTITY_TYPES
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
        rows = (await db.execute(stmt)).all()
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
        rows = (await db.execute(stmt)).all()
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

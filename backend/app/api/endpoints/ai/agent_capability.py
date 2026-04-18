"""
Agent 能力自覺 + 跨專案聯邦 API 端點

包含:
- Agent 能力自覺 (capability-profile, mirror-report, self-profile)
- Agent 主動提醒 (proactive-alerts)
- 跨專案聯邦 (federated-contribute, federated-search, cross-domain-link/path)

Version: 2.0.0 — 重命名自 agent_nemoclaw.py (ADR-0014/0015)
Created: 2026-03-29
Updated: 2026-04-16
"""

import asyncio
import hmac
import logging
import os
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth, require_admin, get_async_db
from app.core.service_auth import require_scope
from app.extended.models import User
from app.schemas.knowledge_graph import (
    FederatedContributionRequest,
    FederatedContributionResponse,
    FederatedSearchRequest,
    FederatedSearchResponse,
    FederatedGraphNode,
    CrossDomainPathRequest,
    CrossDomainPathResponse,
    CrossDomainPathNode,
    KGGraphEdge,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Service-to-service auth for KG Federation
# ---------------------------------------------------------------------------

def _verify_federation_token(
    request: Request,
    x_service_token: str | None = Header(None),
) -> bool:
    """Validate X-Service-Token for cross-project federation calls."""
    current_token = os.getenv("MCP_SERVICE_TOKEN")
    prev_token = os.getenv("MCP_SERVICE_TOKEN_PREV")
    if not current_token:
        is_dev = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
        client_host = request.client.host if request.client else ""
        if is_dev and client_host in ("127.0.0.1", "::1"):
            return True
        raise HTTPException(status_code=403, detail="Service token required")

    if not x_service_token:
        raise HTTPException(status_code=401, detail="Invalid service token")

    token_bytes = x_service_token.encode("utf-8")
    match_current = hmac.compare_digest(token_bytes, current_token.encode("utf-8"))
    match_prev = (
        hmac.compare_digest(token_bytes, prev_token.encode("utf-8"))
        if prev_token
        else False
    )
    if not match_current and not match_prev:
        raise HTTPException(status_code=401, detail="Invalid service token")
    return True


# ---------------------------------------------------------------------------
# Per-source_project federation rate limiter
# ---------------------------------------------------------------------------

FEDERATION_RATE_LIMIT = int(os.getenv("FEDERATION_RATE_LIMIT", "30"))
FEDERATION_RATE_WINDOW = int(os.getenv("FEDERATION_RATE_WINDOW", "60"))


async def _check_federation_rate_limit(source_project: str) -> None:
    """Sliding-window rate limit per source_project using Redis ZSET."""
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if not redis:
            return
        key = f"federation:rate:{source_project}"
        now = time.time()
        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - FEDERATION_RATE_WINDOW)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, FEDERATION_RATE_WINDOW * 2)
        results = await pipe.execute()
        count = results[2]
        if count > FEDERATION_RATE_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded for {source_project}: {count}/{FEDERATION_RATE_LIMIT} per {FEDERATION_RATE_WINDOW}s",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Federation rate limit check failed (allowing): %s", e)


async def _check_idempotency(idempotency_key: str | None) -> dict | None:
    """Check Redis for cached idempotent result."""
    if not idempotency_key:
        return None
    try:
        import json
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if not redis:
            return None
        cached = await redis.get(f"federation:idem:{idempotency_key}")
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    return None


async def _store_idempotency(idempotency_key: str | None, result: dict) -> None:
    """Store idempotent result in Redis with 1h TTL."""
    if not idempotency_key:
        return
    try:
        import json
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis:
            await redis.setex(
                f"federation:idem:{idempotency_key}",
                3600,
                json.dumps(result, default=str),
            )
    except Exception:
        pass


# ============================================================================
# Agent 能力自覺 + 鏡像回饋
# ============================================================================

@router.post("/agent/capability-profile")
async def get_agent_capability_profile(
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """Agent 能力自覺 — 分析最近 7 天各領域的表現。"""
    from app.services.ai.agent.agent_capability_tracker import get_capability_profile

    try:
        profile = await get_capability_profile(db)
        return {"success": True, **profile}
    except Exception as e:
        logger.error("能力剖面查詢失敗: %s", e, exc_info=True)
        return {"success": False, "domains": {}, "strengths": [], "weaknesses": [], "overall_score": 0.0, "total_queries": 0}


@router.post("/agent/mirror-report")
async def get_agent_mirror_report(
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """Agent 鏡像回饋 — 生成自我觀察報告。"""
    from app.core.ai_connector import get_ai_connector
    from app.services.ai.agent.agent_mirror_feedback import generate_mirror_report

    try:
        ai_connector = get_ai_connector()
    except Exception:
        ai_connector = None

    try:
        report = await generate_mirror_report(db, ai_connector)
        return {"success": True, **report}
    except Exception as e:
        logger.error("鏡像回饋報告生成失敗: %s", e, exc_info=True)
        return {"success": False, "summary": "", "stats": {}, "learnings": [], "strengths": [], "weaknesses": []}


@router.post("/agent/self-profile")
async def get_agent_self_profile(
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """Agent 自我檔案 — 我是誰、我擅長什麼。"""
    from app.services.ai.agent.agent_self_profile import get_self_profile

    try:
        profile = await get_self_profile(db)
        return {"success": True, **profile}
    except Exception as e:
        logger.error("Agent 自我檔案查詢失敗: %s", e, exc_info=True)
        return {"success": False, "identity": "乾坤", "total_queries": 0, "top_domains": [], "favorite_tools": [], "avg_score": 0.0, "learnings_count": 0, "conversation_summaries": 0, "personality_hint": "系統資料暫時無法存取"}


@router.post("/agent/proactive-alerts")
async def get_agent_proactive_alerts(
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """Agent 主動提醒 — 即將到期公文 + 系統健康 + 未讀通知。"""
    from app.services.ai.agent.agent_proactive_scanner import scan_agent_alerts

    try:
        alerts = await scan_agent_alerts(db)
        return {"success": True, **alerts}
    except Exception as e:
        logger.error("Agent 主動提醒掃描失敗: %s", e, exc_info=True)
        return {"success": False, "deadline_alerts": [], "health_issues": [], "unread_notifications": 0, "total_alerts": 0}


# ============================================================================
# 跨專案聯邦 (KG Federation)
# ============================================================================

@router.post("/graph/federated-contribute", response_model=FederatedContributionResponse)
async def federated_contribute(
    request: FederatedContributionRequest,
    _auth: bool = Depends(require_scope("write:kg")),
    db: AsyncSession = Depends(get_async_db),
):
    """接收外部專案的實體貢獻。"""
    from app.services.ai.domain.cross_domain_contribution_service import CrossDomainContributionService
    from app.services.ai.domain.cross_domain_linker import CrossDomainLinker

    _log_ctx = {"source_project": request.source_project, "entity_count": len(request.contributions), "relation_count": len(request.relations), "idempotency_key": request.idempotency_key}
    t0 = time.time()

    await _check_federation_rate_limit(request.source_project)

    cached = await _check_idempotency(request.idempotency_key)
    if cached is not None:
        logger.info("federation.contribute.idempotency_hit %s", _log_ctx)
        return FederatedContributionResponse(**cached)

    try:
        svc = CrossDomainContributionService(db)
        result = await svc.process_contribution(request)

        if result.success and result.resolved:
            from app.services.ai.graph.graph_helpers import invalidate_graph_cache
            try:
                cleared = await invalidate_graph_cache("path:*")
                cleared += await invalidate_graph_cache("neighbors:*")
                cleared += await invalidate_graph_cache("search:*")
                if cleared > 0:
                    logger.info("Invalidated %d graph cache keys after contribution", cleared)
            except Exception:
                pass

        if result.success and result.resolved:
            async def _deferred_link(src_project: str) -> None:
                try:
                    from app.db.database import AsyncSessionLocal
                    async with AsyncSessionLocal() as link_db:
                        linker = CrossDomainLinker(link_db)
                        link_report = await linker.link_after_contribution(src_project)
                        if link_report.links_created > 0:
                            await link_db.commit()
                            logger.info("Deferred cross-domain linking after %s: %d new links", src_project, link_report.links_created)
                except Exception as link_err:
                    logger.warning("Deferred cross-domain linking failed (non-fatal): %s", link_err)

            asyncio.create_task(_deferred_link(request.source_project))

        if result.success:
            await _store_idempotency(request.idempotency_key, result.model_dump())

        _log_ctx["processing_ms"] = int((time.time() - t0) * 1000)
        logger.info("federation.contribute.complete %s", _log_ctx)
        return result
    except Exception as e:
        _log_ctx["processing_ms"] = int((time.time() - t0) * 1000)
        logger.error("federation.contribute.failed %s", _log_ctx, exc_info=True)
        return FederatedContributionResponse(success=False, message="聯邦貢獻處理失敗，請檢查伺服器日誌")


@router.post("/graph/federated-search", response_model=FederatedSearchResponse)
async def federated_search(
    request: FederatedSearchRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """跨專案實體搜尋，回傳含 source_project 標記的節點與邊。"""
    import re as _re
    from sqlalchemy import select, and_, or_
    from app.extended.models import CanonicalEntity, EntityAlias, EntityRelationship

    try:
        escaped_query = _re.sub(r'([%_\\])', r'\\\1', request.query)
        query_pattern = f"%{escaped_query}%"

        name_or_ext = or_(CanonicalEntity.canonical_name.ilike(query_pattern), CanonicalEntity.external_id.ilike(query_pattern))
        alias_subq = select(EntityAlias.canonical_entity_id).where(EntityAlias.alias_name.ilike(query_pattern)).scalar_subquery()
        search_condition = or_(name_or_ext, CanonicalEntity.id.in_(alias_subq))

        filters = [search_condition]
        if request.entity_types:
            filters.append(CanonicalEntity.entity_type.in_(request.entity_types))
        if request.source_projects:
            filters.append(CanonicalEntity.source_project.in_(request.source_projects))

        result = await db.execute(select(CanonicalEntity).where(and_(*filters)).order_by(CanonicalEntity.mention_count.desc()).limit(request.limit))
        entities = result.scalars().all()

        nodes = [FederatedGraphNode(id=e.id, name=e.canonical_name, type=e.entity_type, source_project=e.source_project, mention_count=e.mention_count or 0, external_id=e.external_id) for e in entities]

        entity_ids = set(e.id for e in entities)
        edges = []
        if entity_ids:
            edge_result = await db.execute(select(EntityRelationship).where(and_(or_(EntityRelationship.source_entity_id.in_(entity_ids), EntityRelationship.target_entity_id.in_(entity_ids)), EntityRelationship.invalidated_at.is_(None))).limit(200))
            neighbor_ids = set()
            for rel in edge_result.scalars().all():
                edges.append(KGGraphEdge(source_id=rel.source_entity_id, target_id=rel.target_entity_id, relation_type=rel.relation_type, relation_label=rel.relation_label, weight=rel.weight or 1.0))
                neighbor_ids.add(rel.source_entity_id)
                neighbor_ids.add(rel.target_entity_id)

            missing_ids = neighbor_ids - entity_ids
            if missing_ids:
                neighbor_result = await db.execute(select(CanonicalEntity).where(CanonicalEntity.id.in_(missing_ids)))
                for ne in neighbor_result.scalars().all():
                    nodes.append(FederatedGraphNode(id=ne.id, name=ne.canonical_name, type=ne.entity_type, source_project=ne.source_project, mention_count=ne.mention_count or 0, external_id=ne.external_id, hop=1))

        return FederatedSearchResponse(success=True, nodes=nodes, edges=edges, total=len(nodes), source_projects_found=list(set(n.source_project for n in nodes)))
    except Exception as e:
        logger.error("Federated search failed: %s", e, exc_info=True)
        return FederatedSearchResponse(success=False)


@router.post("/graph/cross-domain-link")
async def cross_domain_link(
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """觸發 CrossDomainLinker 執行四條跨域連結規則。"""
    from app.services.ai.domain.cross_domain_linker import CrossDomainLinker

    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis:
            acquired = await redis.set("federation:linker:lock", "1", nx=True, ex=300)
            if not acquired:
                return {"success": False, "error": "跨域連結正在執行中，請稍後再試"}
    except Exception:
        pass

    try:
        linker = CrossDomainLinker(db)
        report = await linker.run_all_rules()
        return {"success": True, "links_created": report.links_created, "links_skipped": report.links_skipped, "processing_ms": report.processing_ms, "details": [{"bridge_type": d.bridge_type, "source_name": d.source_name, "target_name": d.target_name, "relation_type": d.relation_type, "similarity": round(d.similarity, 3)} for d in report.details], "errors": report.errors}
    except Exception as e:
        logger.error("Cross-domain linking failed: %s", e, exc_info=True)
        return {"success": False, "error": "跨域連結處理失敗，請檢查伺服器日誌"}
    finally:
        try:
            from app.core.redis_client import get_redis
            redis = await get_redis()
            if redis:
                await redis.delete("federation:linker:lock")
        except Exception:
            pass


@router.post("/graph/federation-health")
async def federation_health(
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """回傳各來源專案的實體數量、最後更新時間、跨專案關係數。"""
    from app.services.ai.graph.graph_statistics_service import GraphStatisticsService

    try:
        svc = GraphStatisticsService(db)
        result = await svc.get_federation_health()
        return {"success": True, **result}
    except Exception as e:
        logger.error("federation_health 端點錯誤: %s", e, exc_info=True)
        return {"success": False, "projects": [], "cross_project_relations": 0, "total_projects": 0}


@router.post("/graph/embedding-backfill")
async def embedding_backfill(
    batch_size: int = 100,
    _current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """KG-3: 批次回填缺少 embedding 的實體向量。"""
    from app.services.ai.domain.cross_domain_contribution_service import CrossDomainContributionService

    try:
        svc = CrossDomainContributionService(db)
        result = await svc.backfill_embeddings(batch_size=min(batch_size, 500))
        await db.commit()
        return {"success": True, **result}
    except Exception as e:
        logger.error("embedding_backfill 端點錯誤: %s", e, exc_info=True)
        return {"success": False, "error": "Embedding 回填失敗"}


@router.post("/graph/cross-domain-path", response_model=CrossDomainPathResponse)
async def cross_domain_path(
    request: CrossDomainPathRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """KG-4: 跨專案最短路徑查詢。"""
    from app.services.ai.graph.graph_traversal_service import GraphTraversalService

    try:
        svc = GraphTraversalService(db)
        result = await svc.find_shortest_path(source_id=request.source_id, target_id=request.target_id, max_hops=request.max_hops)

        if not result or not result.get("found"):
            return CrossDomainPathResponse(success=True, found=False)

        path_nodes = [CrossDomainPathNode(id=n["id"], name=n["name"], type=n["type"], source_project=n.get("source_project", "ck-missive")) for n in result["path"]]
        projects = list(dict.fromkeys(n.source_project for n in path_nodes))

        return CrossDomainPathResponse(success=True, found=True, depth=result["depth"], path=path_nodes, relations=result.get("relations", []), source_projects_traversed=projects, is_cross_project=len(projects) > 1)
    except Exception as e:
        logger.error("cross_domain_path 端點錯誤: %s", e, exc_info=True)
        return CrossDomainPathResponse(success=False)

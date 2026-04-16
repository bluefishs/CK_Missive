"""
Digital Twin 代理端點 — 本地 Agent 推理 + 自省能力

流程:
  前端 → POST /ai/digital-twin/query/stream
       → 本地資料查詢 → AgentOrchestrator 合成 → SSE 回傳

Version: 4.0.0
Created: 2026-03-22
Updated: 2026-04-16 — v4.0 移除 OpenClaw/NemoClaw 依賴 (ADR-0014/0015)
"""

import hashlib
import json
import logging
import re
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth, get_async_db
from app.extended.models import User
from app.api.sse_utils import SSE_HEADERS
from app.schemas.ai.digital_twin import (
    DelegateAutoRequest,
    DigitalTwinQueryRequest,
    TaskApprovalRequest,
    TaskRejectionRequest,
)
from app.services.ai.domain.digital_twin_service import DigitalTwinService

logger = logging.getLogger(__name__)

router = APIRouter()

_JOB_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


def _validate_job_id(job_id: str) -> str:
    if not _JOB_ID_RE.match(job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id format")
    return job_id


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ── V-2.0: SSE Query Stream (本地優先) ─────────────────────

@router.post("/digital-twin/query/stream")
async def digital_twin_query_stream(
    request: DigitalTwinQueryRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
) -> StreamingResponse:
    """
    數位分身串流查詢 — 本地 Agent 推理

    v4.0: 直接使用本地 AgentOrchestrator（ADR-0014/0015 移除 OpenClaw/NemoClaw 依賴）。
    流程: 問題 → 本地資料查詢 → AgentOrchestrator 串流合成
    """

    async def _stream_local_agent():
        """
        v4.0 本地 Agent 架構:
        1. Missive 本地直查資料 API（無 LLM，純 DB）→ 原始 JSON
        2. AgentOrchestrator 串流合成
        """
        t0 = time.time()

        yield _sse_event({"type": "self_awareness", "identity": "數位分身"})
        yield _sse_event({"type": "role", "identity": "數位分身 (本地 Agent)", "context": "local"})

        # ── Step 1: 本地資料查詢（無 LLM，純 DB，快速） ──
        yield _sse_event({"type": "thinking", "step": "查詢本地資料庫...", "step_index": 0})

        data_context = await _gather_local_data(db, request.question)

        tool_names = [k for k, v in data_context.items() if v]
        if tool_names:
            yield _sse_event({
                "type": "tool_result", "tool": "local_data",
                "summary": f"查到 {', '.join(tool_names)} 共 {sum(len(v) if isinstance(v, list) else 1 for v in data_context.values() if v)} 筆",
                "count": len(tool_names), "step_index": 1,
            })

        # ── Step 2: 本地 Agent 串流合成 ──
        yield _sse_event({"type": "thinking", "step": "Agent 合成中...", "step_index": 2})

        from app.services.ai.agent.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator(db)
        async for event in orch.stream_agent_query(
            question=request.question, history=[], session_id=request.session_id or "",
        ):
            yield event
    return StreamingResponse(
        _stream_local_agent(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


# ── Helper: 本地資料查詢（無 LLM，純 DB） ─────────────────

async def _gather_local_data(db: AsyncSession, question: str) -> dict:
    """從問題中提取關鍵資訊，直接查 DB 取原始 JSON（無 LLM 參與）"""
    import re as _re
    data: dict = {}

    # 派工單號偵測
    m = _re.search(r'派工單[號]?\s*(\d{2,4})', question)
    if not m:
        m = _re.search(r'(?:^|\D)0*(\d{2,3})(?:\D|$)', question)
    if m and ('派工' in question or m.group(1).isdigit()):
        dispatch_no = m.group(1).zfill(3)
        roc_year = 115  # 當前年度
        search_term = f"{roc_year}年_派工單號{dispatch_no}"
        try:
            from app.repositories.taoyuan.dispatch_order_repository import DispatchOrderRepository
            repo = DispatchOrderRepository(db)
            items, total = await repo.filter_dispatch_orders(search=search_term, limit=5)
            if items:
                from app.services.taoyuan.dispatch_response_formatter import dispatch_to_response_dict
                data["dispatch"] = [dispatch_to_response_dict(item) for item in items]
        except Exception as e:
            logger.debug("Dispatch query failed: %s", e)

    # 派工進度
    if '進度' in question or '彙整' in question:
        try:
            from app.services.ai.domain.dispatch_progress_synthesizer import DispatchProgressSynthesizer
            synth = DispatchProgressSynthesizer(db)
            report = await synth.generate_report()
            data["progress"] = synth.to_dict(report)
        except Exception as e:
            logger.debug("Progress query failed: %s", e)

    # 公文搜尋
    if '公文' in question or '函' in question or not data:
        try:
            from app.repositories.document_repository import DocumentRepository
            doc_repo = DocumentRepository(db)
            keywords = [w for w in question.replace('的', ' ').split() if len(w) >= 2][:4]
            if keywords:
                docs, total = await doc_repo.filter_documents(
                    keyword=' '.join(keywords), skip=0, limit=5,
                )
                data["documents"] = [
                    {"id": d.id, "doc_number": d.doc_number, "subject": d.subject,
                     "doc_date": str(d.doc_date) if d.doc_date else None}
                    for d in docs
                ]
        except Exception as e:
            logger.debug("Document query failed: %s", e)

    return data


# ── E-6: Delegate Auto Proxy (跨域自動委派) ────────────────

@router.post("/digital-twin/delegate/auto")
async def delegate_auto_proxy(
    request: DelegateAutoRequest,
    current_user: User = Depends(require_auth()),
):
    """
    跨域自動委派 — Federation Client 依 intent 自動選擇最佳插件

    三層路由：領域關鍵字 → capabilities 匹配 → KG Hub 回退
    """
    from app.services.ai.federation.federation_client import get_federation_client

    client = get_federation_client()
    try:
        result = await client.delegate_auto(
            intent=request.intent,
            context=request.context,
            timeout=request.timeout,
        )
    except Exception as e:
        logger.error("delegate_auto proxy error: %s", e)
        return {"success": False, "error": str(e)}

    return {
        "success": result.get("success", False),
        "target_agent_id": result.get("target_agent_id"),
        "delegated": result.get("delegated"),
        "target_response": result.get("target_response"),
        "routing_reason": result.get("routing_reason"),
        "latency_ms": result.get("latency_ms"),
        "error": result.get("error"),
    }


# ── V-2.1: Task Approval Gate ──────────────────────────────

@router.post("/digital-twin/tasks/{job_id}/approve")
async def approve_task(
    job_id: str, request: TaskApprovalRequest,
    current_user: User = Depends(require_auth()),
):
    """代理審批 — 已停用 (ADR-0014/0015)"""
    return JSONResponse(status_code=410, content={"success": False, "error": "Task approval service retired (ADR-0014/0015)"})


@router.post("/digital-twin/tasks/{job_id}/reject")
async def reject_task(
    job_id: str, request: TaskRejectionRequest,
    current_user: User = Depends(require_auth()),
):
    """代理拒絕 — 已停用 (ADR-0014/0015)"""
    return JSONResponse(status_code=410, content={"success": False, "error": "Task rejection service retired (ADR-0014/0015)"})


@router.post("/digital-twin/tasks/{job_id}")
async def get_task_status(job_id: str, _current_user: User = Depends(require_auth())):
    """代理查詢任務狀態 — 已停用 (ADR-0014/0015)"""
    return JSONResponse(status_code=410, content={"success": False, "error": "Task status service retired (ADR-0014/0015)"})


# ── V-2.2: Live Activity Stream ────────────────────────────

@router.get("/digital-twin/live-activity/stream")
async def live_activity_stream(
    channel: str = "jobs", _current_user: User = Depends(require_auth()),
) -> StreamingResponse:
    """即時活動轉播 — 已停用 (ADR-0014/0015，原 OpenClaw EventRelay)"""

    async def _retired_stream():
        yield _sse_event({"type": "error", "error": "Live activity service retired (ADR-0014/0015)"})

    return StreamingResponse(_retired_stream(), media_type="text/event-stream", headers=SSE_HEADERS)


# ── V-3.1: Agent Topology (委派 Service) ───────────────────

@router.post("/digital-twin/agent-topology")
async def agent_topology(_current_user: User = Depends(require_auth())):
    """Agent 組織圖資料 — 委派至 DigitalTwinService"""
    return await DigitalTwinService.build_topology()


# ── V-3.3: QA Impact (委派 Service) ────────────────────────

@router.post("/digital-twin/qa-impact")
async def qa_impact_analysis(
    base_branch: str = "main", _current_user: User = Depends(require_auth()),
):
    """Diff-aware QA 影響分析 — 委派至 DigitalTwinService"""
    return await DigitalTwinService.analyze_qa_impact(base_branch)


# ── V-4.0: Dashboard Snapshot (新增) ───────────────────────

@router.post("/digital-twin/dashboard")
async def dashboard_snapshot(
    db: AsyncSession = Depends(get_async_db),
    _current_user: User = Depends(require_auth()),
):
    """聚合分身狀態快照 — profile + capability + daily + health"""
    return await DigitalTwinService.get_dashboard_snapshot(db)


# ── Health Check ───────────────────────────────────────────

@router.post("/digital-twin/health")
async def digital_twin_health(_current_user: User = Depends(require_auth())):
    """
    數位分身健康狀態 — 本地能力 + Gateway 可達性

    本地 Agent 永遠可用；Gateway 為可選增強。
    """
    # 本地能力（永遠回傳）
    local_roles = []
    try:
        from app.services.ai.agent.agent_roles import get_all_role_profiles
        local_roles = list(get_all_role_profiles().keys())
    except Exception:
        pass

    health = {
        "local_agent": True,
        "local_roles": local_roles,
        "local_roles_count": len(local_roles),
        "gateway_available": False,
        "gateway_systems": [],
    }

    # Gateway（可選）
    try:
        from app.services.ai.federation.federation_client import get_federation_client
        client = get_federation_client()
        systems = client.list_available_systems()
        health["gateway_available"] = len(systems) > 0
        health["gateway_systems"] = systems
    except Exception as e:
        health["gateway_error"] = str(e)

    return health


# ── Predictive Insights ──────────────────────────────────

@router.post("/digital-twin/insights")
async def get_predictive_insights(_current_user: User = Depends(require_auth())):
    """
    數位分身智能洞察 — 品質預測 + 工具降級預警 + 進化信號摘要

    基於 eval_history 線性迴歸預測品質趨勢，
    基於 tool_monitor 成功率識別即將降級的工具。
    """
    result = await DigitalTwinService.get_predictive_insights()
    return {"success": True, **result}


# ── V-5.0: Agent Introspection (自省) ─────────────────────

@router.post("/digital-twin/introspection")
async def agent_introspection(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    _current_user: User = Depends(require_auth()),
):
    """Agent 自省 — 統一的 self-model + capability + evolution 查詢 (ETag 支援)"""
    from app.services.ai.agent.agent_introspection import AgentIntrospectionService
    svc = AgentIntrospectionService(db)
    result = await svc.get_unified_dashboard()

    # Generate ETag from content hash
    content_json = json.dumps(result, default=str, sort_keys=True)
    etag = hashlib.md5(content_json.encode()).hexdigest()[:16]

    # Check If-None-Match — return 304 if unchanged
    if_none_match = request.headers.get("if-none-match")
    if if_none_match == etag:
        return Response(status_code=304)

    response = JSONResponse({"success": True, "data": result})
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "private, max-age=30"
    return response


@router.post("/digital-twin/introspection/profile")
async def agent_self_profile(
    db: AsyncSession = Depends(get_async_db),
    _current_user: User = Depends(require_auth()),
):
    """Agent 自我檔案"""
    from app.services.ai.agent.agent_introspection import AgentIntrospectionService
    svc = AgentIntrospectionService(db)
    result = await svc.get_self_profile()
    return JSONResponse({"success": True, "data": result})


@router.post("/digital-twin/introspection/capabilities")
async def agent_capability_scores(
    db: AsyncSession = Depends(get_async_db),
    _current_user: User = Depends(require_auth()),
):
    """Agent 各領域能力分數"""
    from app.services.ai.agent.agent_introspection import AgentIntrospectionService
    svc = AgentIntrospectionService(db)
    scores = await svc.get_capability_scores()
    sw = await svc.get_strengths_and_weaknesses()
    return JSONResponse({
        "success": True,
        "data": {
            "scores": scores,
            "strengths": sw["strengths"],
            "weaknesses": sw["weaknesses"],
        },
    })


# ── Shared Helper ──────────────────────────────────────────

async def _proxy_task_action(job_id: str, action: str, body: dict):
    """已停用 — OpenClaw/NemoClaw gateway 不再可用 (ADR-0014/0015)"""
    return JSONResponse(
        status_code=410,
        content={"success": False, "error": "Task proxy service retired (ADR-0014/0015)"},
    )

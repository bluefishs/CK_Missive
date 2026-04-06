"""
Digital Twin 代理端點 — OpenClaw 推理 + 本地 Agent fallback

流程:
  前端 → POST /ai/digital-twin/query/stream
       → FederationClient.query_external('openclaw') → SSE 回傳
       → fallback: AgentOrchestrator 本地推理

Version: 3.0.0
Created: 2026-03-22
Updated: 2026-03-27 — v3.0 OpenClaw 委派 + E-6 delegate_auto + self_awareness SSE
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
from app.services.ai.digital_twin_service import DigitalTwinService

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
    數位分身串流查詢 — 透過 OpenClaw (Claude Haiku) 回答

    v3.0: 委派至 OpenClaw 外部 AI，與左側本地 Agent 形成對比。
    流程: 問題 → FederationClient.query_external('openclaw') → SSE 回傳
    Fallback: OpenClaw 不可用時降級至本地 NemoClawAgent。
    """

    async def _stream_data_then_haiku():
        """
        v4.0 一層 LLM 架構:
        1. Missive 本地直查資料 API（無 LLM，純 DB）→ 原始 JSON
        2. 打包資料 + 問題 → OpenClaw Claude Haiku 一次合成
        3. Fallback: OpenClaw 不可用 → 本地 Agent
        """
        t0 = time.time()

        yield _sse_event({"type": "self_awareness", "identity": "數位分身"})
        yield _sse_event({"type": "role", "identity": "數位分身 (Claude Haiku)", "context": "openclaw"})

        # ── Step 1: 本地資料查詢（無 LLM，純 DB，快速） ──
        yield _sse_event({"type": "thinking", "step": "查詢本地資料庫...", "step_index": 0})

        data_context = await _gather_local_data(db, request.question)
        data_summary = json.dumps(data_context, ensure_ascii=False, default=str)[:4000]

        tool_names = [k for k, v in data_context.items() if v]
        if tool_names:
            yield _sse_event({
                "type": "tool_result", "tool": "local_data",
                "summary": f"查到 {', '.join(tool_names)} 共 {sum(len(v) if isinstance(v, list) else 1 for v in data_context.values() if v)} 筆",
                "count": len(tool_names), "step_index": 1,
            })

        # ── Step 2: 送給 OpenClaw Claude Haiku 合成（一次 LLM） ──
        yield _sse_event({"type": "thinking", "step": "Claude Haiku 合成中...", "step_index": 2})

        answer = ""
        model = "fallback-local"
        try:
            from app.services.ai.federation_client import get_federation_client
            client = get_federation_client()

            prompt = (
                f"根據以下資料回答問題。請用繁體中文，結構化回答。\n\n"
                f"問題: {request.question}\n\n"
                f"資料:\n{data_summary}\n\n"
                f"請直接回答，不要說「根據資料」。如果資料不足以回答，請說明缺少什麼。"
            )

            result = await client.query_external(
                system_id="openclaw",
                question=prompt,
                context={"source": "digital-twin-v4", "mode": "data-synthesis"},
                timeout=20.0,
            )
            answer = result.get("answer", result.get("response", ""))
            model = result.get("model", "claude-haiku")

        except Exception as e:
            logger.info("OpenClaw unavailable (%s), fallback synthesis", e)

        # Fallback: 無 OpenClaw 時用本地簡單合成
        if not answer:
            yield _sse_event({"type": "thinking", "step": "降級至本地 Agent...", "step_index": 3})
            from app.services.ai.agent_orchestrator import AgentOrchestrator
            orch = AgentOrchestrator(db)
            async for event in orch.stream_agent_query(
                question=request.question, history=[], session_id=request.session_id or "",
            ):
                yield event
            return

        yield _sse_event({"type": "thinking", "step": f"完成 ({model})", "step_index": 3})
        yield _sse_event({"type": "token", "token": answer})

        latency = int((time.time() - t0) * 1000)
        yield _sse_event({
            "type": "done",
            "latency_ms": latency,
            "model": model,
            "tools_used": tool_names,
            "iterations": 1,
        })

    return StreamingResponse(
        _stream_data_then_haiku(),
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
            from app.services.ai.dispatch_progress_synthesizer import DispatchProgressSynthesizer
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
    跨域自動委派 — NemoClaw Gateway 依 intent 自動選擇最佳插件

    三層路由：領域關鍵字 → capabilities 匹配 → KG Hub 回退
    """
    from app.services.ai.federation_client import get_federation_client

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
    """代理審批 — 轉發至 OpenClaw"""
    _validate_job_id(job_id)
    return await _proxy_task_action(job_id, "approve", {"approved_by": request.approved_by or current_user.username})


@router.post("/digital-twin/tasks/{job_id}/reject")
async def reject_task(
    job_id: str, request: TaskRejectionRequest,
    current_user: User = Depends(require_auth()),
):
    """代理拒絕 — 轉發至 OpenClaw"""
    _validate_job_id(job_id)
    return await _proxy_task_action(job_id, "reject", {
        "rejected_by": request.rejected_by or current_user.username, "reason": request.reason,
    })


@router.post("/digital-twin/tasks/{job_id}")
async def get_task_status(job_id: str, _current_user: User = Depends(require_auth())):
    """代理查詢任務狀態"""
    _validate_job_id(job_id)
    import os
    try:
        import httpx
    except ImportError:
        return JSONResponse(status_code=503, content={"success": False, "error": "後端缺少必要套件"})

    gateway_url = os.getenv("NEMOCLAW_GATEWAY_URL", "http://nemoclaw_tower:9000")
    token = os.getenv("MCP_SERVICE_TOKEN", "")
    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["X-Service-Token"] = token

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{gateway_url.rstrip('/')}/tasks/{job_id}", headers=headers)
            if resp.status_code >= 400:
                return JSONResponse(
                    status_code=resp.status_code,
                    content={"success": False, "error": f"上游服務回應 HTTP {resp.status_code}"},
                )
            return resp.json()
    except Exception as e:
        logger.error("Task status proxy error: %s", e)
        return JSONResponse(status_code=503, content={"success": False, "error": "任務狀態查詢失敗"})


# ── V-2.2: Live Activity Stream ────────────────────────────

@router.get("/digital-twin/live-activity/stream")
async def live_activity_stream(
    channel: str = "jobs", _current_user: User = Depends(require_auth()),
) -> StreamingResponse:
    """即時 Swarm 轉播 — 代理 OpenClaw EventRelay SSE"""
    import os
    allowed_channels = {"jobs", "agents"}
    if channel not in allowed_channels:
        channel = "jobs"

    gateway_url = os.getenv("NEMOCLAW_GATEWAY_URL", "http://nemoclaw_tower:9000")
    token = os.getenv("MCP_SERVICE_TOKEN", "")

    async def event_generator():
        try:
            import httpx
        except ImportError:
            yield _sse_event({"type": "error", "error": "httpx not installed"})
            return

        headers: dict[str, str] = {"Accept": "text/event-stream"}
        if token:
            headers["X-Service-Token"] = token

        try:
            timeout = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("GET", f"{gateway_url.rstrip('/')}/events",
                                         params={"channel": channel}, headers=headers) as resp:
                    if resp.status_code != 200:
                        yield _sse_event({"type": "error", "error": f"EventRelay HTTP {resp.status_code}"})
                        return
                    async for line in resp.aiter_lines():
                        if line.startswith("data: ") or line.startswith(":"):
                            yield f"{line}\n\n"
        except Exception as e:
            logger.warning("Live activity stream error: %s", e)
            yield _sse_event({"type": "error", "error": "即時轉播連線中斷"})

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=SSE_HEADERS)


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
        from app.services.ai.agent_roles import get_all_role_profiles
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
        from app.services.ai.federation_client import get_federation_client
        client = get_federation_client()
        systems = client.list_available_systems()
        health["gateway_available"] = any(s["id"] in ("openclaw", "nemoclaw") for s in systems)
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
    from app.services.ai.agent_introspection import AgentIntrospectionService
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
    from app.services.ai.agent_introspection import AgentIntrospectionService
    svc = AgentIntrospectionService(db)
    result = await svc.get_self_profile()
    return JSONResponse({"success": True, "data": result})


@router.post("/digital-twin/introspection/capabilities")
async def agent_capability_scores(
    db: AsyncSession = Depends(get_async_db),
    _current_user: User = Depends(require_auth()),
):
    """Agent 各領域能力分數"""
    from app.services.ai.agent_introspection import AgentIntrospectionService
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
    import os
    try:
        import httpx
    except ImportError:
        return JSONResponse(status_code=503, content={"success": False, "error": "後端缺少必要套件"})

    gateway_url = os.getenv("NEMOCLAW_GATEWAY_URL", "http://nemoclaw_tower:9000")
    token = os.getenv("MCP_SERVICE_TOKEN", "")
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["X-Service-Token"] = token

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{gateway_url.rstrip('/')}/tasks/{job_id}/{action}", json=body, headers=headers)
            if resp.status_code >= 400:
                return JSONResponse(
                    status_code=resp.status_code,
                    content={"success": False, "error": f"上游服務回應 HTTP {resp.status_code}"},
                )
            return resp.json()
    except Exception as e:
        logger.error("Task %s proxy error: %s", action, e)
        return JSONResponse(status_code=503, content={"success": False, "error": f"任務{action}操作失敗"})

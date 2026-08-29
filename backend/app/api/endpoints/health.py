"""
API 健康監控端點

v3.0 - 2026-02-24: 業務邏輯遷移至 SystemHealthService
"""
import time
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import Response
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.build_info import build_info
from app.db.database import get_async_db

from app.core.rate_limiter import limiter
from app.extended.models import User
from app.core.dependencies import require_admin, get_service
from app.services.system.health_service import (
    SystemHealthService,
    set_startup_time,
    get_uptime,
)

from app.core.health_probe import check_business_data_present

logger = logging.getLogger(__name__)
router = APIRouter()

# 向後相容: main.py 呼叫 set_startup_time()
__all__ = ["router", "set_startup_time", "get_uptime"]


@router.get("/health", summary="基本健康檢查")
@limiter.limit("60/minute")
async def basic_health_check(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
):
    """基本健康檢查端點 —— **公網探的就是這一支**。

    ⚠️ 2026-08-29：這支原本是**靜態 dict、完全不碰 DB**，postgres 掛掉
    它照樣回 `healthy`。而 L43（volume mount drift）的修法寫著
    「面向公網的 /health 必須包含業務量檢查」，那個防禦卻只做在
    `main.py` 的 `/health` 上 —— **公網走的是這一條**
    （`https://missive.cksurvey.tw/api/health`）⇒ 防禦在真正的路徑上不存在。

    它騙過的不只是監控：部署後用它驗「公網 200」也比看起來的弱。

    現在與 `/health` 共用同一份業務量檢查（`app/core/health_probe`）。
    ⚠️ **`/health/liveness` 維持不碰 DB** —— 那是故意的：
    「程序活著嗎」與「系統可用嗎」是兩個問題，不該合併。
    """
    db_status = "disconnected"
    try:
        if (await db.execute(text("SELECT 1"))).scalar() == 1:
            db_status = "connected"
    except Exception as e:
        logger.error("健康檢查 DB 失敗: %s", e)
        db_status = "error"

    business = {"ok": False, "reason": "db_unavailable"}
    if db_status == "connected":
        business = await check_business_data_present(db)

    healthy = db_status == "connected" and business.get("ok", False)
    if not healthy:
        response.status_code = 503
    return {
        "status": "healthy" if healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "service": "CK Missive API",
        "database": {"status": db_status},
        "business_data": business,
        # ⚠️ 2026-08-29：**明說這個綠燈涵蓋什麼、不涵蓋什麼。**
        #
        # 由 CK_AaaP 跨 session 提出：「錯的不是範圍窄，是**看不出來範圍有多窄**。」
        # 判定範圍窄是**刻意**的 —— 這支是公網探針讀的，若把 AI／KG／快取
        # 也納入判定，ollama 沒開就會讓整站被判死，那是**判不準的健康檢查，
        # 比沒有更糟**。但「範圍窄」與「沒說範圍」是兩件事：
        # 後者會讓讀的人以為綠燈涵蓋了它其實沒看的東西
        # （同本站 `/api/health/detailed` 那句「All systems operational」）。
        #
        # AI／KG／連線池的狀態在 `/api/health/detailed`（需 admin）。
        "verdict_inputs": {
            "deciding": ["database", "business_data"],
            "not_covered": ["ai_services", "kg_federation",
                            "connection_pool", "system_resources"],
            "note": ("綠燈只涵蓋 deciding 這兩項。not_covered 的項目失敗**不會**"
                     "讓本端點回 503 —— 那些要看 /api/health/detailed（需 admin）。"),
        },
    }


@router.get("/health/detailed", summary="詳細健康檢查")
@limiter.limit("60/minute")
async def detailed_health_check(
    request: Request,
    response: Response,
    service: SystemHealthService = Depends(get_service(SystemHealthService)),
    current_user: User = Depends(require_admin()),
) -> Dict[str, Any]:
    """詳細系統健康檢查"""
    start_time = time.time()
    # ⚠️ 2026-08-29：`"status"` **刻意不放在這個字典字面值裡**。
    #
    # 原本它是 `"status": "healthy"` 的寫死初始值，稍後才被覆寫 ——
    # 而覆寫只發生在檢查 1（database）與 2（tables）。
    # 檢查 3~6（連線池／系統資源／AI 服務／KG 聯邦）**記錄了卻不影響判定** ⇒
    # AI 服務整個 exception，頂層照樣說 healthy，而且訊息字面上寫著
    # **「All systems operational」**。
    #
    # ⚠️ 還有一個更隱蔽的：`if total_ms > 5000: status = "slow"` 會**覆蓋掉
    # `unhealthy`** —— DB 掛了又慢，結論變成「只是慢」，嚴重度被降級。
    #
    # 由 CK_AaaP 同日回報同型後查出（他們的 `all_healthy: True` 是寫死的
    # 初始值，刪掉覆寫那行就會靜靜回來）。⇒ **判定值不放初始值，最後一次算出來。**
    health_data: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "service": "CK Missive API",
        "build": build_info(),   # 硬編版本號無法回答「跑的是哪一份程式碼」
        "checks": {},
    }
    #: 致命（回 503）／降級（回 200 但說出來）分開記 ——
    #: AI 或 KG 聯邦掛掉不該讓公文系統被判死，但也不該說「一切正常」。
    fatal: list = []
    degraded: list = []

    # 1. 資料庫連線
    db_check = await service.check_database()
    health_data["checks"]["database"] = db_check
    if db_check["status"] != "healthy":
        fatal.append("database")

    # 2. 核心資料表
    tables_check = await service.check_core_tables()
    health_data["checks"]["tables"] = tables_check
    if any(t["status"] != "healthy" for t in tables_check.values()):
        fatal.append("tables")

    # 3. 連線池
    pool_check = service.check_connection_pool()
    health_data["checks"]["connection_pool"] = pool_check
    if pool_check.get("status") != "healthy":
        degraded.append("connection_pool")

    # 4. 系統資源
    res_check = service.check_system_resources()
    health_data["checks"]["system_resources"] = res_check
    if res_check.get("status") != "healthy":
        degraded.append("system_resources")

    # 5. AI 服務狀態
    try:
        from app.core.ai_connector import get_ai_connector
        ai_connector = get_ai_connector()
        ai_health = await ai_connector.check_health()
        health_data["checks"]["ai_services"] = ai_health
        # ⚠️ `check_health()` 回的是**逐 provider 的 `available` 布林**
        # （groq／nvidia_cloud／ollama／vllm_local），**沒有頂層 `status`**。
        # 我首版寫 `ai_health.get("status") not in (None, "healthy")` ——
        # 那個條件**永遠不會觸發**，等於這一項白加。實測 dict 的鍵才發現。
        #
        # 判準是**三層 fallback 全斷才算降級**：還有任一 provider 可用時，
        # 推論仍然做得出來（ADR：Groq → NVIDIA → Ollama → canned）。
        providers = {k: v for k, v in (ai_health or {}).items() if isinstance(v, dict)}
        if providers and not any(v.get("available") for v in providers.values()):
            degraded.append("ai_services")
            health_data["checks"]["ai_services"]["_verdict"] = (
                "所有推論 provider 皆不可用 —— AI 功能會落到 canned 回應")
    except Exception as e:
        health_data["checks"]["ai_services"] = {"status": "error", "error": str(e)[:200]}
        degraded.append("ai_services")

    # 6. KG Federation 指標
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        fed_check: Dict[str, Any] = {"status": "healthy"}
        if redis:
            # 各 source_project 最近 1 分鐘 contribute 次數
            for proj in ("ck-tunnel", "ck-lvrland"):
                key = f"federation:rate:{proj}"
                now = time.time()
                cnt = await redis.zcount(key, now - 60, "+inf")
                fed_check[f"{proj}_requests_1m"] = cnt
            # linker lock 狀態
            lock_val = await redis.get("federation:linker:lock")
            fed_check["linker_running"] = lock_val is not None
        else:
            fed_check["status"] = "redis_unavailable"
        health_data["checks"]["kg_federation"] = fed_check
        if fed_check.get("status") != "healthy":
            degraded.append("kg_federation")
    except Exception as e:
        health_data["checks"]["kg_federation"] = {"status": "error", "error": str(e)[:100]}
        degraded.append("kg_federation")

    # 7. 回應時間
    total_ms = (time.time() - start_time) * 1000
    health_data["total_response_time_ms"] = round(total_ms, 2)

    # 7. 整體狀態 —— **最後一次算出來**，沒有初始值可以殘留
    #
    # 順序即嚴重度：fatal > degraded > slow > healthy。
    # ⚠️ `slow` **不得覆蓋** fatal/degraded —— 原本 `if total_ms > 5000` 是第一個
    # 分支，會把 `unhealthy` 蓋成 `slow`（DB 掛了又慢＝「只是慢」）。
    if total_ms > 5000:
        degraded.append("response_time")

    if fatal:
        health_data["status"] = "unhealthy"
        health_data["message"] = f"核心依賴異常：{'、'.join(fatal)}"
        response.status_code = 503
    elif degraded:
        health_data["status"] = "degraded"
        health_data["message"] = (
            f"核心可用，但這些項目異常：{'、'.join(degraded)}"
            "（不影響公文與案件功能，故仍回 200）"
        )
    else:
        health_data["status"] = "healthy"
        health_data["message"] = "All systems operational"
    health_data["failing"] = {"fatal": fatal, "degraded": degraded}

    return health_data


@router.get("/health/metrics", summary="效能指標")
@limiter.limit("60/minute")
async def get_performance_metrics(
    request: Request,
    response: Response,
    service: SystemHealthService = Depends(get_service(SystemHealthService)),
    current_user: User = Depends(require_admin()),
):
    """獲取系統效能指標"""
    try:
        metrics = await service.run_performance_benchmarks()
        return {
            "timestamp": datetime.now().isoformat(),
            "database_metrics": metrics,
            "recommendations": service.get_performance_recommendations(metrics),
        }
    except Exception as e:
        logger.error(f"無法獲取效能指標: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="無法獲取效能指標，請稍後再試"
        )


@router.get("/health/readiness", summary="就緒狀態檢查")
@limiter.limit("60/minute")
async def readiness_check(
    request: Request,
    response: Response,
    service: SystemHealthService = Depends(get_service(SystemHealthService)),
):
    """檢查服務是否已準備好接受流量"""
    try:
        await service.check_readiness()
        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "message": "Service is ready to accept traffic",
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service is not ready to accept traffic",
        )


@router.get("/health/liveness", summary="存活狀態檢查")
@limiter.limit("60/minute")
async def liveness_check(request: Request, response: Response):
    """檢查服務是否存活"""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "message": "Service is alive",
    }


@router.get("/health/pool", summary="連接池狀態")
@limiter.limit("60/minute")
async def connection_pool_status(
    request: Request,
    response: Response,
    current_user: User = Depends(require_admin()),
):
    """取得資料庫連接池詳細狀態"""
    try:
        from app.core.db_monitor import DatabaseMonitor

        health = DatabaseMonitor.get_health_status()
        events = DatabaseMonitor.get_recent_events(limit=20)
        return {
            "timestamp": datetime.now().isoformat(),
            "health": health,
            "recent_events": events,
        }
    except Exception as e:
        logger.error(f"無法獲取連接池狀態: {e}", exc_info=True)
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "monitor_not_available",
            "message": "連接池監控未啟用或發生錯誤",
        }


@router.get("/health/tasks", summary="背景任務狀態")
@limiter.limit("60/minute")
async def background_tasks_status(
    request: Request,
    response: Response,
    current_user: User = Depends(require_admin()),
):
    """取得背景任務執行統計"""
    try:
        from app.core.background_tasks import BackgroundTaskManager

        stats = BackgroundTaskManager.get_stats()
        success_rate = 0.0
        if stats["total_tasks"] > 0:
            success_rate = stats["completed_tasks"] / stats["total_tasks"]
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy" if success_rate >= 0.9 else "degraded",
            "stats": stats,
            "success_rate": round(success_rate * 100, 2),
        }
    except Exception as e:
        logger.error(f"無法獲取背景任務狀態: {e}", exc_info=True)
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "unknown",
            "message": "無法獲取背景任務狀態",
        }


@router.get("/health/audit", summary="審計服務狀態")
@limiter.limit("60/minute")
async def audit_service_status(
    request: Request,
    response: Response,
    service: SystemHealthService = Depends(get_service(SystemHealthService)),
    current_user: User = Depends(require_admin()),
):
    """檢查審計服務運行狀態"""
    result = await service.check_audit_service()
    result["timestamp"] = datetime.now().isoformat()
    return result


@router.get("/health/backup", summary="備份系統狀態")
@limiter.limit("60/minute")
async def backup_health_check(
    request: Request,
    response: Response,
    current_user: User = Depends(require_admin()),
):
    """取得備份系統健康狀態（排程器、最近備份、異地同步）"""
    result = SystemHealthService.check_backup_status()
    result["timestamp"] = datetime.now().isoformat()
    return result


@router.get("/health/summary", summary="系統健康摘要")
@limiter.limit("60/minute")
async def health_summary(
    request: Request,
    response: Response,
    service: SystemHealthService = Depends(get_service(SystemHealthService)),
    current_user: User = Depends(require_admin()),
):
    """整合所有健康檢查的摘要報告"""
    return await service.build_summary()


@router.get("/health/scheduler", summary="排程器健康狀態")
@limiter.limit("60/minute")
async def scheduler_health(
    request: Request,
    response: Response,
    current_user: User = Depends(require_admin()),
):
    """取得排程器執行狀態 — 每個任務的最後執行時間、成功/失敗次數"""
    from app.core.scheduler import get_scheduler_status, SchedulerTracker

    scheduler_info = get_scheduler_status()
    tracker_records = SchedulerTracker.get_all()
    tracker_summary = SchedulerTracker.get_summary()

    # 合併排程器的 next_run 與追蹤器的 last_run
    jobs = []
    for job in scheduler_info.get("jobs", []):
        job_id = job["id"]
        track = tracker_records.get(job_id, {})
        jobs.append({
            **job,
            "last_run": track.get("last_run"),
            "last_status": track.get("last_status"),
            "last_duration_ms": track.get("last_duration_ms"),
            "last_error": track.get("last_error"),
            "success_count": track.get("success_count", 0),
            "failure_count": track.get("failure_count", 0),
        })

    return {
        "timestamp": datetime.now().isoformat(),
        "scheduler_running": scheduler_info["running"],
        **tracker_summary,
        "jobs": jobs,
    }


@router.get("/health/services", summary="推理服務健康狀態")
@limiter.limit("60/minute")
async def health_services(
    request: Request,
    response: Response,
):
    """
    推理服務即時健康探測

    週期性背景探測結果 + 手動觸發即時探測。
    回傳 Ollama / vLLM / Redis / PostgreSQL 連線狀態。
    """
    from app.core.service_health_probe import get_health_probe
    probe = get_health_probe()
    result = await probe.probe_once()
    all_healthy = all(s["healthy"] for s in result.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": result,
    }

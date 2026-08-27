# -*- coding: utf-8 -*-
"""
任務排程器

提供定時任務排程功能，用於：
- 處理待發送提醒
- 清理過期事件
- 其他定時任務

v2.0.0 - 2026-04-08: 新增排程執行追蹤 (SchedulerTracker)
"""
import logging
import os
import time
from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager
from functools import wraps

import asyncio as _asyncio
import subprocess as _subprocess
from pathlib import Path as _Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.core.paths import LOGS_DIR as _LOGS_DIR_DEFAULT  # 2026-08-19 規約 E：不自算路徑

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prometheus expose (v6.12 進化 #2 補完 2026-05-30): cron silent dormant 偵測
# ---------------------------------------------------------------------------
try:
    from prometheus_client import Gauge, Counter, REGISTRY

    def _get_or_create_gauge(name: str, doc: str, labels: list[str]) -> Gauge:
        """避免 module 重複載入時 Duplicated time series 錯誤"""
        try:
            return Gauge(name, doc, labels)
        except ValueError:
            # 已存在 — 從 REGISTRY 撈
            for collector in list(REGISTRY._collector_to_names.keys()):  # type: ignore[attr-defined]
                if getattr(collector, "_name", None) == name:
                    return collector  # type: ignore[return-value]
            raise

    def _get_or_create_counter(name: str, doc: str, labels: list[str]) -> Counter:
        try:
            return Counter(name, doc, labels)
        except ValueError:
            for collector in list(REGISTRY._collector_to_names.keys()):  # type: ignore[attr-defined]
                if getattr(collector, "_name", None) == name:
                    return collector  # type: ignore[return-value]
            raise

    SCHED_LAST_RUN_AGE_SECONDS = _get_or_create_gauge(
        "scheduler_job_last_run_age_seconds",
        "Seconds since each scheduled job last completed (cron silent dormant 偵測)",
        ["job_id"],
    )
    SCHED_SUCCESS_TOTAL = _get_or_create_counter(
        "scheduler_job_success_total",
        "Cumulative success count per scheduled job",
        ["job_id"],
    )
    SCHED_FAILURE_TOTAL = _get_or_create_counter(
        "scheduler_job_failure_total",
        "Cumulative failure count per scheduled job",
        ["job_id"],
    )
    _PROM_ENABLED = True
except Exception as _e:  # pragma: no cover
    logger.warning("prometheus_client unavailable for scheduler: %s", _e)
    _PROM_ENABLED = False


async def _run_script_async(
    cmd: list[str],
    cwd: str,
    timeout: int = 120,
    job_name: str = "script",
) -> tuple[int, str, str]:
    """非阻塞執行外部腳本（不凍結 event loop）。"""
    try:
        proc = await _asyncio.create_subprocess_exec(
            *cmd, cwd=cwd,
            stdout=_asyncio.subprocess.PIPE,
            stderr=_asyncio.subprocess.PIPE,
        )
        stdout, stderr = await _asyncio.wait_for(proc.communicate(), timeout=timeout)
        return (
            proc.returncode or 0,
            (stdout or b"").decode("utf-8", errors="replace").strip(),
            (stderr or b"").decode("utf-8", errors="replace").strip(),
        )
    except _asyncio.TimeoutError:
        proc.kill()  # type: ignore[union-attr]
        logger.warning("%s timeout (>%ds), killed", job_name, timeout)
        return (-1, "", "timeout")
    except Exception as e:
        logger.error("%s subprocess error: %s", job_name, e)
        return (-1, "", str(e))


# 全域排程器實例
_scheduler: Optional[AsyncIOScheduler] = None


# ---------------------------------------------------------------------------
# 排程執行追蹤器
# ---------------------------------------------------------------------------

class SchedulerTracker:
    """記錄每個排程任務的最後執行時間、持續時間、成功/失敗次數

    v6.13 (2026-05-31) 對齊 owner「真活大於規劃 + 紀錄變文件化」訴求:
    - in-memory tracker (既有)
    - prometheus metric (既有 v6.12)
    - **jsonl event log** (本批新增) — 寫 /app/logs/cron_events.jsonl
      事件追溯依據 + 跨 backend restart 持久化
    """

    _records: Dict[str, Dict[str, Any]] = {}
    # 2026-08-19：原本 fallback 寫死 "/app/logs"（容器內路徑）。在**本機**執行時
    # Windows 會把它解讀成「當前磁碟根目錄下的 app\logs」→ 實際產生了 D:pp\logs，
    # cron 事件因此寫到容器外、容器裡反而看不到。改用 paths.LOGS_DIR：
    # 它由 PROJECT_ROOT 推導（容器內 CK_PROJECT_ROOT=/app、本機為專案根），兩邊都對。
    _EVENTS_LOG = _Path(os.getenv("CK_LOGS_DIR") or _LOGS_DIR_DEFAULT) / "cron_events.jsonl"

    @classmethod
    def _append_event(cls, job_id: str, status: str, duration_ms: Optional[float],
                      error: Optional[str] = None,
                      detail: Optional[Dict[str, Any]] = None) -> None:
        """v6.13: 寫 jsonl event log — fire-and-forget 不阻斷主流程

        2026-07-15: 加 detail — 讓 job 附業務產出（如 embedded 計數/reason），
        破解「status=success/duration 綠燈但實際沒做事」silent success 盲點
        （kg_embedding_backfill 04:30 冷啟動空轉現形）。
        """
        import json as _json
        try:
            cls._EVENTS_LOG.parent.mkdir(parents=True, exist_ok=True)
            event = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "job_id": job_id,
                "status": status,
                "duration_ms": duration_ms,
            }
            if error:
                event["error"] = error[:200]
            if detail:
                # 只納入 JSON-safe 純量鍵值，避免把 ORM/大物件寫進 log
                event["detail"] = {
                    k: v for k, v in detail.items()
                    if isinstance(v, (str, int, float, bool)) or v is None
                }
            with cls._EVENTS_LOG.open("a", encoding="utf-8") as f:
                f.write(_json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass  # event log silent fail 不阻斷

    @classmethod
    def record_start(cls, job_id: str):
        if job_id not in cls._records:
            cls._records[job_id] = {
                "success_count": 0,
                "failure_count": 0,
                "last_status": None,
                "last_run": None,
                "last_duration_ms": None,
                "last_error": None,
            }
        cls._records[job_id]["_start_time"] = time.time()

    @classmethod
    def record_success(cls, job_id: str, detail: Optional[Dict[str, Any]] = None):
        rec = cls._records.get(job_id, {})
        start = rec.pop("_start_time", None)
        duration = round((time.time() - start) * 1000, 1) if start else None
        now_ts = time.time()
        rec.update({
            "success_count": rec.get("success_count", 0) + 1,
            "last_status": "success",
            "last_run": datetime.now().isoformat(),
            "last_run_ts": now_ts,
            "last_duration_ms": duration,
            "last_error": None,
            "last_detail": detail if detail else None,
        })
        cls._records[job_id] = rec
        cls._append_event(job_id, "success", duration, detail=detail)  # v6.13 jsonl log
        if _PROM_ENABLED:
            try:
                SCHED_LAST_RUN_AGE_SECONDS.labels(job_id=job_id).set(0)
                SCHED_SUCCESS_TOTAL.labels(job_id=job_id).inc()
            except Exception:
                pass

    @classmethod
    def record_failure(cls, job_id: str, error: str):
        rec = cls._records.get(job_id, {})
        start = rec.pop("_start_time", None)
        duration = round((time.time() - start) * 1000, 1) if start else None
        now_ts = time.time()
        rec.update({
            "failure_count": rec.get("failure_count", 0) + 1,
            "last_status": "failure",
            "last_run": datetime.now().isoformat(),
            "last_run_ts": now_ts,
            "last_duration_ms": duration,
            "last_error": error[:200],
        })
        cls._records[job_id] = rec
        cls._append_event(job_id, "failure", duration, error)  # v6.13 jsonl log
        if _PROM_ENABLED:
            try:
                SCHED_LAST_RUN_AGE_SECONDS.labels(job_id=job_id).set(0)
                SCHED_FAILURE_TOTAL.labels(job_id=job_id).inc()
            except Exception:
                pass

    @classmethod
    def refresh_age_gauges(cls) -> None:
        """每次 /metrics scrape 時更新 age (避免 stuck 0)"""
        if not _PROM_ENABLED:
            return
        now_ts = time.time()
        for jid, rec in cls._records.items():
            last_ts = rec.get("last_run_ts")
            if last_ts:
                try:
                    SCHED_LAST_RUN_AGE_SECONDS.labels(job_id=jid).set(now_ts - last_ts)
                except Exception:
                    pass

    @classmethod
    def get_all(cls) -> Dict[str, Dict[str, Any]]:
        return {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
                for k, v in cls._records.items()}

    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        records = cls.get_all()
        total = len(records)
        healthy = sum(1 for r in records.values() if r.get("last_status") == "success")
        failed = sum(1 for r in records.values() if r.get("last_status") == "failure")
        never_run = sum(1 for r in records.values() if r.get("last_run") is None)
        return {
            "total_jobs": total,
            "healthy": healthy,
            "failed": failed,
            "never_run": never_run,
            "status": "healthy" if failed == 0 else ("degraded" if failed < 3 else "unhealthy"),
        }


def tracked_job(job_id: str):
    """裝飾器：自動追蹤排程任務的執行狀態，失敗時觸發 Telegram 告警"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            SchedulerTracker.record_start(job_id)
            try:
                result = await func(*args, **kwargs)
                # 2026-07-15: job 若回 dict → 當作業務產出 detail 寫入 cron_events
                # （embedded/reason 等），讓 silent success 現形。非 dict → 行為不變。
                detail = result if isinstance(result, dict) else None
                SchedulerTracker.record_success(job_id, detail=detail)
                return result
            except Exception as e:
                SchedulerTracker.record_failure(job_id, str(e))
                # 失敗告警 (fire-and-forget)
                try:
                    from app.core.scheduler_alert import get_alert_manager
                    mgr = get_alert_manager()
                    rec = SchedulerTracker._records.get(job_id, {})
                    failure_count = rec.get("failure_count", 1)
                    if mgr.should_alert(job_id, failure_count):
                        import asyncio
                        asyncio.create_task(
                            mgr.send_failure_alert(job_id, str(e), failure_count)
                        )
                except Exception:
                    pass  # 告警失敗不影響主流程
                raise
        return wrapper
    return decorator


def get_scheduler() -> AsyncIOScheduler:
    """取得排程器實例"""
    global _scheduler
    if _scheduler is None:
        # 2026-08-16：全域 job_defaults —— APScheduler 的 misfire_grace_time
        # **預設是 1 秒**，也就是排定時刻起算超過 1 秒沒被排到就整個跳過。
        #
        # 為什麼一直沒發現：5 分鐘週期的 job 一天有 288 次機會，
        # 偶爾錯過一次看不出來；**每小時的 job 一次沒排到就整整少一小時**，
        # 而事件迴圈在那一秒剛好在忙是很常見的事。
        # 實測 `ezbid_cache_refresh`（每小時）最後執行停在 01:26，
        # 14:15 那次排定時刻完全沒有 Running job 紀錄 —— 被靜靜 misfire 掉。
        #
        # 這是 L72 的同一個根因（當時修的是 cleanup_events/security_scan/
        # fitness_daily 三支「02:00 壅塞 skip 從不執行」），但當時**只修了那三支**，
        # 而全檔 52 個 add_job 有 **38 個**沒有這個參數。
        # 設在 job_defaults 而不是逐一補：一個地方，不會有第 39 個漏網的。
        #
        # 1 小時：足以吸收事件迴圈壅塞，又不會讓一個停機半天的 job
        # 在恢復後補跑一堆過期任務（coalesce 另外處理重複觸發）。
        _scheduler = AsyncIOScheduler(
            job_defaults={"misfire_grace_time": 3600, "coalesce": True}
        )
    return _scheduler


@tracked_job("process_reminders")
async def process_pending_reminders_job():
    """處理待發送提醒的排程任務"""
    from app.db.database import async_session_maker
    from app.services.calendar.reminder_service import ReminderService

    logger.info("開始執行提醒處理排程任務")

    try:
        async with async_session_maker() as db:
            service = ReminderService(db)
            stats = await service.process_pending_reminders()
            logger.info(f"提醒處理完成: 總數={stats['total']}, 成功={stats['sent']}, 失敗={stats['failed']}")
            # 2026-08-14：補回 detail。它一直有 {total, sent, failed, retries}，
            # 只是沒回傳 —— 於是「發了 30 則」與「一則都沒發」在 cron_events 裡
            # 長得一模一樣。total=0 是常態（沒有到期提醒），failed>0 才是訊號。
            return {
                "total": stats.get("total", 0), "sent": stats.get("sent", 0),
                "failed": stats.get("failed", 0), "retries": stats.get("retries", 0),
                "reason": "ok",
            }
    except Exception as e:
        logger.error(f"提醒處理排程任務失敗: {e}", exc_info=True)
        raise


@tracked_job("cleanup_events")
async def cleanup_expired_events_job():
    """清理過期事件的排程任務"""
    from app.db.database import async_session_maker
    from datetime import datetime, timedelta

    logger.info("開始執行過期事件清理排程任務")

    try:
        async with async_session_maker() as db:
            # ⚠️ 2026-08-14 發現它什麼都沒做；2026-08-15 查證後改為做真正需要做的事。
            #
            # 量測：DB 裡**沒有累積的垃圾** —— 唯二超過 5000 列的表
            # （canonical_entities 49k、entity_relationships 10k）都是業務資料。
            # 所以「清理過期事件」要清的東西並不存在，這支不是「還沒實作」，
            # 是它的前提不成立。
            #
            # 而真正無界成長的是**稽核軌跡自己**：cron_events.jsonl
            # 7.3MB / 71,298 筆 / 最舊 2026-05-31，每天約 +1000 筆。
            # 那份軌跡是今天多個機制的依據（producer watchdog、
            # cron_silent_dormant_check 的持久紀錄退路、逐步結果歷史），
            # 所以保留期取 **90 天** —— 遠大於所有既有門檻（最大 336h＝14 天），
            # 也遠大於有效性報告需要的 30 次執行。
            #
            # 只在超過門檻時才重寫，避免每天重寫 7MB 檔案。
            # 修剪筆數一律回報：**靜靜刪掉稽核軌跡是最不該沉默的一件事**。
            # 舊註解保留於此供對照：
            #
            # 它每天被排程叫醒、log 印「執行完成」、cron_events 記 success，
            # 至今已 64 次以上 —— 而清理邏輯從來沒有被寫進來（原註解就寫著
            # 「此處可添加清理邏輯，目前僅記錄日誌」）。
            #
            # 這比「壞掉的 job」更難發現：壞掉會留下錯誤，而它一切正常，
            # 只是不做事。整整一輪 producer 契約盤點都沒抓到它，因為契約問的是
            # 「有沒有留下產出」，而它被歸在「純清理無產出」的豁免名單裡 ——
            # 那個豁免的理由是我 2026-08-13 寫的，我當時假設了它會清東西。
            #
            # 不擅自實作清理邏輯（要刪什麼、保留多久屬 owner 決定，且刪除不可逆），
            # 但**必須停止假裝它在工作**：reason 明說是 not_implemented，
            # 讓它在 cron_events 與 producer 報告裡都看得見。
            from app.core.paths import LOGS_DIR
            RETAIN_DAYS = 90
            MAX_BYTES = 20 * 1024 * 1024   # 超過才修剪，避免每天重寫大檔
            events = LOGS_DIR / "cron_events.jsonl"
            if not events.exists():
                return {"trimmed": 0, "reason": "no_events_file"}
            size = events.stat().st_size
            if size < MAX_BYTES:
                return {"trimmed": 0, "size_mb": round(size / 1048576, 1),
                        "reason": "under_threshold"}
            cutoff = (datetime.now() - timedelta(days=RETAIN_DAYS)).isoformat()
            kept, dropped = [], 0
            with events.open(encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    # 解析失敗的行一律保留 —— 看不懂不等於可以丟
                    ts = line[8:27] if line.startswith('{"ts": "') else ""
                    if ts and ts < cutoff:
                        dropped += 1
                    else:
                        kept.append(line)
            tmp = events.with_suffix(".jsonl.tmp")
            tmp.write_text("".join(kept), encoding="utf-8")
            tmp.replace(events)   # 原子替換，避免修剪途中被讀到半個檔
            logger.info("cron_events 修剪: 移除 %d 筆（保留 %d 天）", dropped, RETAIN_DAYS)
            return {"trimmed": dropped, "retained": len(kept),
                    "size_mb": round(size / 1048576, 1), "reason": "ok"}
    except Exception as e:
        logger.error(f"過期事件清理排程任務失敗: {e}", exc_info=True)
        raise


@tracked_job("einvoice_sync")
async def einvoice_sync_job():
    """電子發票自動同步排程任務 — 每晚從財政部下載公司統編發票"""
    from app.db.database import async_session_maker
    from app.services.einvoice.einvoice_sync_service import EInvoiceSyncService

    logger.info("開始執行電子發票自動同步排程任務")

    try:
        async with async_session_maker() as db:
            service = EInvoiceSyncService(db)
            stats = await service.sync_invoices()
            logger.info(
                f"電子發票同步完成: 取得={stats.get('total_fetched', 0)}, "
                f"新增={stats.get('new_imported', 0)}, "
                f"重複={stats.get('skipped_duplicate', 0)}"
            )
    except Exception as e:
        logger.error(f"電子發票同步排程任務失敗: {e}", exc_info=True)


@tracked_job("erp_graph_ingest")
async def erp_graph_ingest_job():
    """ERP 圖譜入圖 — 掃描 ERP 表 → canonical_entities + case_code 橋接"""
    from app.db.database import async_session_maker

    logger.info("開始執行 ERP 圖譜入圖")
    try:
        async with async_session_maker() as db:
            from app.services.ai.graph.erp_graph_ingest import ErpGraphIngestService
            service = ErpGraphIngestService(db)
            stats = await service.ingest_all()
            logger.info(
                "ERP 圖譜入圖完成: entities=%d, relations=%d, bridges=%d, %dms",
                stats.get("entities", 0), stats.get("relations", 0),
                stats.get("cross_graph_bridges", 0), stats.get("duration_ms", 0),
            )
    except Exception as e:
        logger.error("ERP 圖譜入圖失敗: %s", e, exc_info=True)


@tracked_job("code_graph_incremental")
async def code_graph_incremental_job():
    """Code Graph 每日全量重建 — 掃描 Python AST + DB schema 重建圖譜實體與關係。

    2026-07-20 治本（重大靜默 bug）：原 incremental=True 每次跑 `_recreate_relations`
    無條件全刪 code_graph 關係、只重插「本次變更檔」的關係 → 未變更檔跳過 → 關係圖
    每日塌成僅 FK（9669→85）；僅週日 reconcile 才還原 → 一週 6 天圖譜殘缺＝圖譜低價值隱因。
    改 incremental=False（全量、6s 可接受）＋傳 db_url（建 db_table + model→db_table maps_to
    橋 + FK）→ 圖譜每日完整。週日 reconcile 續作 orphan mark-and-sweep（互補）。
    （容器無 frontend/src → 前端 ts_ 關係本就不落地，非本次變更。）
    """
    from app.db.database import async_session_maker
    from app.core.config import settings

    logger.info("開始執行 Code Graph 每日全量重建")

    try:
        async with async_session_maker() as db:
            from app.services.ai.graph.code_graph_service import CodeGraphIngestionService
            service = CodeGraphIngestionService(db)
            from app.core.paths import BACKEND_DIR, FRONTEND_DIR  # v6.10 P1-E SSOT
            backend_dir = BACKEND_DIR / "app"
            frontend_dir = FRONTEND_DIR / "src"

            stats = await service.ingest(
                backend_app_dir=backend_dir,
                db_url=settings.DATABASE_URL,  # 啟用 db_table + maps_to 橋 + FK（SchemaReflectorService SSOT）
                incremental=False,             # 治本：全量重建，防每日洗關係圖
                frontend_src_dir=frontend_dir if frontend_dir.exists() else None,
            )
            await db.commit()
            logger.info(
                f"Code Graph 每日全量重建完成: "
                f"modules={stats.get('modules', 0)}, "
                f"classes={stats.get('classes', 0)}, "
                f"functions={stats.get('functions', 0)}, "
                f"tables={stats.get('tables', 0)}, "
                f"relations={stats.get('relations', 0)}"
            )
    except Exception as e:
        logger.error(f"Code Graph 每日全量重建失敗: {e}", exc_info=True)


@tracked_job("code_graph_reconcile")
async def code_graph_reconcile_job():
    """Code Graph 全掃 reconcile（mark-and-sweep）— 每週清 stale orphan，防圖譜污染。

    根治「incremental ingest 只增不刪 → 累積 Wave 搬檔舊路徑 orphan」（2026-07-17 立法）。
    流程：記 sweep_start → 全掃 ingest（stamp 現存 symbol last_seen_at、保留 embedding）
         → sweep 掉 last_seen_at < sweep_start 的【Python】entity（＝本輪未見＝stale）。
    安全：①僅 Python 型（backend 容器無 frontend 源，ts_* 不 stamp 不能 sweep）
         ②安全閘 stamp < 3500 則 ABORT（防全掃部分失敗誤刪存活）。
    詳見 docs/architecture/HETEROGENEOUS_WORK_REGISTRY.md、scripts/sync/code_graph_reconcile.py。
    """
    from app.db.database import async_session_maker
    from app.services.ai.graph.code_graph_service import CodeGraphIngestionService
    from app.core.paths import BACKEND_DIR, FRONTEND_DIR
    from app.core.config import settings
    from sqlalchemy import text

    PY_TYPES = "('py_function','py_class','py_module','api_endpoint','service','repository','schema')"
    MIN_STAMPED = 3500

    logger.info("開始執行 Code Graph 全掃 reconcile")
    try:
        async with async_session_maker() as db:
            sweep_start = await db.scalar(text("SELECT now()::timestamp without time zone"))
            before = await db.scalar(text("SELECT COUNT(*) FROM canonical_entities WHERE graph_domain='code'"))
            service = CodeGraphIngestionService(db)
            frontend_dir = FRONTEND_DIR / "src"
            await service.ingest(
                backend_app_dir=BACKEND_DIR / "app",
                db_url=settings.DATABASE_URL,  # 建 db_table + maps_to 橋 + FK（2026-07-20）
                incremental=False,
                frontend_src_dir=frontend_dir if frontend_dir.exists() else None,
            )
            await db.commit()
            stamped = await db.scalar(text(
                f"SELECT COUNT(*) FROM canonical_entities WHERE graph_domain='code' "
                f"AND entity_type IN {PY_TYPES} AND last_seen_at >= :ts"), {"ts": sweep_start})
            if stamped < MIN_STAMPED:
                logger.error(
                    f"Code Graph reconcile ABORT：Python stamp {stamped} < {MIN_STAMPED}"
                    f"（全掃疑部分失敗）→ 不 sweep，避免誤刪存活")
                return {"aborted": True, "stamped": stamped, "swept": 0}
            result = await db.execute(text(
                f"DELETE FROM canonical_entities WHERE graph_domain='code' AND entity_type IN {PY_TYPES} "
                f"AND (last_seen_at < :ts OR last_seen_at IS NULL)"), {"ts": sweep_start})
            await db.commit()
            after = await db.scalar(text("SELECT COUNT(*) FROM canonical_entities WHERE graph_domain='code'"))
            logger.info(f"Code Graph reconcile 完成：{before}→{after}（stamp {stamped} live、sweep {result.rowcount} stale）")
            return {"before": before, "after": after, "stamped": stamped, "swept": result.rowcount}
    except Exception as e:
        logger.error(f"Code Graph 全掃 reconcile 失敗: {e}", exc_info=True)
        return {"error": str(e)}


@tracked_job("code_dup_triage")
async def code_dup_triage_job():
    """程式圖譜語意異質同工「自動判定」job（每月）— 閉合自我優化迴圈。

    回應 owner「圖譜能否真自我檢核與成長」：把「發現→判定→提報」自動化。
    流程（仿 crystallizer 的自動偵測+自動判定+owner gate）：
    1. pgvector 撈跨模組語意近重複的鏡像模組對（sim>0.95、共享>=4）
    2. 排除已知合理拆分（LEGIT_SPLIT_WHITELIST）
    3. 對每個新候選呼叫 LLM 判定 TRUE_DUPLICATE vs LEGIT_SPLIT + 信心 + 理由
    4. verdict 寫 /app/logs/code_dup_triage.jsonl（持久、host 可見）；
       TRUE_DUPLICATE 額外 LOUD log 供 owner 收斂（收斂動作仍人審 gate）
    詳見 docs/architecture/HETEROGENEOUS_WORK_REGISTRY.md §程式圖譜自我優化。
    """
    from app.db.database import async_session_maker
    from app.core.ai_connector import get_ai_connector
    from sqlalchemy import text
    import json as _json

    # 已 triage 判定為合理拆分的 module-pair（與 code_semantic_duplication_audit 同步）
    LEGIT = {
        ("app.api.endpoints.ai.graph_admin", "app.api.endpoints.ai.graph_admin_code"),
        ("app.api.endpoints.erp.expenses", "app.api.endpoints.erp.expenses_io"),
        ("app.api.endpoints.erp.expenses", "app.api.endpoints.erp.operational"),
    }
    MIN_SHARED = 4

    logger.info("開始執行 程式圖譜語意異質同工自動判定")
    try:
        async with async_session_maker() as db:
            rows = await db.execute(text("""
                WITH ce AS (
                    SELECT id, split_part(canonical_name,'::',1) AS mod,
                           split_part(canonical_name,'::',2) AS sym, embedding
                    FROM canonical_entities
                    WHERE graph_domain='code'
                      AND entity_type IN ('api_endpoint','service')
                      AND embedding IS NOT NULL
                )
                SELECT a.mod mod_a, b.mod mod_b, a.sym sym_a, b.sym sym_b,
                       (1-(a.embedding <=> b.embedding)) sim
                FROM ce a JOIN ce b ON a.id < b.id AND a.mod <> b.mod
                  AND (1-(a.embedding <=> b.embedding)) > 0.95
            """))
            pairs = {}
            for r in rows:
                key = tuple(sorted((r.mod_a, r.mod_b)))
                d = pairs.setdefault(key, {"shared": 0, "examples": []})
                d["shared"] += 1
                if len(d["examples"]) < 3:
                    d["examples"].append(f"{r.sym_a}~{r.sym_b}({r.sim:.2f})")
            candidates = [(k, v) for k, v in pairs.items() if v["shared"] >= MIN_SHARED and k not in LEGIT]

            conn = get_ai_connector()
            verdicts, true_dups = [], 0
            for (a, b), v in candidates:
                prompt = (
                    f"判定兩模組是「真異質同工(該收斂)」還是「合理領域拆分(保留)」。\n"
                    f"模組A: {a}\n模組B: {b}\n共享語意近重複函式 {v['shared']} 個，例：{'; '.join(v['examples'])}\n"
                    f'只回 JSON: {{"verdict":"TRUE_DUPLICATE 或 LEGIT_SPLIT","confidence":0-1,"reason":"一句話"}}'
                )
                try:
                    ans = await conn.chat_completion(
                        messages=[{"role": "user", "content": prompt}],
                        task_type="planning", temperature=0.1, max_tokens=200)
                    rec = {"pair": [a, b], "shared": v["shared"], "llm": ans.strip()}
                    if "TRUE_DUPLICATE" in ans:
                        true_dups += 1
                        logger.warning(f"[CODE_DUP] 疑真異質同工待 owner 收斂: {a} ⇄ {b}（{v['shared']} 共享）→ {ans.strip()[:120]}")
                    verdicts.append(rec)
                except Exception as le:
                    verdicts.append({"pair": [a, b], "error": str(le)})

            # 寫持久 log
            try:
                # 2026-08-19：這一行原本完全寫死 "/app/logs"，連 CK_LOGS_DIR 都不讀 ——
                # 也就是說無論怎麼設環境變數，本機執行時都會寫進 D:pp\logs。
                _triage = _Path(os.getenv("CK_LOGS_DIR") or _LOGS_DIR_DEFAULT) / "code_dup_triage.jsonl"
                _triage.parent.mkdir(parents=True, exist_ok=True)
                with open(_triage, "a", encoding="utf-8") as f:
                    for rec in verdicts:
                        f.write(_json.dumps(rec, ensure_ascii=False) + "\n")
            except Exception as we:
                logger.error(f"[CODE_DUP] 寫 triage log 失敗: {we}")

            logger.info(f"程式圖譜語意判定完成：候選 {len(candidates)}、疑真重複 {true_dups}（詳見 logs/code_dup_triage.jsonl）")
            return {"candidates": len(candidates), "true_duplicates": true_dups}
    except Exception as e:
        logger.error(f"程式圖譜語意異質同工自動判定失敗: {e}", exc_info=True)
        return {"error": str(e)}


@tracked_job("db_graph_refresh")
async def db_schema_refresh_job():
    """DB Schema 快照更新 — 反射 PostgreSQL information_schema 並重建快取"""

    logger.info("開始執行 DB Schema 快照更新")

    try:
        from app.services.ai.graph.schema_reflector import SchemaReflectorService
        # 清除快取，強制重新反射
        SchemaReflectorService._cache = None
        SchemaReflectorService._cache_time = 0
        schema = await SchemaReflectorService.get_full_schema_async()
        tables = len(schema.get("tables", []))
        logger.info(f"DB Schema 快照更新完成: {tables} 表")
    except Exception as e:
        logger.error(f"DB Schema 快照更新失敗: {e}", exc_info=True)


@tracked_job("kb_coverage_check")
async def kb_coverage_check_job():
    """OfficialDocument Embedding 覆蓋率檢查（監測，非自癒）。

    ⚠️ 2026-07-20 校正命名混淆：本 job 名為「kb」但 get_coverage_stats 實測的是
    **OfficialDocument**（業務公文 RAG embedding）覆蓋率，非 KB docs（kb_chunks）。
    kb_chunks 由手動 /embed 維護（現 100%）；OfficialDocument embedding 由文件入庫/
    backfill 流程維護。此處僅監測 + 低覆蓋告警，不在此自癒（避免錯接重建目標）。
    """
    from app.db.database import async_session_maker

    logger.info("開始執行 OfficialDocument Embedding 覆蓋率檢查")

    try:
        async with async_session_maker() as db:
            from app.services.ai.core.embedding_manager import EmbeddingManager
            stats = await EmbeddingManager.get_coverage_stats(db)
            # 2026-08-03：原本讀 total_chunks / embedded_chunks / coverage_percent，
            # 但 `get_coverage_stats` 回的是 total / with_embedding / coverage ——
            # **三個 key 全部對不上**，`.get(..., 0)` 一律回 0。
            # 於是這支檢查連續 16 次回報「總數 0、覆蓋率 0%」，
            # 而實際是 1971 份公文全部有 embedding（100%）。
            # 與同日發現的 NER 關係抽取（relation vs relation_type）同型：
            # 欄位名漂移 + 靜默預設值 = 檢查看起來有跑、數字卻是假的。
            total = stats.get("total", 0)
            embedded = stats.get("with_embedding", 0)
            coverage = stats.get("coverage", 0)
            logger.info(
                f"OfficialDocument 覆蓋率檢查完成: "
                f"total={total}, embedded={embedded}, coverage={coverage:.1f}%"
            )
            if total == 0:
                # 原條件是 `coverage < 95 and total > 0` —— total=0 時連告警都不觸發，
                # 使「查不到任何資料」與「一切正常」在輸出上無法區分（雙重靜默）。
                logger.warning(
                    "OfficialDocument 覆蓋率檢查取得 total=0；"
                    "公文表不應為空，請確認查詢對象是否正確"
                )
            elif coverage < 95.0:
                logger.warning(
                    f"OfficialDocument Embedding 覆蓋率低於 95%: {coverage:.1f}% "
                    f"({total - embedded} 未 embed)"
                )
            return {"coverage": coverage, "total": total, "embedded": embedded}
    except Exception as e:
        logger.error(f"覆蓋率檢查失敗: {e}", exc_info=True)
        return {"error": str(e)}


@tracked_job("security_scan")
async def security_scan_job():
    """自動安全掃描 — 偵測硬編碼密鑰、SQL 注入、缺認證端點等"""
    from app.db.database import async_session_maker
    from app.services.security.scanner import SecurityScanner

    logger.info("開始執行自動安全掃描")
    try:
        async with async_session_maker() as db:
            scanner = SecurityScanner(db)
            result = await scanner.run_full_scan()
            logger.info(
                "安全掃描完成: total=%d, critical=%d, high=%d (%.1fs)",
                result["total_issues"], result.get("critical", 0),
                result.get("high", 0), result["duration_seconds"],
            )
            # 2026-08-14：補回 detail。掃到幾個問題是明確數字（實測 9 個），
            # 只是沒回傳。掃描器本身壞掉時 total 會變 0 —— 那與「真的沒問題」
            # 在原本的紀錄裡無法區分。
            return {
                "total_issues": result["total_issues"],
                "critical": result.get("critical", 0),
                "high": result.get("high", 0), "reason": "ok",
            }
    except Exception as e:
        logger.error("安全掃描失敗: %s", e, exc_info=True)
        raise


def _summarize_alerts(actionable: list, scanned: int) -> str:
    """把吹哨者告警**依類型分群**摘要，而不是列前三筆標題。

    2026-08-05 owner 回報：晨報那行長這樣 ——
        「actionable 告警 48 筆（掃描 50）：事件已逾期 1 天、事件已逾期 1 天、
          事件已逾期 1 天…」
    原本取 `a.title[:30]`，而這類告警的標題前 30 字是通用句型，
    三筆截出來一模一樣 → **看起來像壞掉，實際是三件不同的事**。
    48 筆裡真正該知道的是「哪一類、幾筆」，不是任意三筆的開頭。

    分群後同時保留每群一個**可辨識的例子**（含 entity id），
    否則又會變成只有數字、依然不知道去哪裡看。
    """
    from collections import Counter, defaultdict

    counts: Counter = Counter()
    sample: dict = defaultdict(str)
    for a in actionable:
        key = getattr(a, "alert_type", None) or "unknown"
        counts[key] += 1
        if not sample[key]:
            ent = getattr(a, "entity_type", "") or ""
            eid = getattr(a, "entity_id", None)
            tag = f"{ent}#{eid}" if eid else ent
            # 用 message 而非 title —— 這類告警的 title 是通用句型（「事件已逾期 N 天」），
            # 真正指出「是哪一件」的內容在 message（「『…公文標題…』已逾期 N 天」）。
            body = (getattr(a, "message", "") or getattr(a, "title", "") or "")[:44]
            sample[key] = f"{body}{f'（{tag}）' if tag else ''}"

    zh = {
        "deadline_overdue": "已逾期",
        "deadline_warning": "即將到期",
        "stale_backlog": "長期停滯",
        "data_quality": "資料品質",
        "system_health": "系統健康",
        "billing_payable_mismatch": "請款/應付差異",
        "billing_overdue": "請款逾期",
    }
    lines = [f"actionable {len(actionable)} 筆（掃描 {scanned}）"]
    for key, n in counts.most_common():
        lines.append(f"  • {zh.get(key, key)} {n} 筆｜例：{sample[key]}")
    return "\n".join(lines)


@tracked_job("proactive_trigger_scan")
async def proactive_trigger_scan_job():
    """
    夜間吹哨者 — 掃描 PM/ERP 預算超支、逾期請款、待核銷發票等警報。

    掃描結果：
    1. 持久化至 SystemNotification (DB)
    2. 推播至 LINE (若已設定)
    """
    from app.db.database import async_session_maker
    from app.services.ai.proactive.proactive_triggers import ProactiveTriggerService
    from app.services.ai.proactive.proactive_triggers_erp import ERPTriggerScanner
    from app.services.notification.helpers import _safe_create_notification

    logger.info("開始執行夜間吹哨者掃描")

    try:
        async with async_session_maker() as db:
            # 掃描所有警報 (公文截止日/資料品質 + ERP 預算/請款/發票/廠商付款)
            # 修法（2026-06-03 LINE 推播鏈）：base_service.scan_all() 內部已呼叫
            # ERPTriggerScanner.scan_all（proactive_triggers.py:66-69），原本此處再掃一次
            # 造成 (a) ERP alert 重複兩份 (b) 第二次用同一 session 撞 InFailedSQLTransactionError
            # → 整個夜間吹哨者在 LINE 推播前 raise，LINE 推播段從未執行。
            base_service = ProactiveTriggerService(db)
            all_alerts = await base_service.scan_all()

            # 篩選 warning 以上持久化至 DB
            severity_order = {"critical": 3, "warning": 2, "info": 1}
            actionable = [
                a for a in all_alerts
                if severity_order.get(a.severity, 0) >= 2
            ]

            persisted = 0
            for alert in actionable:
                # 去重 key 必須取「同一件事」的穩定識別 —— 不可用 title，
                # 因為「已逾期 573 天 → 574 天」每天都是新字串，去重會完全失效
                # （2026-07-30：正是這點讓每日 66 筆重複累積成 4094 筆 / 未讀 4708）。
                dedupe_key = (
                    f"{alert.alert_type}:{alert.entity_type}:{alert.entity_id}"
                    if alert.entity_id is not None
                    else f"{alert.alert_type}:{alert.entity_type}:{alert.title}"
                )
                ok = await _safe_create_notification(
                    notification_type="proactive_alert",
                    severity=alert.severity,
                    title=alert.title,
                    message=alert.message,
                    source_table=alert.entity_type,
                    source_id=alert.entity_id,
                    changes=alert.metadata,
                    dedupe_key=dedupe_key,
                )
                if ok:
                    persisted += 1

            logger.info(
                f"吹哨者完成: "
                f"掃描={len(all_alerts)}, "
                f"warning+={len(actionable)}, "
                f"已通知={persisted}"
            )

            # LINE 推播減量合併（2026-07-02）：吹哨者 alerts + 派工進度預設不單推 LINE，
            # 避免 LINE 免費月配額 200 則於下旬用罄（吹哨者原佔 2 則/日/管理員為最大消耗源）。
            # 內容仍寫入 DB alerts / 前端可見；晨報 morning_report 08:00 為唯一每日 LINE 推播。
            # 要恢復吹哨者 LINE 推播：設 PROACTIVE_LINE_PUSH_ENABLED=true。
            if os.getenv("PROACTIVE_LINE_PUSH_ENABLED", "false").lower() == "true":
                # LINE 推播 (嘗試性，失敗不影響主流程)
                try:
                    from app.services.integration.line_push_scheduler import LinePushScheduler
                    push_scheduler = LinePushScheduler(db)
                    push_result = await push_scheduler.scan_and_push(min_severity="warning")
                    if push_result.get("sent", 0) > 0:
                        logger.info(f"LINE 推播完成: {push_result}")
                except Exception as line_err:
                    logger.debug(f"LINE 推播跳過: {line_err}")

                # 派工進度彙整推送 (LINE Flex + Discord Embed)
                try:
                    from app.services.integration.line_push_scheduler import LinePushScheduler
                    progress_scheduler = LinePushScheduler(db)
                    progress_result = await progress_scheduler.push_dispatch_progress()
                    if progress_result.get("sent", 0) > 0:
                        logger.info(f"派工進度 LINE 推送完成: {progress_result}")
                except Exception as progress_err:
                    logger.debug(f"派工進度推送跳過: {progress_err}")
            else:
                # 2026-07-07 主題合併落地：不單推 → queue 進 digest buffer，
                # 隔日 08:00 晨報「昨日主題摘要」段一次帶出（常規 1 則/日/管理員）。
                if actionable:
                    from app.services.integration.line_digest_buffer import queue_digest
                    await queue_digest(
                        "🚨 吹哨者", _summarize_alerts(actionable, len(all_alerts)),
                    )
                logger.info("吹哨者/派工進度 LINE 推播已合併至晨報（PROACTIVE_LINE_PUSH_ENABLED=false）")

    except Exception as e:
        logger.error(f"夜間吹哨者失敗: {e}", exc_info=True)


@tracked_job("kg_embedding_backfill")
async def kg_embedding_backfill_job():
    """KG 實體 Embedding 自動回填 — 批次生成缺少向量的跨專案實體"""
    from app.db.database import async_session_maker

    logger.info("開始執行 KG Embedding 自動回填")

    try:
        async with async_session_maker() as db:
            from app.services.ai.domain.cross_domain_contribution_service import (
                CrossDomainContributionService,
            )
            svc = CrossDomainContributionService(db)
            # batch 2000：涵蓋 lvrland 聯邦 transaction 日增常態~400+尖峰2000。
            # 04:30 離峰 nomic-embed ~36/s → 2000 筆 <1 min，負載無虞。
            # ⚠️ 2026-07-09 訂正：07-08 曾誤判「batch 200 太小」為 RAG-blind 根因，
            # 實際根因是 backfill_embeddings 的 await bug（見該檔）致 cron 長期
            # processed=0、從未真正 backfill；batch 大小在 bug 修復前完全無作用。
            result = await svc.backfill_embeddings(batch_size=2000)
            await db.commit()
            processed = result.get("processed", 0)
            embedded = result.get("embedded", 0)
            skipped = result.get("skipped", 0)
            reason = result.get("reason")
            # 2026-07-09 L79：reason 存在＝早退（未真正 backfill）→ LOUD warning。
            # 2026-07-15：新增「processed>0 但 embedded=0」告警——04:30 冷啟動
            #   ollama nomic-embed 未溫熱時 batch 全空、cron 卻 status=success 的病灶
            #   （backfill_embeddings 已加暖機閘門，此處為第二道可見性防線）。
            if reason:
                logger.warning(
                    "KG Embedding 回填早退（未執行）: reason=%s（processed=%d）",
                    reason, processed,
                )
            elif processed > 0 and embedded == 0:
                logger.warning(
                    "KG Embedding 回填空轉：processed=%d 但 embedded=0（疑 ollama nomic 冷啟動）",
                    processed,
                )
            else:
                logger.info(
                    f"KG Embedding 回填完成: processed={processed}, embedded={embedded}, skipped={skipped}"
                )

            # v5.10.2 #7：順手 refresh KG metrics（避免 dead integration / L01）
            try:
                from app.core.kg_stats_metrics import get_kg_stats_metrics
                metrics = get_kg_stats_metrics()
                stats = await metrics.refresh_from_db(db)
                logger.info(
                    "KG metrics refreshed: total=%d embedded=%d coverage=%.3f edges=%d",
                    stats["total"], stats["embedded"], stats["coverage"], stats["edges"],
                )
            except Exception as m_err:
                logger.error("KG metrics refresh failed: %s", m_err, exc_info=True)

            # 2026-07-15：回傳業務產出 → tracked_job 寫入 cron_events.detail
            # （embedded/reason 可見化，破解 silent success）。
            return {
                "processed": processed,
                "embedded": embedded,
                "skipped": skipped,
                "reason": reason,
            }
    except Exception as e:
        logger.error(f"KG Embedding 回填失敗: {e}", exc_info=True)
        return {"processed": 0, "embedded": 0, "skipped": 0, "reason": f"job error: {e}"}


@tracked_job("kg_metrics_refresh")
async def kg_metrics_refresh_job():
    """v5.10.2 #7：KG metrics 即時刷新 — 每 15 分鐘從 DB 讀最新覆蓋率到 Prometheus

    領域：knowledge growth governance
      讓 Grafana dashboard 能看「kg_embedding_coverage_ratio」即時值，
      而非依賴每日 04:30 backfill job 才更新一次。
    """
    from app.db.database import async_session_maker
    from app.core.kg_stats_metrics import get_kg_stats_metrics

    # 2026-08-12：補 @tracked_job + 回 detail。在此之前它既不寫 cron_events
    # （沒有裝飾子）也沒有自己的 gauge，是 53 支排程裡唯二**完全沒有存活訊號**的
    # ——它掛了的症狀會是「Grafana 上的 KG 覆蓋率停住」，而沒有任何一支檢核會出聲。
    # 例外改為 raise：吞掉就回到沉默失敗（ADR-0028），tracked_job 會記 status=error。
    async with async_session_maker() as db:
        metrics = get_kg_stats_metrics()
        stats = await metrics.refresh_from_db(db)
        logger.debug(
            "KG metrics refreshed: total=%d embedded=%d coverage=%.3f",
            stats["total"], stats["embedded"], stats["coverage"],
        )
        return {
            "total": stats["total"],
            "embedded": stats["embedded"],
            "coverage": round(stats["coverage"], 4),
            "reason": "ok",
        }


@tracked_job("memory_metrics_refresh")
async def memory_metrics_refresh_job():
    """v5.10.2 Phase 1：Memory Wiki metrics 即時刷新 — 每 15 分鐘掃 wiki/memory/*

    領域：consciousness observability
      過去 metrics 定義齊全但 refresh_from_disk 只在 endpoint /api/ai/memory/stats
      被觸發時 lazy refresh，沒人進 memory dashboard 時 gauge 永遠 0
      → Grafana 看不到坤哥意識體健康度（同 #4 dead integration 病灶）。

    本 job 從 wiki/memory/ 子目錄計檔數（diary / patterns / failures /
    crystals / proposals / evolutions），更新 7 個 gauge 到 Prometheus。
    """
    from pathlib import Path
    from app.core.memory_wiki_metrics import get_memory_wiki_metrics

    # 2026-08-12：補 @tracked_job + 回 detail（同 kg_metrics_refresh，見該處說明）。
    # 例外改為 raise —— 吞掉就回到沉默失敗（ADR-0028）。
    # PROJECT_ROOT/wiki/memory 路徑（同 endpoints/ai/memory.py 用法）
    # 2026-05-24 fix: docker container 內 PROJECT_ROOT 計算偏 1 層（=/ 非 /app）
    # 因 docker layout flatten backend/ → /app，與 host layout 不同。
    # 加 CK_WIKI_DIR env override：docker compose 設 /app/wiki，host 走 fallback。
    from app.core.paths import PROJECT_ROOT as project_root  # v6.10 P1-E SSOT
    wiki_memory = _Path(os.getenv("CK_WIKI_DIR", str(project_root / "wiki"))) / "memory"
    if not wiki_memory.exists():
        # 目錄不在＝這支永遠刷不到值，屬設定問題而非「沒事可做」→ reason 要說得出來
        logger.warning("wiki/memory 目錄不存在，skip metrics refresh (path=%s)", wiki_memory)
        return {"reason": f"wiki_memory_missing:{wiki_memory}"}

    metrics = get_memory_wiki_metrics()
    metrics.refresh_from_disk(wiki_memory)
    diary = int(metrics.diary_days._value.get())
    patterns = int(metrics.patterns._value.get())
    crystals = int(metrics.crystals._value.get())
    pending = int(metrics.proposals_pending._value.get())
    logger.debug(
        "Memory metrics refreshed: diary=%d patterns=%d crystals=%d proposals_pending=%d",
        diary, patterns, crystals, pending,
    )
    return {
        "diary_days": diary,
        "patterns": patterns,
        "crystals": crystals,
        "proposals_pending": pending,
        "reason": "ok",
    }


async def _push_channel(channel: str, recipient: str, text: str) -> tuple[bool, str | None]:
    """
    B1: 統一 channel push 抽象，回傳 (ok, error_msg)。

    2026-04-22 修正：telegram 改用 push_message（含 ADR-0027 gate + sanitizer），
    避免 scheduler 繞過 gate 直接送 send_message。
    """
    try:
        if channel == "telegram":
            from app.services.integration.telegram_bot import get_telegram_bot_service
            tg = get_telegram_bot_service()
            if not tg.enabled:
                return False, "telegram service disabled"
            if not tg.push_enabled:
                return False, "telegram push disabled (ADR-0027)"
            ok = await tg.push_message(int(recipient), text)
            return bool(ok), None if ok else "push_message returned false"
        if channel == "line":
            from app.services.integration.line_bot import LineBotService
            line = LineBotService()
            if not line.enabled:
                return False, "line service disabled"
            # ⚠️ LINE 也必須套用金額遮蔽 —— 這不是「順便一致」，是有代價的教訓。
            #
            # 2026-04-21 owner 的 Telegram 帳號被官方**永久封禁、申訴駁回**，
            # owner 2026-08-15 確認原因：**推播內容的金額與其對應呈現方式
            # 被判定為非正常金流**。這不是推測性風險，是已經發生過的事，
            # 而且代價是一個帳號永久失去。
            #
            # 我在 2026-08-15 一度以「Telegram 已死、遮蔽器沒必要」為由把 LINE
            # 排除掉，那是錯的：**判斷風險要看「這件事有沒有發生過」，
            # 不是看「我覺得這個平臺會不會這樣做」**。已還原。
            #
            # 真正該解的不是「要不要遮」，而是**遮了之後訊息還讀不讀得懂** ——
            # 見 morning_report_formatter 的金額呈現規則。
            from app.services.common.telegram_content_sanitizer import sanitize
            safe_text = sanitize(text)
            ok = await line.push_message(recipient, safe_text)
            return bool(ok), None if ok else "push_message returned false"
        return False, f"unsupported channel: {channel}"
    except Exception as e:
        return False, str(e)


@tracked_job("morning_report")
async def morning_report_job():
    """每日 08:00 — 晨報生成 + snapshot 留存 + per-user 訂閱分發（A1~A3 + B1+B4）"""
    import os
    from app.db.database import async_session_maker
    from app.services.ai.domain.morning_report_service import MorningReportService
    from app.services.ai.domain.morning_report_delivery import (
        log_delivery, consecutive_failure_days, today_taipei,
        save_snapshot, get_active_subscriptions,
    )

    logger.info("開始執行每日晨報生成")
    report_date = today_taipei()
    data: dict = {}
    sections_count: int = 0

    # Step 1: Generate report data (once, 共用給所有訂閱者)
    try:
        async with async_session_maker() as db:
            svc = MorningReportService(db)
            data = await svc.generate_report()
            sections_count = sum(
                1 for v in data.values()
                if isinstance(v, dict) and (
                    v.get("count", 0) or v.get("week_count", 0)
                    or v.get("dispatch_count", 0)
                )
            )
    except Exception as e:
        logger.error("Morning report generation failed: %s", e, exc_info=True)
        async with async_session_maker() as db2:
            await log_delivery(
                db2, report_date=report_date, channel="system",
                status="failed", error_msg=f"generation: {e}",
            )
        return

    # Step 1b: 填報缺口（2026-08-16 owner「承攬報價案件對應填報人員通報管控」）
    #
    # 走**既有** digest buffer 由晨報一次帶出，不新建通知管道 ——
    # 核銷卡了 16 天沒人知道，不是因為少一個通道，是因為沒有人在算這件事。
    # 失敗只記 warning 不中斷晨報：缺口是附加資訊，不該讓主報表發不出去。
    try:
        from app.services.erp.filing_gap import FilingGapService
        from app.services.integration.line_digest_buffer import queue_digest

        async with async_session_maker() as gap_db:
            gap_svc = FilingGapService(gap_db)
            gap_data = await gap_svc.collect()
            gap_text = gap_svc.to_digest_text(gap_data)
        if gap_text:
            await queue_digest("填報缺口", gap_text)
            logger.info("填報缺口已入 digest：%s 項", gap_data["total"])
        else:
            # 0 項要說出來 —— 「今天沒有缺口」與「這段根本沒跑」
            # 在 log 裡不得長得一樣（本專案的沉默成功家族）。
            logger.info("填報缺口 0 項，不入 digest")
    except Exception as e:
        logger.warning("填報缺口彙整失敗（晨報照常）: %s: %s", type(e).__name__, e)

    # Step 2: Build admin default summary for snapshot + fallback
    admin_svc = MorningReportService(None)  # pure formatter, db not needed
    admin_summary = await admin_svc.generate_summary_from_data(data)

    # Step 2.5: 主題合併（2026-07-07）— 取走各主題 job 暫存的摘要（吹哨者/自省/
    # cron 健康/排程產出/標案訂閱），組「昨日主題摘要」尾段附於推播訊息。
    # snapshot 保持純晨報（尾段僅存在於投遞訊息）；drain 失敗回空不影響晨報。
    digest_tail = ""
    try:
        from app.services.integration.line_digest_buffer import (
            build_digest_tail, drain_digest,
        )
        digest_tail = build_digest_tail(await drain_digest())
        if digest_tail:
            logger.info("Morning digest tail attached (%d chars)", len(digest_tail))
    except Exception as e:
        logger.warning("Morning digest tail 組裝失敗（晨報照常推）: %s", e)

    # Step 3: Persist snapshot (B4)
    async with async_session_maker() as db:
        await save_snapshot(
            db, report_date=report_date, sections_json=data,
            summary_text=admin_summary, sections_count=sections_count,
        )

    # Step 4: Resolve recipients — subscriptions first, fallback to ENV admins
    async with async_session_maker() as db:
        subscriptions = await get_active_subscriptions(db)

    pushed_to: list[str] = []

    if subscriptions:
        # B1: per-user fanout
        for sub in subscriptions:
            personalized = await admin_svc.generate_summary_from_data(
                data, sections=sub["sections"]
            )
            if digest_tail:
                personalized = personalized + digest_tail
            ok, err = await _push_channel(
                sub["channel"], sub["channel_recipient"], personalized
            )
            async with async_session_maker() as db:
                await log_delivery(
                    db, report_date=report_date, channel=sub["channel"],
                    recipient=sub["channel_recipient"],
                    status="success" if ok else "failed",
                    summary_length=len(personalized),
                    sections_count=sections_count,
                    error_msg=err,
                )
            if ok:
                pushed_to.append(f"{sub['channel']}:{sub.get('display_name') or sub['channel_recipient']}")
    else:
        # Fallback: ENV admin (向後相容，無訂閱時仍推給管理員)
        env_targets = [
            ("telegram", os.getenv("TELEGRAM_ADMIN_CHAT_ID")),
            ("line", os.getenv("LINE_ADMIN_USER_ID")),
        ]
        for channel, recipient in env_targets:
            if not recipient:
                continue
            ok, err = await _push_channel(
                channel, recipient,
                admin_summary + digest_tail if digest_tail else admin_summary,
            )
            async with async_session_maker() as db:
                await log_delivery(
                    db, report_date=report_date, channel=channel,
                    recipient=recipient,
                    status="success" if ok else "failed",
                    summary_length=len(admin_summary),
                    sections_count=sections_count,
                    error_msg=err,
                )
            if ok:
                pushed_to.append(f"{channel} (env admin)")

    if pushed_to:
        logger.info("Morning report pushed to %d recipients: %s",
                    len(pushed_to), ", ".join(pushed_to))
    else:
        logger.warning("Morning report generated but NO recipients")

    # Step 5: 連續失敗告警（A2）
    async with async_session_maker() as db:
        for ch in ("telegram", "line"):
            try:
                streak = await consecutive_failure_days(db, ch, window_days=7)
                if streak >= 2:
                    logger.error(
                        "MORNING_REPORT_ALERT: channel=%s 連續 %d 天失敗，"
                        "請檢查 bot token / recipient 設定",
                        ch, streak,
                    )
            except Exception as e:
                logger.debug("consecutive_failure_days check failed: %s", e)


@tracked_job("pcc_today_scrape")
async def pcc_today_scrape_job():
    """PCC 今日標案爬取 — 每 2 小時抓 web.pcc.gov.tw/prkms/today（權威來源）

    2026-05-27 修法：補回 P0-1 缺失 — PCC scraper 自 2026-04-08 起 50 天
    silent dormant（scheduler 缺 cron）。權威來源依賴 ezbid 單軌支撐至今。
    每 2 小時與 ezbid 每小時錯開，避免雙爬 PCC 站。
    """
    # 2026-07-18 治本（沉默成功家族）：記錄產出數 + 區分「週末合理空」vs「爬蟲失敗空」。
    #   原問題＝「今日標案卡數據消失」反覆修：真相是週末政府不發標案＝合理 0，但 job
    #   報 success 146ms 無 detail、卡片無法辨「週末 0」vs「失敗 0」→ 每個週末像壞掉。
    #   @tracked_job 記回傳 dict 為 detail → 沉默成功現形（同 KG embedding 修法）。
    from app.db.database import async_session_maker
    from datetime import date as _date

    is_weekend = _date.today().weekday() >= 5  # 5=Sat, 6=Sun（政府非發標日）
    logger.info("開始 PCC 今日標案爬取")
    try:
        from app.services.tender.pcc_today_scraper import PccTodayScraper
        from app.core.redis_client import get_redis
        redis = await get_redis()
        scraper = PccTodayScraper(redis_client=redis)
        result = await scraper.fetch_today_tenders()
        records = result.get("records", [])
        by_type = result.get("by_type", {})
        fetch_error = result.get("error")  # _fetch_page 失敗＝"PCC 網站無回應"
        saved = 0

        if records:
            try:
                async with async_session_maker() as db:
                    from app.services.tender.cache import (
                        save_search_results, _ingest_tender_entities,
                    )
                    saved = await save_search_results(db, records, source="pcc")
                    ingested = await _ingest_tender_entities(db, records)
                    logger.info(f"PCC → DB: {saved} 筆新增, KG: {ingested} 實體入圖")
            except Exception as e:
                logger.warning(f"PCC DB 寫入失敗 (非致命): {e}", exc_info=True)

        # 產出診斷（區分合理空 vs 失敗）
        if fetch_error:
            reason = "fetch_failed"  # 來源無回應/封鎖 → 真問題
            logger.warning(f"[PCC_SCRAPE] 抓取失敗（{fetch_error}）→ 0 筆，非週末合理空，需查來源")
        elif len(records) == 0 and is_weekend:
            reason = "weekend_no_publish"  # 週末政府不發標 → 合理空
            logger.info("[PCC_SCRAPE] 今日（週末）無新標案＝合理空，非失敗")
        elif len(records) == 0:
            reason = "weekday_zero_suspicious"  # 平日卻 0 → 疑 parse 失敗/來源改版
            logger.warning("[PCC_SCRAPE] 平日抓取 0 筆但來源有回應＝可疑（parse 失敗或來源改版？），需查")
        else:
            reason = "ok"
            logger.info(f"PCC 全量爬取: {len(records)} 筆 / saved={saved} / by_type={by_type}")

        return {"records": len(records), "saved": saved, "reason": reason, "is_weekend": is_weekend}
    except Exception as e:
        logger.error(f"PCC 今日標案爬取失敗: {e}", exc_info=True)
        return {"records": 0, "reason": "exception", "error": str(e)}


@tracked_job("ezbid_cache_refresh")
async def ezbid_cache_refresh_job():
    """ezbid 全量快取刷新 — 每小時抓取今日全量 + 寫入 DB + 預熱 dashboard"""
    from app.db.database import async_session_maker

    logger.info("開始 ezbid 全量快取刷新")
    try:
        from app.services.tender.ezbid_scraper import EzbidScraper
        scraper = EzbidScraper()
        # 使用統一服務層 get_today_all() — 10 頁 × 100 筆 + Redis 共享快取
        result = await scraper.get_today_all()
        records = result.get("records", [])
        logger.info(f"ezbid 全量刷新: {len(records)} 筆")

        # 寫入 DB (持久化)
        #
        # 2026-08-16：這一段原本 `except` 只記 warning 就吞掉，而 job 照樣回報 success，
        # 且**完全不回傳 detail** —— 1737 次執行全部 `success / detail: None`，
        # 於是「抓到 1000 筆寫入 800 筆」與「抓到 0 筆寫入 0 筆」在紀錄裡長得一樣。
        #
        # 而 owner 反覆感覺到的「ezbid 常複發」，實際形狀是：
        # dashboard 預熱（每 5 分鐘、analytics.py）一直在抓那 1000 筆並放進 Redis，
        # 所以畫面看起來是有資料的；但**真正負責寫 DB 的就是這一支**，
        # 它一停，DB 就停止成長而畫面完全看不出來
        # （實測 2026-08-16：tender_records 最新一筆停在 08-14 18:53）。
        saved = ingested = 0
        db_error = None
        if records:
            try:
                async with async_session_maker() as db:
                    from app.services.tender.cache import save_search_results
                    saved = await save_search_results(db, records, source="ezbid")
                    # 同步入圖 (標案機關/廠商 → canonical_entities)
                    from app.services.tender.cache import _ingest_tender_entities
                    ingested = await _ingest_tender_entities(db, records)
                    logger.info(f"ezbid → DB: {saved} 筆新增, KG: {ingested} 實體入圖")
            except Exception as e:
                # 仍不 raise（抓取本身成功，讓整包失敗不合比例），
                # 但要把失敗交出去 —— producer watchdog 看得到才叫「有人在看」。
                db_error = f"{type(e).__name__}: {e}"
                logger.error("ezbid DB 寫入失敗: %s", db_error, exc_info=True)

        # 2026-04-24: 預熱 dashboard Redis cache，使 /tender/dashboard 首次訪問
        # 就能 cache-hit（否則首次 miss 要並行爬 ezbid+PCC+15 keywords 約 15s）
        try:
            # 先刪舊 cache 強制重算
            from app.core.redis_client import get_redis
            redis = await get_redis()
            if redis:
                await redis.delete("tender:dashboard:result")

            from app.services.tender.analytics import TenderAnalyticsService
            warmup = await TenderAnalyticsService().dashboard()
            total = warmup.get("total_found", 0) if warmup else 0
            logger.info(f"dashboard cache 預熱完成: total_found={total}")
        except Exception as e:
            logger.warning(f"dashboard cache 預熱失敗 (非致命): {e}")

        # 2026-08-16：交出 detail。原本這支**完全不回傳** ——
        # 1737 次執行全是 `success / detail: None`，於是「抓到 1000 筆寫入 800 筆」
        # 與「抓到 0 筆寫入 0 筆」在 cron_events 裡長得一模一樣，
        # 而 producer watchdog 只看得到「它有跑」。
        return {
            "fetched": len(records),
            "saved": saved,
            "kg_ingested": ingested,
            "reason": db_error or ("已寫入" if saved else "抓到但無新增（可能全是既有標案）"),
        }
    except Exception as e:
        # 抓取整個失敗要 raise —— 原本只記 error 就吞掉，
        # job 照樣記 success，而那正是「常複發卻沒人知道」的來源。
        logger.error(f"ezbid 快取刷新失敗: {e}", exc_info=True)
        raise


@tracked_job("ledger_reconciliation")
async def ledger_reconciliation_job():
    """帳本對帳 — 每日比對 ERP billing/payable 與 FinanceLedger 差異"""
    from app.db.database import async_session_maker

    logger.info("開始帳本對帳檢查")
    try:
        async with async_session_maker() as db:
            from sqlalchemy import select, func
            from app.extended.models.erp import ERPBilling, ERPVendorPayable
            from app.extended.models.finance import FinanceLedger

            # AR: 已付 billing vs ledger
            paid_billing_total = await db.scalar(
                select(func.coalesce(func.sum(ERPBilling.payment_amount), 0))
                .where(ERPBilling.payment_status == "paid")
            ) or 0

            ledger_billing_total = await db.scalar(
                select(func.coalesce(func.sum(FinanceLedger.amount), 0))
                # 2026-08-15：改為同時涵蓋 "billing" 與 "erp_billing"。
                # 補上 detail 後第一次執行就報 AR 差額 1,329,710 —— 查證後
                # **帳本沒有掉錢，是這支對帳自己查錯標籤**：
                # 帳本裡 35 筆舊資料用 `billing`（總額正好 1,329,710，與已收款帳單一致），
                # 而寫入端某次改名為 `erp_billing` 時**舊資料沒有跟著遷移**，
                # 對帳只查新值 → 看到 1 筆 0 元 → 報一個不存在的百萬差額。
                # 它一直在報，但沒有 detail、通知也沒建立成功，所以沒有人知道。
                .where(FinanceLedger.source_type.in_(("billing", "erp_billing")))
            ) or 0

            # AP: 已付 payable vs ledger
            paid_payable_total = await db.scalar(
                select(func.coalesce(func.sum(ERPVendorPayable.paid_amount), 0))
                .where(ERPVendorPayable.payment_status == "paid")
            ) or 0

            ledger_payable_total = await db.scalar(
                select(func.coalesce(func.sum(FinanceLedger.amount), 0))
                .where(FinanceLedger.source_type == "erp_vendor_payable")
            ) or 0

            from decimal import Decimal
            ar_diff = abs(Decimal(str(paid_billing_total)) - Decimal(str(ledger_billing_total)))
            ap_diff = abs(Decimal(str(paid_payable_total)) - Decimal(str(ledger_payable_total)))

            if ar_diff > 0 or ap_diff > 0:
                logger.warning(
                    "帳本對帳差異: AR 差額=%.2f (billing=%s, ledger=%s), "
                    "AP 差額=%.2f (payable=%s, ledger=%s)",
                    ar_diff, paid_billing_total, ledger_billing_total,
                    ap_diff, paid_payable_total, ledger_payable_total,
                )
                # 寫入告警通知
                from app.services.notification.helpers import _safe_create_notification
                if ar_diff > 0:
                    await _safe_create_notification(
                        notification_type="reconciliation_alert",
                        severity="warning",
                        title="帳本 AR 對帳差異",
                        message=f"已收款帳單總額 {paid_billing_total} vs 帳本收入 {ledger_billing_total}，差額 {ar_diff}",
                        source_table="finance_ledger",
                    )
                if ap_diff > 0:
                    await _safe_create_notification(
                        notification_type="reconciliation_alert",
                        severity="warning",
                        title="帳本 AP 對帳差異",
                        message=f"已付應付總額 {paid_payable_total} vs 帳本支出 {ledger_payable_total}，差額 {ap_diff}",
                        source_table="finance_ledger",
                    )
            else:
                logger.info("帳本對帳通過: AR 一致, AP 一致")
            # 2026-08-14：補回 detail。「對不上幾筆／差額多少」是明確數字，
            # 只是沒回傳 —— 於是「對帳通過」與「對帳根本沒跑」在紀錄裡一樣。
            # 差額為 0 是常態且是好事，所以不判紅；但它必須是可見的。
            # 標籤漂移**不吸收掉**：上面用 in_ 讓金額對得上，但兩套值並存本身
            # 是待處理的資料問題（舊 35 筆 billing／新 1 筆 erp_billing），
            # 任何依 source_type 篩選的新功能都會看到不完整的資料。
            legacy_n = await db.scalar(
                select(func.count()).select_from(FinanceLedger)
                .where(FinanceLedger.source_type == "billing")
            ) or 0
            return {
                "ar_diff": float(ar_diff), "ap_diff": float(ap_diff),
                "legacy_source_type_rows": int(legacy_n),
                "reason": "ok" if (ar_diff == 0 and ap_diff == 0) else "mismatch",
            }
    except Exception as e:
        logger.error(f"帳本對帳失敗: {e}", exc_info=True)
        raise


@tracked_job("monthly_arch_review")
async def monthly_architecture_review_job():
    """月度架構覆盤 — ADR 狀態盤點 + Wiki/KG 健康 + 知識地圖重建提醒"""
    from app.db.database import async_session_maker
    try:
        report_lines = ["[月度架構覆盤]"]

        # 1. ADR 生命週期閘門 — proposed>14d 自動標記 overdue
        import glob
        import re as _re
        from datetime import datetime as _dt, timedelta as _td
        adr_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs", "adr")
        proposed = []
        overdue = []
        for f in sorted(glob.glob(os.path.join(adr_dir, "*.md"))):
            try:
                fname = os.path.basename(f)
                # 2026-08-03：原本只看檔案內容有沒有 "proposed"，於是 README.md 與
                # TEMPLATE.md（兩者都在說明 proposed 這個狀態）被算成待決 ADR，
                # 讓 adr_proposed 從 2 虛報成 4。ADR 檔名一律是 NNNN-*.md。
                if not _re.match(r"^\d{4}-", fname):
                    continue
                with open(f, encoding="utf-8") as fp:
                    head = fp.read(800)
                if "proposed" in head.lower():
                    proposed.append(fname)
                    # 檢查日期 — 超過 14 天標記 overdue
                    date_m = _re.search(r'\*\*日期\*\*:\s*(\d{4}-\d{2}-\d{2})', head)
                    if date_m:
                        adr_date = _dt.strptime(date_m.group(1), "%Y-%m-%d")
                        if (_dt.now() - adr_date) > _td(days=14):
                            overdue.append(fname)
            except Exception:
                pass
        status_line = f"ADR: {len(proposed)} proposed"
        if overdue:
            status_line += f", {len(overdue)} OVERDUE (>14d): {', '.join(overdue)}"
        elif proposed:
            status_line += f" — {', '.join(proposed)}"
        else:
            status_line += " — all resolved"
        report_lines.append(status_line)

        # 2. Wiki 健康
        from app.services.wiki.service import get_wiki_service
        wiki = get_wiki_service()
        lint = await wiki.lint()
        stats = wiki.get_stats()
        report_lines.append(
            f"Wiki: {stats.get('total', 0)} pages, {lint['health']}, "
            f"{len(lint['orphan_pages'])} orphans, {len(lint['broken_links'])} broken"
        )

        # 3. KG 統計
        async with async_session_maker() as session:
            from sqlalchemy import select, func
            from app.extended.models.knowledge_graph import CanonicalEntity
            kg_count = await session.scalar(
                select(func.count()).where(CanonicalEntity.graph_domain == "knowledge")
            ) or 0
            report_lines.append(f"KG: {kg_count} entities (knowledge domain)")

        # 4. 測試提醒
        report_lines.append("Action: 檢查 MEMORY.md 鮮度 + 知識地圖 --if-stale")

        report = "\n".join(report_lines)
        logger.info(report)

        # ── 2026-08-03：把輸出端接回來 ────────────────────────────────
        # 這支 job 一直在跑（cron_events 有 3 次 success），但**產出沒有任何接收者**：
        #   報告只 logger.info → 沖進 log；唯一推播管道是 Telegram，而該 token
        #   實測 401、且 TELEGRAM_ADMIN_PUSH_ENABLED=false —— 兩層都送不出去；
        #   不落地成檔 → 無法跨月對照；未註冊 producer → watchdog 看不到它。
        # 結果就是每次架構檢視都得由人手動發起。缺的不是機制，是輸出端。
        from app.core.paths import WIKI_DIR
        review_dir = WIKI_DIR / "memory" / "arch-review"
        review_dir.mkdir(parents=True, exist_ok=True)
        stamp = _dt.now().strftime("%Y-%m")
        target = review_dir / f"{stamp}.md"

        # 與上一份比對，只報「變了什麼」。每月推一份長得一樣的報告
        # 只會訓練人忽略它 —— 那就回到原點了。
        prev = sorted(p for p in review_dir.glob("*.md") if p.name != target.name)
        delta_lines: list[str] = []
        if prev:
            prev_body = prev[-1].read_text(encoding="utf-8", errors="replace")
            # 寫入時每行前面加了 "- "，讀回來比對必須先剝掉 —— 不剝的話 prev_set
            # 永遠是空的，於是「本月與上月完全相同」也會被報成三項全變。
            # （2026-08-03 用「無變化」情境的負向測試當場抓到；沒驗這一步的話，
            #   每月都報「全部都變了」＝ 又回到沒人看的噪音。）
            def _norm_line(s: str) -> str:
                return s.strip().lstrip("-").strip()
            prev_set = {_norm_line(l) for l in prev_body.splitlines()
                        if _norm_line(l).startswith(("ADR:", "Wiki:", "KG:"))}
            cur_set = {l.strip() for l in report_lines if l.startswith(("ADR:", "Wiki:", "KG:"))}
            changed = sorted(cur_set - prev_set)
            delta_lines = changed or ["（與上次相比無變化）"]
        else:
            delta_lines = ["（首次產出，無對照基準）"]

        target.write_text(
            f"# 月度架構覆盤 {stamp}\n\n"
            f"> 產出時間：{_dt.now().isoformat(timespec='seconds')}\n\n"
            f"## 本次盤點\n\n" + "\n".join(f"- {l}" for l in report_lines[1:]) +
            f"\n\n## 與上次的差異\n\n" + "\n".join(f"- {l}" for l in delta_lines) + "\n",
            encoding="utf-8",
        )

        # 走既有的跨通道扇出（LINE 為主），不新建通知路徑。
        # Telegram 那條保留在 facade 內部，但不再是唯一出口。
        pushed = False
        try:
            from app.services.contracts.facades.integration import IntegrationFacade
            summary = "；".join(delta_lines[:3])
            pushed = bool(await IntegrationFacade().push_admin_alert(
                title="月度架構覆盤", body=summary, channel="line",
            ))
        except Exception as e:
            logger.warning("月度架構覆盤推播失敗（報告已落地，不影響產出）: %s", e)

        return {
            "report_file": str(target),
            "adr_proposed": len(proposed),
            "adr_overdue": len(overdue),
            "delta_count": 0 if delta_lines == ["（與上次相比無變化）"] else len(delta_lines),
            "pushed": pushed,
            "reason": "ok" if pushed else "report written, push unavailable",
        }
    except Exception as e:
        logger.error("Monthly arch review failed: %s", e, exc_info=True)
        # 失敗要 raise —— 只 log 的話 cron_events 仍記 success（07-30 契約規則 4）
        raise


@tracked_job("wiki_compile")
async def wiki_compile_job():
    """Wiki 增量編��� — 只重編有新公文的機關/案件 (Karpathy Phase 2, v1.1 增量)"""
    from app.db.database import async_session_maker
    try:
        async with async_session_maker() as session:
            from app.services.wiki.compiler import WikiCompiler
            compiler = WikiCompiler(session)
            result = await compiler.compile_incremental(min_doc_count=5)
            mode = result.get("mode", "full")
            logger.info(
                "Wiki compile (%s): agencies=%s, projects=%s",
                mode,
                result["agencies"]["compiled"],
                result["projects"]["compiled"],
            )

            # 2026-08-03：每週編譯出新頁，卻**沒有重建索引** ——
            # `rebuild_index()` 只在 API 端點被人工呼叫，於是 `wiki/index.md`
            # 停在 **2026-04-19**，之後產生的 topics / synthesis 全部沒有入口。
            # 編完就順手重建，兩件事本來就該綁在一起。
            # 2026-08-03：把 code-wiki 的模組說明也帶進來。
            # `CodeWikiGenerator` 早就能產出模組 markdown（原規劃的「模組 Wiki
            # 自動生成」），但一直沒有出口——不落地、無索引、前端零消費。
            # LLM Wiki 這側有完整的落地/索引/lint/搜尋管線，接上即可。
            # 分批（每次最多 20 頁）避免週級 job 卡在上百次 LLM 呼叫。
            mod_stat = await compiler.compile_module_wiki(top_n=120, max_new=20)

            # 補齊進度要能被發現卡住 —— 否則「每週補一點」可能悄悄停在中途，
            # 而 job 依然週週回 success（正是這幾天一路在治的形態）。
            # 還有待補、這輪卻一頁都沒產出 = 卡住，queue 進晨報讓人看得到。
            if mod_stat.get("remaining", 0) > 0 and mod_stat.get("compiled", 0) == 0:
                try:
                    from app.services.integration.line_digest_buffer import queue_digest
                    await queue_digest(
                        "📘 模組 Wiki",
                        f"補齊疑似卡住：本輪 0 頁產出，仍有 {mod_stat['remaining']} 個待補"
                        f"（失敗 {mod_stat.get('failed', 0)}）",
                    )
                except Exception as e:
                    logger.warning("模組 wiki 卡住通知 queue 失敗: %s", e)
            elif mod_stat.get("remaining", 0) > 0:
                logger.info(
                    "模組 wiki 補齊進行中：本輪 +%d，尚餘 %d",
                    mod_stat.get("compiled", 0), mod_stat["remaining"],
                )

            from app.services.wiki.service import get_wiki_service
            index_counts = await get_wiki_service().rebuild_index()

        return {
            "mode": mode,
            "agencies": result["agencies"]["compiled"],
            "projects": result["projects"]["compiled"],
            "modules": mod_stat.get("compiled", 0),
            "modules_remaining": mod_stat.get("remaining", 0),
            "index": index_counts,
            "reason": "ok",
        }
    except Exception as e:
        logger.error("Wiki compile failed: %s", e, exc_info=True)
        raise


@tracked_job("optimization_pipeline")
async def cron_optimization_pipeline_job():
    """v6.10 P0-1 (2026-05-18): Optimization Pipeline 每日巡檢

    跑 `optimization_pipeline_orchestrator.run_daily_pipeline()` 5 step：
      1. fitness (run_fitness.sh, 27 step)
      2. capability_audit
      3. memory_loop_health
      4. shadow_baseline_summary
      5. precommit_hook_probe

    產出 JSON report + Markdown digest，YELLOW/RED 時推 LINE。
    防 v6.10 candidate「orchestrator skeleton 0 importer 孤兒」反模式。
    """
    try:
        # 非阻塞執行（pipeline 內含 subprocess 呼叫，可能 30s+）
        from app.services.optimization_pipeline_orchestrator import (
            run_daily_pipeline,
            format_line_digest,
            display_overall_zh,
        )
        report = await _asyncio.to_thread(run_daily_pipeline)
        overall = report.get("overall_status", "unknown")
        logger.info(
            "Optimization Pipeline 完成: overall=%s, %d steps",
            overall,
            len(report.get("steps", [])),
        )

        # 每日推 admin（含 GREEN）— 形成 forcing function 避免 silent dormant
        # 2026-05-22 教訓：5 個月 silent fail 沒人察覺，正是因為「GREEN 不推」=「無告警 = 不知壞」
        # GREEN 推單行摘要（低雜訊），YELLOW/RED 推完整 digest
        # 7 天觀察期後若 owner 嫌雜，可改回 if overall in ("yellow","red","error")
        #
        # 2026-06-23 owner 決策：LINE 免費月配額 200 則優先給「晨報 + 坤哥相關紀錄」，
        # 系統每日巡檢訊息暫緩推送（report 仍寫入 wiki/memory/pipeline-reports/ + 治理
        # 儀表板，owner 可從首選入口 GOVERNANCE_INTEGRATED_DASHBOARD.md 查看）。
        # 要恢復巡檢 LINE 推送：設 PIPELINE_LINE_PUSH_ENABLED=true。
        if os.getenv("PIPELINE_LINE_PUSH_ENABLED", "false").lower() != "true":
            logger.info(
                "系統每日巡檢 digest 推送已暫緩（PIPELINE_LINE_PUSH_ENABLED=false，"
                "節省 LINE 月配額）— report 已產出，可從治理儀表板查看 overall=%s",
                overall,
            )
            return
        try:
            from app.services.contracts.facades.integration import IntegrationFacade
            # v6.21 (2026-06-18) owner 回饋：管理端訊息中文化 + 具體化。
            # title 改中文 + display-overall（已知限制不誤報 🔴）；body 用 LINE 友善的
            # 分區白話 digest（取代英文 markdown 表格與 raw dict）。
            n_steps = len(report.get("steps", []))
            disp = display_overall_zh(report)
            title = f"系統每日巡檢｜{disp}"
            if overall == "green":
                body = f"五項巡檢全綠通過（{n_steps} 項）。明日同時推送。"
            else:
                body = format_line_digest(report)[:2000]
            await IntegrationFacade().push_admin_alert(title=title, body=body)
        except Exception as push_exc:
            logger.warning(
                "Optimization Pipeline digest push 失敗（pipeline 已產出 report）: %s",
                push_exc,
            )
    except Exception as e:
        logger.error("Optimization Pipeline crashed: %s", e, exc_info=True)


@tracked_job("wiki_lint")
async def wiki_lint_job():
    """Wiki 健康檢查 — 偵測孤立頁面、斷裂連結

    漂移通知策略（避免長期背景雜訊）：
    - 只有「超過閾值」或「較上次惡化」才寫入 wiki/log.md + Telegram
    - 閾值透過 env 可調：WIKI_ORPHAN_RATIO_THRESHOLD (default 0.35),
      WIKI_BROKEN_LINKS_THRESHOLD (default 10),
      WIKI_DRIFT_DELTA (default 5) — orphans/broken 比上次多這麼多就警示
    - 上次狀態記於 wiki/.lint_state.json
    """
    import json
    from pathlib import Path
    from datetime import datetime

    try:
        from app.services.wiki.service import get_wiki_service
        svc = get_wiki_service()
        result = await svc.lint()
        total_pages = result["total_pages"] or 1
        orphan_count = len(result["orphan_pages"])
        broken_count = len(result["broken_links"])
        orphan_ratio = orphan_count / total_pages
        logger.info(
            "Wiki lint: %d pages, %d orphans (%.1f%%), %d broken links, health=%s",
            total_pages, orphan_count, orphan_ratio * 100,
            broken_count, result["health"],
        )

        # 讀閾值
        orphan_ratio_th = float(os.getenv("WIKI_ORPHAN_RATIO_THRESHOLD", "0.35"))
        broken_th = int(os.getenv("WIKI_BROKEN_LINKS_THRESHOLD", "10"))
        drift_delta = int(os.getenv("WIKI_DRIFT_DELTA", "5"))

        # 讀前次狀態
        from app.core.paths import PROJECT_ROOT as project_root  # v6.10 P1-E SSOT
        state_path = project_root / "wiki" / ".lint_state.json"
        prev_orphan = 0
        prev_broken = 0
        if state_path.exists():
            try:
                prev = json.loads(state_path.read_text(encoding="utf-8"))
                prev_orphan = int(prev.get("orphans", 0))
                prev_broken = int(prev.get("broken", 0))
            except Exception:
                pass

        # 判定警示條件
        alerts = []
        if orphan_ratio > orphan_ratio_th:
            alerts.append(
                f"orphan_ratio={orphan_ratio:.1%} > {orphan_ratio_th:.0%}"
            )
        if broken_count > broken_th:
            alerts.append(f"broken_links={broken_count} > {broken_th}")
        if orphan_count - prev_orphan >= drift_delta:
            alerts.append(
                f"orphans drift: {prev_orphan}→{orphan_count} (+{orphan_count - prev_orphan})"
            )
        if broken_count - prev_broken >= drift_delta:
            alerts.append(
                f"broken drift: {prev_broken}→{broken_count} (+{broken_count - prev_broken})"
            )

        # 更新狀態
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "total_pages": total_pages,
                    "orphans": orphan_count,
                    "broken": broken_count,
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("wiki_lint state save failed: %s", e)

        # 有警示才通知
        if alerts:
            logger.warning("Wiki lint ALERTS: %s", "; ".join(alerts))
            # wiki/log.md append 審計
            log_path = project_root / "wiki" / "log.md"
            if log_path.exists():
                ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                log_path.write_text(
                    log_path.read_text(encoding="utf-8")
                    + f"\n## {ts} — Wiki lint drift alert\n"
                    + f"- pages={total_pages}, orphans={orphan_count} ({orphan_ratio:.1%}), broken={broken_count}\n"
                    + "".join(f"- ⚠️ {a}\n" for a in alerts),
                    encoding="utf-8",
                )
            # 2026-08-03：原本推 Telegram —— 而該 token 實測 401、
            # `TELEGRAM_ADMIN_PUSH_ENABLED` 也是 false，**兩層都送不出去**，
            # 於是 wiki 的漂移警示只留在 log 裡，沒有任何人會看到。
            # 改走既有的 line_digest_buffer：不單推、queue 進 buffer 由 08:00
            # 晨報一次帶出（v6.24 建立的機制），零配額增加。
            try:
                from app.services.integration.line_digest_buffer import queue_digest
                await queue_digest(
                    "📚 Wiki 漂移",
                    f"pages={total_pages}, orphans={orphan_count}, broken={broken_count}\n"
                    + "\n".join(f"• {a}" for a in alerts),
                )
            except Exception as e:
                logger.warning("wiki lint digest queue 失敗（警示仍在 log/wiki 審計）: %s", e)

        return {
            "pages": total_pages,
            "orphans": orphan_count,
            "broken": broken_count,
            "health": result["health"],
            "alerts": len(alerts),
            "reason": "ok",
        }
    except Exception as e:
        logger.error("Wiki lint failed: %s", e, exc_info=True)
        raise


@tracked_job("health_snapshot_log")
async def health_snapshot_log_job():
    """每日健康快照 → wiki/log.md append

    指標：24h commits / wiki 頁數 / scheduler jobs / DB/Redis 狀態 / AgentLearning 數。
    純 append，不觸發其他排程，失敗不影響其他 job。
    """

    from app.core.paths import PROJECT_ROOT as project_root  # v6.10 P1-E SSOT
    script = project_root / "scripts" / "health" / "log-health-snapshot.cjs"
    if not script.exists():
        logger.error("health_snapshot: script not found at %s — raise 供 cron watchdog 抓 (防 silent no-op)", script)
        raise FileNotFoundError(f"cron script 缺失: {script}")
    rc, out, err = await _run_script_async(
        ["node", str(script)], cwd=str(project_root), timeout=30, job_name="health_snapshot",
    )
    if rc == 0:
        logger.info("health_snapshot: %s", out or "ok")
    else:
        logger.warning("health_snapshot failed (rc=%d): %s", rc, err)


@tracked_job("shadow_baseline_export")
async def shadow_baseline_export_job():
    """每日 20:00 匯出 Hermes shadow baseline（ADR-0014 Phase 0）

    寫入 logs/shadow-baseline/YYYY-MM-DD.json 供 GO/NO-GO 累積判斷。
    目標：樣本 ≥100 筆且 3+ 頻道後，進入 Telegram 灰度。
    """
    from datetime import date as _date

    from app.core.paths import PROJECT_ROOT as project_root  # v6.10 P1-E SSOT
    script = project_root / "scripts" / "checks" / "shadow-baseline-report.cjs"
    if not script.exists():
        logger.error("shadow_baseline: script not found at %s — raise 供 cron watchdog 抓 (防 silent no-op)", script)
        raise FileNotFoundError(f"cron script 缺失: {script}")

    out_dir = project_root / "logs" / "shadow-baseline"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{_date.today().isoformat()}.json"

    rc, out, err = await _run_script_async(
        ["node", str(script), "--json"], cwd=str(project_root), timeout=60, job_name="shadow_baseline",
    )
    if rc == 0 and out:
        out_file.write_text(out, encoding="utf-8")
        logger.info("shadow_baseline: exported → %s", out_file.name)
    else:
        logger.warning("shadow_baseline failed (rc=%d): %s", rc, err or "empty stdout")


@tracked_job("synthetic_baseline_inject")
async def synthetic_baseline_inject_job():
    """每日 3 次合成基線注入（09:00/14:00/20:00）

    執行 scripts/checks/synthetic-baseline-inject.py 注入合成測試資料，
    用於 shadow baseline 持續累積與 GO/NO-GO 品質監控。
    """
    from app.core.paths import PROJECT_ROOT as project_root  # v6.10 P1-E SSOT
    script = project_root / "scripts" / "checks" / "synthetic-baseline-inject.py"
    if not script.exists():
        logger.error("synthetic_baseline_inject: script not found at %s — raise 供 cron watchdog 抓 (防 silent no-op)", script)
        raise FileNotFoundError(f"cron script 缺失: {script}")

    rc, out, err = await _run_script_async(
        ["python", str(script), "--count", "10", "--timeout", "90"],
        cwd=str(project_root), timeout=1200, job_name="synthetic_baseline_inject",
    )
    if rc == 0:
        logger.info("synthetic_baseline_inject: %s", out[-200:] if out else "ok")
    else:
        logger.warning("synthetic_baseline_inject failed (rc=%d): %s", rc, err[-200:] if err else "unknown")


@tracked_job("cf_tunnel_verify")
async def cloudflare_tunnel_verify_job():
    """每日 Cloudflare Tunnel 健康驗證（ADR-0015/0016）— Python 原生實作

    檢查 7 項：本機 health / 公網 health / TLS / Manifest POST-only /
    Manifest 拒 GET / ACP 無 token 應拒 / Feedback 無 token 應拒。
    失敗時寫入 wiki/log.md 並 logger.error。
    只在有 MISSIVE_PUBLIC_URL (且含 cksurvey.tw) 時執行。

    ⚠️ 2026-07-30 改為 Python httpx 原生（原本呼叫
    `scripts/ops/verify-cloudflare-tunnel.ps1`）：
    5/27 廢 PM2 改純 Docker 後，Linux 容器內**沒有 pwsh/powershell**，
    原碼在 `shutil.which` 找不到時 `logger.warning + return` →
    **cron 記 success 但什麼都沒驗**，公網監控實質失效數月（沉默成功家族）。
    .ps1 保留供 host 手動執行（輸出較豐富、含診斷提示）。
    """
    import httpx

    public_url = os.getenv("MISSIVE_PUBLIC_URL", "").rstrip("/")
    if "cksurvey.tw" not in public_url:
        # 本機/開發部署跳過屬正常；但**生產環境**沒有這個值＝config drift（L70 同型），
        # 不可 debug-skip：那正是「cron 記 success 卻什麼都沒驗」的第二個成因。
        if os.getenv("ENVIRONMENT", "").lower() in ("production", "prod"):
            logger.error(
                "cf_tunnel_verify: 生產環境未設 MISSIVE_PUBLIC_URL（實得 %r）— "
                "raise 供 cron watchdog 抓（防 silent no-op）",
                public_url,
            )
            raise RuntimeError("cf_tunnel_verify: 生產環境缺 MISSIVE_PUBLIC_URL 設定")
        logger.debug("cf_tunnel_verify: 非公網部署，跳過")
        return

    local_url = os.getenv("MISSIVE_LOCAL_URL", "http://localhost:8001").rstrip("/")

    # (名稱, method, url, body, 期望狀態碼集合)
    checks = [
        ("1. 本機 health", "GET", f"{local_url}/api/health", None, {200}),
        ("2. CF Tunnel health", "GET", f"{public_url}/api/health", None, {200}),
        ("3. TLS 憑證", "GET", f"{public_url}/api/health", None, {200}),
        # 2026-08-27 修：這一項原本不帶憑證打 POST 並期望 **200**，而 2026-08-21 已把
        # `/api/ai/agent/tools` 改為需要 `X-Service-Token`（在那之前公網未登入、
        # 帶一枚公開可取的 CSRF token 就拿得到整份工具清冊）⇒ **它從 08-21 起就是紅的**。
        #
        # 紅了 6 天沒人處理，因為結果只寫進 `cf-tunnel-verify.json`，
        # 而讀它的 producer watchdog 直到今天的月度覆盤才把它印出來。
        #
        # 當時修了 `integration_e2e_validation`（chain_3 改帶 token），
        # **同一件事的第二個消費端沒有一起修** —— L81「換了出口就要換整條鏈」。
        #
        # 改為驗「沒有憑證就要被擋」，與下面第 6、7 項同一個形狀。
        # 刻意不在這裡帶 token：這一項要回答的是「公網有沒有被保護」，
        # 而「帶對 token 會回 200」由 `integration_e2e_validation` 驗（它拿得到 env）。
        ("4. Manifest 無 token", "POST", f"{public_url}/api/ai/agent/tools", {}, {401, 403}),
        # 405（方法不符）或 404（API 命名空間不 fallback SPA）皆代表「GET 未被服務」＝政策生效。
        # 2026-07-30 前此檢查恆 FAIL：spa_fallback 未排除 /api/* → 回 200 index.html。
        ("5. Manifest 拒 GET", "GET", f"{public_url}/api/ai/agent/tools", None, {404, 405}),
        (
            "6. ACP 無 token", "POST", f"{public_url}/api/hermes/acp",
            {"session_id": "verify", "messages": [{"role": "user", "content": "ping"}]},
            {401, 403},
        ),
        (
            "7. Feedback 無 token", "POST", f"{public_url}/api/hermes/feedback",
            {"session_id": "v", "skill_name": "x", "outcome": "success", "latency_ms": 1},
            {401, 403},
        ),
    ]

    lines: list[str] = []
    failed = 0
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        for name, method, url, body, expected in checks:
            try:
                resp = await client.request(method, url, json=body) if body is not None \
                    else await client.request(method, url)
                status: object = resp.status_code
                ok = resp.status_code in expected
            except Exception as e:  # 連線層失敗（DNS/TLS/tunnel down）
                status, ok = f"ERR({type(e).__name__})", False
            if not ok:
                failed += 1
            lines.append(
                f"  {'✓' if ok else '✗'} {name:<24} {status}  (expected {sorted(expected)})"
            )

    report = "\n".join(lines)
    from app.core.paths import PROJECT_ROOT as project_root  # v6.10 P1-E SSOT

    # ⭐ 產出可驗結果檔（2026-07-30）：驗證型 job 也必須留下「真的驗過」的證據，
    # 否則 cron 記 success 與「什麼都沒驗」在外部完全無法區分（本 job 即前科）。
    # 由 producer_output_watchdog 的 file_fresh 信號監測新鮮度。
    try:
        import json as _json
        out_dir = project_root / "wiki" / "memory" / "integration-health"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "cf-tunnel-verify.json").write_text(
            _json.dumps(
                {
                    "checked_at": datetime.now().isoformat(timespec="seconds"),
                    "public_url": public_url,
                    "passed": len(checks) - failed,
                    "total": len(checks),
                    "overall": "PASS" if failed == 0 else "FAIL",
                    "report": lines,
                },
                ensure_ascii=False, indent=1,
            ),
            encoding="utf-8",
        )
    except Exception as e:  # 寫檔失敗不可吞（否則 watchdog 也看不到）
        logger.error("cf_tunnel_verify: 結果檔寫入失敗: %s", e, exc_info=True)

    if failed == 0:
        logger.info("cf_tunnel_verify: PASS %d/%d\n%s", len(checks), len(checks), report)
        return {"checks_passed": len(checks), "reason": "ok"}

    logger.error(
        "cf_tunnel_verify: FAIL %d/%d\n%s", failed, len(checks), report
    )
    log_path = project_root / "wiki" / "log.md"
    if log_path.exists():
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        log_path.write_text(
            log_path.read_text(encoding="utf-8")
            + f"\n## {ts} — CF Tunnel verify FAIL ({failed}/{len(checks)})\n"
            + f"```\n{report}\n```\n",
            encoding="utf-8",
        )


@tracked_job("tender_refresh_pending")
async def tender_refresh_pending_job():
    """標案狀態更新 — 每日重查等標期標案的決標結果"""
    from app.db.database import async_session_maker

    logger.info("開始標案狀態更新")
    try:
        async with async_session_maker() as db:
            from app.services.tender.cache import refresh_pending_tenders
            result = await refresh_pending_tenders(db, limit=30)
            logger.info(f"標案狀態更新完成: checked={result['checked']}, updated={result['updated']}")
    except Exception as e:
        logger.error(f"標案狀態更新失敗: {e}", exc_info=True)


@tracked_job("tender_subscription")
async def tender_subscription_check_job():
    """標案訂閱檢查 — 每日 3 次比對 PCC API，新公告 → 系統+LINE 通知"""
    from app.db.database import async_session_maker

    logger.info("開始執行標案訂閱檢查")
    try:
        async with async_session_maker() as db:
            from app.services.tender.subscription_scheduler import check_all_subscriptions
            result = await check_all_subscriptions(db)
            logger.info(
                f"標案訂閱檢查完成: checked={result['checked']}, notified={result['notified']}"
            )
    except Exception as e:
        logger.error(f"標案訂閱檢查失敗: {e}", exc_info=True)


@tracked_job("tender_business_recommend")
async def tender_business_recommend_job():
    """標案業務推薦 LINE 推送 (ADR-0046 Phase 4)

    每日 09:00 跑 — 推「過去 1 日新增 + 預算 ≥ 100萬 + 合作機關」標案。

    2026-06-23 owner 決策：LINE 免費月配額 200 則須優先分配給「晨報為主 + 坤哥相關
    紀錄」，標案推送暫緩以節省額度。預設 TENDER_LINE_PUSH_ENABLED=false（不推）；
    enrichment/scraper/dashboard 預熱等資料 job 不受影響，/tender UI 仍即時更新。
    要恢復標案 LINE 推送：設 TENDER_LINE_PUSH_ENABLED=true。
    """
    from app.db.database import async_session_maker

    # 契約規則 2（2026-07-30 落實）：回傳 detail 讓 watchdog 能區分「政策關閉」與「真失敗」。
    # 原本此 job 不回傳任何東西，registry 又用 db_table_today 監控 tender_recommendation_history
    # （該表自 2026-06-23 關閉推送後即停寫）→ 每日 07:00 對 owner 誤報「排程產出異常」。
    if os.getenv("TENDER_LINE_PUSH_ENABLED", "false").lower() != "true":
        logger.info(
            "標案業務推薦 LINE 推送已暫緩（TENDER_LINE_PUSH_ENABLED=false，"
            "節省 LINE 月配額供晨報/坤哥使用）"
        )
        return {"pushed": 0, "reason": "line_push_disabled"}

    logger.info("開始執行標案業務推薦推送")
    try:
        async with async_session_maker() as db:
            from app.services.tender.business_recommendation import push_daily_recommendations
            result = await push_daily_recommendations(db, days_back=1)
            logger.info(
                f"標案業務推薦完成: found={result['found']} pushed={result['pushed']} "
                f"dup={result['skipped_duplicate']} err={result['errors']}"
            )
            return {
                "pushed": result["pushed"],
                "found": result["found"],
                "reason": "ok" if result["found"] else "no_match",
            }
    except Exception as e:
        # 契約規則 4b 精神：原本只 log 不 raise → @tracked_job 仍記 success，
        # 代表 gate 打開後真的失敗也只會靜默（沉默成功家族）。
        logger.error(f"標案業務推薦失敗: {e}", exc_info=True)
        raise


@tracked_job("tender_pcc_enrichment")
async def tender_pcc_enrichment_job():
    """ezbid → PCC enrichment 每日 03:30 執行 (ADR-0046 Phase 3)

    對未 matched 的 ezbid records 跑 fuzzy match + HIGH only auto-link。
    使用 exact title match strict guard 避免 false positive。
    """
    from app.db.database import async_session_maker

    logger.info("開始執行 ezbid → PCC enrichment")
    try:
        async with async_session_maker() as db:
            # 2026-08-26（owner：「無法成功等同無用」）：從 pg_trgm 換成精確鍵。
            # 舊的 `enrich_all_unmatched` 用 similarity() 計分、門檻 0.85，而
            # **pg_trgm 對中文無效** —— 標題與機關名完全相同時 similarity 仍是
            # 0.0000 ⇒ 分數結構上永遠到不了。它每天都在跑而只配到 4.5%。
            # 換成三個精確條件（job_number ＋ 標題前 20 字 ＋ 機關名）後
            # 一次補上 10,199 筆，配對率 4.5% → 25.1%。
            from app.services.tender.enrichment import (
                enrich_all_exact, enrich_all_fallback,
            )
            # 兩階段：① 有案號 → 三個精確條件；② 無案號（改版前的舊資料）
            # → 標題＋機關名＋公告日差 ≤3 天，confidence 記 0.9 以保留差別。
            s1 = await enrich_all_exact(db, dry_run=False)
            s2 = await enrich_all_fallback(db, dry_run=False)
            stats = {
                "exact": s1["applied"], "fallback": s2["applied"],
                "applied": s1["applied"] + s2["applied"],
            }
            logger.info(f"ezbid PCC 配對完成: {stats}")
            return stats
    except Exception as e:
        logger.error(f"ezbid → PCC enrichment 失敗: {e}", exc_info=True)


@tracked_job("tender_detail_enrichment")
async def tender_detail_enrichment_job():
    """標案詳情補料 —— 每日 03:45（避開 03:30 的 ezbid↔PCC 配對）。

    ⚠️ 2026-08-26：`detail_enrichment.py` 從建立起**沒有任何人呼叫它**
    （全 repo 零 import）。它的檔頭寫著「不掛自動 cron」（06-17，因 PCC 反爬），
    但那條對 **ezbid 來源不適用** —— ezbid 的 `unit_id` 本身就是點分 org_id，
    直接查 openfun 即可，**完全不打 PCC 詳情頁**、零反爬風險。

    所以這裡只跑 `only_dotted_org=True`（＝ezbid 那一段）。
    `source='pcc'` 需要 2-hop 取 org_id，維持手動/低量，不進排程。

    量：limit 40 × 節流 0.8s ≈ 32 秒、40 次 openfun 請求／日。
    `detail_enriched_at` 會標記已試過，所以不會每天重撞同一批。
    """
    from app.db.database import async_session_maker

    try:
        async with async_session_maker() as db:
            from app.services.tender.detail_enrichment import enrich_recent
            stats = await enrich_recent(
                db, days_back=14, limit=40, only_unenriched=True, only_dotted_org=True,
            )
            logger.info(f"標案詳情補料完成: {stats}")
            return stats
    except Exception as e:
        logger.error(f"標案詳情補料失敗: {e}", exc_info=True)
        raise


@tracked_job("tender_dashboard_warm")
async def tender_dashboard_warm_job():
    """標案儀表板 cache 預熱 — 每 5 min 主動寫 Redis cache，避用戶 first hit 等 scraper

    背景：dashboard() cache miss latency ~525ms（需並行 ezbid + PCC + g0v scrape）
    對策：scheduler 每 5min 主動 hit svc.dashboard()，配合 TTL 600s = 用戶永遠 cache hit ~12ms

    L51 (2026-05-28)：配合 analytics.py TTL 3900→600 修法，落地零 cold miss 設計
    """
    logger.info("開始執行標案儀表板 cache 預熱")
    try:
        from app.services.tender.analytics import TenderAnalyticsService
        svc = TenderAnalyticsService()
        result = await svc.dashboard()
        logger.info(
            "標案儀表板 cache 預熱完成: total_found=%d",
            result.get("total_found", 0),
        )
    except Exception as e:
        logger.error("標案儀表板 cache 預熱失敗: %s", e, exc_info=True)


KUNGE_URL_BASE = "https://missive.cksurvey.tw/kunge"


def _kunge_quick_actions(tab: str = "memory") -> str:
    """L51.7 Sprint 2.P2.9：給 LINE 訊息加 /kunge quick action 引流 web 入口

    Args:
        tab: chat / identity / memory / evolution / nebula / dialogues / ops
    """
    return (
        f"\n\n📲 Web 完整檢視:\n"
        f"  {KUNGE_URL_BASE}/{tab}"
    )


def _parse_red_steps(out: str) -> list[str]:
    """從 fitness runner 的輸出解析「哪幾步紅」。

    daily 與 weekly 的摘要格式相同（`✗ <步驟名>` 逐行 + 一行 `N step(s) RED` 總計），
    2026-08-11 從 weekly job 內抽成模組層級共用 —— 複製第二份就是製造會漂的兩份判定。

    解析不到就回空 list，**不猜**：空 list 會讓呼叫端的差異比對自動退回
    「只報連紅次數」的舊行為，而不是報出錯誤的差異。

    去 ANSI 色碼用逐字元過濾而非 re —— 本模組沒有 import re，為了一行解析
    多一個 import 不划算（而我最初就是直接用了不存在的 `re` 與 `_strip_ansi`，
    靠實際查證才發現）。
    """
    def _clean(line: str) -> str:
        out_chars, in_esc = [], False
        for ch in line:
            if ch == "\x1b":
                in_esc = True
                continue
            if in_esc:
                if ch.isalpha():
                    in_esc = False
                continue
            out_chars.append(ch)
        return "".join(out_chars).strip()

    return sorted({
        s[1:].strip()
        for s in (_clean(ln) for ln in (out or "").splitlines())
        # 只取「✗ 開頭且不是那行總計」的行
        if s.startswith("✗") and "step(s) RED" not in s and len(s) > 2
    })


def _daily_red_should_notify(red_streak: int, new_steps: list[str]) -> bool:
    """daily RED 要不要推播。抽成純函式才驗得了鑑別力 —— 否則「不推」和「壞掉」長得一樣。

    · 首日 RED、或出現新的紅步驟 → 推（這是新資訊）
    · 連續相同 → 不逐日重複，但每 7 天提醒一次，避免無限靜默
    """
    if red_streak <= 1 or new_steps:
        return True
    return red_streak % 7 == 0


@tracked_job("fitness_weekly")
async def fitness_weekly_job():
    """Tier 2 Weekly 檢核的**接收者**（2026-08-07 起不再自己執行）。

    真正的執行在 host（Windows 排程 CK_Missive-Fitness-Weekly →
    scripts/checks/run_fitness_weekly_host.sh），因為 weekly 多數步驟需要 docker
    CLI／powershell／sibling repo／host 目錄結構，容器裡本來就做不到。

    本 job 每週日 02:30 讀 host 寫下的交接檔（wiki/memory/fitness_weekly_last_run.json，
    wiki 為雙向 bind mount），負責：寫 history、算連紅週數、連 2 週 RED 發 LINE digest，
    並在**交接檔缺失或過期時直接 RED** —— 「host 排程沒跑」不得靜靜地變成「檢核通過」。

    對應 docs/architecture/FITNESS_LAYERED_EXECUTION_SOP_20260530.md Tier 2
    """
    import json
    import os
    from datetime import datetime
    from pathlib import Path

    # 2026-06-02 L52 family 修：CK_PROJECT_ROOT=/app，.parent 會變 / → script 找 /scripts (不存在，
    # 實際 mount /app/scripts) → 8 cron job silent 早退。每日覆盤停 05-31+無 LINE 即此。移除 .parent。
    project_root = Path(os.getenv("CK_PROJECT_ROOT", "/app"))

    # 2026-08-07：本 job 由「執行者」改為「接收者」。
    #
    # weekly 的多數步驟需要 host 才有的東西（docker CLI／powershell／sibling repo／
    # host 目錄結構）—— 實測容器內 32 步有 6 步 RED，host 只有 1 步。而在此之前
    # CRLF 更讓它連 bash 都過不了（2026-W23~W31 連 9 週 RED，一行檢核都沒跑過）。
    #
    # 現在真正的執行在 host（Windows 排程 CK_Missive-Fitness-Weekly →
    # run_fitness_weekly_host.sh），結果經 wiki/（雙向 bind mount）交接過來。
    # 本 job 保留既有的接收者角色：寫 history、算連紅週數、發 LINE digest。
    #
    # 交接檔帶時間戳 → **host 排程若停掉，這裡會因為結果過期而 RED**，
    # 「檢核沒跑」不會靜靜地變成「檢核通過」。
    handoff = project_root / "wiki" / "memory" / "fitness_weekly_last_run.json"
    STALE_DAYS = 8  # 週排程 + 1 天餘裕（機器關機那天補跑也涵蓋）

    out = ""
    if not handoff.exists():
        rc = 2
        out = (
            f"host 端 weekly 交接檔不存在：{handoff}\n"
            "→ Windows 排程 CK_Missive-Fitness-Weekly 可能未註冊或從未成功執行。"
        )
        logger.error("fitness_weekly: %s", out.replace("\n", " "))
    else:
        try:
            payload = json.loads(handoff.read_text(encoding="utf-8"))
            ran_at = datetime.fromisoformat(str(payload["ts"]).replace("Z", "+00:00"))
            age_days = (datetime.now(ran_at.tzinfo) - ran_at).total_seconds() / 86400
            if age_days > STALE_DAYS:
                rc = 2
                out = (
                    f"host 端 weekly 結果已過期 {age_days:.1f} 天（門檻 {STALE_DAYS}）\n"
                    "→ 排程沒在跑，不是檢核通過。"
                )
                logger.error("fitness_weekly: %s", out.replace("\n", " "))
            else:
                rc = int(payload.get("rc", 2))
                out = str(payload.get("tail", ""))
                logger.info("fitness_weekly: 讀入 host 結果 rc=%s（%.1f 天前）", rc, age_days)
        except Exception as e:  # noqa: BLE001
            rc = 2
            out = f"host 端 weekly 交接檔無法解析：{e}"
            logger.error("fitness_weekly: %s", out, exc_info=True)

    # 紀錄本週結果到 wiki/memory/fitness_weekly_history.json
    state_file = project_root / "wiki" / "memory" / "fitness_weekly_history.json"
    today = datetime.now().strftime("%Y-W%V")
    history = {}
    if state_file.exists():
        try:
            history = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 2026-08-09：一併記下**是哪幾步紅**。
    #
    # 原本只記 rc/status，於是「連續 N 週 RED」這個訊號無法回答最重要的問題：
    # 這一週跟上一週紅的是不是同一批？現況已連紅 10 週（多為 owner 待辦的
    # 長期項目），若第 11 週冒出一個**新**的 RED，在只有 rc 的歷史裡
    # 與那些舊的長得一模一樣 —— 正是 L88 說的「永遠是紅的＝訊號失去意義」。
    #
    # 解析 runner 摘要段的 `✗ <步驟名>` 行 —— 實作見模組層級的 _parse_red_steps
    # （daily 與 weekly 的摘要格式相同，故共用一份；2026-08-11 從此處抽出）。
    red_steps = _parse_red_steps(out)

    history[today] = {
        "rc": rc,
        "status": "PASS" if rc == 0 else "RED",
        "ts": datetime.now().isoformat(),
        "red_steps": red_steps,
    }
    # 只保留最近 12 週
    keys = sorted(history.keys())[-12:]
    history = {k: history[k] for k in keys}

    # 2026-08-21：`history_ok` 原本**從來沒有在這個函式裡定義過**，
    # 而下方兩處 return 都把它放進 detail ⇒ 每次執行到 return 就 NameError。
    # （另一個函式在 2607 行有同名變數，pyflakes 的 F821 才把它揪出來。）
    #
    # 語意就是「這一輪的歷史檔有沒有寫成功」—— 寫不進去時 red_streak
    # 會從殘缺的歷史算出來，那個數字不能當真，所以要讓收的人知道。
    history_ok = True
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        history_ok = False
        logger.warning(f"weekly fitness history save failed: {e}")

    # 2026-08-05：一律回 detail（含連紅週數）—— 否則 cron_events 只有 success，
    # 而 W23~W31 連續 9 週 RED 這件事在自動監看裡完全看不到。
    red_streak = 0
    for w in sorted(history.keys(), reverse=True):
        if history[w].get("status") != "RED":
            break
        red_streak += 1

    if rc == 0:
        logger.info("Fitness Tier 2 Weekly: all step passed")
        return {"rc": 0, "status": "PASS", "red_streak": 0, "delivered": 1,
                "history_ok": history_ok}

    # 偵測連續 2 週 RED → 通知
    consecutive_red = red_streak >= 2

    if not consecutive_red:
        # 首次 RED 刻意不通知（等下週確認，避免單次抖動就叫人）——
        # 這是設計上的靜默，故 delivered=1：機制運作正常。
        logger.info("Fitness Tier 2 Weekly RED (本週首次)，等下週確認")
        return {"rc": rc, "status": "RED", "red_streak": red_streak, "delivered": 1}

    # 連續 2 週 RED → 進 digest
    notified = False
    try:
        tail_lines = (out or "").splitlines()[-30:]
        digest = "\n".join(tail_lines)

        # 2026-08-09：**先講與上週的差異**，再貼原始輸出。
        #
        # 連紅 10 週的情況下，「連續 RED 已 N 週」每週長得一模一樣，
        # 讀的人很快就學會略過它 —— 而那正是新問題出現時最需要被看見的時刻。
        # 可行動的訊號是「這週多了什麼」，不是「還是紅的」。
        weeks = sorted(history.keys())
        prev = history.get(weeks[-2], {}).get("red_steps") if len(weeks) >= 2 else None
        if red_steps and prev is not None:
            new = [s for s in red_steps if s not in prev]
            gone = [s for s in prev if s not in red_steps]
            if new:
                delta = "🆕 本週新增 RED：" + "、".join(new)
            elif gone:
                delta = "本週未新增；已消失：" + "、".join(gone)
            else:
                delta = f"與上週完全相同（{len(red_steps)} 步），無新增"
        else:
            # 解析不到步驟名時退回舊行為，不編造差異
            delta = f"RED {len(red_steps)} 步" if red_steps else "（未能解析步驟名）"

        body = (
            f"{delta}\n"
            f"連續 RED 已 {red_streak} 週\n"
            f"\n"
            f"{digest[:1500]}\n"
            f"\n"
            f"完整: scripts/checks/run_fitness_weekly.sh"
            + _kunge_quick_actions("ops")
        )
        # 2026-08-05：改走 digest（L81）。原本直推且不看回傳值 ——
        # push_admin 全通道失敗時只回 False，呼叫端無從得知。
        from app.services.integration.line_digest_buffer import queue_digest
        await queue_digest("🚨 每週檢核連續 RED", body)
        notified = True
    except Exception as push_e:
        logger.error("Fitness Tier 2 Weekly 告警入 digest 失敗: %s", push_e, exc_info=True)

    return {
        "rc": rc, "status": "RED", "red_streak": red_streak,
        "red_steps": red_steps,
        "delivered": 1 if notified else 0,
        "reason": None if notified else "digest_queue_failed",
        "history_ok": history_ok,
    }


@tracked_job("case_finance_bridge_selfheal")
async def case_finance_bridge_selfheal_job():
    """每日自動補齊承攬案件的財務橋樑（自我修復，2026-07-31）

    owner：「活化系統自我覆盤檢核與修復機制」。

    背景：`case_code` 是承攬案件通往財務/核銷的唯一橋樑（報價、費用核銷、
    核銷 QR 都靠它）。方案 B 已讓**新建**案件在建立當下就補上，但：
      * 既有資料仍可能有缺（2026-07-31 手動補了 187/188/190/191）
      * 未來若有新的寫入路徑繞過 ProjectService.create，又會再長出來

    偵測到就修，而不是等 fitness 標黃、等人來看 —— 這是「檢核」與「修復」的差別。

    安全性：
      * 只補**缺少**的（有值不動），冪等
      * 走 ProjectService 既有方法，與手動建立走同一條路
      * 金額一律留空（屬業務決策），只帶 contract_amount 當預算上限
      * 逐案 try：單一案件失敗不影響其他案件
      * 回傳 detail 供 watchdog 區分「合理 0」與「真失敗」（契約規則 2）
    """
    from sqlalchemy import select
    from app.db.database import async_session_maker
    from app.extended.models.core import ContractProject
    from app.services.contract.case_code import CaseCodeService
    from app.services.contract.core import ProjectService

    healed, failed = [], []
    async with async_session_maker() as db:
        rows = (await db.execute(
            select(ContractProject).where(ContractProject.case_code.is_(None))
        )).scalars().all()

        if not rows:
            logger.info("case_finance_bridge_selfheal: 無缺 case_code 的承攬案件")
            return {"healed": 0, "reason": "nothing_to_heal"}

        svc = ProjectService(db)
        for p in rows:
            # 每案獨立 savepoint：一案撞唯一鍵不得讓整批 session 進入失敗狀態
            #（首跑實測：第二筆 UniqueViolationError 後，同 session 後續操作全部連帶失敗）
            try:
                code = await CaseCodeService(db).generate_case_code(
                    "pm", p.year or 2026, p.category or "01",
                )
                p.case_code = code
                await db.flush()
                await svc._ensure_finance_container(p)
                await db.commit()
                healed.append(f"{p.project_code}->{code}")
            except Exception as e:  # noqa: BLE001
                await db.rollback()
                failed.append(f"{p.project_code}: {str(e)[:80]}")
                logger.warning("case_finance_bridge_selfheal 單案失敗 %s: %s", p.project_code, e)

    logger.info(
        "case_finance_bridge_selfheal: 修復 %d 案、失敗 %d 案 %s",
        len(healed), len(failed), healed[:5],
    )
    return {
        "healed": len(healed),
        "failed": len(failed),
        "reason": "ok" if not failed else "partial_failure",
        "detail": healed[:10],
    }


@tracked_job("daily_self_retrospective")
async def daily_self_retrospective_job():
    """v6.12 #4 升級版 — 每日 06:30 自我覆盤 7 面向 + LINE 推 owner

    Owner 反饋:
    > 是否能建構每日自我覆盤機制 以及核心服務議題
    > 避免規範現況落差 實現自我進化檢核 非重複錯誤
    > 已建構程式圖譜 llmwiki 等好像都無法自動化與覆盤

    對齊元覆盤 §4 進化原則 #4 (從「季初強制」升級「daily 自我覆盤」)
    """
    import os
    from pathlib import Path

    # 2026-06-02 L52 family 修：CK_PROJECT_ROOT=/app，.parent 會變 / → script 找 /scripts (不存在，
    # 實際 mount /app/scripts) → 8 cron job silent 早退。每日覆盤停 05-31+無 LINE 即此。移除 .parent。
    project_root = Path(os.getenv("CK_PROJECT_ROOT", "/app"))
    script = project_root / "scripts" / "checks" / "daily_self_retrospective.py"
    if not script.exists():
        logger.error("daily_self_retrospective: script not found at %s — raise 供 cron watchdog 抓 (防 silent no-op)", script)
        raise FileNotFoundError(f"cron script 缺失: {script}")

    logger.info("開始執行 Daily Self-Retrospective")
    rc, out, err = await _run_script_async(
        ["python", str(script)],
        cwd=str(project_root), timeout=300, job_name="daily_self_retrospective",
    )

    if rc != 0:
        logger.warning("daily_self_retrospective rc=%d", rc)
        return

    # 取 stdout 中 markdown 報告，推 LINE
    try:
        # 從 stdout 取 # Daily 之後內容（過濾 echo 行）
        report_md = ""
        in_report = False
        for line in (out or "").splitlines():
            if line.startswith("# Daily Self-Retrospective"):
                in_report = True
            if in_report:
                report_md += line + "\n"

        if report_md:
            body = (
                "🪞 Daily Self-Retrospective\n"
                f"\n"
                f"{report_md[:1800]}"  # LINE 訊息限制
                + _kunge_quick_actions("ops")
            )
            from app.services.contracts.facades.integration import IntegrationFacade
            await IntegrationFacade().push_admin_alert(title="", body=body, channel="line")
            logger.info("Daily Self-Retrospective LINE 推送完成")
    except Exception as e:
        logger.warning("Daily Self-Retrospective LINE push 失敗: %s", e)


@tracked_job("governance_dashboard_regen")
async def governance_dashboard_regen_job():
    """v6.12 解 owner「每次詢問都有缺漏」meta 問題

    每日 06:00 regenerate docs/architecture/GOVERNANCE_INTEGRATED_DASHBOARD.md
    整合 5 處 171+ 治理文件成 single SSOT view
    Session 啟動讀此檔取完整快照，無需重新 grep
    """
    import os
    from pathlib import Path

    # 2026-06-02 L52 family 修：CK_PROJECT_ROOT=/app，.parent 會變 / → script 找 /scripts (不存在，
    # 實際 mount /app/scripts) → 8 cron job silent 早退。每日覆盤停 05-31+無 LINE 即此。移除 .parent。
    project_root = Path(os.getenv("CK_PROJECT_ROOT", "/app"))
    script = project_root / "scripts" / "checks" / "generate_governance_dashboard.py"
    if not script.exists():
        logger.error("governance_dashboard_regen: script not found at %s — raise 供 cron watchdog 抓 (防 silent no-op)", script)
        raise FileNotFoundError(f"cron script 缺失: {script}")

    rc, out, err = await _run_script_async(
        ["python", str(script)],
        cwd=str(project_root), timeout=120, job_name="governance_dashboard_regen",
    )

    if rc != 0:
        logger.warning("governance_dashboard_regen rc=%d err=%s", rc, err[-200:] if err else "")
        return

    logger.info("governance_dashboard_regen: %s", out[-200:] if out else "ok")


@tracked_job("fitness_daily")
async def fitness_daily_job():
    """v6.12 治理進化 #2 — Tier 1 Daily 6 critical fitness step (~1 min)

    每日 02:00 跑 6 個 silent-failure 偵測 step，任一 RED → LINE 推 owner。

    對應 docs/architecture/FITNESS_LAYERED_EXECUTION_SOP_20260530.md Tier 1

    包含 step:
    - 38 docker_compose_volume_consistency
    - 40 compose/dockerfile healthcheck SSOT
    - 47 startup race condition
    - 57 container env alignment
    - 58 agent_query starvation
    - 60 container image freshness
    """
    import os
    from pathlib import Path

    # 2026-06-02 L52 family 修：CK_PROJECT_ROOT=/app，.parent 會變 / → script 找 /scripts (不存在，
    # 實際 mount /app/scripts) → 8 cron job silent 早退。每日覆盤停 05-31+無 LINE 即此。移除 .parent。
    project_root = Path(os.getenv("CK_PROJECT_ROOT", "/app"))
    script = project_root / "scripts" / "checks" / "run_fitness_daily.sh"
    if not script.exists():
        logger.error("fitness_daily: script not found at %s — raise 供 cron watchdog 抓 (防 silent no-op)", script)
        raise FileNotFoundError(f"cron script 缺失: {script}")

    logger.info("開始執行 Fitness Tier 1 Daily")
    rc, out, err = await _run_script_async(
        ["bash", str(script), "--strict"],
        cwd=str(project_root), timeout=300, job_name="fitness_daily",
    )

    # 2026-08-05：回 detail —— 原本一律 return None，於是 cron_events 只看得到
    # 「有跑」而看不到「跑出什麼」，這支檢核階梯的最底層自己反而不在 producer
    # registry 的監看範圍內（檢核者不被檢核）。
    # delivered 的語意＝「跑完且結論有送達」。對 producer 契約而言，
    # RED 本身不是故障（那是檢核在做事），**RED 卻沒人收到才是故障**。
    # 2026-08-11：daily 補上與 weekly 同構的「連續紅」機制。
    #
    # 為什麼要補：08-09～08-11 連續三天 RED，每天推的是**內容一模一樣**的
    # 30 行 tail（兩支檢核在容器內不可能通過）。每天推同一則等於訓練人略過它，
    # 而那正是新問題出現時最需要被看見的時刻 —— weekly 早有 red_streak 與
    # delta 敘述，daily 沒有，於是最高頻的那一層反而最吵。
    #
    # 記 history 也讓「連續紅」本身在自動監看裡看得見（先前只有當日 rc）。
    # 2026-08-11：`import json` 是必要的 —— 本函式的區域 import 原本只有 os/Path，
    # 而我第一版直接用了 json，於是寫檔在 except 裡變成一行 warning，
    # **回傳值卻完全正常**（red_streak=1、red_steps 有值），看起來像機制運作中。
    # 那正是我今天一整天在治的形態，自己又犯一次；靠看完整 stdout 才發現。
    import json  # noqa: PLC0415
    red_steps = _parse_red_steps(out)
    state_file = project_root / "wiki" / "memory" / "fitness_daily_history.json"
    today = datetime.now().strftime("%Y-%m-%d")
    history = {}
    history_ok = True
    if state_file.exists():
        try:
            history = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception as e:
            # 讀不到不得靜默：history 一旦讀不到，red_streak 永遠算成 1
            # → 永遠判「首次 RED」→ 每天都推，機制退化回原狀且沒有人會知道。
            history_ok = False
            logger.warning("daily fitness history 讀取失敗（連續紅將無法累計）: %s", e)
    history[today] = {
        "rc": rc,
        "status": "PASS" if rc == 0 else "RED",
        "ts": datetime.now().isoformat(),
        "red_steps": red_steps,
    }
    # 只保留最近 30 天
    history = {k: history[k] for k in sorted(history.keys())[-30:]}
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        history_ok = False
        logger.warning("daily fitness history save failed: %s", e)

    days = sorted(history.keys())
    red_streak = 0
    for d in reversed(days):
        if history[d].get("status") != "RED":
            break
        red_streak += 1

    if rc == 0:
        # 2026-08-11：原本寫死「all 6 step passed」，實際是 12 步 —— 又一份會漂的第二份事實
        # （08-05 已把兩支 runner 的表頭改成自我推導，這行漏了）。
        # 步數只由 runner 自己講，這裡不重複宣稱。
        logger.info("Fitness Tier 1 Daily: all step passed")
        return {"rc": 0, "status": "PASS", "red_streak": 0, "delivered": 1,
                "history_ok": history_ok}

    # 與前一天比較：有沒有**新**的紅。無法解析步驟名時不編造差異。
    prev = history.get(days[-2], {}).get("red_steps") if len(days) >= 2 else None
    new_steps = [s for s in red_steps if s not in prev] if (red_steps and prev is not None) else []
    gone_steps = [s for s in prev if s not in red_steps] if (red_steps and prev is not None) else []

    # 推播決策 —— 只在「有新東西」或「該提醒了」時出聲：
    #   · 首日 RED、或出現新的紅步驟 → 推（這是新資訊）
    #   · 連續相同 → 不逐日重複，但每 7 天提醒一次，避免無限靜默
    # 不推時 delivered 仍為 1：那是設計上的抑制，機制運作正常
    #（同 weekly「首次 RED 刻意不通知」的既有語意）。
    if not _daily_red_should_notify(red_streak, new_steps):
        logger.info(
            "Fitness Tier 1 Daily RED（連續 %d 天、與昨日相同 %s）—— 抑制重複推播",
            red_streak, red_steps or "（未能解析步驟名）",
        )
        return {
            "rc": rc, "status": "RED", "red_streak": red_streak,
            "red_steps": red_steps, "delivered": 1, "suppressed": "same_as_yesterday",
            "history_ok": history_ok,
        }

    logger.warning("Fitness Tier 1 Daily RED rc=%d（連續 %d 天），queueing digest", rc, red_streak)
    notified = False
    try:
        # 先講差異，再貼原始輸出 —— 可行動的訊號是「今天多了什麼」，不是「還是紅的」。
        if new_steps:
            delta = "🆕 今日新增 RED：" + "、".join(new_steps)
        elif gone_steps:
            delta = "今日未新增；已消失：" + "、".join(gone_steps)
        elif red_streak <= 1:
            delta = ("首次 RED：" + "、".join(red_steps)) if red_steps else "首次 RED"
        else:
            delta = f"連續 {red_streak} 天相同（{len(red_steps)} 步），此為每 7 天提醒"

        tail_lines = (out or "").splitlines()[-30:]
        digest = "\n".join(tail_lines)
        body = (
            f"{delta}\n"
            f"連續 RED 已 {red_streak} 天\n"
            f"\n"
            f"{digest[:1500]}\n"
            f"\n"
            f"立即修法或排 sprint\n"
            f"完整: scripts/checks/run_fitness_daily.sh"
            + _kunge_quick_actions("ops")
        )
        # 2026-08-05：改走 digest（L81）。原本直推 push_admin_alert，
        # 且**不檢查回傳值** —— 該方法送不出去時只回 False 並 log error，
        # 對呼叫端而言「送到」與「沒送到」長得一模一樣。
        from app.services.integration.line_digest_buffer import queue_digest
        await queue_digest("🚨 每日檢核 RED", body)
        notified = True
    except Exception as push_e:
        logger.error("Fitness Tier 1 Daily 告警入 digest 失敗: %s", push_e, exc_info=True)

    return {
        "rc": rc, "status": "RED", "red_streak": red_streak,
        "red_steps": red_steps,
        "delivered": 1 if notified else 0,
        "reason": None if notified else "digest_queue_failed",
        "history_ok": history_ok,
    }


@tracked_job("crystal_review_overdue")
async def crystal_review_overdue_alarm_job():
    """L51.7 (2026-05-30) crystallization workflow watchdog

    每週日 09:30 掃 wiki/memory/proposals/，若有 status=pending 超過 N 天
    主動推 LINE 提示 owner approve（避「proposals → 0 crystals」死局）。

    L51.7 覆盤揭發: 4 proposals 累積 1+ 月無 owner action，crystallization=0
    → 學習閉環死。weekly alarm 強迫 forcing function。
    """
    import os
    from datetime import datetime, timedelta
    from pathlib import Path

    logger.info("開始執行 crystal_review_overdue alarm")
    try:
        proposals_dir = Path(os.getenv("CK_WIKI_DIR", "/app/wiki")) / "memory" / "proposals"
        if not proposals_dir.exists():
            logger.info("No proposals directory, skip")
            return

        overdue_days_threshold = 7  # >7d pending 即提示
        now = datetime.now()
        cutoff = now - timedelta(days=overdue_days_threshold)
        overdue_list = []

        for f in proposals_dir.glob("*.md"):
            try:
                text = f.read_text(encoding="utf-8")
                # 取 frontmatter 內 proposed_at
                import re as _re
                m = _re.search(r"^proposed_at:\s*['\"]?(.+?)['\"]?\s*$", text, _re.MULTILINE)
                status_m = _re.search(r"^status:\s*pending", text, _re.MULTILINE)
                if not (m and status_m):
                    continue
                proposed_at_str = m.group(1).split("+")[0]  # 去 tz suffix
                try:
                    proposed_at = datetime.fromisoformat(proposed_at_str)
                except Exception:
                    continue
                if proposed_at < cutoff:
                    age_days = (now - proposed_at).days
                    overdue_list.append((f.name, age_days))
            except Exception:
                continue

        if not overdue_list:
            logger.info(f"crystal review: 0 overdue (threshold={overdue_days_threshold}d)")
            return

        overdue_list.sort(key=lambda x: x[1], reverse=True)
        lines = [
            f"🔔 Crystallization 提示 ({len(overdue_list)} proposals overdue ≥{overdue_days_threshold}d)",
            "",
            f"等 owner 看 1 次即可啟動學習閉環:",
            "",
        ]
        for fname, age in overdue_list[:5]:
            lines.append(f"  • {fname[:40]} ({age}d ago)")
        lines.extend([
            "",
            "操作: 直接編輯 wiki/memory/proposals/*.md",
            "approve → 寫 SOUL/intent_rules",
            "delete → 拒絕",
        ])
        body = "\n".join(lines) + _kunge_quick_actions("memory")
        from app.services.contracts.facades.integration import IntegrationFacade
        await IntegrationFacade().push_admin_alert(title="", body=body, channel="line")
        logger.info(f"crystal review alarm pushed: {len(overdue_list)} overdue")
    except Exception as e:
        logger.error("crystal_review_overdue alarm 失敗: %s", e, exc_info=True)


@tracked_job("proposal_aging_alert")
async def proposal_aging_alert_job():
    """v6.13 (2026-05-31) — 每週日 02:20 推 owner pending proposal aging

    對齊 owner「學習閉環 + 日誌 + 坤哥真活」訴求

    揭發背景:
    - 5/31 self-retro RED 主因 = 學習閉環 flow=0% (crystals=0)
    - 5 proposal pending 多達 40 天 (2 LOW intent + 3 MEDIUM soul)
    - owner 健忘 / 決策成本高 = 結晶閉環斷層真因

    本 job 主動揭發 + 降低 owner 決策成本:
    - 列風險分級 (LOW/MEDIUM)
    - 含完整 reason + age + target file
    - 含 approve curl SOP
    - 不繞 owner approve (依 crystal_applier 7 step 安全 SOP)
    """
    import os
    from pathlib import Path

    # 2026-06-02 L52 family 修：CK_PROJECT_ROOT=/app，.parent 會變 / → script 找 /scripts (不存在，
    # 實際 mount /app/scripts) → 8 cron job silent 早退。每日覆盤停 05-31+無 LINE 即此。移除 .parent。
    project_root = Path(os.getenv("CK_PROJECT_ROOT", "/app"))
    script = project_root / "scripts" / "checks" / "proposal_aging_alert.py"
    if not script.exists():
        logger.error("proposal_aging_alert: script not found at %s — raise 供 cron watchdog 抓 (防 silent no-op)", script)
        raise FileNotFoundError(f"cron script 缺失: {script}")

    rc, out, _ = await _run_script_async(
        ["python", str(script), "--min-age-days", "7"],
        cwd=str(project_root), timeout=30, job_name="proposal_aging_alert",
    )
    # rc=1 = 揭發 aging (主動推 owner)
    # rc=0 = 無 aging (健康)
    logger.info("proposal_aging_alert rc=%d", rc)


@tracked_job("integration_e2e_validation")
async def integration_e2e_validation_job():
    """v6.13 (2026-05-31) — 每日 02:05 跑 5 鏈整合 E2E 驗證

    對齊 owner「坤哥+Hermes+智能體 整合連通真活 突破性 非一次性」訴求

    5 驗證鏈:
    1. Missive /health (業務量)
    2. Missive /api/ai/kunge/snapshot (坤哥 snapshot)
    3. Missive /api/ai/agent/tools (manifest 含 kunge_snapshot)
    4. Hermes gateway HTTP healthy (8642/9119)
    5. ck-missive-bridge skill 對齊 (chain 3 已驗為主)

    任一鏈斷 → LINE 推 owner + 寫 integration-health marker
    """
    import os
    from pathlib import Path

    # 2026-06-02 L52 family 修：CK_PROJECT_ROOT=/app，.parent 會變 / → script 找 /scripts (不存在，
    # 實際 mount /app/scripts) → 8 cron job silent 早退。每日覆盤停 05-31+無 LINE 即此。移除 .parent。
    project_root = Path(os.getenv("CK_PROJECT_ROOT", "/app"))
    script = project_root / "scripts" / "checks" / "integration_e2e_validation.py"
    if not script.exists():
        logger.error("integration_e2e_validation: script not found at %s — raise 供 cron watchdog 抓 (防 silent no-op)", script)
        raise FileNotFoundError(f"cron script 缺失: {script}")

    rc, out, err = await _run_script_async(
        ["python", str(script)],
        cwd=str(project_root), timeout=60, job_name="integration_e2e_validation",
    )

    # rc != 0 = 某鏈斷
    if rc != 0:
        try:
            from app.services.contracts.facades import IntegrationFacade
            broken_lines = [l for l in (out or "").split("\n") if "❌" in l]
            body = (
                "🔴 整合連通鏈斷 — v6.13 E2E\n\n"
                f"{chr(10).join(broken_lines[:5]) if broken_lines else 'check log'}\n\n"
                "對齊 owner 訴求:\n"
                "「突破性成長 非一次性」\n\n"
                "標誌: integration 持續驗證機制\n"
                "揭發 silent dormant 第一時間\n\n"
                "marker: wiki/memory/integration-health/"
            )
            await IntegrationFacade().push_admin_alert(
                title="", body=body, channel="line",
            )
        except Exception as line_err:
            logger.warning("integration_e2e LINE push failed: %s", line_err)

    logger.info("integration_e2e_validation rc=%d: %s", rc, out[-300:] if out else "ok")


@tracked_job("critique_health_audit")
async def critique_health_audit_job():
    """v6.13 (2026-05-31) — 每週日 02:15 揭發 critique silent dormant

    對齊 owner「日誌與周報成為實質平臺靈魂」訴求。

    揭發背景：
    - 5/31 三層覆盤揭發 critiques/ 5/13 後 17 天 0 條
    - critic 鏈真活 (agent_post_processing.py:181)，但 trigger 嚴格
    - 監督 silent dormant，不改 critic 設計

    若 7d 內 0 critique 且 query ≥ 5 → 寫 health-empty marker + LINE 推
    """
    import os
    from pathlib import Path

    # 2026-06-02 L52 family 修：CK_PROJECT_ROOT=/app，.parent 會變 / → script 找 /scripts (不存在，
    # 實際 mount /app/scripts) → 8 cron job silent 早退。每日覆盤停 05-31+無 LINE 即此。移除 .parent。
    project_root = Path(os.getenv("CK_PROJECT_ROOT", "/app"))
    script = project_root / "scripts" / "checks" / "critique_health_audit.py"
    if not script.exists():
        logger.error("critique_health_audit: script not found at %s — raise 供 cron watchdog 抓 (防 silent no-op)", script)
        raise FileNotFoundError(f"cron script 缺失: {script}")

    rc, out, err = await _run_script_async(
        ["python", str(script)],
        cwd=str(project_root), timeout=30, job_name="critique_health_audit",
    )

    # rc=1 = 揭發 silent dormant (非錯誤，是有效偵測)
    if rc == 1 and "SILENT DORMANT" in out:
        # 推 LINE 揭發 (沿用 IntegrationFacade，避免直接 import line_bot)
        try:
            from app.services.contracts.facades import IntegrationFacade
            body = (
                "⚠️ Critique Silent Dormant 揭發\n\n"
                f"最近 7 天 0 critique 但有 query\n\n"
                "可能訊號:\n"
                "- agent 質性反省機制斷層\n"
                "- 或 critic trigger threshold 太嚴\n\n"
                "已寫 marker: wiki/memory/critiques/\n"
                "  critique-health-empty-*.md\n\n"
                "對齊 owner: 日誌+周報=靈魂訴求\n"
                "本 marker 即一條質性反省"
            )
            await IntegrationFacade().push_admin_alert(
                title="", body=body, channel="line"
            )
        except Exception as line_err:
            logger.warning("critique_health LINE push failed: %s", line_err)

    logger.info("critique_health_audit rc=%d: %s", rc, out[-200:] if out else "ok")


@tracked_job("weekly_evolution_generator")
async def weekly_evolution_generator_job():
    """v6.13 (2026-05-31) — 每週日 02:00 產出 wiki/memory/evolutions/W{NN}.md

    對齊 owner「日誌與周報成為實質平臺靈魂」訴求。

    揭發背景：
    - 5/31 KG×Hermes×坤哥 三層覆盤揭發 W22 缺檔
    - 真因: 既有 kunge_weekly_learning_summary 只 LINE 推摘要不產檔
    - 修法: 本 job 真實產出 W{NN}.md，防 W22 重演

    不覆寫已存在 (W22 手寫保留為證據)。
    """
    import os
    from pathlib import Path

    # 2026-06-02 L52 family 修：CK_PROJECT_ROOT=/app，.parent 會變 / → script 找 /scripts (不存在，
    # 實際 mount /app/scripts) → 8 cron job silent 早退。每日覆盤停 05-31+無 LINE 即此。移除 .parent。
    project_root = Path(os.getenv("CK_PROJECT_ROOT", "/app"))
    script = project_root / "scripts" / "checks" / "weekly_evolution_generator.py"
    if not script.exists():
        logger.error("weekly_evolution_generator: script not found at %s — raise 供 cron watchdog 抓 (防 silent no-op)", script)
        raise FileNotFoundError(f"cron script 缺失: {script}")

    rc, out, err = await _run_script_async(
        ["python", str(script)],
        cwd=str(project_root), timeout=60, job_name="weekly_evolution_generator",
    )

    if rc != 0:
        logger.warning("weekly_evolution_generator rc=%d err=%s", rc, err[-200:] if err else "")
        return

    logger.info("weekly_evolution_generator: %s", out[-200:] if out else "ok")


@tracked_job("kunge_weekly_learning_summary")
async def kunge_weekly_learning_summary_job():
    """L51.7 Sprint 3.P3.13 (2026-05-30) — 每週日 11:00 推「坤哥這週學到什麼」摘要

    來源 (各取 last 7d)：
    - patterns: 新累積 / success_rate
    - failures: 新增 lesson
    - evolutions: 本週 autobiography 摘要
    - proposals: pending review 數

    目的：引發 owner 反饋寫入 patterns，啟動學習閉環（v7_critique_pct 從 0 推升）
    """
    import os
    from datetime import datetime, timedelta
    from pathlib import Path

    logger.info("開始執行 Kunge weekly learning summary")
    try:
        wiki_memory = Path(os.getenv("CK_WIKI_DIR", "/app/wiki")) / "memory"
        if not wiki_memory.exists():
            logger.warning("kunge weekly: wiki/memory not found")
            return

        cutoff = datetime.now() - timedelta(days=7)
        # 7d 統計
        new_failures = []
        for f in (wiki_memory / "failures").glob("*.md") if (wiki_memory / "failures").exists() else []:
            if f.stat().st_mtime > cutoff.timestamp():
                new_failures.append(f.stem[:50])
        new_patterns = sum(
            1 for f in (wiki_memory / "patterns").glob("*.md") if (wiki_memory / "patterns").exists()
            and f.stat().st_mtime > cutoff.timestamp()
        )
        new_evolutions = []
        if (wiki_memory / "evolutions").exists():
            for f in sorted((wiki_memory / "evolutions").glob("*.md"))[-2:]:
                if f.stat().st_mtime > cutoff.timestamp():
                    new_evolutions.append(f.stem)
        pending_proposals = sum(
            1 for f in (wiki_memory / "proposals").glob("*.md") if (wiki_memory / "proposals").exists()
            and "status: pending" in f.read_text(encoding="utf-8", errors="ignore")
        )

        # 組訊息
        lines = [
            f"🧠 坤哥這週學到什麼 ({datetime.now().strftime('%Y-W%V')})",
            "",
            f"📊 7 天彙整:",
            f"  • 新 patterns: {new_patterns} 個",
            f"  • 新 failures (lessons): {len(new_failures)}",
            f"  • 新 evolutions: {len(new_evolutions)}",
            f"  • Pending proposals: {pending_proposals}",
        ]
        if new_failures:
            lines.extend(["", "🔴 本週新 lessons:"])
            for fn in new_failures[:3]:
                lines.append(f"  • {fn}")
        if new_evolutions:
            lines.extend(["", "📖 本週 evolutions:"])
            for ev in new_evolutions:
                lines.append(f"  • {ev}")
        lines.extend([
            "",
            "💭 想反饋什麼？回覆此訊息或進 /kunge/dialogues",
            "(L51.7 Sprint 3.P3.13 學習閉環啟動)",
        ])
        body = "\n".join(lines) + _kunge_quick_actions("evolution")

        from app.services.contracts.facades.integration import IntegrationFacade
        await IntegrationFacade().push_admin_alert(title="", body=body, channel="line")
        logger.info(
            f"Kunge weekly learning summary pushed: "
            f"patterns+{new_patterns} failures+{len(new_failures)} "
            f"evolutions+{len(new_evolutions)} pending={pending_proposals}"
        )
    except Exception as e:
        logger.error("Kunge weekly learning summary 失敗: %s", e, exc_info=True)


@tracked_job("line_weekly_pulse")
async def line_weekly_pulse_job():
    """LINE 通報活體確認 — 每週日 10:00 推「pulse」訊息 (L51 防 silent fail 反覆)

    L51 教訓：PM2 → docker 切換期間 LINE 全鏈 silent disabled 40h 才被揭發。
    Weekly pulse 保證 owner 每週收到一次「LINE 服務真活」訊息；
    若連續 1 週無此訊息 → owner 可主動察覺異常。

    搭配：
    - main.py startup probe（每次啟動驗 critical env）
    - messaging_push_total counter（每次 attempt 計數，alertmanager 失敗率 >50%/1h 觸發）
    - fitness step 57（每月跑 container env vs host env 對齊）
    """
    logger.info("開始執行 LINE weekly pulse")
    try:
        from datetime import datetime
        from app.services.contracts.facades import IntegrationFacade
        facade = IntegrationFacade()
        msg = (
            "📡 LINE 通報活體確認 (weekly pulse)\n"
            f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            "\n"
            "如果你連續一週沒收到此訊息，表示 LINE 通報鏈可能 silent fail\n"
            "請查: docker logs | grep STARTUP-PROBE | grep messaging\n"
            "或直接跑: python scripts/checks/container_env_alignment_audit.py\n"
            "\n"
            "L51 (2026-05-29) lesson: PM2 → docker 切換引爆 40h silent disabled"
        )
        ok = await facade.push_admin_alert(title="", body=msg, channel="line")
        logger.info(f"LINE weekly pulse: {'sent' if ok else 'FAILED'}")
    except Exception as e:
        logger.error("LINE weekly pulse 失敗: %s", e, exc_info=True)


@tracked_job("embedding_warmup")
async def embedding_warmup_job():
    """Embedding 預熱 — 為 top-500 高頻實體預先載入向量至記憶體快取"""
    logger.info("開始執行 Embedding 預熱")
    try:
        from app.services.ai.core.embedding_manager import warmup_entity_embeddings
        result = await warmup_entity_embeddings(top_n=500)
        warmed = result.get("warmed", 0)
        candidates = result.get("total_candidates", 0)
        logger.info(
            "Embedding 預熱完成: warmed=%d, candidates=%d",
            warmed, candidates,
        )
        # 2026-08-15：warmed/candidates 一直算得出來卻沒回傳。
        # warmed=0 是常態（全部已快取＝好事），所以不判紅；
        # 但 status 會區分 all_cached 與其他情形，讓「沒事做」與「壞掉」分得開。
        return {"warmed": warmed, "candidates": candidates,
                "status": result.get("status", "ok"), "reason": "ok"}
    except Exception as e:
        logger.error("Embedding 預熱失敗: %s", e, exc_info=True)
        raise


# Health check 去抖動 — 連續 N 次失敗才告警，避免 transient 偽警報
# 2026-04-19: asyncpg connection invalidate 瞬間觸發誤警，加入 2-strike 門檻
_HEALTH_FAIL_STREAK = 0
_HEALTH_ALERT_THRESHOLD = 2  # 連續 2 次（10 分鐘）失敗才告警


@tracked_job("health_check_broadcast")
async def health_check_broadcast_job():
    """系統健康檢查 — 每 5 分鐘輪詢，連續 2 次異常才告警（去抖動）。

    出口自 2026-08-03 起為 LINE digest（Telegram 管道已死）；08-04 一併移除
    `TELEGRAM_ADMIN_CHAT_ID` 這道殘留閘門 —— 出口換了閘門沒換，等於讓一個已宣告
    死亡的設定繼續決定健康告警發不發。
    """
    global _HEALTH_FAIL_STREAK
    import httpx

    health_url = "http://127.0.0.1:8001/health"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(health_url)
            data = resp.json()

        is_healthy = resp.status_code == 200 and data.get("status") == "healthy"

        if is_healthy:
            # 健康 — 若上次剛告警（streak >= threshold），推一次「恢復」通知後歸零
            if _HEALTH_FAIL_STREAK >= _HEALTH_ALERT_THRESHOLD:
                # 2026-08-03：原推 Telegram（token 401、開關 false，兩層都送不出去）。
                # 改走 line_digest_buffer 統一由 07:30 晨報帶出 ——
                # owner 要求 LINE 訊息統整分群、上班前一次看完，不要分散推播。
                try:
                    from app.services.integration.line_digest_buffer import queue_digest
                    await queue_digest(
                        "🩺 系統健康",
                        f"✅ 已恢復（時間 {data.get('timestamp', 'N/A')}）",
                    )
                except Exception as e:
                    logger.warning("健康恢復通知 queue 失敗: %s", e)
            _HEALTH_FAIL_STREAK = 0
            return

        # 不健康 — 累計 streak，達閾值才告警
        _HEALTH_FAIL_STREAK += 1
        logger.warning(
            "健康檢查異常 (streak=%d/%d): status=%s",
            _HEALTH_FAIL_STREAK, _HEALTH_ALERT_THRESHOLD, data.get("status"),
        )
        if _HEALTH_FAIL_STREAK < _HEALTH_ALERT_THRESHOLD:
            return  # 還沒到閾值，暫不告警

        # 連續失敗達閾值 — 告警
        db_status = data.get("database", {}).get("status", "unknown")
        msg = (
            f"🚨 公文系統健康異常（連續 {_HEALTH_FAIL_STREAK} 次失敗）\n\n"
            f"狀態: {data.get('status', 'unknown')}\n"
            f"資料庫: {db_status}\n"
            f"時間: {data.get('timestamp', 'N/A')}"
        )
        # 統一走 digest，由 07:30 晨報帶出（owner：LINE 訊息統整分群，勿分散）。
        # 取捨記在這裡：系統異常最多延遲到隔日 07:30 才通知。
        # 這個延遲在架構上原本就存在很大一部分 —— scheduler 與被監控的 API 同進程，
        # 進程整個掛掉時即時推也一樣發不出去。若日後要即時逃生門，
        # 建議條件是「streak 遠高於告警閾值」（代表持續數小時異常）才破例即時推。
        from app.services.integration.line_digest_buffer import queue_digest
        await queue_digest("🩺 系統健康", msg)
        logger.warning("健康檢查連續異常已 queue 至晨報: %s", data.get("status"))

    except Exception as e:
        # API 完全無回應 — 同樣採用 streak 機制
        _HEALTH_FAIL_STREAK += 1
        logger.error(
            "健康檢查失敗 (streak=%d/%d): %s",
            _HEALTH_FAIL_STREAK, _HEALTH_ALERT_THRESHOLD, e,
        )
        if _HEALTH_FAIL_STREAK < _HEALTH_ALERT_THRESHOLD:
            return
        msg = f"🚨 API 無回應（連續 {_HEALTH_FAIL_STREAK} 次）\n錯誤: {str(e)[:200]}"
        try:
            from app.services.integration.line_digest_buffer import queue_digest
            await queue_digest("🩺 系統健康", msg)
        except Exception as ex:
            logger.warning("API 無回應通知 queue 失敗（仍在 log）: %s", ex)


# LLM quota 預警 — 已告警旗標（防重複通知，每日 00:00 自動 reset）
_LLM_QUOTA_ALERT_FLAGS: dict[str, str] = {}  # provider -> alert_date


@tracked_job("llm_quota_check")
async def llm_quota_check_job():
    """LLM 統一告警（2026-04-19 整合）：三維度一次 Telegram 推送。

    **整合 3 維度**：
      1. Groq per-day request（對應 free tier 每日上限）
      2. NVIDIA per-month credits（對應 NIM 免費額度）
      3. Token 總成本（日 USD cost ceiling）

    每日每維度僅告警一次（去重 via ``_LLM_QUOTA_ALERT_FLAGS``）。

    env 配置:
      GROQ_DAILY_REQ_LIMIT        Groq free tier 每日請求上限（預設 1000）
      NVIDIA_MONTHLY_CRED_LIMIT   NVIDIA NIM 每月 credits（預設 5000）
      TOKEN_DAILY_COST_USD_LIMIT  日總成本上限 USD（預設 1.00）
      LLM_QUOTA_WARN_PCT          告警閾值百分比（預設 80）
    """
    import os
    # 2026-08-04：移除 `TELEGRAM_ADMIN_CHAT_ID` 這道殘留閘門。
    # 08-03 已把告警改走 LINE digest，但出口換了、閘門沒換 —— 一個「已宣告死亡」
    # 的 Telegram env 仍在決定 LINE 告警發不發。目前它剛好有值所以看不出問題，
    # 一旦有人清掉死設定，配額預警會**靜默消失**且沒有任何訊號。
    groq_daily_limit = int(os.getenv("GROQ_DAILY_REQ_LIMIT", "1000"))
    nvidia_monthly_limit = int(os.getenv("NVIDIA_MONTHLY_CRED_LIMIT", "5000"))
    cost_daily_limit = float(os.getenv("TOKEN_DAILY_COST_USD_LIMIT", "1.00"))
    warn_pct = float(os.getenv("LLM_QUOTA_WARN_PCT", "80"))

    try:
        from app.services.ai.core.token_usage_tracker import get_token_tracker
        tracker = get_token_tracker()
        report = await tracker.get_usage_report()

        providers = report.get("daily", {}).get("by_provider", {})
        groq_req = providers.get("groq", {}).get("count", 0)
        nvidia_req = providers.get("nvidia", {}).get("count", 0)

        # 月 NVIDIA 累計（token tracker 月指標用 token，我們直接累 count — 用 Redis scan）
        nvidia_month_req = await _sum_monthly_count(tracker, "nvidia")

        # 今日總成本（跨 provider）
        daily_cost = report.get("daily", {}).get("total_cost_usd", 0.0)

        alerts = []
        today = report["date"]

        # (1) Groq 日 request
        groq_pct = (groq_req / groq_daily_limit * 100) if groq_daily_limit > 0 else 0
        if groq_pct >= warn_pct and _LLM_QUOTA_ALERT_FLAGS.get("groq") != today:
            alerts.append(
                f"🟡 Groq 日請求量 {groq_req}/{groq_daily_limit} ({groq_pct:.0f}%)"
                f"\n   {'🚨 已超額，將降級 NVIDIA/Ollama' if groq_pct >= 100 else f'達告警閾值 {warn_pct}%'}"
            )
            _LLM_QUOTA_ALERT_FLAGS["groq"] = today

        # (2) NVIDIA 月 credit
        nvidia_pct = (nvidia_month_req / nvidia_monthly_limit * 100) if nvidia_monthly_limit > 0 else 0
        if nvidia_pct >= warn_pct and _LLM_QUOTA_ALERT_FLAGS.get("nvidia") != today:
            alerts.append(
                f"🟡 NVIDIA 月 credits {nvidia_month_req}/{nvidia_monthly_limit} ({nvidia_pct:.0f}%)"
                f"\n   {'🚨 已超額，將降級 Ollama' if nvidia_pct >= 100 else f'達告警閾值 {warn_pct}%'}"
            )
            _LLM_QUOTA_ALERT_FLAGS["nvidia"] = today

        # (3) 日總成本 USD
        cost_pct = (daily_cost / cost_daily_limit * 100) if cost_daily_limit > 0 else 0
        if cost_pct >= warn_pct and _LLM_QUOTA_ALERT_FLAGS.get("cost") != today:
            alerts.append(
                f"🟡 LLM 日成本 ${daily_cost:.4f}/${cost_daily_limit:.2f} ({cost_pct:.0f}%)"
                f"\n   {'🚨 超過成本上限，建議下調 provider priority' if cost_pct >= 100 else f'達告警閾值 {warn_pct}%'}"
            )
            _LLM_QUOTA_ALERT_FLAGS["cost"] = today

        if alerts:
            msg = "\n".join(alerts) + f"\n（{today}）"
            # 2026-08-03：原推 Telegram（已失效）→ 改走 digest，統一由 07:30 晨報帶出
            from app.services.integration.line_digest_buffer import queue_digest
            await queue_digest("⚡ LLM 配額預警", msg)
            logger.warning(
                "LLM quota 預警推送: groq=%.0f%% nvidia=%.0f%% cost=%.0f%%",
                groq_pct, nvidia_pct, cost_pct,
            )
        else:
            logger.debug(
                "LLM quota OK: groq=%d/%d (%.0f%%) nvidia_mo=%d/%d (%.0f%%) cost=$%.4f/$%.2f (%.0f%%)",
                groq_req, groq_daily_limit, groq_pct,
                nvidia_month_req, nvidia_monthly_limit, nvidia_pct,
                daily_cost, cost_daily_limit, cost_pct,
            )
        # 2026-08-15：健康路徑原本只寫 logger.debug —— 生產不輸出 debug，
        # 所以**實際用量從來看不到**，只有超標時才有一行 warning。
        # 把三個百分比交出來：既能看出趨勢，也讓「有在算」與「沒在算」分得開。
        return {
            "alerts": len(alerts),
            "groq_pct": round(groq_pct, 1), "nvidia_pct": round(nvidia_pct, 1),
            "cost_pct": round(cost_pct, 1), "warn_pct": warn_pct,
            "daily_cost_usd": round(daily_cost, 4),
            "reason": "已 queue 進晨報 digest" if alerts else "三項皆低於告警閾值",
        }

    except Exception as e:
        # 原本只 warning 就吞掉 → 檢核失敗時這支 job 仍然記 success。
        # 交出 reason 讓 producer watchdog 看得到它其實沒算成。
        logger.warning("LLM quota check 失敗: %s", e)
        return {"alerts": 0, "reason": f"檢查失敗（{type(e).__name__}: {e}）"}


# ─────────────────────────────────────────────────
# Memory Wiki Phase 2: Pattern Extractor scheduled job
# 2026-04-19: 每日掃 agent_query_traces → patterns/failures wiki pages
# ─────────────────────────────────────────────────
@tracked_job("memory_weekly_autobiography")
async def memory_weekly_autobiography_job():
    """週日 18:00 生成 Agent 週自傳。

    2026-04-19 Memory Wiki Phase 4:
    - 聚合本週 signals → LLM 第一人稱 narrative
    - 寫 wiki/memory/evolutions/YYYY-WNN.md
    - SOUL.md 成長段落自動追加（agent_writable section 特權）
    - Telegram 推播

    L51.7 (2026-05-30) Sprint 2.P2.10：autobiography 寫 SOUL.md 後
    立即寫 soul_drift_snapshot.json + 推 LINE 提示 owner 跑 cross-repo sync
    防 SOUL drift 反覆發生（L51 sprint 1 已手動 sync 1 次）
    """
    from app.db.database import AsyncSessionLocal
    from app.services.memory.autobiography import AutobiographyGenerator

    logger.info("開始執行 Memory Weekly Autobiography")
    try:
        async with AsyncSessionLocal() as db:
            gen = AutobiographyGenerator(db)
            result = await gen.run()
            logger.info(
                "Weekly Autobiography 完成: %s, queries=%d, soul=%s, line=%s, chars=%d",
                result.get("week_id"), result.get("total_queries"),
                result.get("soul_updated"), result.get("line_pushed"),
                result.get("narrative_chars"),
            )

            # L51.7 Sprint 2.P2.10：SOUL.md 更新後寫 drift snapshot + 提示 owner
            if result.get("soul_updated"):
                try:
                    await _refresh_soul_drift_snapshot()
                    await _push_soul_sync_reminder(result.get("week_id"))
                except Exception as e:
                    logger.warning(f"SOUL drift snapshot/reminder 失敗 (非致命): {e}")
    except Exception as e:
        logger.error("Weekly Autobiography 失敗: %s", e, exc_info=True)


async def _refresh_soul_drift_snapshot() -> None:
    """寫 wiki/memory/soul_drift_snapshot.json — v7_soul_drift metric 讀此檔

    L51.7 Sprint 2.P2.10：container 內找不到 ../CK_AaaP/，autobiography 跑時
    可能在 host 端，host 路徑能 reach CK_AaaP。寫 snapshot 給 backend metric 讀。
    """
    import json
    import os
    from pathlib import Path
    wiki_dir = Path(os.getenv("CK_WIKI_DIR", "/app/wiki"))
    soul_a = wiki_dir / "SOUL.md"
    # 嘗試多個可能 path（container 內 vs host）
    candidates = [
        Path("/CK_AaaP/runbooks/hermes-stack/SOUL.md"),  # 跨 repo mount (若有)
        wiki_dir.parent / ".." / "CK_AaaP" / "runbooks" / "hermes-stack" / "SOUL.md",
    ]
    soul_b = None
    for c in candidates:
        try:
            if c.exists():
                soul_b = c
                break
        except Exception:
            continue
    snapshot_path = wiki_dir / "memory" / "soul_drift_snapshot.json"
    missive_lines = len(soul_a.read_text(encoding="utf-8").splitlines()) if soul_a.exists() else 0
    # drift 語意（2026-06-12 重定義）：核心人格不變量跨層缺口，非整檔行數差。
    _CORE_INV = ["身份", "三信念", "倫理紅線", "反迴聲"]
    snapshot = {
        "missive_lines": missive_lines, "hermes_lines": 0, "line_delta": 0,
        "core_invariant_gap": -1, "missing_invariants": [], "drift_lines": -1,
    }
    if soul_b:
        import re as _re
        a_txt = soul_a.read_text(encoding="utf-8") if soul_a.exists() else ""
        b_txt = soul_b.read_text(encoding="utf-8")
        a_secs = _re.findall(r"^##\s+(.+)$", a_txt, _re.M)
        b_secs = _re.findall(r"^##\s+(.+)$", b_txt, _re.M)
        missing = [kw for kw in _CORE_INV
                   if any(kw in s for s in a_secs) and not any(kw in s for s in b_secs)]
        snapshot["hermes_lines"] = len(b_txt.splitlines())
        snapshot["line_delta"] = abs(missive_lines - snapshot["hermes_lines"])
        snapshot["core_invariant_gap"] = len(missing)
        snapshot["missing_invariants"] = missing
        snapshot["drift_lines"] = len(missing)
        source = "autobiography_post_write"
    else:
        # L73: container 看不到 ../CK_AaaP → 不可 clobber host fitness（soul_mirror_drift_check）真值；
        # 保留既有 snapshot 的 hermes_lines/core_invariant_gap/missing，只刷新 missive_lines。
        try:
            if snapshot_path.exists():
                prev = json.loads(snapshot_path.read_text(encoding="utf-8"))
                for k in ("hermes_lines", "line_delta", "core_invariant_gap",
                          "missing_invariants", "drift_lines"):
                    if k in prev:
                        snapshot[k] = prev[k]
        except Exception:
            pass
        source = "autobiography_post_write(preserve_host_drift)"
    snapshot["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    snapshot["source"] = source
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"SOUL drift snapshot updated: core_invariant_gap={snapshot['drift_lines']} source={source}")


async def _push_soul_sync_reminder(week_id: str | None) -> None:
    """推 LINE 提示 owner 跨 repo SOUL sync

    L51.7 Sprint 2.P2.10：autobiography 更新 SOUL 後，提示 owner 跑
    sync_soul_to_hermes.sh + CK_AaaP commit 完成跨 repo 同步
    """
    body = (
        f"🧠 SOUL.md 已更新 ({week_id or 'autobiography'})\n"
        f"\n"
        f"提示: 跨 repo 同步:\n"
        f"  bash scripts/sync/sync_soul_to_hermes.sh --apply\n"
        f"  cd ../CK_AaaP\n"
        f"  git add runbooks/hermes-stack/SOUL.md\n"
        f"  git commit -m 'sync: SOUL from Missive'\n"
        f"  git push\n"
        f"\n"
        f"未同步 → v7_soul_drift 上升 → 跨通道人格不一致\n"
        f"(L51.7 Sprint 2.P2.10 配套)"
        + _kunge_quick_actions("identity")
    )
    try:
        from app.services.contracts.facades.integration import IntegrationFacade
        await IntegrationFacade().push_admin_alert(title="", body=body, channel="line")
        logger.info("SOUL sync reminder 推送 LINE 成功")
    except Exception as e:
        logger.warning(f"SOUL sync reminder push 失敗: {e}")


@tracked_job("memory_anti_echo_scan")
async def memory_anti_echo_scan_job():
    """反迴聲室協議 — 每週一 06:00 掃近 7 天 diary，偵測過度一致。

    2026-04-21 v5.8.0 坤哥意識體 D5-A。

    觸發條件（預設）：
    - 7 天內 ≥ 20 筆 diary entry
    - success_rate ≥ 90%
    - failure ≤ 2
    - 3 天內未觸發過（cooldown）

    觸發後在當日 diary append「反迴聲室」段落，列 1-3 條質疑候選。
    """
    from app.services.memory.anti_echo import AntiEchoProtocol
    logger.info("開始執行 Anti-Echo Chamber Scan")
    try:
        protocol = AntiEchoProtocol()
        result = await protocol.scan_and_reflect()
        if result.get("triggered"):
            logger.info(
                "AntiEcho triggered: %s reflections=%d",
                result.get("reason"),
                len(result.get("reflections", [])),
            )
            # 2026-08-03：原推 Telegram（token 401 + 開關 false，送不出去），
            # 且以 TELEGRAM_ADMIN_CHAT_ID 是否存在當推播開關 —— 改走 digest，
            # 由 07:30 晨報依主題分群一次帶出。
            try:
                from app.services.integration.line_digest_buffer import queue_digest
                msg = (
                    f"原因：{result.get('reason')}\n候選質疑：\n"
                    + "\n".join(
                        f"{i+1}. {r}" for i, r in enumerate(
                            result.get("reflections", [])[:3]
                        )
                    )
                    + "\n（已寫入今日 diary）"
                )
                await queue_digest("🔔 反迴聲室", msg)
            except Exception as e:
                logger.debug("AntiEcho digest queue failed: %s", e)
        else:
            logger.info("AntiEcho not triggered: %s", result.get("reason"))
            # L51.7 Sprint 2.P2.12 (2026-05-30) 連續 N 週未觸發 → 主動 prompt owner critique
            # 防 v7_reference_density_critique_pct=0 死局（坤哥從不質疑自己）
            try:
                await _check_critique_starvation()
            except Exception as e:
                logger.warning(f"critique starvation check 失敗 (非致命): {e}")
    except Exception as e:
        logger.error("Anti-Echo Scan 失敗: %s", e, exc_info=True)


async def _check_critique_starvation() -> None:
    """L51.7 Sprint 2.P2.12 — 連續 4 週 anti_echo 未觸發 → LINE prompt owner critique

    v7_reference_density_critique_pct=0 是「坤哥從不被質疑」的訊號。
    主動推 LINE 給 owner，請他選 1 個本週決策反向思考一下。
    """
    import os
    from datetime import datetime, timedelta
    from pathlib import Path

    wiki_memory = Path(os.getenv("CK_WIKI_DIR", "/app/wiki")) / "memory"
    critiques_dir = wiki_memory / "critiques"

    # 計算最近 critique mtime
    #
    # ⚠️ glob 必須維持**非遞迴**：`critiques/_health/` 放的是 critique_health_audit
    # 自己產的 marker。2026-08-05 前 marker 與真 critique 混放同一層，而該稽核每兩週
    # 寫一個 → 最新 mtime 永遠 ≤14 天 → **28 天門檻在結構上永遠達不到**，
    # 這道安全網不管有沒有真的斷層都不會響。改成 rglob 或把 marker 移回上層即復活死局。
    # （查證當下沒有斷層：真 critique 最新 2026-08-02、每 1-2 週一篇 ——
    #   所以這是潛伏缺陷，它從未失效過是因為從未被需要過。）
    last_critique_days = 999
    if critiques_dir.exists():
        files = list(critiques_dir.glob("critique-*.md"))
        if files:
            latest = max(f.stat().st_mtime for f in files)
            last_critique_days = (datetime.now() - datetime.fromtimestamp(latest)).days

    # 連續 28d (4 週) 無 critique → 主動推
    if last_critique_days < 28:
        return

    # 取本週 diary 一筆作為「可質疑候選」
    diary_dir = wiki_memory / "diary"
    today = datetime.now().strftime("%Y-%m-%d")
    sample_topic = "本週任一決策"
    if diary_dir.exists():
        today_diary = diary_dir / f"{today}.md"
        if today_diary.exists():
            try:
                text = today_diary.read_text(encoding="utf-8")
                # 取第一個 ## 標題作為候選
                import re as _re
                m = _re.search(r"^## (\d{2}:\d{2}:\d{2}.*)$", text, _re.MULTILINE)
                if m:
                    sample_topic = m.group(1)[:60]
            except Exception:
                pass

    body = (
        "🪞 反迴聲室提示 (L51.7 Sprint 2.P2.12)\n"
        "\n"
        f"距上次 critique 已 {last_critique_days} 天\n"
        f"v7_reference_density_critique_pct=0 警示\n"
        "「坤哥從不被質疑」反模式\n"
        "\n"
        f"💭 候選質疑題目:\n"
        f"  {sample_topic}\n"
        "\n"
        "建議：花 5 分鐘寫一篇 critique → \n"
        "  wiki/memory/critiques/critique-YYYYMMDD-小標題.md\n"
        "  內含: 「這個決策可能錯在...」+ entity_id 引用\n"
        "\n"
        "目標: 每 4 週至少 1 篇 critique\n"
        "→ v7_reference_density_critique_pct 從 0 啟動"
        + _kunge_quick_actions("dialogues")
    )
    # 2026-08-05：改走 digest（L81「換了出口就要換整條鏈」）。
    # 同一個 job 的 sibling 路徑（AntiEcho triggered）2026-08-03 已改 queue_digest，
    # 這條 else 分支被漏掉、仍直推 LINE —— 同一個 job 兩個出口，正是 L81 的形狀。
    # 統一由 07:30 晨報依主題帶出，不另佔配額、不在週一 06:00 單獨叫醒 owner。
    try:
        from app.services.integration.line_digest_buffer import queue_digest
        await queue_digest("🪞 反迴聲室提示", body)
        logger.info(f"critique starvation prompt 已入 digest (last={last_critique_days}d)")
    except Exception as e:
        logger.warning(f"critique starvation prompt 入 digest 失敗: {e}")


@tracked_job("daily_self_reflection_line_push")
async def daily_self_reflection_line_push_job():
    """v6.6 Phase B2 (5c)：每日 22:00 彙總當日自我反思推 LINE owner。

    解體感「anti_echo 觸發即推會變雜訊」— 改每日彙總一次。

    來源：今日 diary 中的「反迴聲室」段落 + 失敗 query 統計。
    無觸發、無失敗 → silent skip（不推「沒事」雜訊）。

    ENV：
    - LINE_ADMIN_USER_ID 未設 → silent skip
    - LINE_GROWTH_NOTIFY_ENABLED=false → 顯式關閉
    """
    import os
    if os.getenv("LINE_GROWTH_NOTIFY_ENABLED", "true").lower() in ("false", "0"):
        return
    line_user_id = os.getenv("LINE_ADMIN_USER_ID")
    if not line_user_id:
        return

    from app.services.memory.anti_echo import summarize_today_self_reflection
    summary = summarize_today_self_reflection()
    if not summary:
        logger.info("Daily self-reflection: no events today, skip LINE push")
        return

    lines = [
        f"🌙 我今日的自我反思（{summary['today']}）",
        "",
        f"📊 今日對話：{summary['total_count']} 筆"
        f"（成功 {summary['success_count']} / 失敗 {summary['failure_count']}）",
    ]
    if summary["anti_echo_count"] > 0:
        lines.append(f"🔔 反迴聲室觸發：{summary['anti_echo_count']} 次")
        if summary["reflection_lines"]:
            lines.append("")
            lines.append("💭 我可能錯了的地方：")
            for i, r in enumerate(summary["reflection_lines"][:3], 1):
                lines.append(f"  {i}. {r}")
    elif summary["failure_count"] > 0:
        lines.append("")
        lines.append("⚠ 今日無 anti_echo 觸發，但有失敗 query — 明日可關注。")

    text_msg = "\n".join(lines)
    # 2026-07-07 主題合併落地：22:00 不再單推 LINE（原 1 則/日），改 queue 進
    # digest buffer，隔日 08:00 晨報「昨日主題摘要」段帶出。內容本已寫 diary/wiki。
    # 要恢復單推：設 SELF_REFLECTION_LINE_PUSH_ENABLED=true。
    if os.getenv("SELF_REFLECTION_LINE_PUSH_ENABLED", "false").lower() == "true":
        try:
            from app.services.integration.line_bot import LineBotService
            line_bot = LineBotService()
            if not line_bot.enabled:
                return
            ok = await line_bot.push_message(line_user_id, text_msg)
            if ok:
                logger.info(
                    "Daily self-reflection pushed to LINE: anti_echo=%d failure=%d",
                    summary["anti_echo_count"], summary["failure_count"],
                )
        except Exception as e:
            logger.error(
                "Daily self-reflection LINE push failed: %s", e, exc_info=True,
            )
    else:
        from app.services.integration.line_digest_buffer import queue_digest
        await queue_digest("🌙 坤哥自省", text_msg)
        logger.info("Daily self-reflection queued to morning digest（不單推）")


@tracked_job("cron_self_health_alert")
async def cron_self_health_alert_job():
    """v6.7 E4：cron 自我健康檢查推 LINE owner（每日 06:30）。

    解體感「fitness step 13 偵測 cron 健康但只 log 不推 LINE」斷鏈
    （與 v6.6 5a/5b/5c 對齊：所有重要事件都該 LINE 體感）。

    判定規則：
    - failed >= 1 → 推 LINE「⚠ cron 異常通知」（含失敗 cron 名稱）
    - never_run >= total / 2 → 推 LINE「⚠ 多數 cron 從未執行」（系統剛重啟）
    - 全綠 → silent（不推「沒事」雜訊）

    ENV 共用：
    - LINE_ADMIN_USER_ID 未設 → silent skip
    - LINE_GROWTH_NOTIFY_ENABLED=false → 顯式關閉
    """
    import os
    # 三條 return 路徑原本都不留任何痕跡 —— 於是「今天沒有異常」與
    # 「這支根本沒在做事」在 cron_events 裡長得一模一樣（2026-08-15 補）。
    if os.getenv("LINE_GROWTH_NOTIFY_ENABLED", "true").lower() in ("false", "0"):
        return {"queued": False, "reason": "LINE_GROWTH_NOTIFY_ENABLED=false（顯式關閉）"}
    line_user_id = os.getenv("LINE_ADMIN_USER_ID")
    if not line_user_id:
        return {"queued": False, "reason": "LINE_ADMIN_USER_ID 未設＝這支告警沒有收件人"}

    summary = SchedulerTracker.get_summary()
    records = SchedulerTracker.get_all()

    total = summary.get("total_jobs", 0)
    failed = summary.get("failed", 0)
    never_run = summary.get("never_run", 0)
    status = summary.get("status", "unknown")

    # 全綠 → silent
    if failed == 0 and never_run < (total / 2 if total else 0):
        logger.info("Cron self-health: all healthy, skip LINE push")
        return {"queued": False, "total": total, "failed": 0, "never_run": never_run,
                "reason": "全綠，不推「沒事」雜訊"}

    failed_jobs = [
        job_id for job_id, rec in records.items()
        if rec.get("last_status") == "failure"
    ]

    lines = [
        f"⚠ cron 異常通知（{datetime.now().strftime('%Y-%m-%d %H:%M')}）",
        "",
        f"📊 排程狀態：{status}",
        f"  總計 {total} / 健康 {summary.get('healthy', 0)} / 失敗 {failed} / 未跑 {never_run}",
    ]
    if failed_jobs:
        lines.append("")
        lines.append("🔴 失敗的 cron：")
        for job_id in failed_jobs[:10]:
            rec = records.get(job_id, {})
            err = (rec.get("last_error") or "")[:80]
            lines.append(f"  • {job_id}: {err}")
    if never_run >= (total / 2 if total else 0) and total > 0:
        lines.append("")
        lines.append("⏳ 多數 cron 從未執行（可能剛重啟，等候首次觸發）")

    text_msg = "\n".join(lines)
    # 2026-07-07 主題合併落地：06:30 告警不單推（08:00 晨報僅差 90 分鐘），
    # queue 進 digest buffer 由晨報帶出。內容本已在 /admin/scheduler-events 可查。
    from app.services.integration.line_digest_buffer import queue_digest
    await queue_digest("🩺 Cron 健康", text_msg)
    logger.info(
        "Cron self-health alert queued to morning digest: failed=%d never_run=%d",
        failed, never_run,
    )
    return {"queued": True, "total": total, "failed": failed,
            "never_run": never_run, "failed_jobs": failed_jobs[:10]}


@tracked_job("cron_outcome_freshness")
async def cron_outcome_freshness_job():
    """2026-06-02 outcome-freshness watchdog（每日 07:00）。

    解 owner 洞察「沒人回報就又中斷連線」+ watchdog 對 silent no-op 失明：
    cron_self_health 只抓 failed>=1，但 silent 早退（假成功）逃過偵測。
    本 watchdog 改驗『輸出檔是否今日新鮮』— 不管 job 怎麼假成功，
    只要該機制沒產出今日檔 → LINE 報。比 failed 監控徹底（連 rc!=0 早退也抓）。

    全綠 silent（不推雜訊）；任一 stale → LINE 推 owner + cron_events 記錄。
    """
    import os
    import time
    from pathlib import Path as _Path

    if os.getenv("LINE_GROWTH_NOTIFY_ENABLED", "true").lower() in ("false", "0"):
        return
    root = _Path(os.getenv("CK_PROJECT_ROOT", "/app"))
    now = time.time()

    # 2026-07-18：改讀共享 producer registry JSON（backend/config，與 host watchdog 同源）。
    #   信號型別與判定規則見 scripts/checks/producer_registry.py（單一實作）。
    #   新增 producer 只加一筆 JSON → host + cron 兩處自動涵蓋（契約 PRODUCER_SELF_CHECK_CONTRACT.md）。
    import json as _json

    # 2026-08-05：判定改用共用模組 scripts/checks/producer_registry.py。
    #
    # 先前這裡自己實作了一份判定，與 host watchdog 各一份 —— 08-04 就咬過：
    # registry 早已有 db_row_count（07-20）與 json_result（08-04），這邊只認 3 種、
    # **認不得就靜靜跳過**，於是那些 producer 在無人值守的每日告警裡等於不存在，
    # 手動跑 host watchdog 卻全綠。當時補上型別是補丁；只要判定有兩份，
    # 下一個新型別還會再犯一次。
    #
    # scripts/ 以 ro bind-mount 掛在 /app/scripts，容器可直接 import canonical 那份。
    import sys as _sys
    _checks_dir = str(root / "scripts" / "checks")
    if _checks_dir not in _sys.path:
        _sys.path.insert(0, _checks_dir)
    try:
        from producer_registry import (  # type: ignore
            RegistryUnavailable, build_count_sql, judge, load_registry, resolve_path,
        )
    except ImportError as _e:
        # 掛載缺失時**不得**靜靜跳過 —— 那會讓整個 producer 監看消失而畫面全綠
        logger.error("producer_registry 無法載入（scripts 掛載缺失？）: %s", _e, exc_info=True)
        raise

    try:
        registry = load_registry(root / "config" / "producer_outcome_registry.json")
    except RegistryUnavailable as _e:
        # 同理：registry 壞掉＝未驗完，必須讓 cron watchdog 抓到，不能當成全部正常
        logger.error("producer registry 不可用，本輪未驗完: %s", _e)
        raise

    from datetime import date as _date
    _is_weekend = _date.today().weekday() >= 5

    # 讀 cron_events 供 cron_detail 檢
    _latest = {}
    try:
        _ev = root / "logs" / "cron_events.jsonl"
        if _ev.exists():
            for _line in _ev.read_text(encoding="utf-8", errors="ignore").splitlines()[-3000:]:
                _line = _line.strip()
                if not _line:
                    continue
                try:
                    _e = _json.loads(_line)
                    if _e.get("job_id"):
                        _latest[_e["job_id"]] = _e
                except Exception:
                    continue
    except Exception:
        pass

    async def _db_count(spec: dict):
        """db_* 兩種信號的取值；SQL 來自共用模組，兩端不會漂移。"""
        from app.db.database import async_session_maker as _asm
        from sqlalchemy import text as _text
        async with _asm() as _db:
            return await _db.scalar(_text(build_count_sql(spec)))

    stale = []
    for spec in registry:
        _sig = spec.get("signal")
        try:
            _facts = {"is_weekend": _is_weekend}
            if _sig == "file_fresh":
                # registry 用 repo-root 相對路徑；容器 root=/app=backend，故剝 backend/ 前綴
                _p = resolve_path(root, spec["path"], strip_backend_prefix=True)
                if _p.is_dir():
                    _files = list(_p.glob("*.md")) + list(_p.glob("*.json"))
                    _facts["newest_mtime"] = max(
                        (f.stat().st_mtime for f in _files), default=0)
                else:
                    _facts["newest_mtime"] = _p.stat().st_mtime if _p.exists() else 0
            elif _sig == "cron_detail":
                _facts["latest_event"] = _latest.get(spec["job"])
            elif _sig in ("db_table_today", "db_row_count"):
                _facts["db_value"] = await _db_count(spec)
            elif _sig == "json_result":
                _rp = spec["path"]
                if _rp.startswith("backend/"):
                    _rp = _rp[len("backend/"):]
                _facts["json_files"] = (
                    list(root.glob(_rp)) if "*" in _rp
                    else ([root / _rp] if (root / _rp).exists() else [])
                )
            _problem = judge(spec, now=now, **_facts)
            if _problem:
                stale.append(f"  • {_problem}")
        except Exception as _ex:
            stale.append(f"  • {spec.get('name', '?')}: 檢查異常 {_ex}")

    if not stale:
        logger.info("✅ outcome-freshness：registry 全 producer 產出正常（file/cron_detail/db_table/db_row_count/json_result），skip LINE")
        return

    line_user_id = os.getenv("LINE_ADMIN_USER_ID")
    if not line_user_id:
        logger.error("🔴 outcome-freshness 偵測 %d 機制 stale 但 LINE_ADMIN_USER_ID 未設：%s",
                     len(stale), stale)
        return

    body = (
        "⚠️ 排程產出異常通知（outcome-freshness）\n\n"
        f"以下機制未產出今日新鮮輸出（可能 silent 中斷）：\n"
        + "\n".join(stale)
        + "\n\n請查 /admin/scheduler-events 或 backend log"
    )
    # 2026-07-07 主題合併落地：07:00 告警不單推（08:00 晨報僅差 60 分鐘），
    # queue 進 digest buffer 由晨報帶出。log 仍 LOUD（warning 級）供即時排查。
    from app.services.integration.line_digest_buffer import queue_digest
    await queue_digest("⚠️ 排程產出", body)
    logger.warning("🔴 outcome-freshness queued to morning digest：%d 機制 stale", len(stale))


@tracked_job("memory_crystallization_scan")
async def memory_crystallization_scan_job():
    """每日掃 patterns/ 產生 crystal proposals（不自動 apply，等人批准）。

    2026-04-19 Memory Wiki Phase 3：
    - scan crystallization_candidates（hit >= 5, success_rate >= 95%）
    - 寫 proposal 至 wiki/memory/proposals/
    - **不自動改 yaml**，需人批准（via Phase 5 UI 或 API）
    """
    from app.services.memory.crystallizer import Crystallizer
    logger.info("開始執行 Memory Crystallization Scan")
    try:
        crys = Crystallizer()
        proposals = await crys.scan_and_propose()
        logger.info("Memory Crystallization Scan 完成: %d proposals", len(proposals))
        # 2026-08-05：補 detail（契約規則 2）。
        # 這支 job 每天回 success 但 detail=null，而 proposals/crystals **自 07-07 起
        # 28 天零產出**完全沒有人看得到 —— 「0 提案」與「根本沒掃到」在 log 裡長得一樣。
        # 有了這些數字才能區分「沒有 pattern 達門檻」（合理空）、「達門檻但都已結晶／
        # 剛被拒絕」（也是合理空，但意義不同）與「掃描本身失敗」。
        # ⚠️ 初版寫 `crys.list_candidates()` —— **那個方法不存在**，會被 except 吞成 -1，
        # 等於又造一個沉默失敗。改為直接用 Crystallizer 既有的判準逐檔算。
        _total = _met = 0
        try:
            from app.services.memory.crystallizer import PATTERNS_DIR as _PD
            if _PD.exists():
                for _f in _PD.glob("pattern-*.md"):
                    _m = crys._parse_pattern_meta(_f)
                    if not _m:
                        continue
                    _total += 1
                    if crys._meets_crystal_threshold(_m):
                        _met += 1
        except Exception as _e:
            logger.warning("結晶候選統計失敗（不影響主流程）: %s", _e)
            _total = _met = -1
        # 2026-08-03：原推 Telegram（已失效）→ 改走 digest，07:30 晨報統一帶出
        if proposals:
            try:
                from app.services.integration.line_digest_buffer import queue_digest
                msg = (
                    f"新提案 {len(proposals)} 筆\n"
                    + "\n".join(f"• {p.proposal_id}: {p.reason[:80]}" for p in proposals[:5])
                    + "\n批准請至 /ai/memory Dashboard 或 API。"
                )
                await queue_digest("🔮 Crystal 提案", msg)
            except Exception as e:
                logger.debug("Crystal proposal digest queue failed: %s", e)
        return {
            "proposals": len(proposals),
            "patterns_total": _total,
            "patterns_met_threshold": _met,
            "reason": "ok" if proposals else (
                "stat_failed" if _met < 0 else
                "no_pattern_met_threshold" if _met == 0 else
                "all_met_already_proposed_or_applied"
            ),
        }
    except Exception as e:
        logger.error("Memory Crystallization 失敗: %s", e, exc_info=True)
        return {"proposals": 0, "candidates": -1, "reason": f"error:{str(e)[:60]}"}


@tracked_job("agent_self_diagnosis")
async def agent_self_diagnosis_job():
    """v5.13 Gap 1: 每日 06:00 主動讀自己 metrics 寫 diary。

    讓 agent 真正「回看自己」，不只執行還會反思健康度。
    異常即 push Telegram alert（agent 主動告訴 owner 問題）。
    """
    from app.services.memory.self_diagnosis import SelfDiagnosis

    logger.info("開始執行 Agent Self-Diagnosis")
    try:
        sd = SelfDiagnosis()
        result = await sd.run()
        logger.info(
            "Self-diagnosis 完成: counter=%d alerts=%d alert_pushed=%s",
            result.get("evolution_counter_value", 0),
            len(result.get("alerts", [])),
            result.get("alert_pushed"),
        )
    except Exception as e:
        logger.error("Self-diagnosis 失敗: %s", e, exc_info=True)


@tracked_job("memory_pattern_extract")
async def memory_pattern_extract_job():
    """每日從 traces 萃取 success patterns + failure modes 寫入 wiki/memory/。

    成功率 > 80% 且 count >= 3 → wiki/memory/patterns/
    失敗率 > 50% → wiki/memory/failures/ + defensive_rule（planner 自動注入）
    """
    from app.db.database import AsyncSessionLocal
    from app.services.memory.pattern_extractor import PatternExtractor
    from datetime import date, timedelta

    target_date = date.today() - timedelta(days=1)  # 萃取昨日的 traces
    logger.info("開始執行 Memory Pattern Extraction for %s", target_date)

    try:
        async with AsyncSessionLocal() as db:
            extractor = PatternExtractor(db)
            result = await extractor.extract_daily(target_date)
            logger.info(
                "Memory Pattern Extract 完成: scanned=%d patterns=%d (saved %d) failures=%d (saved %d) in %dms",
                result.total_traces_scanned,
                len(result.patterns), result.saved_pattern_files,
                len(result.failures), result.saved_failure_files,
                result.duration_ms,
            )
            return {
                "patterns": len(result.patterns),
                "saved": result.saved_pattern_files,
                "scanned": result.total_traces_scanned,
                # 沒有 trace 可掃（閒置日）是合理空，與「掃了但萃不出」不同
                "reason": "ok" if result.saved_pattern_files else (
                    "no_traces" if not result.total_traces_scanned else "no_pattern_met_threshold"
                ),
            }
    except Exception as e:
        logger.error("Memory Pattern Extraction 失敗: %s", e, exc_info=True)
        return {"patterns": 0, "saved": 0, "scanned": 0, "reason": f"error:{str(e)[:60]}"}


@tracked_job("soul_mirror_sync")
async def soul_mirror_sync_job():
    """SOUL.md 跨 repo 自動同步（v6.4 C1）— 每日 04:45。

    為何自動：
    - soul_mirror_drift_check.py 已偵測 drift，但同步腳本 sync_soul_to_hermes.sh
      原為 manual gate（owner 手動跑 --apply）→ 跨通道人格漂移持續存在
    - Web 用戶看 Missive SOUL，Telegram/LINE 用戶看 Hermes SOUL，內容不同步
    - 跨 repo 寫檔風險評估後接受：cp 是 reversible（AaaP 端 git 可回溯）

    安全閘：
    - 只覆蓋 ../CK_AaaP/runbooks/hermes-stack/SOUL.md（單一 target）
    - 不自動 git commit/push（owner 端決定 commit 時機）
    - 內容相同時 no-op（exit 0 silent）
    - target 不存在時 silent skip（dev 環境 AaaP 可能未 clone）

    關聯：
    - SYSTEM_INTEGRATION_REVIEW_v2.md 軸線 C
    - scripts/sync/sync_soul_to_hermes.sh
    """
    from app.core.paths import PROJECT_ROOT as project_root, SCRIPTS_DIR, CKPROJECT_ROOT  # v6.10 P1-E SSOT
    script_path = SCRIPTS_DIR / "sync" / "sync_soul_to_hermes.sh"
    target_path = CKPROJECT_ROOT / "CK_AaaP" / "runbooks" / "hermes-stack" / "SOUL.md"

    # ⚠️ 2026-08-15：這支在容器裡**每次都靜默跳過**，已「成功」74 次卻從未同步過。
    #
    # 容器沒有掛 sibling repo → CKPROJECT_ROOT 解析成 `/` →
    # 目標 `/CK_AaaP/runbooks/hermes-stack/SOUL.md` 永遠不存在 →
    # 原本 `logger.debug` 一行就 return，cron_events 記 success、detail=None。
    # 「跳過」與「同步完成」在紀錄上完全一樣。
    #
    # host 端看得到那個目標（實測存在），所以這是**環境問題不是設定問題** ——
    # 與 weekly fitness（08-07）、履歷編譯（08-13）同一個處置：該跑在 host。
    # 在移交之前，至少讓它說出自己沒做事，而不是回報成功。
    if not script_path.exists():
        logger.warning("SOUL sync 未執行：同步腳本不存在 %s", script_path)
        return {"synced": False, "reason": f"script_missing:{script_path}"}
    if not target_path.exists():
        logger.warning(
            "SOUL sync 未執行：跨 repo 目標不存在 %s —— "
            "容器沒有掛 sibling repo，這支需要在 host 執行才有效力", target_path)
        return {"synced": False, "reason": "target_unreachable_in_container"}

    logger.info("開始執行 SOUL Mirror Sync")
    rc, stdout, stderr = await _run_script_async(
        ["bash", str(script_path), "--apply"],
        cwd=str(project_root),
        timeout=30,
        job_name="soul_mirror_sync",
    )
    if rc == 0:
        # 解析 stdout 取 delta 資訊（best-effort）
        identical = "identical" in (stdout or "")
        logger.info(
            "SOUL Mirror Sync 完成: identical=%s rc=%d",
            identical, rc,
        )
        # 「內容相同所以沒動」與「真的同步了」是兩件事，紀錄要分得出來
        return {"synced": not identical, "identical": identical, "reason": "ok"}
    logger.error(
        "SOUL Mirror Sync 失敗 rc=%d stderr=%s",
        rc, (stderr or "")[:200],
    )
    raise RuntimeError(f"soul_mirror_sync rc={rc}: {(stderr or '')[:120]}")


async def _sum_monthly_count(tracker, provider: str) -> int:
    """Helper: 取 provider 當月累計 request count（掃 Redis monthly key）。"""
    try:
        r = await tracker._get_redis()
        if not r:
            return 0
        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        data = await r.hgetall(f"{tracker.PREFIX}:monthly:{month}:{provider}")
        return int(data.get("count", 0)) if data else 0
    except Exception:
        return 0


def setup_scheduler(
    reminder_interval_minutes: int = 5,
    cleanup_hour: int = 2,
    cleanup_minute: int = 0
) -> AsyncIOScheduler:
    """
    設定排程器

    Args:
        reminder_interval_minutes: 提醒處理間隔（分鐘）
        cleanup_hour: 清理任務執行小時
        cleanup_minute: 清理任務執行分鐘

    Returns:
        設定完成的排程器
    """
    scheduler = get_scheduler()

    # 移除現有任務（避免重複添加）
    existing_jobs = scheduler.get_jobs()
    for job in existing_jobs:
        scheduler.remove_job(job.id)

    # 添加提醒處理任務 - 每 N 分鐘執行一次
    scheduler.add_job(
        process_pending_reminders_job,
        trigger=IntervalTrigger(minutes=reminder_interval_minutes),
        id='process_reminders',
        name='處理待發送提醒',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info(f"已添加提醒處理任務: 每 {reminder_interval_minutes} 分鐘執行")

    # 添加清理任務 - 每日凌晨執行
    scheduler.add_job(
        cleanup_expired_events_job,
        trigger=CronTrigger(hour=cleanup_hour, minute=cleanup_minute),
        id='cleanup_events',
        name='清理過期事件',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,  # L72: 凌晨壅塞防 misfire skip
    )
    logger.info(f"已添加清理任務: 每日 {cleanup_hour:02d}:{cleanup_minute:02d} 執行")

    # 添加電子發票同步任務 - 每日凌晨 01:00 執行
    import os
    if os.getenv("MOF_APP_ID"):
        scheduler.add_job(
            einvoice_sync_job,
            trigger=CronTrigger(hour=1, minute=0),
            id='einvoice_sync',
            name='電子發票自動同步 (財政部)',
            replace_existing=True,
            max_instances=1,
            coalesce=True
        )
        logger.info("已添加電子發票同步任務: 每日 01:00 執行")
    else:
        logger.info("電子發票同步未啟用 (MOF_APP_ID 未設定)")

    # 夜間吹哨者 — 每日 00:30 掃描預算/逾期/待核銷
    scheduler.add_job(
        proactive_trigger_scan_job,
        trigger=CronTrigger(hour=0, minute=30),
        id='proactive_trigger_scan',
        name='夜間吹哨者 (預算/逾期/待核銷)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加夜間吹哨者: 每日 00:30 執行")

    # 添加安全掃描 — 每日 02:00 自動偵測資安問題
    scheduler.add_job(
        security_scan_job,
        trigger=CronTrigger(hour=2, minute=0),
        id='security_scan',
        name='自動安全掃描 (OWASP)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,  # L72: 02:00 壅塞防 misfire skip
    )
    logger.info("已添加安全掃描: 每日 02:00 執行")

    # ERP 圖譜入圖 — 每日 03:30 掃描 ERP 表
    scheduler.add_job(
        erp_graph_ingest_job,
        trigger=CronTrigger(hour=3, minute=30),
        id='erp_graph_ingest',
        name='ERP 圖譜入圖 (quotation/expense/asset)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 ERP 圖譜入圖: 每日 03:30 執行")

    # 添加 Code Graph 增量更新 — 每日 03:00 掃描 Python/TypeScript AST
    scheduler.add_job(
        code_graph_incremental_job,
        trigger=CronTrigger(hour=3, minute=0),
        id='code_graph_incremental',  # L72: align add_job id = @tracked_job id（消 freshness 不符）
        name='Code Graph 增量更新 (AST)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,  # L72: 03:00 在 02:00-03:00 治理群壅塞時不被 skip（與 sibling 一致）
    )
    logger.info("已添加 Code Graph 增量更新: 每日 03:00 執行")

    # 添加 Code Graph 全掃 reconcile — 每週日 03:15 mark-and-sweep 清 stale orphan（防圖譜污染）
    scheduler.add_job(
        code_graph_reconcile_job,
        trigger=CronTrigger(day_of_week='sun', hour=3, minute=15),
        id='code_graph_reconcile',
        name='Code Graph 全掃 reconcile (mark-and-sweep)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,
    )
    logger.info("已添加 Code Graph 全掃 reconcile: 每週日 03:15 執行")

    # 添加程式圖譜語意異質同工自動判定 — 每月 1 號 04:00（發現→LLM判定→提報 owner）
    scheduler.add_job(
        code_dup_triage_job,
        trigger=CronTrigger(day=1, hour=4, minute=0),
        id='code_dup_triage',
        name='程式圖譜語意異質同工自動判定 (LLM triage)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,
    )
    logger.info("已添加 程式圖譜語意異質同工自動判定: 每月 1 號 04:00 執行")

    # 添加 DB Schema 快照更新 — 每日 03:30 反射 PostgreSQL schema
    scheduler.add_job(
        db_schema_refresh_job,
        trigger=CronTrigger(hour=3, minute=35),  # 2026-05-18 P1: 與 erp_graph_ingest 03:30 錯開 5min
        id='db_graph_refresh',
        name='DB Schema 快照更新 (03:35)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 DB Schema 快照更新: 每日 03:30 執行")

    # 添加 KB Embedding 覆蓋率檢查 — 每日 04:00 驗證文件向量完整性
    scheduler.add_job(
        kb_coverage_check_job,
        trigger=CronTrigger(hour=4, minute=0),
        id='kb_coverage_check',
        name='KB Embedding 覆蓋率檢查',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 KB Embedding 覆蓋率檢查: 每日 04:00 執行")

    # P5-2: KG 實體 Embedding 自動回填 — 每日 04:30 批次回填跨專案實體向量
    scheduler.add_job(
        kg_embedding_backfill_job,
        trigger=CronTrigger(hour=4, minute=30),
        id='kg_embedding_backfill',
        name='KG 實體 Embedding 自動回填',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 KG Embedding 自動回填: 每日 04:30 執行")

    # 每日晨報生成 + 推送 — 每日 07:30
    # 2026-08-03：原為 08:00 整點發送。owner 要求「上班 8 點前完成訊息發送，
    # 以利檢視與安排」，故提前至 07:30 —— 實測執行時長最近 20.5s、歷史最長 77.8s，
    # 30 分鐘餘裕充足。晨報同時是所有 LINE 訊息的統一出口
    #（各主題 job queue 進 line_digest_buffer，由此一次帶出並依主題分群）。
    scheduler.add_job(
        morning_report_job,
        trigger=CronTrigger(hour=7, minute=30),
        id='morning_report',
        name='每日晨報生成 + 推送 (Telegram/LINE)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加每日晨報: 每日 08:00 執行")

    # 標案訂閱檢查 — 每日 08:00, 12:00, 18:00 (上班時段 3 次)
    for hour in [8, 12, 18]:
        scheduler.add_job(
            tender_subscription_check_job,
            trigger=CronTrigger(hour=hour, minute=0),
            id=f'tender_subscription_{hour}',
            name=f'標案訂閱檢查 ({hour:02d}:00)',
            replace_existing=True,
            max_instances=1,
            coalesce=True
        )
    logger.info("已添加標案訂閱檢查: 每日 08:00/12:00/18:00 執行")

    # ADR-0046 Phase 4: 標案業務推薦 LINE 通知 — 每日 09:00 (避 03:30 / 08:00 高峰)
    scheduler.add_job(
        tender_business_recommend_job,
        trigger=CronTrigger(hour=9, minute=0),
        id='tender_business_recommend',
        name='標案業務推薦 LINE 推送',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("已添加標案業務推薦 LINE: 每日 09:00 執行")

    # ADR-0046 Phase 3: ezbid → PCC enrichment — 每日 03:30 (避 03:00 Pipeline)
    scheduler.add_job(
        tender_pcc_enrichment_job,
        trigger=CronTrigger(hour=3, minute=30),
        id='tender_pcc_enrichment',
        name='ezbid → PCC enrichment（HIGH only auto-link）',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("已添加 ezbid → PCC enrichment: 每日 03:30 執行")

    # 標案詳情補料（採購性質/底價/決標/廠商）— 每日 03:45
    # 只跑 ezbid 那一段（unit_id 本身就是 org_id，不打 PCC 詳情頁）
    scheduler.add_job(
        tender_detail_enrichment_job,
        trigger=CronTrigger(hour=3, minute=45),
        id='tender_detail_enrichment',
        name='標案詳情補料（ezbid → openfun，不打 PCC）',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("已添加標案詳情補料: 每日 03:45 執行")

    # ezbid 即時快取刷新 — 每小時
    scheduler.add_job(
        ezbid_cache_refresh_job,
        trigger=IntervalTrigger(hours=1),
        id='ezbid_cache_refresh',
        name='ezbid 即時快取刷新 (每小時)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 ezbid 快取刷新: 每小時執行")

    # PCC 今日標案爬取 — 每 2 小時（2026-05-27 P0-1 修法 / 解 50 天 silent dormant）
    # 與 ezbid 每小時錯開，避免雙爬同時打 PCC 站
    scheduler.add_job(
        pcc_today_scrape_job,
        trigger=IntervalTrigger(hours=2),
        id='pcc_today_scrape',
        name='PCC 今日標案爬取 (每 2 小時)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 PCC 今日標案爬取: 每 2 小時執行 (P0-1 修法)")

    # 標案狀態更新 — 每日 06:00 (重查等標期標案的決標結果)
    scheduler.add_job(
        tender_refresh_pending_job,
        trigger=CronTrigger(hour=6, minute=0),
        id='tender_refresh_pending',
        name='標案狀態更新 (每日 06:00)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加標案狀態更新: 每日 06:00 執行")

    # L51 (2026-05-28) 標案儀表板 cache 預熱 — 每 5 min 主動寫 Redis cache
    # 配合 analytics.py TTL 3900→600 修法，用戶 100% cache hit (~12ms vs cold 10s+)
    # next_run_time=+15s：backend 啟動後立即 warm，避用戶 first-hit 等 scraper
    from datetime import datetime as _dt2, timedelta as _td2
    scheduler.add_job(
        tender_dashboard_warm_job,
        trigger=IntervalTrigger(minutes=5),
        id='tender_dashboard_warm',
        name='標案儀表板 cache 預熱 (每 5 min)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=_dt2.now() + _td2(seconds=15),  # 啟動 15s 後立即 warm
    )
    logger.info("已添加標案儀表板 cache 預熱: 每 5 min + startup +15s 首次 (L51)")

    # L51 (2026-05-29) LINE weekly pulse — 每週日 10:00 推活體確認
    # 防 PM2→docker 切換型 silent disabled 再潛伏 40h
    scheduler.add_job(
        line_weekly_pulse_job,
        trigger=CronTrigger(day_of_week='sun', hour=10, minute=0),
        id='line_weekly_pulse',
        name='LINE 通報活體確認 (每週日 10:00)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("已添加 LINE weekly pulse: 每週日 10:00 執行 (L51)")

    # v6.12 治理進化 #2 (2026-05-30) Fitness Tier 1 Daily — 每日 02:00
    # 對應 docs/architecture/FITNESS_LAYERED_EXECUTION_SOP_20260530.md
    # 6 critical step：38/40/47/57/58/60，任一 RED 推 LINE
    scheduler.add_job(
        fitness_daily_job,
        trigger=CronTrigger(hour=2, minute=0),
        id='fitness_daily',
        name='Fitness Tier 1 Daily (每日 02:00, 6 step)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,  # L72: 02:00 壅塞防 misfire skip（與其他治理 cron 對齊）
    )
    logger.info("已添加 Fitness Tier 1 Daily: 每日 02:00 執行 (v6.12 #2)")

    # v6.12 治理進化 #2 完整落地 (2026-05-30) Fitness Tier 2 Weekly — 週日 02:30
    # 12 trend step + 連續 2 週 RED 推 LINE
    scheduler.add_job(
        fitness_weekly_job,
        trigger=CronTrigger(day_of_week='sun', hour=2, minute=30),
        id='fitness_weekly',
        name='Fitness Tier 2 Weekly (週日 02:30, 12 step)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("已添加 Fitness Tier 2 Weekly: 週日 02:30 執行 (v6.12 #2 完整)")

    # v6.12 治理進化 #4 升級版 (2026-05-30) Daily Self-Retrospective — 每日 06:30
    # 7 面向覆盤: ADR/SOP/核心服務/L4x family/學習閉環/觀測閉環/已建構資產
    # Owner 反饋: 「已建構程式圖譜 llmwiki 等好像都無法自動化與覆盤」
    scheduler.add_job(
        daily_self_retrospective_job,
        trigger=CronTrigger(hour=2, minute=45),
        id='daily_self_retrospective',
        name='Daily Self-Retrospective (每日 02:45, 7 面向)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,  # v6.13: missed 2h 內仍補跑
    )
    # v6.13 (2026-05-31): 06:30 → 02:45 避開 LINE 推播 / morning_report 07:30 / 用戶活動
    # owner 訴求: 凌晨時段執行避免相關訊息推播或任務執行導致中斷
    logger.info("已添加 Daily Self-Retrospective: 每日 02:45 執行 (v6.13 改凌晨避干擾)")

    # 自我修復（2026-07-31）— owner：「活化系統自我覆盤檢核與修復機制」
    # 檢核與修復的差別：fitness step 74 只會把缺 case_code 的案件標黃等人處理，
    # 此 job 直接補上。排 02:50（緊接自省之後、早於 03:00 pipeline）。
    scheduler.add_job(
        case_finance_bridge_selfheal_job,
        trigger=CronTrigger(hour=2, minute=50),
        id='case_finance_bridge_selfheal',
        name='案件財務橋樑自我修復 (每日 02:50)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,
    )
    logger.info("已添加案件財務橋樑自我修復: 每日 02:50 執行")

    # v6.12 解 owner「每次詢問都有缺漏」meta 問題
    # 每日 06:00 regenerate GOVERNANCE_INTEGRATED_DASHBOARD.md
    # 整合 5 處 171+ 治理文件 (ADR/lesson/SOP/fitness/architecture) 成 single SSOT
    # Session 啟動讀此檔取完整快照無需重新 grep
    scheduler.add_job(
        governance_dashboard_regen_job,
        trigger=CronTrigger(hour=2, minute=30),
        id='governance_dashboard_regen',
        name='Governance Dashboard Regen (每日 02:30, 整合 5 處 SSOT)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,
    )
    # v6.13 (2026-05-31): 06:00 → 02:30 凌晨執行避干擾
    # 排序: 02:00 fitness daily → 02:30 dashboard → 02:45 self-retro
    logger.info("已添加 Governance Dashboard Regen: 每日 02:30 執行 (v6.13 改凌晨)")

    # L51.7 (2026-05-30) Crystal review overdue alarm — 每週日 09:30
    # 防 proposals → crystals = 0 「學習閉環死」反模式
    scheduler.add_job(
        crystal_review_overdue_alarm_job,
        trigger=CronTrigger(day_of_week='sun', hour=9, minute=30),
        id='crystal_review_overdue',
        name='Crystal Review Overdue Alarm (每週日 09:30)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("已添加 Crystal Review Overdue Alarm: 每週日 09:30 執行 (L51.7)")

    # v6.13 (2026-05-31) Weekly Evolution Generator — 每週日 02:00
    # 對齊 owner「日誌與周報成為實質平臺靈魂」訴求
    # 揭發背景: 5/31 三層覆盤揭發 W22 缺檔，既有 kunge_weekly_summary 只推不產
    # 不覆寫已存在 (W22 手寫保留)
    scheduler.add_job(
        weekly_evolution_generator_job,
        trigger=CronTrigger(day_of_week='sun', hour=2, minute=0),
        id='weekly_evolution_generator',
        name='Weekly Evolution Generator (每週日 02:00, 防 W22 重演)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,
    )
    logger.info("已添加 Weekly Evolution Generator: 每週日 02:00 (v6.13 防 W22 重演)")

    # v6.13 (2026-05-31) Proposal Aging Alert — 每週日 02:20
    # 對齊 owner「學習閉環 + 日誌 + 坤哥真活」訴求
    # 揭發 pending proposal > 7d → 主動 LINE 推 owner (降決策成本)
    # 解 pipeline_red_consecutive_days=11 主因 (crystals=0 學習閉環斷)
    scheduler.add_job(
        proposal_aging_alert_job,
        trigger=CronTrigger(day_of_week='sun', hour=2, minute=20),
        id='proposal_aging_alert',
        name='Proposal Aging Alert (每週日 02:20, 降 owner 決策成本)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,
    )
    logger.info("已添加 Proposal Aging Alert: 每週日 02:20 (v6.13 學習閉環真活)")

    # v6.13 (2026-05-31) Integration E2E Validation — 每日 02:05
    # 對齊 owner「坤哥+Hermes+智能體 整合連通真活 突破性 非一次性」訴求
    # 5 鏈 E2E 驗證 / 任一鏈斷自動 LINE 推 + 寫 marker
    scheduler.add_job(
        integration_e2e_validation_job,
        trigger=CronTrigger(hour=2, minute=5),
        id='integration_e2e_validation',
        name='Integration E2E Validation (每日 02:05, 5 鏈持續驗證)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,
    )
    logger.info("已添加 Integration E2E Validation: 每日 02:05 (v6.13 5 鏈持續驗證真活)")

    # v6.13 (2026-05-31) Critique Health Audit — 每週日 02:15
    # 揭發 critique silent dormant (5/13 後 17 天 0 條的真因監督)
    # 對齊 owner「日誌+周報=靈魂」訴求 — 揭發本身即一條質性反省
    scheduler.add_job(
        critique_health_audit_job,
        trigger=CronTrigger(day_of_week='sun', hour=2, minute=15),
        id='critique_health_audit',
        name='Critique Health Audit (每週日 02:15, 揭發 silent dormant)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,
    )
    logger.info("已添加 Critique Health Audit: 每週日 02:15 (v6.13 揭發 critique silent dormant)")

    # L51.7 Sprint 3.P3.13 — 每週日 11:00「坤哥這週學到什麼」LINE 推
    # 引發 owner 反饋寫入 patterns，啟動 v7_critique_pct 從 0 推升
    scheduler.add_job(
        kunge_weekly_learning_summary_job,
        trigger=CronTrigger(day_of_week='sun', hour=11, minute=0),
        id='kunge_weekly_learning_summary',
        name='坤哥這週學到什麼 (每週日 11:00)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("已添加坤哥週學習摘要: 每週日 11:00 執行 (L51.7 Sprint 3)")

    # Embedding 預熱 — 每日 04:45 為高頻實體預載向量 (在 KG 回填 04:30 之後)
    scheduler.add_job(
        embedding_warmup_job,
        trigger=CronTrigger(hour=4, minute=45),
        id='embedding_warmup',
        name='Embedding 預熱 (top-500 實體)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 Embedding 預熱: 每日 04:45 執行")

    # 帳本對帳 — 每日 05:00 比對 ERP billing/payable vs FinanceLedger
    scheduler.add_job(
        ledger_reconciliation_job,
        trigger=CronTrigger(hour=5, minute=0),
        id='ledger_reconciliation',
        name='帳本對帳檢查 (每日 05:00)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加帳本對帳檢查: 每日 05:00 執行")

    # 系統健康檢查 + Telegram 推播 — 每 5 分鐘
    scheduler.add_job(
        health_check_broadcast_job,
        trigger=IntervalTrigger(minutes=5),
        id='health_check_broadcast',
        name='系統健康檢查 + Telegram 推播 (每5分鐘)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加健康檢查 Telegram 推播: 每 5 分鐘")

    # LLM quota 預警 — 每 6 小時檢查 Groq/NVIDIA 用量，達 80% 閾值即告警
    scheduler.add_job(
        llm_quota_check_job,
        trigger=IntervalTrigger(hours=6),
        id='llm_quota_check',
        name='LLM quota 預警 (Groq/NVIDIA, 每6h)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 LLM quota 預警: 每 6 小時檢查")

    # 2026-04-19 Memory Wiki Phase 2: 每日 04:00 萃取 patterns/failures
    scheduler.add_job(
        memory_pattern_extract_job,
        trigger=CronTrigger(hour=4, minute=5),  # 2026-05-18 P1: 與 kb_coverage_check 04:00 錯開 5min
        id='memory_pattern_extract',
        name='Memory Wiki Pattern Extractor (每日 04:05)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 Memory Pattern Extractor: 每日 04:00 執行")

    # v5.13 Gap 1: 每日 06:00 agent self-diagnosis（主動讀自己 metrics）
    scheduler.add_job(
        agent_self_diagnosis_job,
        trigger=CronTrigger(hour=6, minute=10),  # 2026-05-18 P1: 與 tender_refresh_pending 06:00 錯開 10min
        id='agent_self_diagnosis',
        name='Agent Self-Diagnosis (每日 06:10 — 主動性 Gap 1)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 Agent Self-Diagnosis: 每日 06:00 執行")

    # v5.10.2 #7 KG metrics 即時刷新（Prometheus + Grafana dashboard）
    # next_run_time=now：startup 後立刻 fire 一次填值，不等 15 分（避免 dead startup gap）
    from datetime import datetime as _dt, timedelta as _td
    scheduler.add_job(
        kg_metrics_refresh_job,
        trigger=IntervalTrigger(minutes=15),
        id='kg_metrics_refresh',
        name='KG metrics refresh (每 15 分鐘 → Prometheus)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=_dt.now() + _td(seconds=10),  # 啟動 10s 後 fire 首次
    )
    logger.info("已添加 KG metrics 刷新: 每 15 分鐘 + startup +10s 首次")

    # v5.10.2 Phase 1: Memory Wiki metrics 刷新（坤哥意識體觀測，修 hollow gauge）
    scheduler.add_job(
        memory_metrics_refresh_job,
        trigger=IntervalTrigger(minutes=15),
        id='memory_metrics_refresh',
        name='Memory metrics refresh (每 15 分鐘 → Prometheus)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=_dt.now() + _td(seconds=12),  # 啟動 12s 後 fire 首次（KG 後 2 秒）
    )
    logger.info("已添加 Memory metrics 刷新: 每 15 分鐘 + startup +12s 首次")

    # 2026-04-19 Memory Wiki Phase 3: 每日 04:30 crystal scan（在 pattern extract 之後）
    scheduler.add_job(
        memory_crystallization_scan_job,
        trigger=CronTrigger(hour=4, minute=35),  # 2026-05-18 P1: 與 kg_embedding_backfill 04:30 錯開 5min
        id='memory_crystallization_scan',
        name='Memory Wiki Crystallization Scan (每日 04:35)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 Memory Crystallization Scan: 每日 04:30 執行")

    # 2026-04-19 Memory Wiki Phase 4: 週日 18:00 Agent 週自傳
    scheduler.add_job(
        memory_weekly_autobiography_job,
        trigger=CronTrigger(day_of_week='sun', hour=18, minute=0),
        id='memory_weekly_autobiography',
        name='Memory Wiki Weekly Autobiography (週日 18:00)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 Memory Weekly Autobiography: 週日 18:00 執行")

    # 2026-04-21 v5.8.0 D5-A: 反迴聲室協議（週一 06:00）
    scheduler.add_job(
        memory_anti_echo_scan_job,
        trigger=CronTrigger(day_of_week='mon', hour=6, minute=0),
        id='memory_anti_echo_scan',
        name='反迴聲室協議 (週一 06:00)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("已添加 Anti-Echo Chamber Scan: 週一 06:00 執行")

    # 2026-05-02 v6.4 C1: SOUL.md 跨 repo 自動同步（每日 04:45）
    # 解 SEVERE drift（Missive SOUL ↔ AaaP/Hermes SOUL 不同步問題）
    scheduler.add_job(
        soul_mirror_sync_job,
        trigger=CronTrigger(hour=4, minute=50),  # 2026-05-18 P1: 與 embedding_warmup 04:45 錯開 5min
        id='soul_mirror_sync',
        name='SOUL.md 跨 repo 自動同步 (每日 04:50)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("已添加 SOUL Mirror Sync: 每日 04:45 執行")

    # 2026-05-02 v6.6 Phase B2 (5c): 日終反思 LINE 彙總（每日 22:00）
    # 解體感「anti_echo 觸發即推雜訊」— 每日一次彙總當日自我反思
    scheduler.add_job(
        daily_self_reflection_line_push_job,
        trigger=CronTrigger(hour=22, minute=0),
        id='daily_self_reflection_line_push',
        name='日終反思 LINE 彙總 (每日 22:00)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("已添加 Daily Self-Reflection LINE Push: 每日 22:00 執行")

    # 2026-05-03 v6.7 E4: cron 自我健康檢查 LINE 推（每日 06:30，其他 cron 跑完）
    # 解 fitness step 13 偵測但 silent 的體感斷鏈（與 v6.6 5a/5b/5c 對齊）
    scheduler.add_job(
        cron_self_health_alert_job,
        trigger=CronTrigger(hour=6, minute=30),
        id='cron_self_health_alert',
        name='Cron 自我健康檢查 LINE 推 (每日 06:30)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("已添加 Cron Self-Health Alert: 每日 06:30 執行")

    # 2026-06-02 outcome-freshness watchdog（每日 07:00，所有夜間 cron 後）
    # 驗『各機制是否產出今日新鮮輸出』— 抓 silent no-op（failed 監控抓不到的假成功早退）
    scheduler.add_job(
        cron_outcome_freshness_job,
        trigger=CronTrigger(hour=7, minute=0),
        id='cron_outcome_freshness',
        name='Outcome-freshness watchdog (每日 07:00)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("已添加 Outcome-freshness watchdog: 每日 07:00 執行")

    # Wiki lint — 每日 05:30 掃描 (Phase 4 Lint)
    scheduler.add_job(
        wiki_lint_job,
        trigger=CronTrigger(hour=5, minute=30),
        id='wiki_lint',
        name='Wiki 健康檢查 (每日 05:30)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 Wiki lint: 每日 05:30")

    # Wiki compile — 每週一 05:00 重新編譯公文→wiki (Phase 2 Compile)
    scheduler.add_job(
        wiki_compile_job,
        trigger=CronTrigger(day_of_week='mon', hour=5, minute=0),
        id='wiki_compile',
        name='Wiki 公文編譯 (每週一 05:00)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 Wiki compile: 每週一 05:00")

    # 健康快照 — 每日 06:05 寫入 wiki/log.md（緊接 wiki_lint 05:30 之後）
    scheduler.add_job(
        health_snapshot_log_job,
        trigger=CronTrigger(hour=6, minute=5),
        id='health_snapshot_log',
        name='健康快照 → wiki/log.md (每日 06:05)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加健康快照: 每日 06:05")

    # Cloudflare Tunnel 健康驗證 — 每日 06:15（緊接 health_snapshot 之後）
    scheduler.add_job(
        cloudflare_tunnel_verify_job,
        trigger=CronTrigger(hour=6, minute=15),
        id='cf_tunnel_verify',
        name='Cloudflare Tunnel 驗證 (每日 06:15)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 CF Tunnel 驗證: 每日 06:15")

    # Hermes shadow baseline — 每日 20:00 匯出（ADR-0014 Phase 0）
    # v6.12 (2026-05-30) W1 真因 #2 修法: 移除 cron
    # 原因: container 內無 node, .cjs script 跑 ENOENT silent error
    # 替代: prometheus /metrics scrape 已 cover (shadow_baseline_* 5 gauge)
    # 對齊 L59 「上游必先自治」原則 — CK_Missive 自我整合優化
    # scheduler.add_job(
    #     shadow_baseline_export_job,
    #     trigger=CronTrigger(hour=20, minute=0),
    #     id='shadow_baseline_export',
    #     name='Hermes shadow baseline 匯出 (每日 20:00)',
    #     replace_existing=True,
    #     max_instances=1,
    #     coalesce=True
    # )
    # logger.info("已添加 Hermes baseline 匯出: 每日 20:00")
    logger.info("[v6.12 W1 #2] shadow_baseline_export cron 已移除 (prometheus scrape 已 cover)")

    # 合成基線注入 — 每日 3 次 (09:00/14:00/20:00)
    scheduler.add_job(
        synthetic_baseline_inject_job,
        trigger=CronTrigger(hour='9,14,20', minute=0),
        id='synthetic_baseline_inject',
        name='合成基線注入 (每日 09:00/14:00/20:00)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加合成基線注入: 每日 09:00/14:00/20:00")

    # v6.10 P0-1 (2026-05-18): Optimization Pipeline Orchestrator
    # 每日 03:00 跑 5 step：fitness / capability_audit / memory_loop / shadow_baseline / precommit_probe
    # 合成 digest 寫入 logs/optimization-pipeline/ + 推 LINE
    # 防 v6.10 candidate「自動化流水線 skeleton 0 importer 孤兒」反模式
    scheduler.add_job(
        cron_optimization_pipeline_job,
        trigger=CronTrigger(hour=3, minute=0),
        id='optimization_pipeline',  # L72: align add_job id = @tracked_job id（消 freshness 不符）
        name='Optimization Pipeline 每日巡檢 (03:00, 5 step)',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=600,
    )
    logger.info("已添加 Optimization Pipeline: 每日 03:00")

    # 月度架構覆盤 — 每月 1 日 06:00
    scheduler.add_job(
        monthly_architecture_review_job,
        trigger=CronTrigger(day=1, hour=6, minute=0),
        id='monthly_arch_review',
        name='月度架構覆盤 (每月1日 06:00)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加月度架構覆盤: 每月 1 日 06:00")

    return scheduler


def start_scheduler():
    """啟動排程器 + admin subscription seed"""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("排程器已啟動")

        # 2026-06-02 開機自檢（防 8 cron .parent 路徑 bug 同型 silent 死復發）：
        # script-based cron job 的腳本必須存在，否則 job 每次 silent 早退。
        # 開機 LOUD error（非 silent），讓 mount/path drift 立即暴露。
        try:
            import os as _os
            from pathlib import Path as _Path
            _checks_dir = _Path(_os.getenv("CK_PROJECT_ROOT", "/app")) / "scripts" / "checks"
            _cron_scripts = [
                "daily_self_retrospective.py", "generate_governance_dashboard.py",
                "integration_e2e_validation.py", "proposal_aging_alert.py",
                "critique_health_audit.py", "weekly_evolution_generator.py",
            ]
            _missing = [s for s in _cron_scripts if not (_checks_dir / s).exists()]
            if _missing:
                logger.error(
                    "🔴 開機自檢：%d 個 cron script 找不到 (dir=%s) → 對應 job 將 silent 死："
                    "%s。檢查 CK_PROJECT_ROOT / compose mount target。",
                    len(_missing), _checks_dir, _missing,
                )
            else:
                logger.info("✅ 開機自檢：%d cron script 全在 %s", len(_cron_scripts), _checks_dir)
        except Exception as _e:
            logger.warning("cron script 開機自檢跳過: %s", _e)

        # B-fix2: 自動從 ENV 建立 admin 訂閱（首次啟動時）
        import asyncio
        async def _seed():
            try:
                from app.db.database import async_session_maker
                from app.services.ai.domain.morning_report_delivery import ensure_admin_subscription
                async with async_session_maker() as db:
                    await ensure_admin_subscription(db)
            except Exception as e:
                logger.debug("admin subscription seed skipped: %s", e)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(_seed())
            else:
                loop.run_until_complete(_seed())
        except Exception:
            pass
    else:
        logger.info("排程器已在運行中")


def stop_scheduler():
    """停止排程器"""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("排程器已停止")


def get_scheduler_status() -> dict:
    """取得排程器狀態"""
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()

    return {
        'running': scheduler.running,
        'jobs': [
            {
                'id': job.id,
                'name': job.name,
                'next_run_time': str(job.next_run_time) if job.next_run_time else None,
                'trigger': str(job.trigger)
            }
            for job in jobs
        ]
    }


@asynccontextmanager
async def scheduler_lifespan():
    """
    排程器生命週期管理（用於 FastAPI lifespan）

    Usage:
        app = FastAPI(lifespan=scheduler_lifespan)
    """
    setup_scheduler()
    start_scheduler()
    logger.info("排程器已隨應用程式啟動")
    try:
        yield
    finally:
        stop_scheduler()
        logger.info("排程器已隨應用程式關閉")

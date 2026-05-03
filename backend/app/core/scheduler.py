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

logger = logging.getLogger(__name__)


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
    """記錄每個排程任務的最後執行時間、持續時間、成功/失敗次數"""

    _records: Dict[str, Dict[str, Any]] = {}

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
    def record_success(cls, job_id: str):
        rec = cls._records.get(job_id, {})
        start = rec.pop("_start_time", None)
        duration = round((time.time() - start) * 1000, 1) if start else None
        rec.update({
            "success_count": rec.get("success_count", 0) + 1,
            "last_status": "success",
            "last_run": datetime.now().isoformat(),
            "last_duration_ms": duration,
            "last_error": None,
        })
        cls._records[job_id] = rec

    @classmethod
    def record_failure(cls, job_id: str, error: str):
        rec = cls._records.get(job_id, {})
        start = rec.pop("_start_time", None)
        duration = round((time.time() - start) * 1000, 1) if start else None
        rec.update({
            "failure_count": rec.get("failure_count", 0) + 1,
            "last_status": "failure",
            "last_run": datetime.now().isoformat(),
            "last_duration_ms": duration,
            "last_error": error[:200],
        })
        cls._records[job_id] = rec

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
                SchedulerTracker.record_success(job_id)
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
        _scheduler = AsyncIOScheduler()
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
    except Exception as e:
        logger.error(f"提醒處理排程任務失敗: {e}", exc_info=True)


@tracked_job("cleanup_events")
async def cleanup_expired_events_job():
    """清理過期事件的排程任務"""
    from app.db.database import async_session_maker
    from datetime import datetime, timedelta

    logger.info("開始執行過期事件清理排程任務")

    try:
        async with async_session_maker() as db:
            # 清理 30 天前的已完成事件
            cutoff_date = datetime.now() - timedelta(days=30)
            # 此處可添加清理邏輯，目前僅記錄日誌
            logger.info(f"過期事件清理任務執行完成 (截止日期: {cutoff_date})")
    except Exception as e:
        logger.error(f"過期事件清理排程任務失敗: {e}", exc_info=True)


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
    """Code Graph 增量更新 — 掃描 Python/TypeScript AST 變更並更新圖譜實體"""
    from app.db.database import async_session_maker
    from pathlib import Path

    logger.info("開始執行 Code Graph 增量更新")

    try:
        async with async_session_maker() as db:
            from app.services.ai.graph.code_graph_service import CodeGraphIngestionService
            service = CodeGraphIngestionService(db)
            backend_dir = Path(__file__).parent.parent  # backend/app
            frontend_dir = Path(__file__).parent.parent.parent.parent / "frontend" / "src"

            stats = await service.ingest(
                backend_app_dir=backend_dir,
                incremental=True,
                frontend_src_dir=frontend_dir if frontend_dir.exists() else None,
            )
            await db.commit()
            logger.info(
                f"Code Graph 增量更新完成: "
                f"modules={stats.get('modules', 0)}, "
                f"classes={stats.get('classes', 0)}, "
                f"functions={stats.get('functions', 0)}"
            )
    except Exception as e:
        logger.error(f"Code Graph 增量更新失敗: {e}", exc_info=True)


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
    """KB Embedding 覆蓋率檢查 — 確認所有文件分段都已產生向量"""
    from app.db.database import async_session_maker

    logger.info("開始執行 KB Embedding 覆蓋率檢查")

    try:
        async with async_session_maker() as db:
            from app.services.ai.core.embedding_manager import EmbeddingManager
            stats = await EmbeddingManager.get_coverage_stats(db)
            total = stats.get("total_chunks", 0)
            embedded = stats.get("embedded_chunks", 0)
            coverage = stats.get("coverage_percent", 0)
            logger.info(
                f"KB 覆蓋率檢查完成: "
                f"total={total}, embedded={embedded}, coverage={coverage:.1f}%"
            )
            if coverage < 95.0 and total > 0:
                logger.warning(
                    f"KB Embedding 覆蓋率低於 95%: {coverage:.1f}% "
                    f"({total - embedded} chunks 未 embed)"
                )
    except Exception as e:
        logger.error(f"KB 覆蓋率檢查失敗: {e}", exc_info=True)


@tracked_job("security_scan")
async def security_scan_job():
    """自動安全掃描 — 偵測硬編碼密鑰、SQL 注入、缺認證端點等"""
    from app.db.database import async_session_maker
    from app.services.security_scanner import SecurityScanner

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
    except Exception as e:
        logger.error("安全掃描失敗: %s", e, exc_info=True)


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
    from app.services.notification_helpers import _safe_create_notification

    logger.info("開始執行夜間吹哨者掃描")

    try:
        async with async_session_maker() as db:
            # 掃描基礎警報 (公文截止日/資料品質)
            base_service = ProactiveTriggerService(db)
            base_alerts = await base_service.scan_all()

            # 掃描 ERP 警報 (預算/請款/發票/廠商付款)
            erp_scanner = ERPTriggerScanner(db)
            erp_alerts = await erp_scanner.scan_all()

            all_alerts = base_alerts + erp_alerts

            # 篩選 warning 以上持久化至 DB
            severity_order = {"critical": 3, "warning": 2, "info": 1}
            actionable = [
                a for a in all_alerts
                if severity_order.get(a.severity, 0) >= 2
            ]

            persisted = 0
            for alert in actionable:
                ok = await _safe_create_notification(
                    notification_type="proactive_alert",
                    severity=alert.severity,
                    title=alert.title,
                    message=alert.message,
                    source_table=alert.entity_type,
                    source_id=alert.entity_id,
                    changes=alert.metadata,
                )
                if ok:
                    persisted += 1

            logger.info(
                f"吹哨者完成: "
                f"掃描={len(all_alerts)}, "
                f"warning+={len(actionable)}, "
                f"已通知={persisted}"
            )

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
            result = await svc.backfill_embeddings(batch_size=200)
            await db.commit()
            processed = result.get("processed", 0)
            skipped = result.get("skipped", 0)
            logger.info(
                f"KG Embedding 回填完成: processed={processed}, skipped={skipped}"
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
    except Exception as e:
        logger.error(f"KG Embedding 回填失敗: {e}", exc_info=True)


async def kg_metrics_refresh_job():
    """v5.10.2 #7：KG metrics 即時刷新 — 每 15 分鐘從 DB 讀最新覆蓋率到 Prometheus

    領域：knowledge growth governance
      讓 Grafana dashboard 能看「kg_embedding_coverage_ratio」即時值，
      而非依賴每日 04:30 backfill job 才更新一次。
    """
    from app.db.database import async_session_maker
    from app.core.kg_stats_metrics import get_kg_stats_metrics

    try:
        async with async_session_maker() as db:
            metrics = get_kg_stats_metrics()
            stats = await metrics.refresh_from_db(db)
            logger.debug(
                "KG metrics refreshed: total=%d embedded=%d coverage=%.3f",
                stats["total"], stats["embedded"], stats["coverage"],
            )
    except Exception as e:
        logger.error("KG metrics refresh job 失敗: %s", e, exc_info=True)


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

    try:
        # PROJECT_ROOT/wiki/memory 路徑（同 endpoints/ai/memory.py 用法）
        project_root = Path(__file__).resolve().parents[3]
        wiki_memory = project_root / "wiki" / "memory"
        if not wiki_memory.exists():
            logger.warning("wiki/memory 目錄不存在，skip metrics refresh")
            return

        metrics = get_memory_wiki_metrics()
        metrics.refresh_from_disk(wiki_memory)
        logger.debug(
            "Memory metrics refreshed: diary=%d patterns=%d crystals=%d proposals_pending=%d",
            int(metrics.diary_days._value.get()),
            int(metrics.patterns._value.get()),
            int(metrics.crystals._value.get()),
            int(metrics.proposals_pending._value.get()),
        )
    except Exception as e:
        logger.error("Memory metrics refresh job 失敗: %s", e, exc_info=True)


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
            # LINE push 也套用 sanitizer（與 telegram 一致）
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

    # Step 2: Build admin default summary for snapshot + fallback
    admin_svc = MorningReportService(None)  # pure formatter, db not needed
    admin_summary = await admin_svc.generate_summary_from_data(data)

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
            ok, err = await _push_channel(channel, recipient, admin_summary)
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
                logger.warning(f"ezbid DB 寫入失敗 (非致命): {e}")

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
    except Exception as e:
        logger.error(f"ezbid 快取刷新失敗: {e}", exc_info=True)


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
                .where(FinanceLedger.source_type == "erp_billing")
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
                from app.services.notification_helpers import _safe_create_notification
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
    except Exception as e:
        logger.error(f"帳本對帳失敗: {e}", exc_info=True)


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
                with open(f, encoding="utf-8") as fp:
                    head = fp.read(800)
                if "proposed" in head.lower():
                    fname = os.path.basename(f)
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

        # Telegram 推播
        try:
            from app.services.integration.telegram_bot import get_telegram_bot_service
            tg = get_telegram_bot_service()
            if tg.enabled:
                admin_chat = int(os.getenv("TELEGRAM_ADMIN_CHAT_ID", "0"))
                if admin_chat:
                    await tg.push_message(admin_chat, report)
        except Exception:
            pass
    except Exception as e:
        logger.error("Monthly arch review failed: %s", e, exc_info=True)


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
    except Exception as e:
        logger.error("Wiki compile failed: %s", e, exc_info=True)


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
        project_root = Path(__file__).resolve().parents[3]
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
            # Telegram（低頻，不再每天重複推播）
            try:
                from app.services.integration.telegram_bot import get_telegram_bot_service
                tg = get_telegram_bot_service()
                if tg.enabled:
                    msg = (
                        f"⚠️ Wiki Lint Drift\n"
                        f"pages={total_pages}, orphans={orphan_count}, broken={broken_count}\n"
                        + "\n".join(f"• {a}" for a in alerts)
                    )
                    admin_chat = int(os.getenv("TELEGRAM_ADMIN_CHAT_ID", "0"))
                    if admin_chat:
                        await tg.push_message(admin_chat, msg)
            except Exception:
                pass
    except Exception as e:
        logger.error("Wiki lint failed: %s", e, exc_info=True)


@tracked_job("health_snapshot_log")
async def health_snapshot_log_job():
    """每日健康快照 → wiki/log.md append

    指標：24h commits / wiki 頁數 / scheduler jobs / DB/Redis 狀態 / AgentLearning 數。
    純 append，不觸發其他排程，失敗不影響其他 job。
    """

    project_root = _Path(__file__).resolve().parents[3]
    script = project_root / "scripts" / "health" / "log-health-snapshot.cjs"
    if not script.exists():
        logger.warning("health_snapshot: script not found at %s", script)
        return
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

    project_root = _Path(__file__).resolve().parents[3]
    script = project_root / "scripts" / "checks" / "shadow-baseline-report.cjs"
    if not script.exists():
        logger.warning("shadow_baseline: script not found at %s", script)
        return

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
    project_root = _Path(__file__).resolve().parents[3]
    script = project_root / "scripts" / "checks" / "synthetic-baseline-inject.py"
    if not script.exists():
        logger.warning("synthetic_baseline_inject: script not found at %s", script)
        return

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
    """每日 Cloudflare Tunnel 健康驗證（ADR-0015/0016）

    呼叫 scripts/ops/verify-cloudflare-tunnel.ps1，檢查：
    - Tunnel online / TLS 憑證 / POST-only 政策 / service token 驗證
    失敗時寫入 wiki/log.md 並 logger.error（後續可接 LINE/Discord 通知）。
    只在有 MISSIVE_PUBLIC_URL (且含 cksurvey.tw) 時執行。
    """
    import shutil

    public_url = os.getenv("MISSIVE_PUBLIC_URL", "")
    if "cksurvey.tw" not in public_url:
        logger.debug("cf_tunnel_verify: 非公網部署，跳過")
        return

    project_root = _Path(__file__).resolve().parents[3]
    script = project_root / "scripts" / "ops" / "verify-cloudflare-tunnel.ps1"
    if not script.exists():
        logger.warning("cf_tunnel_verify: script not found at %s", script)
        return

    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if not pwsh:
        logger.warning("cf_tunnel_verify: pwsh/powershell 不存在，跳過")
        return

    rc, out, err = await _run_script_async(
        [pwsh, "-NoProfile", "-File", str(script), "-PublicUrl", public_url],
        cwd=str(project_root), timeout=120, job_name="cf_tunnel_verify",
    )
    if rc == 0:
        logger.info("cf_tunnel_verify: PASS")
    else:
        logger.error("cf_tunnel_verify: FAIL rc=%d\n%s", rc, out[-800:] if out else err)
        log_path = project_root / "wiki" / "log.md"
        if log_path.exists():
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            log_path.write_text(
                log_path.read_text(encoding="utf-8")
                + f"\n## {ts} — CF Tunnel verify FAIL (rc={rc})\n"
                + f"```\n{out[-600:] if out else err}\n```\n",
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
    except Exception as e:
        logger.error("Embedding 預熱失敗: %s", e, exc_info=True)


# Health check 去抖動 — 連續 N 次失敗才告警，避免 transient 偽警報
# 2026-04-19: asyncpg connection invalidate 瞬間觸發誤警，加入 2-strike 門檻
_HEALTH_FAIL_STREAK = 0
_HEALTH_ALERT_THRESHOLD = 2  # 連續 2 次（10 分鐘）失敗才告警


@tracked_job("health_check_broadcast")
async def health_check_broadcast_job():
    """系統健康檢查 — 每 5 分鐘輪詢，連續 2 次異常才推播 Telegram（去抖動）"""
    global _HEALTH_FAIL_STREAK
    import os
    import httpx

    admin_chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
    if not admin_chat_id:
        return  # 未設定管理 chat_id，跳過

    health_url = "http://127.0.0.1:8001/health"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(health_url)
            data = resp.json()

        is_healthy = resp.status_code == 200 and data.get("status") == "healthy"

        if is_healthy:
            # 健康 — 若上次剛告警（streak >= threshold），推一次「恢復」通知後歸零
            if _HEALTH_FAIL_STREAK >= _HEALTH_ALERT_THRESHOLD:
                try:
                    from app.services.integration.telegram_bot import get_telegram_bot_service
                    await get_telegram_bot_service().push_message(
                        int(admin_chat_id),
                        f"✅ 公文系統已恢復\n\n時間: {data.get('timestamp', 'N/A')}",
                    )
                except Exception:
                    pass
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
        from app.services.integration.telegram_bot import get_telegram_bot_service
        await get_telegram_bot_service().push_message(int(admin_chat_id), msg)
        logger.warning("健康檢查連續異常已推播至 Telegram: %s", data.get("status"))

    except Exception as e:
        # API 完全無回應 — 同樣採用 streak 機制
        _HEALTH_FAIL_STREAK += 1
        logger.error(
            "健康檢查失敗 (streak=%d/%d): %s",
            _HEALTH_FAIL_STREAK, _HEALTH_ALERT_THRESHOLD, e,
        )
        if _HEALTH_FAIL_STREAK < _HEALTH_ALERT_THRESHOLD:
            return
        msg = f"🚨 公文系統 API 無回應（連續 {_HEALTH_FAIL_STREAK} 次）\n\n錯誤: {str(e)[:200]}"
        try:
            from app.services.integration.telegram_bot import get_telegram_bot_service
            await get_telegram_bot_service().push_message(int(admin_chat_id), msg)
        except Exception:
            pass  # Telegram 也失敗，只記 log


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
    admin_chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
    if not admin_chat_id:
        return

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
            msg = "⚡ LLM Quota 預警\n\n" + "\n\n".join(alerts) + f"\n\n時間: {today}"
            from app.services.integration.telegram_bot import get_telegram_bot_service
            await get_telegram_bot_service().push_message(int(admin_chat_id), msg)
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

    except Exception as e:
        logger.warning("LLM quota check 失敗: %s", e)


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
    """
    from app.db.database import AsyncSessionLocal
    from app.services.memory.autobiography import AutobiographyGenerator

    logger.info("開始執行 Memory Weekly Autobiography")
    try:
        async with AsyncSessionLocal() as db:
            gen = AutobiographyGenerator(db)
            result = await gen.run()
            logger.info(
                "Weekly Autobiography 完成: %s, queries=%d, soul=%s, tg=%s, line=%s, chars=%d",
                result.get("week_id"), result.get("total_queries"),
                result.get("soul_updated"),
                result.get("telegram_pushed"), result.get("line_pushed"),
                result.get("narrative_chars"),
            )
    except Exception as e:
        logger.error("Weekly Autobiography 失敗: %s", e, exc_info=True)


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
            # Telegram 通知（若觸發）
            import os
            admin_chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
            if admin_chat_id:
                try:
                    from app.services.integration.telegram_bot import get_telegram_bot_service
                    msg = (
                        "🔔 反迴聲室觸發\n\n"
                        f"原因：{result.get('reason')}\n\n"
                        "候選質疑：\n"
                        + "\n".join(
                            f"{i+1}. {r}" for i, r in enumerate(
                                result.get("reflections", [])[:3]
                            )
                        )
                        + "\n\n（已寫入今日 diary）"
                    )
                    await get_telegram_bot_service().push_message(
                        int(admin_chat_id), msg,
                    )
                except Exception as e:
                    logger.debug("AntiEcho Telegram notify failed: %s", e)
        else:
            logger.info("AntiEcho not triggered: %s", result.get("reason"))
    except Exception as e:
        logger.error("Anti-Echo Scan 失敗: %s", e, exc_info=True)


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
    if os.getenv("LINE_GROWTH_NOTIFY_ENABLED", "true").lower() in ("false", "0"):
        return
    line_user_id = os.getenv("LINE_ADMIN_USER_ID")
    if not line_user_id:
        return

    summary = SchedulerTracker.get_summary()
    records = SchedulerTracker.get_all()

    total = summary.get("total_jobs", 0)
    failed = summary.get("failed", 0)
    never_run = summary.get("never_run", 0)
    status = summary.get("status", "unknown")

    # 全綠 → silent
    if failed == 0 and never_run < (total / 2 if total else 0):
        logger.info("Cron self-health: all healthy, skip LINE push")
        return

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
    try:
        from app.services.integration.line_bot import LineBotService
        line_bot = LineBotService()
        if not line_bot.enabled:
            return
        ok = await line_bot.push_message(line_user_id, text_msg)
        if ok:
            logger.info(
                "Cron self-health alert pushed: failed=%d never_run=%d",
                failed, never_run,
            )
    except Exception as e:
        logger.error(
            "Cron self-health LINE push failed: %s", e, exc_info=True,
        )


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
        # Telegram 通知（若有新 proposal）
        if proposals:
            import os
            admin_chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
            if admin_chat_id:
                try:
                    from app.services.integration.telegram_bot import get_telegram_bot_service
                    msg = (
                        f"🔮 新 Crystal 提案（{len(proposals)} 筆）\n\n"
                        + "\n".join(f"• {p.proposal_id}: {p.reason[:80]}" for p in proposals[:5])
                        + "\n\n批准請至 /ai/memory Dashboard（Phase 5）或使用 API。"
                    )
                    await get_telegram_bot_service().push_message(int(admin_chat_id), msg)
                except Exception as e:
                    logger.debug("Crystal proposal Telegram notify failed: %s", e)
    except Exception as e:
        logger.error("Memory Crystallization 失敗: %s", e, exc_info=True)


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
    except Exception as e:
        logger.error("Memory Pattern Extraction 失敗: %s", e, exc_info=True)


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
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[3]
    script_path = project_root / "scripts" / "sync" / "sync_soul_to_hermes.sh"
    target_path = project_root.parent / "CK_AaaP" / "runbooks" / "hermes-stack" / "SOUL.md"

    if not script_path.exists():
        logger.warning("SOUL sync script missing, skip: %s", script_path)
        return
    if not target_path.exists():
        logger.debug("AaaP target SOUL.md missing, skip (dev env?): %s", target_path)
        return

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
    else:
        logger.error(
            "SOUL Mirror Sync 失敗 rc=%d stderr=%s",
            rc, (stderr or "")[:200],
        )


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
        coalesce=True
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
        coalesce=True
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
        id='code_graph_update',
        name='Code Graph 增量更新 (AST)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 Code Graph 增量更新: 每日 03:00 執行")

    # 添加 DB Schema 快照更新 — 每日 03:30 反射 PostgreSQL schema
    scheduler.add_job(
        db_schema_refresh_job,
        trigger=CronTrigger(hour=3, minute=30),
        id='db_graph_refresh',
        name='DB Schema 快照更新',
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

    # 每日晨報生成 + 推送 — 每日 08:00 (Telegram/LINE)
    scheduler.add_job(
        morning_report_job,
        trigger=CronTrigger(hour=8, minute=0),
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
        trigger=CronTrigger(hour=4, minute=0),
        id='memory_pattern_extract',
        name='Memory Wiki Pattern Extractor (每日 04:00)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 Memory Pattern Extractor: 每日 04:00 執行")

    # v5.13 Gap 1: 每日 06:00 agent self-diagnosis（主動讀自己 metrics）
    scheduler.add_job(
        agent_self_diagnosis_job,
        trigger=CronTrigger(hour=6, minute=0),
        id='agent_self_diagnosis',
        name='Agent Self-Diagnosis (每日 06:00 — 主動性 Gap 1)',
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
        trigger=CronTrigger(hour=4, minute=30),
        id='memory_crystallization_scan',
        name='Memory Wiki Crystallization Scan (每日 04:30)',
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
        trigger=CronTrigger(hour=4, minute=45),
        id='soul_mirror_sync',
        name='SOUL.md 跨 repo 自動同步 (每日 04:45)',
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
    scheduler.add_job(
        shadow_baseline_export_job,
        trigger=CronTrigger(hour=20, minute=0),
        id='shadow_baseline_export',
        name='Hermes shadow baseline 匯出 (每日 20:00)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 Hermes baseline 匯出: 每日 20:00")

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

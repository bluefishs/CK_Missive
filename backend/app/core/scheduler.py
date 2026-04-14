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
import time
from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager
from functools import wraps

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

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
    """裝飾器：自動追蹤排程任務的執行狀態"""
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
    from app.services.reminder_service import ReminderService

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
    from app.services.document_calendar_service import DocumentCalendarService
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


@tracked_job("code_graph_update")
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
    NemoClaw 夜間吹哨者 — 掃描 PM/ERP 預算超支、逾期請款、待核銷發票等警報。

    掃描結果：
    1. 持久化至 SystemNotification (DB)
    2. 推播至 LINE (若已設定)
    """
    from app.db.database import async_session_maker
    from app.services.ai.proactive.proactive_triggers import ProactiveTriggerService
    from app.services.ai.proactive.proactive_triggers_erp import ERPTriggerScanner
    from app.services.notification_helpers import _safe_create_notification

    logger.info("開始執行 NemoClaw 夜間吹哨者掃描")

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
                f"NemoClaw 吹哨者完成: "
                f"掃描={len(all_alerts)}, "
                f"warning+={len(actionable)}, "
                f"已通知={persisted}"
            )

            # LINE 推播 (嘗試性，失敗不影響主流程)
            try:
                from app.services.line_push_scheduler import LinePushScheduler
                push_scheduler = LinePushScheduler(db)
                push_result = await push_scheduler.scan_and_push(min_severity="warning")
                if push_result.get("sent", 0) > 0:
                    logger.info(f"LINE 推播完成: {push_result}")
            except Exception as line_err:
                logger.debug(f"LINE 推播跳過: {line_err}")

            # 派工進度彙整推送 (LINE Flex + Discord Embed)
            try:
                from app.services.line_push_scheduler import LinePushScheduler
                progress_scheduler = LinePushScheduler(db)
                progress_result = await progress_scheduler.push_dispatch_progress()
                if progress_result.get("sent", 0) > 0:
                    logger.info(f"派工進度 LINE 推送完成: {progress_result}")
            except Exception as progress_err:
                logger.debug(f"派工進度推送跳過: {progress_err}")

    except Exception as e:
        logger.error(f"NemoClaw 夜間吹哨者失敗: {e}", exc_info=True)


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
    except Exception as e:
        logger.error(f"KG Embedding 回填失敗: {e}", exc_info=True)


@tracked_job("morning_report")
async def morning_report_job():
    """每日 08:00 — 生成晨報並推送至 Telegram/LINE"""
    from app.db.database import async_session_maker
    from app.services.ai.domain.morning_report_service import MorningReportService

    logger.info("開始執行每日晨報生成")

    try:
        async with async_session_maker() as db:
            svc = MorningReportService(db)
            summary = await svc.generate_summary()

        pushed_to = []

        # Push to Telegram (direct, no OpenClaw needed)
        try:
            import os
            from app.services.telegram_bot_service import get_telegram_bot_service
            tg = get_telegram_bot_service()
            chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
            if chat_id and tg.enabled:
                ok = await tg.send_message(int(chat_id), summary)
                if ok:
                    pushed_to.append("Telegram")
        except Exception as tg_err:
            logger.debug("Morning report Telegram push skipped: %s", tg_err)

        # Push to LINE (if configured)
        try:
            import os
            from app.services.line_bot_service import LineBotService
            line = LineBotService()
            line_user_id = os.getenv("LINE_ADMIN_USER_ID")
            if line_user_id and line.enabled:
                ok = await line.push_message(line_user_id, summary)
                if ok:
                    pushed_to.append("LINE")
        except Exception as line_err:
            logger.debug("Morning report LINE push skipped: %s", line_err)

        if pushed_to:
            logger.info("Morning report pushed to: %s", ", ".join(pushed_to))
        else:
            logger.info("Morning report generated (no push targets configured)")

    except Exception as e:
        logger.error("Morning report failed: %s", e, exc_info=True)


@tracked_job("ezbid_cache_refresh")
async def ezbid_cache_refresh_job():
    """ezbid 全量快取刷新 — 每小時抓取今日全量 + 寫入 DB (統一服務層)"""
    from app.db.database import async_session_maker

    logger.info("開始 ezbid 全量快取刷新")
    try:
        from app.services.ezbid_scraper import EzbidScraper
        scraper = EzbidScraper()
        # 使用統一服務層 get_today_all() — 10 頁 × 100 筆 + Redis 共享快取
        result = await scraper.get_today_all()
        records = result.get("records", [])
        logger.info(f"ezbid 全量刷新: {len(records)} 筆")

        # 寫入 DB (持久化)
        if records:
            try:
                async with async_session_maker() as db:
                    from app.services.tender_cache_service import save_search_results
                    saved = await save_search_results(db, records, source="ezbid")
                    # 同步入圖 (標案機關/廠商 → canonical_entities)
                    from app.services.tender_cache_service import _ingest_tender_entities
                    ingested = await _ingest_tender_entities(db, records)
                    logger.info(f"ezbid → DB: {saved} 筆新增, KG: {ingested} 實體入圖")
            except Exception as e:
                logger.warning(f"ezbid DB 寫入失敗 (非致命): {e}")
    except Exception as e:
        logger.error(f"ezbid 快取刷新失敗: {e}")


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
        from app.services.wiki_service import get_wiki_service
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
            from app.services.telegram_bot_service import get_telegram_bot_service
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
            from app.services.wiki_compiler import WikiCompiler
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
    """Wiki 健康檢查 — 偵測孤立頁面、斷裂連結"""
    try:
        from app.services.wiki_service import get_wiki_service
        svc = get_wiki_service()
        result = await svc.lint()
        stats = svc.get_stats()
        logger.info(
            "Wiki lint: %d pages, %d orphans, %d broken links, health=%s",
            result["total_pages"], len(result["orphan_pages"]),
            len(result["broken_links"]), result["health"],
        )
        # 推播至 Telegram (若有問題)
        if result["health"] != "good":
            try:
                from app.services.telegram_bot_service import get_telegram_bot_service
                tg = get_telegram_bot_service()
                if tg.enabled:
                    msg = (
                        f"Wiki Lint: {result['total_pages']} pages, "
                        f"{len(result['orphan_pages'])} orphans, "
                        f"{len(result['broken_links'])} broken links"
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
    import subprocess
    from pathlib import Path
    from datetime import date

    project_root = Path(__file__).resolve().parents[3]
    script = project_root / "scripts" / "health" / "log-health-snapshot.cjs"
    if not script.exists():
        logger.warning("health_snapshot: script not found at %s", script)
        return
    try:
        proc = subprocess.run(
            ["node", str(script)],
            cwd=str(project_root),
            capture_output=True, text=True, timeout=30, check=False,
        )
        if proc.returncode == 0:
            logger.info("health_snapshot: %s", proc.stdout.strip() or "ok")
        else:
            logger.warning("health_snapshot failed (rc=%d): %s", proc.returncode, proc.stderr.strip())
    except subprocess.TimeoutExpired:
        logger.warning("health_snapshot timeout (>30s)")
    except Exception as e:
        logger.error("health_snapshot error: %s", e)


@tracked_job("tender_refresh_pending")
async def tender_refresh_pending_job():
    """標案狀態更新 — 每日重查等標期標案的決標結果"""
    from app.db.database import async_session_maker

    logger.info("開始標案狀態更新")
    try:
        async with async_session_maker() as db:
            from app.services.tender_cache_service import refresh_pending_tenders
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
            from app.services.tender_subscription_scheduler import check_all_subscriptions
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


@tracked_job("health_check_broadcast")
async def health_check_broadcast_job():
    """系統健康檢查 — 每 5 分鐘輪詢，異常時推播到 Telegram 管理群組"""
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

        if resp.status_code != 200 or data.get("status") != "healthy":
            db_status = data.get("database", {}).get("status", "unknown")
            msg = (
                f"🚨 公文系統健康異常\n\n"
                f"狀態: {data.get('status', 'unknown')}\n"
                f"資料庫: {db_status}\n"
                f"時間: {data.get('timestamp', 'N/A')}"
            )
            from app.services.telegram_bot_service import get_telegram_bot_service
            await get_telegram_bot_service().push_message(int(admin_chat_id), msg)
            logger.warning("健康檢查異常，已推播至 Telegram: %s", data.get("status"))

    except Exception as e:
        # API 完全無回應 — 這是最嚴重的情況
        msg = f"🚨 公文系統 API 無回應\n\n錯誤: {str(e)[:200]}"
        try:
            from app.services.telegram_bot_service import get_telegram_bot_service
            await get_telegram_bot_service().push_message(int(admin_chat_id), msg)
        except Exception:
            pass  # Telegram 也失敗，只記 log
        logger.error("健康檢查失敗: %s", e)


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

    # 添加 NemoClaw 夜間吹哨者 — 每日 00:30 掃描預算/逾期/待核銷
    scheduler.add_job(
        proactive_trigger_scan_job,
        trigger=CronTrigger(hour=0, minute=30),
        id='proactive_trigger_scan',
        name='NemoClaw 夜間吹哨者 (預算/逾期/待核銷)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 NemoClaw 夜間吹哨者: 每日 00:30 執行")

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
    """啟動排程器"""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("排程器已啟動")
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

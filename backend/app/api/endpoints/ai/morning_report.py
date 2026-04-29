"""
晨報操作 API — Morning Report Operations 領域

從 ai_stats.py 抽出（領域驅動分治）。
這完全不是 stats — 是晨報的生成、推送、歷史快照、派送觀測性。

端點:
- POST /ai/stats/morning-report/preview — 晨報預覽（不推送）
- POST /ai/stats/morning-report/push — 手動推送（含 delivery log + 字數截斷保護）
- POST /ai/stats/morning-report/history — 近 14 天 snapshot 列表（B4）
- POST /ai/stats/morning-report/status — 近 7 天 delivery log + 連續失敗天數（A1）
"""

import logging
import os

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import optional_auth, get_async_db

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_MSG_LEN = 4500  # LINE 上限 5000，留 buffer


@router.post("/stats/morning-report/preview")
async def preview_morning_report(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
):
    """預覽晨報（手動觸發，不推送）— 返回 Gemma 4 生成的自然語言摘要 + 原始數據"""
    from app.services.ai.domain.morning_report_service import MorningReportService

    try:
        svc = MorningReportService(db)
        data = await svc.generate_report()
        summary = await svc.generate_summary_from_data(data)
        return JSONResponse(
            {"success": True, "summary": summary, "data": data},
            media_type="application/json; charset=utf-8",
        )
    except Exception as e:
        logger.error("Morning report preview failed: %s", e, exc_info=True)
        return JSONResponse(
            {"success": False, "error": "晨報預覽失敗，請稍後再試"},
            status_code=500,
            media_type="application/json; charset=utf-8",
        )


@router.post("/stats/morning-report/push")
async def push_morning_report(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
):
    """手動推送晨報到 Telegram/LINE（含 delivery log + 字數截斷保護）"""
    from app.services.ai.domain.morning_report_service import MorningReportService
    from app.services.ai.domain.morning_report_delivery import (
        log_delivery, today_taipei,
    )

    try:
        svc = MorningReportService(db)
        data = await svc.generate_report()
        summary = await svc.generate_summary_from_data(data)

        # B-fix5: 字數截斷保護
        if len(summary) > MAX_MSG_LEN:
            summary = summary[:MAX_MSG_LEN] + "\n\n⋯ 完整版請查閱系統"

        report_date = today_taipei()
        pushed_to = []

        # Telegram push + delivery log
        tg_chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
        if tg_chat_id:
            try:
                from app.services.integration.telegram_bot import get_telegram_bot_service
                tg = get_telegram_bot_service()
                if tg.enabled:
                    ok = await tg.send_message(int(tg_chat_id), summary, parse_mode="")
                    await log_delivery(
                        db, report_date=report_date, channel="telegram",
                        recipient=str(tg_chat_id),
                        status="success" if ok else "failed",
                        summary_length=len(summary),
                        trigger_source="api",
                    )
                    if ok:
                        pushed_to.append("Telegram")
            except Exception as tg_err:
                logger.warning("Morning report Telegram push failed: %s", tg_err)
                await log_delivery(
                    db, report_date=report_date, channel="telegram",
                    recipient=str(tg_chat_id), status="failed",
                    error_msg=str(tg_err), trigger_source="api",
                )

        # LINE push + delivery log
        line_user_id = os.getenv("LINE_ADMIN_USER_ID")
        if line_user_id:
            try:
                from app.services.integration.line_bot import LineBotService
                line = LineBotService()
                if line.enabled:
                    ok = await line.push_message(line_user_id, summary)
                    await log_delivery(
                        db, report_date=report_date, channel="line",
                        recipient=line_user_id,
                        status="success" if ok else "failed",
                        summary_length=len(summary),
                        trigger_source="api",
                    )
                    if ok:
                        pushed_to.append("LINE")
            except Exception as line_err:
                logger.warning("Morning report LINE push failed: %s", line_err)
                await log_delivery(
                    db, report_date=report_date, channel="line",
                    recipient=line_user_id, status="failed",
                    error_msg=str(line_err), trigger_source="api",
                )

        return JSONResponse(
            {
                "success": True,
                "summary": summary,
                "pushed_to": pushed_to,
                "message": (
                    f"已推送至 {', '.join(pushed_to)}"
                    if pushed_to
                    else "已生成但無推送目標 (請設定 TELEGRAM_ADMIN_CHAT_ID 或 LINE_ADMIN_USER_ID)"
                ),
            },
            media_type="application/json; charset=utf-8",
        )
    except Exception as e:
        logger.error("Morning report push failed: %s", e, exc_info=True)
        return JSONResponse(
            {"success": False, "error": "晨報推送失敗，請稍後再試"},
            status_code=500,
            media_type="application/json; charset=utf-8",
        )


@router.post("/stats/morning-report/history")
async def morning_report_history(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
):
    """晨報歷史快照（B4）— 近 14 天 snapshot 列表"""
    from app.services.ai.domain.morning_report_delivery import get_snapshots

    try:
        snapshots = await get_snapshots(db, days=14)
        return JSONResponse(
            {"success": True, "snapshots": snapshots},
            media_type="application/json; charset=utf-8",
        )
    except Exception as e:
        logger.error("Morning report history failed: %s", e, exc_info=True)
        return JSONResponse(
            {"success": False, "error": "晨報歷史查詢失敗"},
            status_code=500,
            media_type="application/json; charset=utf-8",
        )


@router.post("/stats/morning-report/status")
async def morning_report_status(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
):
    """晨報派送觀測性 — 近 7 天 delivery log + 連續失敗天數（A1）"""
    from app.services.ai.domain.morning_report_delivery import (
        get_recent_deliveries, consecutive_failure_days, today_taipei,
    )

    try:
        deliveries = await get_recent_deliveries(db, days=7)
        tg_streak = await consecutive_failure_days(db, "telegram")
        line_streak = await consecutive_failure_days(db, "line")

        return JSONResponse(
            {
                "success": True,
                "today": today_taipei().isoformat(),
                "deliveries": deliveries,
                "alerts": {
                    "telegram_consecutive_failures": tg_streak,
                    "line_consecutive_failures": line_streak,
                    "should_alert": tg_streak >= 2 or line_streak >= 2,
                },
            },
            media_type="application/json; charset=utf-8",
        )
    except Exception as e:
        logger.error("Morning report status failed: %s", e, exc_info=True)
        return JSONResponse(
            {"success": False, "error": "晨報狀態查詢失敗"},
            status_code=500,
            media_type="application/json; charset=utf-8",
        )

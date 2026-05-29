"""
Tender 業務推薦 LINE 通知 (ADR-0046 Phase 4)

對「近 N 日新增 + 預算大 + 機關曾合作」的標案自動 LINE 推送 admin。

═══════════════ 篩選原則（5 條 AND 條件）═══════════════
1. **時間窗口**: announce_date >= CURRENT_DATE - days_back（預設 1 日）
   → 只推「今日新增」標案，避反覆推同一筆

2. **資料來源**: source='pcc' OR pcc_match_unit_id IS NOT NULL
   → PCC 直接公告 或 ezbid HIGH-matched 到 PCC（ADR-0046 enrichment）
   → 排除孤兒 ezbid（無法對應 PCC 詳情）

3. **預算門檻**: budget IS NOT NULL AND budget >= budget_min（預設 100 萬）
   → 過濾小額採購，聚焦業務有意義案件
   → 重要: PCC source 4076 筆 budget 100% NULL → 此分支實際不命中
            業務推薦真實只命中 394 HIGH-matched ezbid 持有 budget 案件
   → 見 docs/architecture/TENDER_PCC_COVERAGE_AUDIT_20260529.md

4. **合作機關**: unit_name IN (SELECT agency_name FROM government_agencies)
   → 只推過去 documents 互動過的機關（避雜訊）
   → agency_match_count = 該機關過往 documents 數量（合作次數標記）

5. **排序**: ORDER BY budget DESC, announce_date DESC
   → 預算大優先（業務 ROI 高）+ 新公告優先
   → LIMIT MAX_RECOMMEND_PER_RUN=20（避刷屏）

═══════════════ 去重機制 ═══════════════
- Redis: 同案號每日只推 1 次（TTL 25h）
- DB: tender_recommendation_history 全推送結果留底
       (L51 task B 觀測閉環 — 含 error 案例追溯)

═══════════════ Cron 排程 ═══════════════
- 每日 09:00（避 03:30 enrichment 與 08:00 morning_report 高峰）
- next_run_time 不立即觸發（避 backend 重啟即刷屏）

═══════════════ LINE 訊息範本 (L51.3 後)═══════════════
  🎯 業務推薦標案
  📋 [案號] 道路鋪面工程
  🏛 苗栗縣公館鄉公所（合作 3 次）
  💰 預算 $1,500,000
  📅 公告 2026-05-29
  🔗 missive 詳情: https://missive.cksurvey.tw/tender/pcc/...
  🏛 PCC 採購網: https://web.pcc.gov.tw/tps/atm/atmAwardAction.do?...

Version: 1.1.0
Created: 2026-05-28 (ADR-0046 Phase 4)
Updated: 2026-05-29 L51.3 — 加 PCC 官方連結 + 完整篩選原則註解
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# 業務門檻
DEFAULT_BUDGET_MIN = 1_000_000  # 100 萬
DEFAULT_DAYS_BACK = 1  # 過去 N 日新增
MAX_RECOMMEND_PER_RUN = 20  # 每次跑最多推 N 個（避刷屏）


async def find_business_recommendations(
    db: AsyncSession,
    days_back: int = DEFAULT_DAYS_BACK,
    budget_min: int = DEFAULT_BUDGET_MIN,
    limit: int = MAX_RECOMMEND_PER_RUN,
) -> List[Dict[str, Any]]:
    """找近期高潛力業務推薦標案。

    條件:
      - 公告日 ≥ NOW() - N days
      - source = pcc (或已 enrichment HIGH-matched 的 ezbid)
      - budget ≥ budget_min
      - unit_name 在合作機關名單

    Returns:
        List[{
            unit_id, job_number, title, unit_name, budget,
            announce_date, agency_match_count
        }]
    """
    sql = text("""
        WITH cooperated_agencies AS (
            -- 從 government_agencies 取合作機關（過去 documents 互動過）
            SELECT DISTINCT agency_name FROM government_agencies
        ),
        recent_tenders AS (
            SELECT
                -- L51.3 (2026-05-29) 對 ezbid HIGH-matched 用 PCC 對應碼，
                -- ezbid 自己的 unit_id 是純數字（如 2249296），打不開 PCC 採購網。
                -- COALESCE → 優先用 pcc_match_*，無對應則 fallback ezbid 原 id
                COALESCE(tr.pcc_match_unit_id, tr.unit_id) AS unit_id,
                COALESCE(tr.pcc_match_job_number, tr.job_number) AS job_number,
                tr.title, tr.unit_name,
                tr.budget, tr.announce_date, tr.source, tr.pcc_match_unit_id,
                tr.pcc_match_job_number, tr.pcc_match_confidence
            FROM tender_records tr
            WHERE
                -- 近期新增
                tr.announce_date >= (CURRENT_DATE - :days_back * INTERVAL '1 day')::date
                -- 預算門檻
                AND tr.budget IS NOT NULL
                AND tr.budget >= :budget_min
                -- 只推 PCC（或 HIGH-matched ezbid 走 PCC 對應）
                AND (tr.source = 'pcc' OR tr.pcc_match_unit_id IS NOT NULL)
        )
        SELECT
            rt.unit_id, rt.job_number, rt.title, rt.unit_name,
            rt.budget, rt.announce_date, rt.source,
            -- 合作次數（同名機關過往 documents 數）
            (
                SELECT COUNT(*) FROM government_agencies ga
                WHERE ga.agency_name = rt.unit_name
            ) AS agency_match_count
        FROM recent_tenders rt
        WHERE
            -- 機關曾合作
            rt.unit_name IN (SELECT agency_name FROM cooperated_agencies)
        ORDER BY rt.budget DESC, rt.announce_date DESC
        LIMIT :limit
    """)

    try:
        result = await db.execute(sql, {
            "days_back": days_back,
            "budget_min": budget_min,
            "limit": limit,
        })
        rows = result.fetchall()
    except Exception as e:
        logger.error(f"find_business_recommendations failed: {e}", exc_info=True)
        return []

    return [
        {
            "unit_id": r.unit_id,
            "job_number": r.job_number,
            "title": r.title,
            "unit_name": r.unit_name,
            "budget": int(r.budget) if r.budget else 0,
            "announce_date": str(r.announce_date) if r.announce_date else "",
            "source": r.source,
            "agency_match_count": int(r.agency_match_count) if r.agency_match_count else 0,
        }
        for r in rows
    ]


async def _is_already_pushed(redis_client, unit_id: str, job_number: str) -> bool:
    """Redis 去重：同案號每日只推 1 次。"""
    if not redis_client:
        return False
    try:
        key = f"tender:recommend:pushed:{unit_id}:{job_number}"
        return await redis_client.exists(key) > 0
    except Exception:
        return False


async def _mark_pushed(redis_client, unit_id: str, job_number: str) -> None:
    """Redis 標記已推（25h TTL — 比日推稍長確保不重發）。"""
    if not redis_client:
        return
    try:
        key = f"tender:recommend:pushed:{unit_id}:{job_number}"
        await redis_client.setex(key, 25 * 3600, "1")
    except Exception:
        pass


def _format_recommendation_line(rec: Dict[str, Any]) -> str:
    """單一推薦 → LINE 訊息文字。

    L51.3 (2026-05-29) Owner 反饋：標案應可連結 PCC 以利檢視
    雙連結設計：
      - missive 詳情頁：含 enrichment / 戰情室 / 廠商分析
      - PCC 政府電子採購網：官方原始公告（決標查詢）
    """
    from urllib.parse import quote

    budget_str = f"${rec['budget']:,}" if rec["budget"] else "（預算未公開）"
    agency_cnt = rec.get("agency_match_count", 0)
    coop_str = f"（合作 {agency_cnt} 次）" if agency_cnt > 1 else "（合作機關）"

    unit_id_url = quote(str(rec["unit_id"]), safe='')
    job_url = quote(str(rec["job_number"]), safe='')

    # missive 詳情頁（內部頁，含 enrichment + 戰情室）
    missive_url = (
        f"https://missive.cksurvey.tw/tender/pcc/"
        f"{unit_id_url}/{job_url}"
    )
    # PCC 政府電子採購網（官方原始公告，方便直接查官方頁面）
    pcc_url = (
        "https://web.pcc.gov.tw/tps/atm/atmAwardAction.do"
        f"?method=goSearch&unitId={unit_id_url}&jobNumber={job_url}"
    )

    return (
        f"🎯 業務推薦標案\n"
        f"📋 [{rec['job_number']}] {rec['title']}\n"
        f"🏛 {rec['unit_name']} {coop_str}\n"
        f"💰 預算 {budget_str}\n"
        f"📅 公告 {rec['announce_date']}\n"
        f"🔗 missive 詳情:\n{missive_url}\n"
        f"🏛 PCC 採購網:\n{pcc_url}"
    )


async def _write_history(
    db: AsyncSession,
    rec: Dict[str, Any],
    status: str,
    error_msg: Optional[str] = None,
    channel: str = "line",
) -> None:
    """L51 (2026-05-28) ADR-0046 Phase 4 觀測閉環：寫推送歷史

    取代 Redis 25h 去重 key 過期就消失問題。failure-safe（寫失敗不擋主流程）。
    """
    try:
        # 找對應 tender_records.id（給 FK）
        tid_row = await db.execute(
            text(
                "SELECT id FROM tender_records "
                "WHERE unit_id = :uid AND COALESCE(job_number, '') = :jn LIMIT 1"
            ),
            {"uid": rec["unit_id"], "jn": rec.get("job_number") or ""},
        )
        tid = tid_row.scalar()

        await db.execute(
            text(
                "INSERT INTO tender_recommendation_history "
                "(tender_record_id, unit_id, job_number, title, unit_name, budget, "
                " agency_match_count, status, error_msg, channel) VALUES "
                "(:tid, :uid, :jn, :title, :uname, :budget, :amc, :status, :err, :ch)"
            ),
            {
                "tid": tid,
                "uid": rec["unit_id"],
                "jn": rec.get("job_number"),
                "title": rec["title"],
                "uname": rec.get("unit_name"),
                "budget": rec.get("budget"),
                "amc": rec.get("agency_match_count", 0),
                "status": status,
                "err": error_msg,
                "ch": channel,
            },
        )
        await db.commit()
    except Exception as e:
        # 寫歷史失敗不擋主流程（ADR-0028 silent failure 例外場景，已有上游 logger）
        logger.warning(f"recommend history write failed (non-fatal): {e}")
        try:
            await db.rollback()
        except Exception:
            pass


async def push_daily_recommendations(
    db: AsyncSession,
    days_back: int = DEFAULT_DAYS_BACK,
    budget_min: int = DEFAULT_BUDGET_MIN,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """每日業務推薦執行入口（給 scheduler 呼叫）。

    流程:
      1. find_business_recommendations
      2. 對每筆檢查 Redis 去重（短期快速）
      3. 透過 IntegrationFacade.push_admin_alert 推 LINE
      4. 記錄 Redis 避免明日重推
      5. 寫 tender_recommendation_history 表（L51 觀測閉環長期歷史）

    Returns:
        {found, pushed, skipped_duplicate, errors}
    """
    import time
    stats = {"found": 0, "pushed": 0, "skipped_duplicate": 0, "errors": 0}

    # L51: Prometheus metric
    try:
        from app.services.tender.metrics import get_tender_metrics
        metrics = get_tender_metrics()
    except Exception:
        metrics = None

    recommendations = await find_business_recommendations(
        db, days_back=days_back, budget_min=budget_min
    )
    stats["found"] = len(recommendations)

    if metrics:
        try:
            metrics.recommend_total.labels(result="found").inc(stats["found"])
            metrics.recommend_last_run.set(time.time())
        except Exception:
            pass

    if not recommendations:
        logger.info("Tender business recommend: 0 candidates today")
        return stats

    # 取 Redis client 做去重
    try:
        from app.core.redis_client import get_redis
        redis_client = await get_redis()
    except Exception:
        redis_client = None

    # 取 IntegrationFacade 推訊息
    try:
        from app.services.contracts.facades import IntegrationFacade
        facade = IntegrationFacade()
    except Exception as e:
        logger.error(f"IntegrationFacade import failed: {e}")
        return stats

    for rec in recommendations:
        if await _is_already_pushed(redis_client, rec["unit_id"], rec["job_number"]):
            stats["skipped_duplicate"] += 1
            if metrics:
                try:
                    metrics.recommend_total.labels(result="skipped_duplicate").inc()
                except Exception:
                    pass
            # L51: 仍寫歷史（觀測完整性，看哪些 dup 案件持續觸發）
            await _write_history(db, rec, status="skipped_duplicate")
            continue

        body = _format_recommendation_line(rec)

        if dry_run:
            logger.info(f"[DRY-RUN] would push: {body[:80]}...")
            stats["pushed"] += 1
            await _write_history(db, rec, status="pushed", channel="dry_run")
            continue

        try:
            ok = await facade.push_admin_alert(
                title="業務推薦標案",
                body=body,
                channel="line",  # 優先 LINE
            )
            if ok:
                stats["pushed"] += 1
                if metrics:
                    try:
                        metrics.recommend_total.labels(result="pushed").inc()
                    except Exception:
                        pass
                await _mark_pushed(redis_client, rec["unit_id"], rec["job_number"])
                await _write_history(db, rec, status="pushed")
            else:
                stats["errors"] += 1
                if metrics:
                    try:
                        metrics.recommend_total.labels(result="error").inc()
                    except Exception:
                        pass
                await _write_history(db, rec, status="error",
                                     error_msg="facade.push_admin_alert returned False")
        except Exception as e:
            logger.error(f"push recommendation failed for {rec['job_number']}: {e}")
            stats["errors"] += 1
            if metrics:
                try:
                    metrics.recommend_total.labels(result="error").inc()
                except Exception:
                    pass
            await _write_history(db, rec, status="error", error_msg=str(e)[:500])

    logger.info(
        f"Tender business recommend done: found={stats['found']} "
        f"pushed={stats['pushed']} dup={stats['skipped_duplicate']} err={stats['errors']}"
    )
    return stats

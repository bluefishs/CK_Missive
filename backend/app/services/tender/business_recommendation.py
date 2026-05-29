"""
Tender 業務推薦 LINE 通知 (ADR-0046 Phase 4)

對「近 N 日新增 + 預算大 + 機關曾合作」的標案自動 LINE 推送 admin。

═══════════════ 篩選原則 v2 (L51.4 業務整合版) ═══════════════

【基本面 3 條 AND】(無條件必須)
1. **時間窗口**: announce_date >= CURRENT_DATE - days_back（預設 1 日）
2. **資料來源**: source='pcc' OR pcc_match_unit_id IS NOT NULL
3. **預算門檻**: budget >= budget_min（預設 100 萬）

【業務相關性 3 重信號 OR】(至少 1 命中即列入)
A. **訂閱關鍵字** (主要 — 與 /tender/search 訂閱機制整合)
   - title 或 unit_name 命中任一 tender_subscriptions.keyword
   - 現行訂閱: 用地取得 / 圖解數化地籍 / 測量 / 樁 / 隧道 / UAV (6 個)
   - 命中即 matched_keywords[] 標註，訊息中顯示原因

B. **合作機關** (次要 — government_agencies 過去 documents 互動)
   - unit_name 在 government_agencies 表
   - agency_match_count = 過往 documents 數

C. **歷史承攬機關** (次要 — contract_projects 過去成功承接)
   - unit_name 在 contract_projects.client_agency
   - 現有 43 個歷史承攬機關

【排序】
- 主排序: 多信號命中數 DESC (3 重 → 2 重 → 1 重)
- 次排序: budget DESC, announce_date DESC
- LIMIT: MAX_RECOMMEND_PER_RUN=20

═══════════════ 重要設計選擇 ═══════════════
- **OR 邏輯而非 AND**：避免錯失（任一信號命中即列入）
- **訂閱關鍵字優先**：用戶在 /tender/search 設定的最直接表達業務興趣
- **訊息透明化**：顯示「為何推這筆」(matched_keywords / cooperated / contracted)
- **PCC budget 100% NULL 警示**：實際命中 394 HIGH-matched ezbid（持 budget）
  見 docs/architecture/TENDER_PCC_COVERAGE_AUDIT_20260529.md

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
    # L51.4 (2026-05-29) Owner 反饋：5 條 AND 與訂閱/業務關聯性極低
    # 重寫整合版 — 加 3 重業務相關性信號（任一命中即列入）：
    #   信號 A: title/unit_name 命中訂閱關鍵字 (tender_subscriptions 6 筆)
    #   信號 B: unit_name 為合作機關 (government_agencies — 過去 documents 互動)
    #   信號 C: unit_name 為歷史承攬機關 (contract_projects 43 個過去承接機關)
    # 任一信號 OR 邏輯，避免錯失。多信號命中者排序優先。
    sql = text("""
        WITH
        sub_keywords AS (
            -- 訂閱關鍵字（用戶在 /tender/search 設定的關注詞彙）
            SELECT keyword FROM tender_subscriptions WHERE is_active = true
        ),
        cooperated_agencies AS (
            -- 合作機關（過去 documents 互動）
            SELECT DISTINCT agency_name FROM government_agencies
            WHERE agency_name IS NOT NULL
        ),
        contracted_agencies AS (
            -- 歷史承攬機關（過去成功承接過案件）
            SELECT DISTINCT client_agency AS agency_name
            FROM contract_projects
            WHERE client_agency IS NOT NULL
        ),
        recent_tenders AS (
            SELECT
                -- L51.3 對 ezbid HIGH-matched 用 PCC 對應碼（COALESCE）
                COALESCE(tr.pcc_match_unit_id, tr.unit_id) AS unit_id,
                COALESCE(tr.pcc_match_job_number, tr.job_number) AS job_number,
                tr.id AS tender_record_id, tr.title, tr.unit_name,
                tr.budget, tr.announce_date, tr.source
            FROM tender_records tr
            WHERE
                -- 條件 1: 近期新增
                tr.announce_date >= (CURRENT_DATE - :days_back * INTERVAL '1 day')::date
                -- 條件 2: 預算門檻
                AND tr.budget IS NOT NULL
                AND tr.budget >= :budget_min
                -- 條件 3: PCC 或 HIGH-matched ezbid 走 PCC 對應
                AND (tr.source = 'pcc' OR tr.pcc_match_unit_id IS NOT NULL)
        )
        SELECT
            rt.unit_id, rt.job_number, rt.title, rt.unit_name,
            rt.budget, rt.announce_date, rt.source,
            -- L51.4 業務相關性三重信號
            (
                SELECT array_agg(sk.keyword)
                FROM sub_keywords sk
                WHERE rt.title ILIKE '%' || sk.keyword || '%'
                   OR rt.unit_name ILIKE '%' || sk.keyword || '%'
            ) AS matched_keywords,
            (rt.unit_name IN (SELECT agency_name FROM cooperated_agencies)) AS is_cooperated,
            (rt.unit_name IN (SELECT agency_name FROM contracted_agencies)) AS is_contracted,
            -- 合作次數
            (
                SELECT COUNT(*) FROM government_agencies ga
                WHERE ga.agency_name = rt.unit_name
            ) AS agency_match_count
        FROM recent_tenders rt
        WHERE
            -- L51.4 業務相關性過濾：訂閱關鍵字 OR 合作機關 OR 歷史承攬機關
            EXISTS (
                SELECT 1 FROM sub_keywords sk
                WHERE rt.title ILIKE '%' || sk.keyword || '%'
                   OR rt.unit_name ILIKE '%' || sk.keyword || '%'
            )
            OR rt.unit_name IN (SELECT agency_name FROM cooperated_agencies)
            OR rt.unit_name IN (SELECT agency_name FROM contracted_agencies)
        ORDER BY
            -- L51.4 加權排序：訂閱關鍵字 = 3 (用戶主動表達興趣，最強信號)
            --                  歷史承攬 = 2 (過去成功承接，業務適配)
            --                  合作機關 = 1 (互動過，次強)
            (
                (CASE WHEN EXISTS (
                    SELECT 1 FROM sub_keywords sk
                    WHERE rt.title ILIKE '%' || sk.keyword || '%'
                       OR rt.unit_name ILIKE '%' || sk.keyword || '%'
                ) THEN 3 ELSE 0 END) +
                (CASE WHEN rt.unit_name IN (SELECT agency_name FROM contracted_agencies) THEN 2 ELSE 0 END) +
                (CASE WHEN rt.unit_name IN (SELECT agency_name FROM cooperated_agencies) THEN 1 ELSE 0 END)
            ) DESC,
            rt.budget DESC, rt.announce_date DESC
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
            # L51.4 業務相關性三重信號
            "matched_keywords": list(r.matched_keywords) if r.matched_keywords else [],
            "is_cooperated": bool(r.is_cooperated),
            "is_contracted": bool(r.is_contracted),
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

    L51.3 (2026-05-29) 雙連結設計：missive 詳情 + PCC 採購網
    L51.4 (2026-05-29) Owner 反饋業務關聯性低：顯示匹配信號（關鍵字 + 合作/承攬）
    """
    from urllib.parse import quote

    budget_str = f"${rec['budget']:,}" if rec["budget"] else "（預算未公開）"
    agency_cnt = rec.get("agency_match_count", 0)
    coop_str = f"（合作 {agency_cnt} 次）" if agency_cnt > 1 else "（合作機關）"

    unit_id_url = quote(str(rec["unit_id"]), safe='')
    job_url = quote(str(rec["job_number"]), safe='')

    # L51.4 業務匹配信號（透明化推薦原因）
    signals = []
    matched_kw = rec.get("matched_keywords") or []
    if matched_kw:
        signals.append(f"🔍 訂閱命中: {', '.join(matched_kw)}")
    if rec.get("is_contracted"):
        signals.append("📜 歷史承攬過此機關")
    if rec.get("is_cooperated"):
        signals.append(f"🤝 documents 互動 {agency_cnt} 次")
    signal_block = "\n".join(signals) if signals else "（無業務匹配信號 — 預算/時間 fallback）"

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
        f"\n"
        f"{signal_block}\n"
        f"\n"
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

"""
Tender 業務推薦 LINE 通知 (ADR-0046 Phase 4)

對「近 N 日新增 + 預算大 + 機關曾合作」的標案自動 LINE 推送 admin。

═══════════════ 篩選原則 v3 (L75 Option B「關鍵字優先＋機關窄通道」) ═══════════════

【基本面 3 條 AND】(無條件必須)
1. **時間窗口**: announce_date >= CURRENT_DATE - days_back（預設 1 日）
2. **資料來源**: source='pcc' OR pcc_match_unit_id IS NOT NULL
3. **預算門檻**: budget >= budget_min（預設 100 萬）

【業務相關性（關鍵字優先；機關為窄通道，非粗放入選）】
A. **訂閱關鍵字＝工項**（主要入選路徑，權重 10 — 公司實做工項）
   - title 或 unit_name 命中任一 tender_subscriptions.keyword → 一律入選（任何 category）
   - 現行訂閱: UAV / 圖根點 / 圖解數化地籍 / 測量 / 用地取得 / 都市計畫樁 / 隧道 (7 個)

B/C. **精準機關窄通道**（次要加權，權重 承攬2 / 合作1）
   - L75: 機關比對改「精準局/所級」— 排除裸府級（`桃園市政府工務局` ≠ `桃園市政府`），
     並正規化 unicode 髒資料（部首字「⼯」U+2F37 → 「工」）
   - 機關「獨立入選」額外要求 **工程類**（category NOT IN 財物/勞務）—
     測量/技術服務（PCC 常歸勞務）改靠關鍵字路徑接，杜絕「學生保險(財物)/地磅(勞務)」噪音

【排序】
- 主排序: 加權分 DESC（關鍵字 10 → 恆排最前；承攬 2；合作 1）
- 次排序: budget DESC, announce_date DESC
- LIMIT: MAX_RECOMMEND_PER_RUN=20

═══════════════ 重要設計選擇 ═══════════════
- **關鍵字＝工項為主、機關為輔**：機關（即使精準到局）會發包大量公司不做的工項，
  唯一可靠相關性訊號是工項（L75；取代 v2「機關可粗放獨立入選」造成的噪音）
- **訊息透明化**：顯示「為何推這筆」(matched_keywords / cooperated / contracted)
- **PCC budget 100% NULL 警示**：實際命中 394 HIGH-matched ezbid（持 budget）
  見 docs/architecture/TENDER_PCC_COVERAGE_AUDIT_20260529.md
- **殘留限制**: 機關窄通道仍可能放行「精準局/所級的工程新案（非關鍵字）」少量；
  若仍嫌寬可升 Option A（關鍵字為硬門檻），見 TENDER_RECOMMENDATION_FLOW.md

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

Version: 2.0.0
Created: 2026-05-28 (ADR-0046 Phase 4)
Updated: 2026-05-29 L51.3 — 加 PCC 官方連結 + 完整篩選原則註解
Updated: 2026-06-16 L75 v2.0.0 — Option B 關鍵字優先＋機關窄通道（關鍵字權重 10、機關精準局/所級
         排除裸府級 + unicode 正規化、機關獨立入選限工程類）；解 owner「推 10 案皆無涉略」
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# 業務門檻
DEFAULT_BUDGET_MIN = 1_000_000  # 100 萬
DEFAULT_DAYS_BACK = 1  # 過去 N 日新增
MAX_RECOMMEND_PER_RUN = 20  # 每次跑最多推 N 個（避刷屏）

# 同義詞 SSOT（synonyms.yaml）— 與既有同義詞字典同檔，避免另建競品 store
_SYNONYMS_PATH = Path(__file__).resolve().parent.parent / "ai" / "synonyms.yaml"


@lru_cache(maxsize=1)
def _load_tender_synonym_groups() -> tuple:
    """讀 synonyms.yaml 的 tender_keyword_synonyms 群組（程序內快取；改 yaml 後需重啟）。"""
    try:
        with open(_SYNONYMS_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        groups = data.get("tender_keyword_synonyms", []) or []
        return tuple(tuple(str(m).strip() for m in g if str(m).strip())
                     for g in groups if isinstance(g, list) and g)
    except Exception as e:  # 載入失敗不擋主流程（退化為「無同義詞展開」）
        logger.warning(f"load tender synonyms failed (non-fatal): {e}")
        return tuple()


def _expand_keyword_terms(keywords: List[str]) -> List[str]:
    """訂閱關鍵字 → 含同義詞的搜尋詞列表（去重、保留原詞、大小寫不敏感比對）。

    L75/2026-06-16：訂閱清單維持精簡（只放主詞，如 UAV），比對時自動展開整組同義詞
    （UAV → 無人機/空拍機/drone…），避免增列過多訂閱關鍵字。同義詞群組維護於 synonyms.yaml。
    """
    groups = _load_tender_synonym_groups()
    terms: List[str] = []
    seen = set()

    def _add(t: str) -> None:
        t = (t or "").strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            terms.append(t)

    for kw in keywords:
        _add(kw)
        kwl = (kw or "").strip().lower()
        for g in groups:
            if any(m.lower() == kwl for m in g):
                for m in g:
                    _add(m)
    return terms


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
    # L75 (2026-06-16) Owner 反饋「推 10 案公司皆無涉略」→ 改 Option B「關鍵字優先＋機關窄通道」：
    #   問題根因＝機關信號可「獨立入選」，而機關（即使精準到局）會發包大量公司不做的工項；
    #   唯一可靠的相關性訊號＝工項＝關鍵字，機關只能加權/窄通道，不能粗放當入選門檻。
    # 三項調整：
    #   (1) 關鍵字命中→一律入選且權重 10（遠高於機關 2/1，確保關鍵字案恆排在最前）。
    #   (2) 機關信號改「精準局/所級」：排除裸府級（agency NOT LIKE '%政府'，如「桃園市政府工務局」
    #       ≠「桃園市政府」），並正規化 unicode 髒資料（部首字 U+2F37「⼯」→「工」，contract_projects 實有）。
    #   (3) 機關獨立入選額外要求「工程類」(NOT IN 財物/勞務)；測量/技服(常歸勞務)靠關鍵字路徑接，
    #       避免「學生保險(財物)/地磅勞務」這類機關噪音。
    sql = text("""
        WITH
        sub_keywords AS (
            -- 訂閱關鍵字（含同義詞展開；主詞 + synonyms.yaml tender_keyword_synonyms，見 _expand_keyword_terms）
            SELECT unnest(CAST(:terms AS text[])) AS keyword
        ),
        cooperated_agencies AS (
            -- 精準合作機關（局/所/處/段級；排除裸府級；正規化 ⼯→工）
            SELECT DISTINCT replace(agency_name, '⼯', '工') AS agency_name
            FROM government_agencies
            WHERE agency_name IS NOT NULL
              AND agency_name NOT LIKE '%政府'   -- L75: 排除裸府級（工務局 ≠ 政府）
        ),
        contracted_agencies AS (
            -- 精準歷史承攬機關（同上規則）
            SELECT DISTINCT replace(client_agency, '⼯', '工') AS agency_name
            FROM contract_projects
            WHERE client_agency IS NOT NULL
              AND client_agency NOT LIKE '%政府'
        ),
        recent_tenders AS (
            SELECT
                -- L51.3 對 ezbid HIGH-matched 用 PCC 對應碼（COALESCE）
                COALESCE(tr.pcc_match_unit_id, tr.unit_id) AS unit_id,
                COALESCE(tr.pcc_match_job_number, tr.job_number) AS job_number,
                tr.id AS tender_record_id, tr.title, tr.unit_name,
                -- L75: 正規化招標機關 unicode 髒資料，供精準比對
                replace(tr.unit_name, '⼯', '工') AS unit_name_norm,
                tr.budget, tr.announce_date, tr.source,
                tr.category, tr.tender_type
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
            -- 業務相關性信號（關鍵字＝工項；機關＝精準局/所級）
            (
                SELECT array_agg(sk.keyword)
                FROM sub_keywords sk
                WHERE rt.title ILIKE '%' || sk.keyword || '%'
                   OR rt.unit_name ILIKE '%' || sk.keyword || '%'
            ) AS matched_keywords,
            (rt.unit_name_norm IN (SELECT agency_name FROM cooperated_agencies)) AS is_cooperated,
            (rt.unit_name_norm IN (SELECT agency_name FROM contracted_agencies)) AS is_contracted,
            -- 合作次數（以精準正規化名稱計）
            (
                SELECT COUNT(*) FROM government_agencies ga
                WHERE replace(ga.agency_name, '⼯', '工') = rt.unit_name_norm
            ) AS agency_match_count
        FROM recent_tenders rt
        WHERE
            -- L75 Option B「關鍵字優先＋機關窄通道」：
            --   關鍵字命中（工項）→ 一律入選（強信號，任何 category）
            --   機關（精準局/所級）→ 僅「工程類」窄通道（NOT IN 財物/勞務；NULL 視為工程）
            EXISTS (
                SELECT 1 FROM sub_keywords sk
                WHERE rt.title ILIKE '%' || sk.keyword || '%'
                   OR rt.unit_name ILIKE '%' || sk.keyword || '%'
            )
            OR (
                (rt.unit_name_norm IN (SELECT agency_name FROM cooperated_agencies)
                 OR rt.unit_name_norm IN (SELECT agency_name FROM contracted_agencies))
                -- L75: 機關窄通道僅放工程類（測量/技服歸勞務者靠關鍵字路徑接，杜絕保險/地磅噪音）
                AND COALESCE(NULLIF(TRIM(rt.category), ''), '工程') NOT IN ('財物', '財物類', '勞務', '勞務類')
            )
        ORDER BY
            -- L75 加權排序：訂閱關鍵字 = 10（工項，遠高於機關 → 關鍵字案恆排最前）
            --              歷史承攬 = 2 / 合作機關 = 1（精準局/所級，僅次要加權）
            (
                (CASE WHEN EXISTS (
                    SELECT 1 FROM sub_keywords sk
                    WHERE rt.title ILIKE '%' || sk.keyword || '%'
                       OR rt.unit_name ILIKE '%' || sk.keyword || '%'
                ) THEN 10 ELSE 0 END) +
                (CASE WHEN rt.unit_name_norm IN (SELECT agency_name FROM contracted_agencies) THEN 2 ELSE 0 END) +
                (CASE WHEN rt.unit_name_norm IN (SELECT agency_name FROM cooperated_agencies) THEN 1 ELSE 0 END)
            ) DESC,
            rt.budget DESC, rt.announce_date DESC
        LIMIT :limit
    """)

    # 取 active 訂閱關鍵字並展開同義詞（失敗則退化為無展開，不擋主流程）
    try:
        kw_rows = await db.execute(
            text("SELECT keyword FROM tender_subscriptions WHERE is_active = true")
        )
        active_keywords = [r.keyword for r in kw_rows if r.keyword]
    except Exception as e:
        logger.warning(f"load active subscription keywords failed (non-fatal): {e}")
        active_keywords = []
    search_terms = _expand_keyword_terms(active_keywords)

    try:
        result = await db.execute(sql, {
            "terms": search_terms,
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

"""標案詳情 Enrichment（P2）— 2-hop: PCC searchTenderDetail 取點分 orgId → openfun API 取乾淨詳情。

⚠️⚠️ 2026-08-26 更正：**這支程式從建立起就沒有任何人呼叫它**（全 repo 零 import）。
scheduler 的 `tender_pcc_enrichment_job` 跑的是名字很像的另一支（`enrichment.py`，
做 ezbid↔PCC 配對）。所以下面那條「不掛 cron」的決定實際上等於「它從未執行過」——
而它一跑就暴露四個 bug（見各處註解）：unit_id 兩來源語意不同、`_pick` 無優先序
且會命中「是否…」欄位、`bidders` 收到廠商代碼與地址、SQL 參數型別未 CAST
導致整筆 UPDATE 失敗且**一筆壞掉後剩下全部陪葬**。

⚠️ 2026-06-17 實測結論：**PCC 詳情頁有反爬限流**——少量請求後即回精簡 stub 頁
（43-49KB、無 orgId），無論 curl/httpx/補 headers/換 UA。故 2-hop 取 orgId **無法可靠規模化**。
   **2026-08-26 實測補充**：這條對 `source='pcc'` 仍成立（要 2-hop），
   但對 **`source='ezbid'` 完全不適用** —— ezbid 的 `unit_id` 本身就是點分 org_id，
   **根本不需要打 PCC 詳情頁**，直接查 openfun 即可（實測 org_ok 5/5、errors 0）。
   近 7 天待補 7,703 筆裡 ezbid 佔 2,472 筆，那一段是零反爬風險的。
   另：今日對 PCC 詳情頁實測 3 筆亦全部 HTTP 200（130KB、orgId 可取），
   與 06-17 的觀察不一致 —— 可能是限流有時間窗，**不據此放寬 pcc 那一段**。

可靠的職能篩選請用確定性自維機制（關鍵字 + 排除 + 承攬史建議，已上線 UI）。
詳見 TENDER_RECOMMENDATION_FLOW。
另：使用者瀏覽器點官方直連（searchTenderDetail?pkPmsMain=，原始 '='）不受此限（非我方伺服 IP）。


補齊 tender_records：標的分類(category)、財物採購性質(procurement_nature)、預算(budget NULL 時)、
底價(base_price)、決標(award_result)、廠商(bidders)、org_id。供：
  - 智能職能篩選（採購性質=財物 → 排除儀器/醫療採購；不再靠無窮負面關鍵字）
  - 詳情頁 5 tab 補料 + 官方直連。

設計：
  - 我方 unit_id = PCC pkPmsMain（官方直連已用）。
  - openfun 需點分 orgId（如 A.13.6.20）→ 從 PCC 詳情頁 HTML regex 取得，cache 進 org_id 欄避免重抓。
  - 節流（每案延遲 + 低併發）避免封 IP；只 enrich 推薦/近期標的（非全量）。
  - 任何步驟失敗不擋主流程（保留既有基本欄，記 logger）。
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

PCC_DETAIL_URL = "https://web.pcc.gov.tw/tps/QueryTender/query/searchTenderDetail?pkPmsMain="
OPENFUN_TENDER = "https://pcc-api.openfun.app/api/tender"
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
_ORG_ID_RE = re.compile(r"orgId=([0-9A-Za-z][0-9A-Za-z.]*\.[0-9.]+)")  # 收 A.13.6.20 與 3.5.48 兩式

#: `unit_id` 這個欄位對兩個來源是**兩種不同的東西**：
#:   * `source='pcc'`   → PCC 的 `pkPmsMain`，base64（`NzEzMTA4MzY=`）
#:   * `source='ezbid'` → **點分機關代碼**（`3.5.10.100`）＝ openfun 要的 org_id 本身
#:
#: 2026-08-26 實測：`enrich_recent` 對近 7 天的資料 `org_ok=0 errors=2`，
#: 而同一支 `_fetch_org_id` 手動餵 base64 unit_id **成功**（HTTP 200、
#: orgId=3.79.14.14）。差別就是撈到的都是 ezbid ——
#: 把 `3.5.10.100` 當成 pkPmsMain 塞進 PCC 詳情頁網址，當然查不到。
#:
#: ⇒ 已是點分格式就直接用，不必再去抓一次 PCC 詳情頁。
#: 這同時省掉 ezbid 那 2,472 筆的外部請求（近 7 天待補的三分之一）。
_DOTTED_ORG_RE = re.compile(r"^[0-9A-Za-z]+(\.[0-9]+)+$")
_THROTTLE_SEC = 0.8  # 每案延遲（禮貌性，避免封 IP）


def _pick(detail: Dict[str, Any], *substrs: str, exclude: tuple = ()) -> Optional[str]:
    """從 openfun detail dict 取值 —— **依 substrs 的順序當優先序**。

    ⚠️ 2026-08-26 修兩個 bug，兩個都會給出「看起來像數字所以像是對的」的錯值：

    ① **原本沒有優先序**：舊版遍歷 `detail` 的 key，第一個命中**任一** substr
       就回 —— 所以 `_pick(det, "總決標金額", "決標金額")` 實際拿到哪一個
       取決於 dict 的順序，很可能是 `決標品項:第1品項:決標金額`（**單一品項**
       的金額）而不是總額。兩者都是合理的數字，看不出錯。

    ② **子字串會命中「是非題」的欄位**：`_pick(det, "底價")` 命中
       `招標資料:是否訂有底價` ⇒ `base_price` 被寫成 **'否'**。
       實測就是這樣：`{'base_price': '否'}`。
       ⇒ 預設排除 key 含「是否」的欄位。
    """
    ex = tuple(exclude) + ("是否",)
    for s in substrs:                       # 外層跑 substrs ＝ 真的有優先序
        for k, v in detail.items():
            if s in k and not any(e in k for e in ex) and v not in (None, "", []):
                return str(v).strip()
    return None


def _parse_budget(s: Optional[str]) -> Optional[int]:
    """'1,310,000元' → 1310000。"""
    if not s:
        return None
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None


def _category_from_class(class_str: Optional[str]) -> Optional[str]:
    """標的分類 '勞務類8675-…' → '勞務'；工程類→工程；財物類→財物。"""
    if not class_str:
        return None
    for c in ("工程", "財物", "勞務"):
        if class_str.startswith(c) or f"{c}類" in class_str[:6]:
            return c
    return None


async def _fetch_org_id(client: httpx.AsyncClient, unit_id: str) -> Optional[str]:
    """抓 PCC 詳情頁，regex 取點分 orgId（openfun 查詢用）。"""
    try:
        from urllib.parse import quote
        r = await client.get(PCC_DETAIL_URL + quote(str(unit_id), safe=""), headers=_UA)
        if r.status_code == 200:
            m = _ORG_ID_RE.search(r.text)
            return m.group(1) if m else None
    except Exception as e:
        logger.warning(f"fetch org_id failed unit_id={unit_id}: {e}")
    return None


async def _fetch_openfun_detail(client: httpx.AsyncClient, org_id: str, job_number: str) -> Dict[str, Any]:
    """openfun API → 解析 標的分類/採購性質/預算/底價/決標/廠商。"""
    out: Dict[str, Any] = {}
    try:
        r = await client.get(OPENFUN_TENDER, params={"unit_id": org_id, "job_number": job_number}, headers=_UA)
        if r.status_code != 200:
            return out
        data = r.json()
        bidders: List[str] = []
        for rec in data.get("records", []):
            det = rec.get("detail", {}) or {}
            cls = _pick(det, "標的分類")
            if cls and not out.get("procurement_class"):
                out["procurement_class"] = cls
                out["category"] = _category_from_class(cls)
            nature = _pick(det, "採購性質")
            if nature and not out.get("procurement_nature"):
                out["procurement_nature"] = nature
            bud = _parse_budget(_pick(det, "預算金額"))
            if bud and not out.get("budget"):
                out["budget"] = bud
            bp = _pick(det, "底價金額", "底價")
            if bp and not out.get("base_price"):
                out["base_price"] = bp
            award = _pick(det, "總決標金額", "決標金額")
            if award and not out.get("award_result"):
                out["award_result"] = award
            # ⚠️ 2026-08-26：原本收所有 key 含「得標廠商／投標廠商」的值 ——
            # 而 openfun 的結構是 `投標廠商:投標廠商N:<欄位>`，**每一個欄位都以
            # 「投標廠商」開頭** ⇒ 廠商代碼、組織型態、地址、電話、是否得標
            # 全被當成廠商名稱收進去。實測結果：
            #   ['3', '22008619', '合記書局有限公司', '是', '公司登記', '其他', '臺北市信義區…']
            # 只有第 3 個是廠商名。**存進 jsonb 之後看起來像資料，其實是垃圾。**
            for k, v in det.items():
                if not v:
                    continue
                # 只收真正的名稱欄（`…:廠商名稱`／`…:得標廠商`），不收其屬性
                if k.endswith(":廠商名稱") or k.endswith(":得標廠商"):
                    name = str(v).strip()
                    if name and name not in bidders:
                        bidders.append(name)
        if bidders:
            out["bidders"] = bidders[:20]
    except Exception as e:
        logger.warning(f"fetch openfun detail failed org_id={org_id} job={job_number}: {e}")
    return out


async def enrich_recent(
    db: AsyncSession, days_back: int = 7, limit: int = 60, only_unenriched: bool = True,
    only_dotted_org: bool = False,
) -> Dict[str, int]:
    """批次 enrich 近 N 日標案（節流）。回 {scanned, org_ok, enriched, updated_budget, errors}。

    `only_dotted_org=True` 只處理 `unit_id` 已是點分 org_id 的記錄（＝ezbid 來源）——
    那一段**完全不需要打 PCC 詳情頁**，所以不受 06-17 記的反爬限流影響，
    可以安全地掛自動排程。pcc 來源仍需 2-hop，維持手動/低量。
    """
    stats = {"scanned": 0, "org_ok": 0, "enriched": 0, "updated_budget": 0, "errors": 0}
    where_unenriched = "AND detail_enriched_at IS NULL" if only_unenriched else ""
    where_dotted = r"AND unit_id ~ '^[0-9A-Za-z]+(\.[0-9]+)+$'" if only_dotted_org else ""
    rows = (await db.execute(text(f"""
        SELECT id, unit_id, job_number, org_id, budget
        FROM tender_records
        WHERE announce_date >= (CURRENT_DATE - :db_days * INTERVAL '1 day')::date
          AND COALESCE(tender_type, '') NOT LIKE '%決標%'
          AND unit_id IS NOT NULL AND job_number IS NOT NULL AND job_number <> ''
          {where_unenriched}
          {where_dotted}
        ORDER BY announce_date DESC
        LIMIT :lim
    """), {"db_days": days_back, "lim": limit})).fetchall()
    stats["scanned"] = len(rows)
    if not rows:
        return stats

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        for r in rows:
            try:
                # ezbid 的 unit_id 本身就是 org_id（見 _DOTTED_ORG_RE 的說明）
                org_id = r.org_id
                if not org_id and r.unit_id and _DOTTED_ORG_RE.match(str(r.unit_id)):
                    org_id = str(r.unit_id)
                if not org_id:
                    org_id = await _fetch_org_id(client, r.unit_id)
                if not org_id:
                    stats["errors"] += 1
                    # 仍標記嘗試過（避免每日重撞），但不寫 enriched 欄
                    await db.execute(text("UPDATE tender_records SET detail_enriched_at=:now WHERE id=:id"),
                                     {"now": datetime.now(), "id": r.id})
                    await asyncio.sleep(_THROTTLE_SEC)
                    continue
                stats["org_ok"] += 1
                det = await _fetch_openfun_detail(client, org_id, r.job_number)
                # UPDATE（budget 僅在原為 NULL 時補；category/性質/底價/決標/廠商補值）
                await db.execute(text("""
                    UPDATE tender_records SET
                        org_id = :org_id,
                        category = COALESCE(NULLIF(:category,''), category),
                        procurement_nature = COALESCE(NULLIF(:nature,''), procurement_nature),
                        -- 同樣要 CAST：`:budget` 在同一句出現兩次且可能為 NULL，
                        -- asyncpg 回 `could not determine data type of parameter $4`
                        budget = CASE WHEN budget IS NULL AND CAST(:budget AS bigint) IS NOT NULL
                                      THEN CAST(:budget AS bigint) ELSE budget END,
                        base_price = COALESCE(NULLIF(:base_price,''), base_price),
                        award_result = COALESCE(NULLIF(:award,''), award_result),
                        -- ⚠️ 必須 CAST：`bidders` 是 jsonb，而參數為 NULL 時
                        -- asyncpg 推不出型別，整筆 UPDATE 會失敗（errors+1）——
                        -- 而失敗只寫在 logger.warning 裡，統計上長得像「這筆沒資料」。
                        bidders = COALESCE(CAST(:bidders AS jsonb), bidders),
                        detail_enriched_at = :now
                    WHERE id = :id
                """), {
                    "org_id": org_id,
                    "category": det.get("category") or "",
                    "nature": det.get("procurement_nature") or "",
                    "budget": det.get("budget"),
                    "base_price": det.get("base_price") or "",
                    "award": det.get("award_result") or "",
                    "bidders": json.dumps(det.get("bidders"), ensure_ascii=False) if det.get("bidders") else None,
                    "now": datetime.now(),
                    "id": r.id,
                })
                stats["enriched"] += 1
                if r.budget is None and det.get("budget"):
                    stats["updated_budget"] += 1
            except Exception as e:
                logger.warning(f"enrich tender id={r.id} failed: {e}")
                stats["errors"] += 1
                # ⚠️ 2026-08-26：沒有這一行的話**一筆壞掉、剩下全部陪葬** ——
                # PostgreSQL 的交易一旦中止，後續每一句都回
                # `current transaction is aborted`，而這裡 except 只是累加
                # errors 繼續跑迴圈。實測 5 筆裡第 1 筆型別錯，後 4 筆全被判 error，
                # **統計上長得像「這些案子都沒有資料」**，而它們根本沒被試過。
                try:
                    await db.rollback()
                except Exception:
                    pass
            await asyncio.sleep(_THROTTLE_SEC)
        await db.commit()
    logger.info(f"tender enrich_recent done: {stats}")
    return stats

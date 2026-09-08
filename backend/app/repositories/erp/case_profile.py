# -*- coding: utf-8 -*-
"""帳款列表的「計畫類別／案件狀態」聚合（owner 2026-09-07：兩頁在統一編號後加這兩欄）。

## 為什麼另開一支而不寫進兩個 repository

委託單位帳款與協力廠商帳款是**兩條不同的路**走到同一個問題：

| | 案件從哪裡來 | 年度口徑 |
|---|---|---|
| 委託單位帳款 | PM 案件（有主檔鍵者）＋ 承攬案（PM 沒涵蓋的） | `PMCase.year`／`ContractProject.year`（案號年） |
| 協力廠商帳款 | 應付 → 報價單 → 案號 | `quotation_case_year_condition`（year 欄優先，09-08 改） |

兩邊要顯示的是同一件事（這家往來對象名下的案是什麼類別、現在什麼狀態），
所以**標籤映射與狀態優先序只能有一份** —— 分開寫就是下一個「同一個 2026 三頁三種答案」。

## 兩個判準上的決定

1. **狀態以承攬案為準**：一個 PM 案成案後同時存在於 `pm_cases`（`status=contracted`）
   與 `contract_projects`（`status=執行中／已結案`）。兩者不是矛盾，是**兩個階段的欄位**；
   執行狀態的權威在承攬案，所以 `COALESCE(承攬案狀態, PM 狀態標籤)`。
   直接把兩邊的值並列會讓同一個案顯示「已承攬」又「執行中」，看起來像資料不一致。

2. **與「合作案件數」同一組案**：腿 1 只收「已承攬或已有成案報價單」、
   **且委託單位主檔類型是 `client`** 的 PM 案 —— 少了後面那個條件，
   主檔登記為協力廠商卻出現在承攬案委託單位欄的那幾家（雙主檔家族 A105），
   狀態欄會多算一案（實測：大有國際 案件數 1、狀態合計 2）。判準與
   與 `client_receivable_repository` 的 `case_count` 判準相同。評估中的案不是合作案件，
   放進狀態欄會讓同一列的兩個數字互相矛盾。

3. **不重複計數**：承攬案那條腿只收「PM 沒有涵蓋到的案號」，與
   `client_receivable_repository` 的腿 2 用同一條排除規則。兩邊各自寫一份排除規則，
   就會出現「列表說 6 案、類別欄的狀態加起來 9 案」。
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

#: `pm_cases.category`／`contract_projects.category` 存的是代碼（01／02／03），
#: 顯示要中文。03～07／99 在 PM 匯入時已歸併為 02，這裡只是把殘留的代碼也譯得出來。
CATEGORY_LABELS: dict[str, str] = {
    "01": "委辦招標",
    "02": "承攬報價",
    "03": "承攬報價",
}

#: PM 階段的狀態碼 → 中文。承攬案的狀態本來就是中文，不需要映射。
PM_STATUS_LABELS: dict[str, str] = {
    "planning": "評估中",
    "evaluating": "評估中",
    "contracted": "已承攬",
    "closed": "已結案",
    "cancelled": "已取消",
    "lost": "未得標",
}

_PM_STATUS_CASE = "CASE p.status " + " ".join(
    f"WHEN '{k}' THEN '{v}'" for k, v in PM_STATUS_LABELS.items()
) + " ELSE COALESCE(p.status, '') END"


def _blank() -> dict[str, Any]:
    return {"categories": [], "statuses": [], "staff": []}


def _merge(profile: dict[str, Any], category: Optional[str], status: Optional[str], count: int) -> None:
    label = CATEGORY_LABELS.get((category or "").strip(), (category or "").strip())
    if label and label not in profile["categories"]:
        profile["categories"].append(label)
    st = (status or "").strip()
    if st:
        for row in profile["statuses"]:
            if row["label"] == st:
                row["count"] += count
                return
        profile["statuses"].append({"label": st, "count": count})


def _finalize(profiles: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    for p in profiles.values():
        p["categories"].sort()
        p["statuses"].sort(key=lambda r: (-r["count"], r["label"]))
    return profiles


async def client_case_codes(db: AsyncSession, year: Optional[int]) -> dict[str, set[str]]:
    """委託單位 → 它名下的 case_code 集合（與 `client_case_profiles` 同一組案）。

    給兩件事用：①承辦同仁欄的聚合 ②依承辦篩選列表。
    **兩者共用同一個來源**，否則會出現「篩了某人卻看到別人的承辦」這種對不起來的組合。
    """
    yr = int(year) if year else None
    out: dict[str, set[str]] = {}
    for r in (await db.execute(text(f"""
        SELECT p.client_vendor_id AS vid, p.case_code AS code
          FROM pm_cases p
          JOIN partner_vendors v ON v.id = p.client_vendor_id AND v.vendor_type = 'client'
         WHERE p.client_vendor_id IS NOT NULL AND p.case_code IS NOT NULL
           AND (CAST(:yr AS INTEGER) IS NULL OR p.year = CAST(:yr AS INTEGER))
           AND (p.status = 'contracted' OR EXISTS (
                   SELECT 1 FROM erp_quotations q
                    WHERE q.case_code = p.case_code
                      AND q.project_code IS NOT NULL AND q.deleted_at IS NULL))
    """), {"yr": yr})).all():
        out.setdefault(f"id:{r.vid}", set()).add(r.code)
    for r in (await db.execute(text("""
        SELECT cp.client_vendor_id AS vid, btrim(cp.client_agency) AS vname, cp.case_code AS code
          FROM contract_projects cp
         WHERE COALESCE(btrim(cp.client_agency), '') <> '' AND cp.case_code IS NOT NULL
           -- 2026-09-08：兩條連法都要認（case_code 相同、或共用 project_code）。
           -- 與 `pm_coverage.contract_covered_by_pm()` 是同一條規則，
           -- 手寫 SQL 無法 import ⇒ 改那邊時這裡要一起改。
           AND NOT (
                cp.case_code IN (SELECT case_code FROM pm_cases
                                  WHERE client_vendor_id IS NOT NULL AND case_code IS NOT NULL)
             OR (cp.project_code IS NOT NULL
                 AND cp.project_code IN (SELECT project_code FROM pm_cases
                                          WHERE client_vendor_id IS NOT NULL AND project_code IS NOT NULL))
           )
           AND (CAST(:yr AS INTEGER) IS NULL OR cp.year = CAST(:yr AS INTEGER))
    """), {"yr": yr})).all():
        key = f"id:{r.vid}" if r.vid is not None else f"name:{r.vname}"
        out.setdefault(key, set()).add(r.code)
    return out


async def vendor_case_codes(db: AsyncSession, year: Optional[int]) -> dict[str, set[str]]:
    """協力廠商 → 它名下的 case_code 集合（與 `vendor_case_profiles` 同一組案）。"""
    yr = int(year) if year else None
    out: dict[str, set[str]] = {}
    for r in (await db.execute(text("""
        SELECT COALESCE('id:' || vp.vendor_id::text, 'name:' || vp.vendor_name) AS vkey,
               q.case_code AS code
          FROM erp_vendor_payables vp
          JOIN erp_quotations q ON q.id = vp.erp_quotation_id
         WHERE q.case_code IS NOT NULL
           AND (CAST(:yr AS INTEGER) IS NULL
                -- 2026-09-08：year 欄優先、案號年僅在 year 為空時備援。
                -- 與 `case_year.quotation_case_year_condition` 同一套判準；
                -- 這裡是手寫 SQL 無法直接 import，**改那邊時這兩處必須一起改**。
                OR q.year = CAST(:yr AS INTEGER)
                OR (q.year IS NULL AND q.case_code LIKE 'CK' || CAST(:yr AS INTEGER)::text || '_%'))
    """), {"yr": yr})).all():
        out.setdefault(r.vkey, set()).add(r.code)
    return out


async def attach_staff(db: AsyncSession, profiles: dict[str, dict[str, Any]],
                       codes_by_vendor: dict[str, set[str]]) -> None:
    """把承辦同仁掛進輪廓（就地改）。承辦的查詢走 `case_staff` 那一家，不另抄 SQL。"""
    from app.repositories.erp.case_staff import staff_by_case_code
    all_codes = {c for cs in codes_by_vendor.values() for c in cs}
    by_code = await staff_by_case_code(db, all_codes)
    for vkey, codes in codes_by_vendor.items():
        seen: dict[int, str] = {}
        for c in codes:
            for s in by_code.get(c, []):
                seen.setdefault(s["user_id"], s["name"])
        prof = profiles.setdefault(vkey, _blank())
        prof["staff"] = [{"user_id": uid, "name": nm} for uid, nm in
                         sorted(seen.items(), key=lambda kv: kv[1] or "")]


async def client_case_profiles(
    db: AsyncSession, year: Optional[int], only_codes: Optional[set[str]] = None,
) -> dict[str, dict[str, Any]]:
    """委託單位 → 案件輪廓。鍵：`id:<vendor_id>`，沒有主檔鍵者退回 `name:<委託單位名>`。

    `only_codes`＝把輪廓限縮到這些案號（承辦篩選用）。**不限縮的話**，
    篩了某位承辦之後「案件數 1」旁邊會出現「狀態合計 3」——同一列自己跟自己矛盾。
    """
    profiles: dict[str, dict[str, Any]] = {}
    yr = int(year) if year else None
    codes = sorted(only_codes) if only_codes is not None else None

    # 腿 1：PM 案件（有委託單位主檔鍵）。狀態以承攬案為準，沒成案才用 PM 階段標籤。
    sql1 = f"""
        SELECT p.client_vendor_id AS vid,
               p.category         AS category,
               COALESCE(NULLIF(btrim(cp.status), ''), {_PM_STATUS_CASE}) AS status,
               count(DISTINCT p.case_code) AS n
          FROM pm_cases p
          LEFT JOIN contract_projects cp ON cp.case_code = p.case_code
          JOIN partner_vendors v ON v.id = p.client_vendor_id AND v.vendor_type = 'client'
         WHERE p.client_vendor_id IS NOT NULL
           AND (CAST(:yr AS INTEGER) IS NULL OR p.year = CAST(:yr AS INTEGER))
           AND (CAST(:codes AS TEXT[]) IS NULL OR p.case_code = ANY(CAST(:codes AS TEXT[])))
           -- 與「合作案件數」同一組案：已承攬，或已經有成案報價單。
           -- 不加這一段的話評估中的案也會進狀態欄，於是列上會出現
           -- 「合作案件數 7、狀態合計 8」這種**自己跟自己矛盾**的兩欄（實測 19 列）。
           -- 判準抄自 client_receivable_repository 腿 1 的 case_count，不是另立一套。
           AND (p.status = 'contracted' OR EXISTS (
                   SELECT 1 FROM erp_quotations q
                    WHERE q.case_code = p.case_code
                      AND q.project_code IS NOT NULL
                      AND q.deleted_at IS NULL))
         GROUP BY 1, 2, 3
    """
    for r in (await db.execute(text(sql1), {"yr": yr, "codes": codes})).all():
        _merge(profiles.setdefault(f"id:{r.vid}", _blank()), r.category, r.status, int(r.n or 0))

    # 腿 2：只收 PM 沒有涵蓋到的承攬案（與 client_receivable_repository 同一條排除規則）
    sql2 = """
        SELECT cp.client_vendor_id AS vid,
               btrim(cp.client_agency) AS vname,
               cp.category AS category,
               cp.status   AS status,
               count(DISTINCT cp.id) AS n
          FROM contract_projects cp
         WHERE COALESCE(btrim(cp.client_agency), '') <> ''
           AND cp.case_code IS NOT NULL
           -- 2026-09-08：兩條連法都要認（同 `pm_coverage.contract_covered_by_pm()`）。
           -- ⚠️ 本檔這條規則有兩處，首次修法只改到上面那處 —— 同型漏改，
           --    症狀是「case_count 2 而 statuses 合計 3」自己跟自己矛盾。
           AND NOT (
                cp.case_code IN (SELECT case_code FROM pm_cases
                                  WHERE client_vendor_id IS NOT NULL AND case_code IS NOT NULL)
             OR (cp.project_code IS NOT NULL
                 AND cp.project_code IN (SELECT project_code FROM pm_cases
                                          WHERE client_vendor_id IS NOT NULL AND project_code IS NOT NULL))
           )
           AND (CAST(:yr AS INTEGER) IS NULL OR cp.year = CAST(:yr AS INTEGER))
           AND (CAST(:codes AS TEXT[]) IS NULL OR cp.case_code = ANY(CAST(:codes AS TEXT[])))
         GROUP BY 1, 2, 3, 4
    """
    for r in (await db.execute(text(sql2), {"yr": yr, "codes": codes})).all():
        key = f"id:{r.vid}" if r.vid is not None else f"name:{r.vname}"
        _merge(profiles.setdefault(key, _blank()), r.category, r.status, int(r.n or 0))

    return _finalize(profiles)


async def vendor_case_profiles(
    db: AsyncSession, year: Optional[int], only_codes: Optional[set[str]] = None,
) -> dict[str, dict[str, Any]]:
    """協力廠商 → 案件輪廓（沿應付 → 報價單 → 案號 這條路）。

    鍵與 `get_vendor_summary_list` 的分組鍵同形：`id:<vendor_id>`／`name:<vendor_name>`，
    否則「彙總列」與「輪廓」會對不起來（同一家在兩邊各分裂成兩列的老問題）。
    """
    profiles: dict[str, dict[str, Any]] = {}
    yr = int(year) if year else None
    codes = sorted(only_codes) if only_codes is not None else None

    # 年度＝year 欄（案號年僅備援），與 quotation_case_year_condition 同一套判準（2026-09-08 改）
    sql = f"""
        SELECT COALESCE('id:' || vp.vendor_id::text, 'name:' || vp.vendor_name) AS vkey,
               COALESCE(cp.category, p.category) AS category,
               COALESCE(NULLIF(btrim(cp.status), ''), {_PM_STATUS_CASE}) AS status,
               count(DISTINCT q.id) AS n
          FROM erp_vendor_payables vp
          JOIN erp_quotations q  ON q.id = vp.erp_quotation_id
          LEFT JOIN contract_projects cp ON cp.case_code = q.case_code
          LEFT JOIN pm_cases p           ON p.case_code = q.case_code
         WHERE (CAST(:yr AS INTEGER) IS NULL
                -- 2026-09-08：year 欄優先、案號年僅在 year 為空時備援。
                -- 與 `case_year.quotation_case_year_condition` 同一套判準；
                -- 這裡是手寫 SQL 無法直接 import，**改那邊時這兩處必須一起改**。
                OR q.year = CAST(:yr AS INTEGER)
                OR (q.year IS NULL AND q.case_code LIKE 'CK' || CAST(:yr AS INTEGER)::text || '_%'))
           AND (CAST(:codes AS TEXT[]) IS NULL OR q.case_code = ANY(CAST(:codes AS TEXT[])))
         GROUP BY 1, 2, 3
    """
    for r in (await db.execute(text(sql), {"yr": yr, "codes": codes})).all():
        _merge(profiles.setdefault(r.vkey, _blank()), r.category, r.status, int(r.n or 0))

    return _finalize(profiles)

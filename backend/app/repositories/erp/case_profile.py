# -*- coding: utf-8 -*-
"""帳款列表的「計畫類別／案件狀態」聚合（owner 2026-09-07：兩頁在統一編號後加這兩欄）。

## 為什麼另開一支而不寫進兩個 repository

委託單位帳款與協力廠商帳款是**兩條不同的路**走到同一個問題：

| | 案件從哪裡來 | 年度口徑 |
|---|---|---|
| 委託單位帳款 | PM 案件（有主檔鍵者）＋ 承攬案（PM 沒涵蓋的） | `PMCase.year`／`ContractProject.year`（案號年） |
| 協力廠商帳款 | 應付 → 報價單 → 案號 | `quotation_case_year_condition`（案號年） |

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
    return {"categories": [], "statuses": []}


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


async def client_case_profiles(db: AsyncSession, year: Optional[int]) -> dict[str, dict[str, Any]]:
    """委託單位 → 案件輪廓。鍵：`id:<vendor_id>`，沒有主檔鍵者退回 `name:<委託單位名>`。"""
    profiles: dict[str, dict[str, Any]] = {}
    yr = int(year) if year else None

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
    for r in (await db.execute(text(sql1), {"yr": yr})).all():
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
           AND cp.case_code NOT IN (
               SELECT case_code FROM pm_cases
                WHERE client_vendor_id IS NOT NULL AND case_code IS NOT NULL)
           AND (CAST(:yr AS INTEGER) IS NULL OR cp.year = CAST(:yr AS INTEGER))
         GROUP BY 1, 2, 3, 4
    """
    for r in (await db.execute(text(sql2), {"yr": yr})).all():
        key = f"id:{r.vid}" if r.vid is not None else f"name:{r.vname}"
        _merge(profiles.setdefault(key, _blank()), r.category, r.status, int(r.n or 0))

    return _finalize(profiles)


async def vendor_case_profiles(db: AsyncSession, year: Optional[int]) -> dict[str, dict[str, Any]]:
    """協力廠商 → 案件輪廓（沿應付 → 報價單 → 案號 這條路）。

    鍵與 `get_vendor_summary_list` 的分組鍵同形：`id:<vendor_id>`／`name:<vendor_name>`，
    否則「彙總列」與「輪廓」會對不起來（同一家在兩邊各分裂成兩列的老問題）。
    """
    profiles: dict[str, dict[str, Any]] = {}
    yr = int(year) if year else None

    # 年度＝案號年，與 quotation_case_year_condition 同一套判準（CK 制看案號，其餘退回 year 欄）
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
                OR q.case_code LIKE 'CK' || CAST(:yr AS INTEGER)::text || '_%'
                OR (q.case_code NOT LIKE 'CK%' AND q.year = CAST(:yr AS INTEGER)))
         GROUP BY 1, 2, 3
    """
    for r in (await db.execute(text(sql), {"yr": yr})).all():
        _merge(profiles.setdefault(r.vkey, _blank()), r.category, r.status, int(r.n or 0))

    return _finalize(profiles)

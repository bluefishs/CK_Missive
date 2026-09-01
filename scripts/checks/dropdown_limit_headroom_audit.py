#!/usr/bin/env python3
"""下拉選單的取數上限 vs 資料實際筆數（weekly 95）

## 為什麼需要它

2026-09-01 owner 從 `/documents/2748` 回報「選不到某個承攬案件」。追下去是
**下拉寫死 `limit: 100` 而承攬案件已 226 筆**，那一筆排第 144 名。

而它昨天還好好的 —— 前一天成案 51 筆，把它擠出了前 100 名。
**上限不會壞在你改它的那天，會壞在資料長過它的那天，而那天沒有人在看。**

同一輪修法還踩了三個坑，每一個都不會報錯：

| 修法 | 失敗方式 |
|---|---|
| `limit: 100 → 200` | 端點上限 `le=100` ⇒ **422** ⇒ useQuery 失敗 ⇒ `?? []` ⇒ **整個下拉變空** |
| 改成分頁續抓 | 讀 `resp.total` 而端點回 `pagination.total` ⇒ total=0 ⇒ **迴圈一次都沒跑** |
| 驗證 | 打的是 service 層（沒有 Pydantic 驗證、回應形狀也不同），**不是端點** |

⇒ 這支要回答的問題只有一個：**每個下拉還能長幾筆才會開始靜默截斷。**

## 判準

對每個登記的下拉，比較三個數字：

    資料表現有筆數  vs  前端送出的 limit  vs  端點的驗證上限

* 現有 >= 送出          → **RED**（現在就在截斷，使用者選不到）
* 送出 > 端點上限        → **RED**（會 422，整個下拉變空 —— 比截斷更糟）
* 餘裕 < 現有的 20%      → YELLOW（快追上了）
* 其餘                  → GREEN

## 這支不做什麼

* **不自動改 limit** —— 放寬多少是取捨（一次拉太多會拖慢頁面），屬人的判斷。
* **不宣稱涵蓋全部下拉**。登記表是手動維護的，而手抄清單會漂移
  （本 repo 的既有教訓）。所以它會**先驗登記表本身**：表裡的資料表不存在
  就 RED，免得清單悄悄過期還一直報綠。

真正的長解是伺服器端搜尋（`hooks/business/useSearchableOptions.ts`），
接上之後對應的登記項就可以移除 —— 那時資料量不再是變數。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# 本檔位於 <repo>/scripts/checks/
sys.path.insert(0, str(Path(__file__).resolve().parent))

#: 登記表：每個「一次抓一批、前端過濾」的下拉。
#:
#: `sent` = 前端實際送出的 limit（改前端時要同步改這裡）
#: `cap`  = 端點的 Pydantic 驗證上限（None = 沒有上限或查不到）
#:
#: ⚠️ 接上伺服器端搜尋之後，請把該項從這裡移除並在下方 SERVER_SEARCH 註記，
#: 否則這支會一直提醒一個已經不存在的風險。
DROPDOWNS = [
    ("contract_projects", "承攬案件 useProjectsDropdown", 1000, 1000),
    ("contract_projects", "公文篩選 useFilterOptions", 1000, 1000),
    ("pm_cases", "PM 案件 usePMCasesDropdown", 1000, 1000),
    ("government_agencies", "機關 agenciesApi.getAgencyOptions", 1000, 1000),
    ("partner_vendors", "委託單位 useClientOptions", 100, 100),
    ("partner_vendors", "協力廠商 useSubcontractorOptions", 100, 100),
    ("taoyuan_projects", "桃園工程 TaoyuanDispatchCreatePage", 500, 1000),
    ("taoyuan_dispatch_orders", "派工 useDispatchQueries", 500, None),
]

#: 已改為伺服器端搜尋、不再受資料量影響的（留著當紀錄，不參與判定）
SERVER_SEARCH: list[str] = []

CONTAINER = "ck_missive_backend"


def _counts(tables: list[str]) -> dict[str, int] | None:
    """一次取回所有資料表的筆數；取不到回 None（呼叫端不得當成 0）。"""
    code = (
        "import sys,asyncio,json; sys.path.insert(0,'/app');"
        "from sqlalchemy import text;"
        "from app.db.database import AsyncSessionLocal;"
        # ⚠️ 這裡必須換行，不能用 `;` —— `async def` 接在分號後是語法錯誤，
        #    而錯誤發生在容器裡、只會出現在 stderr，外層看到的是「連不到資料庫」。
        f"T={tables!r}\n"
        "async def m():\n"
        "    out={}\n"
        "    async with AsyncSessionLocal() as db:\n"
        "        for t in T:\n"
        "            try: out[t]=(await db.execute(text('SELECT COUNT(*) FROM '+t))).scalar()\n"
        "            except Exception: out[t]=None\n"
        "    print('@@'+json.dumps(out))\n"
        "asyncio.run(m())"
    )
    try:
        r = subprocess.run(
            ["docker", "exec", CONTAINER, "python", "-c", code],
            capture_output=True, text=True, timeout=90,
            env={**__import__("os").environ, "MSYS_NO_PATHCONV": "1"},
        )
    except Exception:
        return None
    for line in r.stdout.splitlines():
        if line.startswith("@@"):
            return json.loads(line[2:])
    return None


def main() -> int:
    print("=== 下拉取數上限 vs 資料筆數（weekly 95）===\n")

    tables = sorted({t for t, *_ in DROPDOWNS})
    counts = _counts(tables)
    if counts is None:
        # 「未驗」不是「沒問題」（本 repo 2026-08-30 在 freshness check 上付過這個學費）
        print("  [YELLOW] 連不到容器／資料庫 —— **未驗**，不是沒有風險")
        return 1

    # 先驗登記表本身：表不存在就是清單過期了
    stale = [t for t, v in counts.items() if v is None]
    if stale:
        print("  [RED] 登記表裡的資料表不存在（清單已過期）：")
        for t in stale:
            print(f"        {t}")
        return 2

    red, yellow = [], []
    print(f"  {'下拉':<40}{'現有':>6}{'送出':>7}{'上限':>7}{'餘裕':>7}  判定")
    for table, name, sent, cap in DROPDOWNS:
        n = counts[table]
        if cap is not None and sent > cap:
            verdict = "RED 送出超過端點上限 ⇒ 422 ⇒ 空下拉"
            red.append(f"{name}：送出 {sent} > 端點上限 {cap}")
        elif n >= sent:
            verdict = "RED 現在就在截斷"
            red.append(f"{name}：{table} 已 {n} 筆 >= 送出 {sent}")
        elif (sent - n) < max(n * 0.2, 5):
            verdict = "YELLOW 快追上了"
            yellow.append(f"{name}：只剩 {sent - n} 筆餘裕（{table} {n} 筆）")
        else:
            verdict = "GREEN"
        print(f"  {name:<40}{n:>6}{sent:>7}{str(cap or '—'):>7}{sent - n:>7}  {verdict}")

    if SERVER_SEARCH:
        print("\n  已改伺服器端搜尋（不受資料量影響）：")
        for x in SERVER_SEARCH:
            print(f"    · {x}")

    print()
    if red:
        print(f"[RED] {len(red)} 項：")
        for x in red:
            print(f"  · {x}")
        print("\n  修法二選一：放寬送出的 limit（並確認不超過端點上限），")
        print("  或改用伺服器端搜尋 `hooks/business/useSearchableOptions.ts`（長解）。")
        return 2
    if yellow:
        print(f"[YELLOW] {len(yellow)} 項快追上了：")
        for x in yellow:
            print(f"  · {x}")
        return 1
    print("[GREEN] 所有下拉都還有餘裕")
    return 0


if __name__ == "__main__":
    sys.exit(main())

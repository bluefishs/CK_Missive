# -*- coding: utf-8 -*-
"""成案程序管控 —— 報價／標案 → 承攬 → 成案編碼 → 金流，哪一段斷了、斷了多少錢

## 為什麼需要這一支（2026-08-27，owner 立案）

owner：「ERP 是確認承攬**後**程序」「**前述成案程序的問題就是核心要管控**」
「如同政府標案一鍵建案 也是相同歷程」。

兩條入口（邀標報價／政府標案一鍵建案）走的是同一條鏈，而它在同一個地方斷：

    報價 or 標案 → 承攬 → **成案編碼(project_code)** → 請款/帳本

實查（2026-08-27）：

| 階段 | 件數 | 報價金額 | 有請款 | 有帳本 |
|---|---|---|---|---|
| 已承攬 **有**編碼 | 51 | 892 萬 | 48 | 44 |
| 已承攬 **無**編碼 | **176** | **1,273 萬** | **0** | **0** |

不是相關性偏高，是 48/51 對 0/175 —— 幾乎完全分離。

⚠️ **但編碼不是技術上的阻擋**：金流的外鍵是 `case_code`（finance_ledgers）與
`erp_quotation_id`（erp_billings），**完全不經過 project_code**，那 176 件兩個鍵都有。
⇒ 他們不是「因為沒編碼所以記不了帳」，是**沒有人去記**。
   **把編碼補上，金流依然會是 0** —— 那只是把指標弄綠。

⚠️ 也不是舊資料：1,273 萬裡 **1,264 萬是 2025–2026**，而有編碼那組也全是 2025–2026。
同一時期、同樣的業務，一半走了成案程序、一半沒走。

標案那條路同樣斷：`category='01'` 的 4 件（全庫僅有的 4 件系統編碼）
**沒有一件留下 `source_tender_id`**，也**沒有一件經過 `status='bidding'`** ——
`case_creation.py` 明明兩者都會寫。直接跳到 contracted，2/4 沒有成案編碼。

## 判準：只對「惡化」報紅，不對「既有存量」報紅

存量 176 件是已知的、需要 owner 逐案判斷的業務積欠。
把它判紅會讓這支檢核**從第一天就是紅的**，而永遠紅的訊號與沒有訊號同一個下場
（本 repo 2026-08-27 才在排程稽核上付過這個學費）。

所以：
* **RED** ＝ 相對基線**變差**（無編碼件數增加／金額增加／有編碼卻沒金流的件數增加）
* **標準輸出** ＝ 每一段的件數與金額**照樣大聲印出來**，讓存量看得見
* 基線 `case_award_pipeline_baseline.json`，數字改善時自動收斂（棘輪）

⇒ 這支不負責把 176 件變成 0，它負責**不讓第 177 件靜靜地發生**。
"""
from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
BASELINE = BASE_DIR / "case_award_pipeline_baseline.json"

SQL = """
WITH stage AS (
  SELECT c.id, c.case_code, c.status, c.category, c.source_tender_id,
         (c.project_code IS NOT NULL AND c.project_code <> '') AS has_code
    FROM pm_cases c
),
money AS (
  SELECT s.id, s.case_code, s.status, s.has_code, s.category, s.source_tender_id,
         COALESCE((SELECT sum(q.total_price) FROM erp_quotations q
                    WHERE q.case_code = s.case_code), 0) AS quoted,
         EXISTS(SELECT 1 FROM finance_ledgers l WHERE l.case_code = s.case_code) AS has_ledger,
         EXISTS(SELECT 1 FROM erp_billings b JOIN erp_quotations q ON q.id = b.erp_quotation_id
                 WHERE q.case_code = s.case_code) AS has_billing
    FROM stage s
)
SELECT status, has_code,
       count(*)                                              AS cases,
       COALESCE(round(sum(quoted)), 0)                        AS quoted,
       count(*) FILTER (WHERE has_billing OR has_ledger)      AS with_money
  FROM money GROUP BY status, has_code ORDER BY status, has_code;
"""

SQL_TENDER = """
SELECT count(*) FILTER (WHERE category = '01')                       AS tender_cases,
       count(*) FILTER (WHERE category = '01' AND source_tender_id IS NOT NULL) AS with_origin,
       count(*) FILTER (WHERE status = 'bidding')                    AS bidding
  FROM pm_cases;
"""


def _rows(sql: str):
    """在容器內用 psql 取數 —— 與本 repo 其他 DB 檢核同一種取法。"""
    import subprocess
    container = os.getenv("PIPELINE_AUDIT_CONTAINER", "ck_missive_postgres")
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    out = subprocess.run(
        ["docker", "exec", "-i", container, "psql", "-U", "ck_user", "-d", "ck_documents",
         "-t", "-A", "-F", "|", "-c", sql],
        capture_output=True, encoding="utf-8", env=env, timeout=90,
    )
    if out.returncode != 0:
        # 取不到數必須說出來 —— 靜靜回空會讓「查不到」與「沒有缺口」長得一樣
        print(f"[RED] 無法取數（container={container}）：{(out.stderr or '').strip()[:200]}")
        raise SystemExit(2)
    return [ln.split("|") for ln in out.stdout.strip().split("\n") if ln.strip()]


def main() -> int:
    rows = _rows(SQL)
    tender = _rows(SQL_TENDER)[0]

    stages: dict[tuple[str, bool], dict] = {}
    for st, hc, n, q, wm in rows:
        stages[(st, hc == "t")] = {"cases": int(n), "quoted": int(q), "with_money": int(wm)}

    def g(st, hc, k):
        return stages.get((st, hc), {}).get(k, 0)

    cur = {
        "contracted_no_code": g("contracted", False, "cases"),
        "contracted_no_code_quoted": g("contracted", False, "quoted"),
        "coded_without_money": g("contracted", True, "cases") - g("contracted", True, "with_money"),
        "tender_cases_without_origin": int(tender[0]) - int(tender[1]),
    }

    base = {}
    if BASELINE.exists():
        try:
            base = json.loads(io.open(BASELINE, encoding="utf-8").read())
        except Exception:
            base = {}

    print("=" * 70)
    print("成案程序管控 —— 報價/標案 → 承攬 → 成案編碼 → 金流")
    print("=" * 70)
    print("\n【各階段：件數｜報價金額｜其中有金流】")
    label = {("planning", False): "① 報價/規劃中",
             ("bidding", False): "① 投標中",
             ("contracted", False): "② 已承攬 — 無成案編碼",
             ("contracted", True): "③ 已承攬 — 有成案編碼",
             ("closed", False): "④ 已結案 — 無編碼",
             ("closed", True): "④ 已結案 — 有編碼"}
    for key, v in sorted(stages.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        name = label.get(key, f"{key[0]}／{'有' if key[1] else '無'}編碼")
        print(f"   {name:<22} {v['cases']:>4} 件 ｜ {v['quoted']:>11,} 元 ｜ 有金流 {v['with_money']:>3}")

    print("\n【標案一鍵建案這條路】")
    print(f"   category='01' 案件 {tender[0]} 件｜留下 source_tender_id 的 {tender[1]} 件"
          f"｜status='bidding' 的 {tender[2]} 件")
    if int(tender[0]) and not int(tender[1]):
        print("   ⚠️ 一件都沒有留下來源標案 —— `case_creation.py` 會寫 source_tender_id，"
              "代表這些案件不是走那支建立的，或 tender_id 沒被送進來。"
              "「這個案子從哪個標案來」目前無從追溯。")
    if not int(tender[2]):
        print("   ⚠️ 沒有任何案件處於 'bidding' —— 「投標中」這個階段實際上沒有被使用，"
              "案件是直接出現在 contracted。**成案前沒有可觀察的中間狀態。**")

    reds, notes = [], []
    for k, zh in [("contracted_no_code", "已承攬但無成案編碼的件數"),
                  ("contracted_no_code_quoted", "上述案件的報價金額"),
                  ("coded_without_money", "有成案編碼卻完全沒有金流的件數"),
                  ("tender_cases_without_origin", "標案建案但無來源連結的件數")]:
        b = base.get(k)
        if b is None:
            notes.append(f"{zh}：{cur[k]:,}（首次記錄，納入基線）")
        elif cur[k] > b:
            reds.append(f"{zh} 惡化：{b:,} → {cur[k]:,}（+{cur[k]-b:,}）")
        elif cur[k] < b:
            notes.append(f"{zh} 改善：{b:,} → {cur[k]:,}，基線收斂")
        else:
            notes.append(f"{zh}：{cur[k]:,}（與基線相同）")

    print("\n【與基線比對】")
    for n in notes:
        print(f"   · {n}")
    for r in reds:
        print(f"   🔴 {r}")

    # 棘輪：只往好的方向收，惡化時不動基線（否則下週就把惡化當成新常態）
    new_base = {k: (min(v, base[k]) if k in base else v) for k, v in cur.items()}
    if new_base != base:
        io.open(BASELINE, "w", encoding="utf-8", newline="\n").write(
            json.dumps(new_base, ensure_ascii=False, indent=2) + "\n")

    print("\n" + "-" * 70)
    print("⚠️ 這支**不負責**把存量 176 件變成 0 —— 那需要逐案的業務判斷。")
    print("   它負責的是：不讓第 177 件靜靜地發生。")
    print("⚠️ 也請記得：補上成案編碼**不會**自動帶來金流。")
    print("   金流的外鍵是 case_code 與 erp_quotation_id，不經過 project_code；")
    print("   那 176 件兩個鍵都有，缺的是**有人去記**。")

    if reds:
        print("\nStatus: [RED] 成案程序的缺口正在擴大")
        return 2
    print("\nStatus: [GREEN] 未較基線惡化（存量仍在，見上方各階段數字）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

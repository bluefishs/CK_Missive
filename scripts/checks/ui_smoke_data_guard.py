# -*- coding: utf-8 -*-
"""走查不得改變業務資料 —— 前後列數比對守衛（2026-08-05）。

## 為什麼需要這一支

2026-08-05 owner 回報晨報每天印「🚨 逾期 202 天 派工單號001 … 進行中」，
而該派工單在畫面上是「全部完成／已完成」。追下去發現派工單 1 有 **10 筆**
作業紀錄，其中 **7 筆完全空白**（無說明、無關聯公文、無日期），
建立時間全部落在 2026-07-31 與 08-02 —— 正是我在開發瀏覽器走查的那兩天，
間隔 13~25 分鐘，對應反覆執行走查的節奏。

也就是說：**自我檢核機制自己往生產資料寫了垃圾**，那些垃圾讓完成比例卡在
3/10 → 判定 active → 每天推一則假的逾期告警給 owner。全庫僅這 7 筆，
其他任何日期都沒有，因果非常明確。

當時的 flow 早已改掉，現行設定不會建立紀錄。但**沒有任何東西阻止**
未來某條 flow 又這樣做，而它每天 04:15 無人值守地跑在生產環境上。

## 作法

跑走查前後各數一次關鍵業務表的列數，有變動就 exit 2（未驗完＋出聲）。
刻意**只偵測不阻擋** —— 阻擋要在應用層做（見下方「未做的部分」），
而這支的價值在於：這種事再發生時不會是三個月後由 owner 從晨報裡發現。

## 未做的部分（留給 owner 決定）

後端目前**允許建立完全空白的作業紀錄**。一筆沒有說明、沒有關聯公文、
沒有任何日期的紀錄在業務上沒有意義，卻會參與結案比例計算。
要不要在 API 層擋掉屬於業務規則變更，不擅自更動。

用法：
    python scripts/checks/ui_smoke_data_guard.py --snapshot > before.txt
    ...跑走查...
    python scripts/checks/ui_smoke_data_guard.py --compare before.txt
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

CONTAINER = "ck_missive_postgres"
DB_USER = "ck_user"
DB_NAME = "ck_documents"

# 走查會經過的業務表。刻意**不含** log/事件/快取類（那些本來就會變動），
# 只放「走查絕對不該碰」的業務實體。
WATCHED_TABLES = [
    "taoyuan_work_records",
    "taoyuan_dispatch_orders",
    "documents",
    "document_calendar_events",
    "expense_invoices",
    "erp_quotations",
    "erp_billings",
    "contract_projects",
    "users",
]


def snapshot() -> dict:
    sql = " UNION ALL ".join(
        f"SELECT '{t}' AS t, count(*) AS n FROM {t}" for t in WATCHED_TABLES
    )
    out = subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME,
         "-tAc", sql],
        capture_output=True, text=True, timeout=60,
    )
    if out.returncode != 0:
        raise RuntimeError((out.stderr or "psql 無輸出").strip()[:200])
    counts = {}
    for line in (out.stdout or "").splitlines():
        line = line.strip()
        if "|" in line:
            t, n = line.split("|", 1)
            counts[t] = int(n)
    if len(counts) != len(WATCHED_TABLES):
        raise RuntimeError(f"只取到 {len(counts)}/{len(WATCHED_TABLES)} 張表的列數")
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--compare", type=Path)
    args = ap.parse_args()

    try:
        now = snapshot()
    except Exception as e:
        print(f"✗ 未驗完：無法取得列數快照 — {e}", file=sys.stderr)
        return 2

    if args.snapshot:
        print(json.dumps(now, ensure_ascii=False))
        return 0

    if not args.compare or not args.compare.exists():
        print("✗ 未驗完：--compare 需要指向 --snapshot 產生的檔案", file=sys.stderr)
        return 2

    before = json.loads(args.compare.read_text(encoding="utf-8"))
    diffs = [
        f"  • {t}: {before.get(t)} → {n}（{n - before.get(t, n):+d}）"
        for t, n in now.items() if before.get(t) != n
    ]
    if not diffs:
        print(f"✓ 業務資料未變動（{len(now)} 張表）")
        return 0

    print("✗ 走查期間業務資料被改動了 —— 檢核機制不該寫生產資料：")
    for d in diffs:
        print(d)
    print("\n2026-08-05 實際發生過：走查在派工單 1 建了 7 筆空白作業紀錄，")
    print("讓完成比例卡在 3/10 → 晨報每天推一則假的「逾期 202 天」給 owner。")
    return 2


if __name__ == "__main__":
    sys.exit(main())

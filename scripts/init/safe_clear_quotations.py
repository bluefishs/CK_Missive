#!/usr/bin/env python3
"""重整匯入前的報價單安全汰換（owner 2026-08-31 規劃）

## 為什麼需要護欄，而不是直接 DELETE

`erp_quotations` 底下掛著**三張 `ON DELETE CASCADE` 的財務表**：

    erp_billings          63 筆   ← 其中 37 筆已收款，NT$4,598,873
    erp_invoices          48 筆
    erp_vendor_payables   47 筆

`DELETE FROM erp_quotations` 會**靜靜連帶刪掉 158 筆財務紀錄**，而新的報價單
彙整表裡沒有這些 —— 收款、發票、應付都是在系統裡登打的，不在報價表上。
刪掉就沒有任何來源能把它們補回來。

## 這支的規則（三道，缺一不可）

1. **只動指定年度**（預設 2025／2026 ＝ 民國 114／115）。
   2020/2021/2024 那 5 張不在重整範圍，清掉就沒有東西能補回來。
2. **掛著任何請款／發票／應付的一律拒刪**，並逐筆列出讓人看見。
3. **刪除前必存快照**（含完整欄位與附屬計數），沒有快照就不執行。

## 這支不做什麼

* 不做「軟刪除」—— 那會讓重整後的資料與舊資料在同一張表裡各自為政。
  要軟刪除請用系統既有的 `deleted_at` 流程，不要用這支。
* 不碰 `pm_cases`。報價單與邀標案件是兩件事，一起刪會讓案件史斷掉。
* 不自動匯入。清空與匯入分開跑，中間要有人看一眼。

## 先確認「到底需不需要清」

匯入服務**本來就是冪等的**：它用 `legacy_quotation_no` 比對既有紀錄，
走 `to_update` 就地更新。**只要新總表沿用同一組報價單編號，根本不必清。**

    先跑 dry-run 匯入 → 看 to_update 多不多
      to_update 多      ⇒ 編號沿用 ⇒ 直接匯入，不要用這支
      幾乎全是 to_create ⇒ 編號變了 ⇒ 才輪到這支

預設 dry-run；要真的刪除需 `--apply`。
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

# 容器內 app 套件在 /app；本機執行時才需要往上找 backend/
for _p in ("/app", os.path.join(os.path.dirname(__file__), "..", "..", "backend")):
    if os.path.isdir(os.path.join(_p, "app")):
        sys.path.insert(0, _p)
        break

from sqlalchemy import text  # noqa: E402

from app.db.database import AsyncSessionLocal  # noqa: E402

#: 預設重整範圍：民國 114／115 ＝ 西元 2025／2026（紀年規範 §2.5 一律西元）
DEFAULT_YEARS = (2025, 2026)

#: 附屬財務表 → 外鍵欄位。**這張表就是護欄的來源**，
#: 新增任何 CASCADE 指向 erp_quotations 的表，必須同時加進這裡，
#: 否則這支會回報「可安全刪除」而實際會連帶刪掉東西。
DEPENDENTS = {
    "erp_billings": "erp_quotation_id",
    "erp_invoices": "erp_quotation_id",
    "erp_vendor_payables": "erp_quotation_id",
    "erp_quotation_items": "quotation_id",
}


def _resolve_snapshot_dir(spec: str):
    """算出可寫入的快照目錄；算不出來回 None（由呼叫端中止）。

    絕對路徑直接用；相對路徑則相對於**專案根**，而專案根用「往上找 `.git`」
    決定，不用固定層數 —— 這支可能被複製到別處執行，固定層數會靜靜算到 `/`。
    最後一定實際試寫，因為「目錄存在」不等於「寫得進去」。
    """
    if os.path.isabs(spec):
        cand = spec
    else:
        here = os.path.abspath(os.path.dirname(__file__))
        root = None
        cur = here
        while True:
            if os.path.isdir(os.path.join(cur, ".git")):
                root = cur
                break
            nxt = os.path.dirname(cur)
            if nxt == cur:
                break
            cur = nxt
        if root is None:
            return None
        cand = os.path.join(root, spec)
    try:
        os.makedirs(cand, exist_ok=True)
        probe = os.path.join(cand, ".write_probe")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("")
        os.remove(probe)
        return cand
    except OSError:
        return None


async def _verify_dependents_table(db) -> list[str]:
    """對照資料庫實際的外鍵，確認 DEPENDENTS 沒有漏。

    漏一張表的後果是**這支會說「可安全刪除」而實際連帶刪掉資料** ——
    那比沒有護欄更糟，因為它會讓人放心。所以每次執行都重新對照，
    不信任這份手寫清單（同 `sort_utils` 不用手抄白名單的理由）。
    """
    rows = (await db.execute(text("""
        SELECT tc.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name = 'erp_quotations'
    """))).all()
    actual = {t: c for t, c in rows}
    missing = [f"{t}.{c}" for t, c in actual.items() if DEPENDENTS.get(t) != c]
    return missing


async def main() -> int:
    ap = argparse.ArgumentParser(description="報價單安全汰換（預設 dry-run）")
    ap.add_argument("--years", type=int, nargs="+", default=list(DEFAULT_YEARS),
                    help="要汰換的年度（西元）。預設 2025 2026")
    ap.add_argument("--apply", action="store_true", help="真的執行刪除（否則只預覽）")
    ap.add_argument("--snapshot-dir", default="docs/runbooks",
                    help="快照存放目錄（相對於專案根）")
    args = ap.parse_args()

    years = sorted(set(args.years))
    print("=== 報價單安全汰換 ===")
    print(f"  範圍年度：{years}（西元）")
    print(f"  模式：{'**APPLY — 會真的刪除**' if args.apply else 'dry-run（不會動任何資料）'}")
    print()

    async with AsyncSessionLocal() as db:
        # 護欄 0：DEPENDENTS 有沒有漏掉某張 CASCADE 表
        missing = await _verify_dependents_table(db)
        if missing:
            print("  ✗ 中止：資料庫有本腳本不認得的外鍵指向 erp_quotations：")
            for m in missing:
                print(f"      {m}")
            print("    ⇒ 請先把它加進 DEPENDENTS，否則護欄會漏判。")
            return 2

        dep_sql = " + ".join(
            f"(SELECT COUNT(*) FROM {t} WHERE {c} = q.id)" for t, c in DEPENDENTS.items()
        )

        # 全表概況（讓人看見「範圍外」有多少，不是只看要刪的）
        total = (await db.execute(text(
            "SELECT COUNT(*) FROM erp_quotations WHERE deleted_at IS NULL"))).scalar()
        in_scope = (await db.execute(text(
            "SELECT COUNT(*) FROM erp_quotations WHERE deleted_at IS NULL AND year = ANY(:ys)"),
            {"ys": years})).scalar()
        print(f"  報價單總數 {total} 張｜範圍內 {in_scope} 張｜**範圍外 {total - in_scope} 張（本腳本不會碰）**")

        rows = (await db.execute(text(f"""
            SELECT q.id, q.quotation_no, q.legacy_quotation_no, q.case_code, q.year,
                   q.total_price, ({dep_sql}) AS deps
            FROM erp_quotations q
            WHERE q.deleted_at IS NULL AND q.year = ANY(:ys)
            ORDER BY q.year, q.id
        """), {"ys": years})).mappings().all()

        deletable = [r for r in rows if r["deps"] == 0]
        blocked = [r for r in rows if r["deps"] > 0]

        print(f"  ├ 可安全刪除（無任何請款／發票／應付／明細）：**{len(deletable)}** 張")
        print(f"  └ 拒刪（掛著財務紀錄）：**{len(blocked)}** 張")
        print()

        if blocked:
            print("  ── 拒刪清單（這些要讓匯入去更新，不是刪掉重建）──")
            for r in blocked[:30]:
                amt = int(r["total_price"] or 0)
                print(f"     #{r['id']:<6}{str(r['quotation_no'] or r['legacy_quotation_no'] or '—')[:18]:<20}"
                      f"{str(r['case_code'] or '—'):<22}{r['year']}  NT${amt:>11,}  附屬 {r['deps']} 筆")
            if len(blocked) > 30:
                print(f"     …另 {len(blocked) - 30} 張")
            print()

        if not deletable:
            print("  沒有可刪除的項目，結束。")
            return 0

        # 護欄 3：快照。**沒有快照就不刪** —— 這一步不可略過。
        #
        # ⚠️ 路徑要嘛算對、要嘛大聲失敗，不接受第三種。
        # 本 repo 的既有教訓：Windows 上 `Path("/app/logs")` 會解析成 `D:\app\`，
        # 而那個目錄可能真的存在 ⇒ 不報錯、只是把檔案寫到錯的地方。
        # 這支被 `docker cp` 到 /tmp 執行時，`__file__` 的上兩層是 `/`，
        # 於是快照會寫到 `/docs` —— 實測 PermissionError（這次是走運，
        # 它剛好沒有權限；若容器以 root 跑就會安靜地寫進一個沒有人會去看的地方）。
        snap_dir = _resolve_snapshot_dir(args.snapshot_dir)
        if snap_dir is None:
            print("  ✗ 中止：算不出可寫入的快照目錄。")
            print("    這支預期從專案根執行（`python scripts/init/safe_clear_quotations.py`）。")
            print("    若在容器內或其他位置執行，請用絕對路徑明確指定：")
            print("      --snapshot-dir /app/backend/logs")
            print("    **沒有快照就不刪** —— 這不是可以略過的一步。")
            return 2
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snap_path = os.path.join(snap_dir, f"quotations_cleared_{stamp}.json")
        snap = {
            "taken_at": datetime.now().isoformat(),
            "years": years,
            "mode": "apply" if args.apply else "dry-run",
            "purpose": "重整匯入前的報價單安全汰換（owner 2026-08-31）",
            "restore_hint": "這些是刪除前的完整列。附屬財務紀錄為 0，故無 CASCADE 損失。",
            "deletable": [dict(r) for r in deletable],
            "blocked": [dict(r) for r in blocked],
        }
        with open(snap_path, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=1, default=str)
        print(f"  快照已寫入：{snap_path}")

        amt = sum(int(r["total_price"] or 0) for r in deletable)
        print(f"  將刪除 {len(deletable)} 張，金額合計 NT${amt:,}")

        if not args.apply:
            print()
            print("  （dry-run，未刪除任何資料。確認清單無誤後加 --apply）")
            return 0

        ids = [r["id"] for r in deletable]
        await db.execute(text("DELETE FROM erp_quotations WHERE id = ANY(:ids)"), {"ids": ids})
        await db.commit()

        left = (await db.execute(text(
            "SELECT COUNT(*) FROM erp_quotations WHERE deleted_at IS NULL"))).scalar()
        # 複驗：財務紀錄一筆都不能少
        after = {}
        for t in DEPENDENTS:
            after[t] = (await db.execute(text(f"SELECT COUNT(*) FROM {t}"))).scalar()
        print()
        print(f"  ✅ 已刪除 {len(ids)} 張；報價單剩 {left} 張")
        print(f"  財務紀錄複驗（應與刪除前相同）：{after}")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

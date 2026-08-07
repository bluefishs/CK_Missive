# -*- coding: utf-8 -*-
"""修正「作業成果 → 新通知」的錯誤前序關聯（2026-08-07）。

## 背景

新增作業紀錄時，「前序紀錄」原本會自動預設為**最後一筆**，不管兩者語意上
有沒有關係。使用者若沒注意到欄位已預填就送出，紀錄就被串進一條不該存在的鏈。

owner 實測（派工單 2）：
    派工通知(01-15) → 作業成果(02-05) → 會議通知(07-03) → 會議紀錄(07-27) → 作業成果(08-07)
作業成果不該是五個月後那場會議通知的前序 —— 那是兩件不同的事。

後果不只難看：時間軸的**縮排用途正是看出事件斷點**，鏈錯了等於把兩件事
畫成同一件；長鏈橫跨數月時，下一條鏈接上去也會看起來倒退。

自動預設已於同日移除（WorkRecordFormPage 與 InlineRecordCreator 兩個入口）。
本腳本處理**既有**資料。

## 判準

只處理「父為 `work_result`、子為 `*_notice`」—— 完成的成果被當成後續**新事件**
的前序。這一類把 parent 清成 NULL，讓該筆成為新的鏈起點（＝事件斷點）。

刻意**不**處理其他組合：時間跨度大不代表關聯錯（例如工程本來就拖很久），
那需要人判斷，自動改會製造另一種錯誤。

## 用法

    python scripts/dev/fix_wrong_work_record_parents.py            # 只列出，不改
    python scripts/dev/fix_wrong_work_record_parents.py --apply    # 實際修改（先自動備份）
    python scripts/dev/fix_wrong_work_record_parents.py --revert <備份檔>

備份為 CSV（id,parent_record_id），revert 會逐筆寫回原值。
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "manual"
CONTAINER = "ck_missive_postgres"
DB_USER, DB_NAME = "ck_user", "ck_documents"

FIND_SQL = """
SELECT c.id, c.parent_record_id, c.dispatch_order_id, c.work_category,
       c.record_date, p.work_category, p.record_date
FROM taoyuan_work_records c
JOIN taoyuan_work_records p ON p.id = c.parent_record_id
WHERE c.dispatch_order_id IS NOT NULL
  AND p.work_category = 'work_result'
  AND c.work_category LIKE '%_notice'
ORDER BY c.dispatch_order_id, c.record_date
"""


def psql(sql: str) -> str:
    out = subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME, "-tAF", "|", "-c", sql],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    if out.returncode != 0:
        raise RuntimeError((out.stderr or "psql 失敗").strip()[:300])
    return out.stdout


def find_rows() -> list[list[str]]:
    return [ln.split("|") for ln in psql(FIND_SQL).splitlines() if ln.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--revert", type=Path)
    args = ap.parse_args()

    if args.revert:
        if not args.revert.exists():
            print(f"✗ 備份檔不存在：{args.revert}")
            return 2
        with args.revert.open(encoding="utf-8") as f:
            rows = list(csv.reader(f))[1:]
        for rid, pid in rows:
            psql(f"UPDATE taoyuan_work_records SET parent_record_id={pid} WHERE id={rid}")
        print(f"✓ 已還原 {len(rows)} 筆")
        return 0

    rows = find_rows()
    print("=" * 72)
    print("錯誤前序關聯：作業成果 → 新通知（新事件被掛在舊事件之下）")
    print("=" * 72)
    if not rows:
        print("  沒有符合的紀錄")
        return 0
    for r in rows:
        print(f"  派工單{r[2]:>4}  紀錄#{r[0]:<4} {r[5]}({r[6]}) → {r[3]}({r[4]})")
    print(f"\n共 {len(rows)} 筆。清除其 parent_record_id 後，該筆會成為新的鏈起點（事件斷點）。")

    if not args.apply:
        print("\n這是預覽。要實際修改請加 --apply（會先備份且可 --revert 還原）。")
        return 0

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = BACKUP_DIR / f"work_record_parents_{stamp}.csv"
    with backup.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "parent_record_id"])
        for r in rows:
            w.writerow([r[0], r[1]])
    print(f"\n已備份：{backup}")

    ids = ",".join(r[0] for r in rows)
    psql(f"UPDATE taoyuan_work_records SET parent_record_id=NULL WHERE id IN ({ids})")
    remaining = len(find_rows())
    print(f"✓ 已清除 {len(rows)} 筆的前序；複查剩餘 {remaining} 筆")
    print(f"  要還原：python {Path(__file__).name} --revert {backup}")
    return 0 if remaining == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

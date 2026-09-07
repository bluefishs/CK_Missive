#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""報價單彙整總表 vs 資料庫（weekly 120，2026-09-07）。

owner：「是否部分案件無匯入？例如『苗栗大山南台鐵平交道潛鑽工程地形測量』系統查詢不到。」

實查：那一案在總表的「系統報價單」第 81 列，**已成立、28,000 元**，
而它**沒有報價單編號** —— 而匯入是以報價單編號為鍵 ⇒ 這種列必然被略過，
**而且不會有任何錯誤訊息**（略過與匯入成功在畫面上長得一樣）。

同型共 4 筆（含 2,186,100 元那筆），另有 6 筆有編號卻不在資料庫裡
（首版說 8 筆，其中 2 筆實際是**同一案的不同版次**——`B114-C031-0` 對上資料庫的
`-1`——逐字比對把版次差異報成缺件。判準已分開，那 2 筆列為 YELLOW）。

## 為什麼做成檢核而不是一次補完

補完是一次性的；下次總表再多幾列沒有編號，同樣會安靜地漏掉。
這支回答的是「**現在總表與系統差在哪裡**」，隨時可跑：

| 判定 | 意思 |
|---|---|
| **RED** | 總表有編號、資料庫沒有 ⇒ 漏匯入 |
| **RED** | 總表列沒有報價單編號 ⇒ 匯入的鍵不存在，必然漏掉（且不會報錯） |
| YELLOW | 資料庫有、總表沒有 ⇒ 可能是總表尚未回填，或系統內另建的案 |

⚠️ 只比對「系統報價單」這一張工作表：它是總表自己宣告的彙整表
（其餘是各承辦的作業表與備份，內容會重複）。

用法：`python scripts/checks/quotation_master_table_diff.py [xlsx 路徑]`
預設路徑取 `QUOTATION_MASTER_XLSX` 環境變數，再退回 `D:/報價單/115報價單彙整總表.xlsx`。
檔案不存在時回 YELLOW（**不是 GREEN** —— 「沒看到」不等於「沒問題」）。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402
from lib.docker_exec import python_in  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = repo_root()
DEFAULT_XLSX = os.environ.get("QUOTATION_MASTER_XLSX", r"D:/報價單/115報價單彙整總表.xlsx")
SHEET = "系統報價單"


def read_master(path: Path) -> tuple[dict[str, dict], list[dict]]:
    """回 ({報價單編號: 該列}, [沒有編號的列])。"""
    import openpyxl  # 延後匯入：沒有 openpyxl 時只影響這一支

    ws = openpyxl.load_workbook(path, data_only=True)[SHEET]
    hdr = [str(c.value).strip() if c.value else "" for c in ws[1]]

    def col(name: str, fallback: int) -> int:
        return hdr.index(name) if name in hdr else fallback

    ci = {k: col(k, i) for i, k in enumerate(
        ("序號", "年度", "承辦同仁", "報價單編號", "是否成立", "報價日期", "客戶名稱", "案名"))}
    ci["報價金額"] = col("報價金額", 9)

    keyed: dict[str, dict] = {}
    unkeyed: list[dict] = []
    for rn, r in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not any(c for c in r[:10]):
            continue
        row = {k: (str(r[i]).strip() if i < len(r) and r[i] is not None else "")
               for k, i in ci.items()}
        row["_row"] = rn
        if row["報價單編號"]:
            keyed[row["報價單編號"]] = row
        else:
            unkeyed.append(row)
    return keyed, unkeyed


def db_legacy_numbers() -> set[str] | None:
    out = python_in(
        "import asyncio, json\n"
        "from sqlalchemy import text\n"
        "from app.db.database import AsyncSessionLocal\n"
        "async def m():\n"
        "    async with AsyncSessionLocal() as db:\n"
        "        rows = (await db.execute(text(\n"
        "            'SELECT legacy_quotation_no FROM erp_quotations '\n"
        "            'WHERE legacy_quotation_no IS NOT NULL AND deleted_at IS NULL'))).all()\n"
        "    print('@@' + json.dumps([r[0] for r in rows]))\n"
        "asyncio.run(m())\n"
    )
    line = [l for l in (out or "").splitlines() if l.startswith("@@")]
    return {str(x).strip() for x in json.loads(line[-1][2:])} if line else None


def main() -> int:
    print("=== 報價單彙整總表 vs 資料庫（weekly 120）===")
    path = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_XLSX)
    if not path.exists():
        print(f"[YELLOW] 找不到總表 {path} —— 未驗（「沒看到」不等於「沒問題」）")
        print("        可用 QUOTATION_MASTER_XLSX 指定路徑，或以參數傳入。")
        return 1
    try:
        keyed, unkeyed = read_master(path)
    except Exception as exc:  # noqa: BLE001
        print(f"[YELLOW] 讀不了總表：{str(exc)[:120]}")
        return 1

    db = db_legacy_numbers()
    if db is None:
        print("[YELLOW] 連不到資料庫，未驗")
        return 1

    missing_raw = sorted(set(keyed) - db)
    extra = sorted(db - set(keyed))

    # ⚠️ 逐字比對會把「同一案的不同版次」報成漏匯入：實測 `B114-C031-0`（總表）
    # 對上資料庫的 `B114-C031-1`、`B115-022a-1` 對上 `B115-022a-0`。
    # 那是版次差異，不是缺件 —— 直接當成 RED 交出去就是把誤報說成事實。
    # ⇒ 去掉尾碼版次後再比一次，只有**連詞幹都對不到**的才算漏匯入。
    def stem(no: str) -> str:
        base = no.rsplit("-", 1)[0] if "-" in no else no
        return base.lower()

    db_stems = {stem(n) for n in db}
    missing = [n for n in missing_raw if stem(n) not in db_stems]
    version_only = [n for n in missing_raw if stem(n) in db_stems]
    print(f"  總表「{SHEET}」有編號 {len(keyed)} 筆／無編號 {len(unkeyed)} 筆；"
          f"資料庫有舊編號 {len(db)} 筆")

    rc = 0
    if unkeyed:
        print(f"[RED] {len(unkeyed)} 筆**沒有報價單編號** —— 匯入以編號為鍵，"
              f"這些列必然被略過，而且不會有任何錯誤訊息：")
        for r in unkeyed:
            print(f"    第{r['_row']}列 | {r['年度']} | {r['承辦同仁']} | "
                  f"{r['案名'][:34]} | {r['報價金額']}")
        print("      修法：在總表補上報價單編號後重跑匯入（編號要人給，系統不代為編）。")
        rc = 2
    if missing:
        print(f"[RED] {len(missing)} 筆總表有編號、資料庫沒有 ⇒ 漏匯入：")
        for n in missing[:20]:
            r = keyed[n]
            print(f"    {n} | {r['年度']} | {r['承辦同仁']} | {r['案名'][:30]}")
        rc = 2
    if version_only:
        print(f"[YELLOW] {len(version_only)} 筆是**同一案的不同版次**（詞幹在資料庫裡對得到）"
              f"，不算漏匯入，但兩邊的版次不一致：")
        for n in version_only:
            same = sorted(x for x in db if stem(x) == stem(n))
            print(f"    總表 {n} ↔ 資料庫 {'、'.join(same)}")
        rc = max(rc, 1)
    if extra:
        print(f"[YELLOW] {len(extra)} 筆資料庫有、總表沒有（總表未回填，或系統內另建）：")
        print("    " + "、".join(extra[:20]) + ("…" if len(extra) > 20 else ""))
        rc = max(rc, 1)

    if rc == 0:
        print("[GREEN] 總表與資料庫一致")
    return rc


if __name__ == "__main__":
    sys.exit(main())

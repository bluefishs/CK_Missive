#!/usr/bin/env python
"""SAVEPOINT 內不得自行 commit（weekly）。

## 為什麼需要這一支

2026-08-17 owner 回報「新增紀錄失敗」（`/erp/quotations/152/accounts/receivable/create`）。
追出來的根因是一個**家族**，不是單點：

`retry_on_code_conflict` 在 `db.begin_nested()`（SAVEPOINT）內執行 operation，
而 operation 裡呼叫的 `BaseRepository.create` **預設 `auto_commit=True`** ——
它直接 commit，把外層交易關掉，於是 `sp.commit()` 拋

    ResourceClosedError: This transaction is closed

使用者看到的只是「新增紀錄失敗」，完全看不出是交易層的問題。
**請款與發票兩支都壞著**（實測皆重現），只有 `asset_service` 是對的 ——
它用的 `create_asset` 只 flush、由外層自己 commit。

## 為什麼靜態檢查抓得到

這條規則是純結構的：「在 `begin_nested()` 的作用範圍內，
不得呼叫會 commit 的東西」。不需要跑起來就看得出。

而**測試抓不到它**：那兩支的既有單元測試全部 mock 掉 repo，
mock 不會 commit，所以測試一路綠而真實路徑一路壞。

## ⚠️ 這支的界限

它只認得**同一個檔案內**「`retry_on_code_conflict` + `repo.create(` 沒帶
`auto_commit=False`」這個組合。若日後有別的 savepoint 包裝或別的 repo 方法
自帶 commit，這支照不到 —— 那時要擴充，不是假設它涵蓋全部。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "backend" / "app" / "services"

# 會開 SAVEPOINT 的包裝（用它就代表底下不該自己 commit）
SAVEPOINT_MARKERS = ("retry_on_code_conflict", "begin_nested(")

# 預設會 commit 的 repository 方法。
# `BaseRepository.create(obj_in, auto_commit=True)` 是預設值 —— 沒有明寫就會 commit。
RISKY_CALL = re.compile(r"\.(create|update|delete)\(\s*(?!.*auto_commit\s*=\s*False)[^)]*\)")


def main() -> int:
    print("=" * 74)
    print("SAVEPOINT 內不得自行 commit")
    print("=" * 74)
    print()

    bad: list[tuple[str, int, str]] = []
    scanned = 0

    # ⚠️ 判準收窄（首跑時我用「同一檔案有 savepoint」，太寬 ——
    # 命中 4 處，逐一核實**全部是假陽性**：它們在各自獨立的 method 裡，
    # 根本不在 savepoint 範圍內。判準交付前先驗鑑別力，本專案的老規矩。）
    #
    # 正確做法：只看**被 savepoint 包住的那個內部函式**。
    # 形狀固定：`async def _xxx_op(...)` 定義在外層 method 內，
    # 然後傳給 `retry_on_code_conflict`。所以掃「被當成參數傳進去的那個函式」的本體。
    # 只看**被 savepoint 包住的那個內部函式**：
    #   `async def _xxx_op(...)` 定義在外層 method 內，再傳給 retry_on_code_conflict。
    # 用縮排判斷函式本體範圍 —— 比正則跨行匹配可靠（正則版第一次就寫壞了）。
    INNER_DEF = re.compile(r'^([ \t]+)async def (_\w+)\(')

    for py in SERVICES.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        try:
            src = py.read_text(encoding="utf-8")
        except Exception:
            continue
        if not any(m in src for m in SAVEPOINT_MARKERS):
            continue
        scanned += 1
        rel = str(py.relative_to(SERVICES)).replace("\\", "/")

        # 哪些內部函式真的被傳進 savepoint 包裝
        wrapped = set(re.findall(r"retry_on_code_conflict\(\s*[\w.]+,\s*(\w+)", src))
        if not wrapped:
            continue

        src_lines = src.split(chr(10))
        for i, ln0 in enumerate(src_lines):
            m = INNER_DEF.match(ln0)
            if not m or m.group(2) not in wrapped:
                continue
            base = len(m.group(1))
            # 本體 = 縮排比 def 更深的連續行（空行不中斷）
            for j in range(i + 1, len(src_lines)):
                ln = src_lines[j]
                if ln.strip() and (len(ln) - len(ln.lstrip())) <= base:
                    break
                if 'auto_commit=False' in ln or ln.strip().startswith('#'):
                    continue
                if not re.search(r'\b(self\.)?repo\w*\.', ln):
                    continue
                if RISKY_CALL.search(ln):
                    bad.append((rel + '::' + m.group(2), j + 1, ln.strip()[:88]))

    print(f"  掃描 {scanned} 個含 SAVEPOINT 的服務檔")
    print()

    if bad:
        print(f"  🔴 {len(bad)} 處在 SAVEPOINT 內可能自行 commit：")
        for rel, n, ln in bad:
            print(f"       ✗ {rel}:{n}")
            print(f"           {ln}")
        print()
        print("       `BaseRepository.create` 預設 `auto_commit=True` ——")
        print("       在 SAVEPOINT 內 commit 會關掉外層交易，`sp.commit()` 拋")
        print("       `ResourceClosedError: This transaction is closed`，")
        print("       而使用者只看到「新增失敗」。")
        print()
        print("       修法：傳 `auto_commit=False`，**並在 savepoint 之外自己 commit**")
        print("       —— 少了外層 commit 會變成「不報錯但沒存進去」，比原本更糟。")
        print("       正確範例：`erp/asset_service.py`（create_asset 只 flush）。")
        print()
        print("Status: [RED] SAVEPOINT 內有自行 commit 的風險")
        return 2

    print("Status: [GREEN] SAVEPOINT 內未發現自行 commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())

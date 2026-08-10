#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""腳本強制表態閘門（CK_Missive 薄包裝）— 2026-08-09。

判定邏輯在 `scripts/checks/.shared-selfaudit/script_declaration_gate.py`
（canonical: `shared-modules/selfaudit/src/`）—— **禁手改**，要改回上游改。

## 本 repo 的形態與其他四個不同

DT／pile／CK_Website／lvrland 導入時都是**零存量**（腳本全數寫進索引表）。
CK_Missive 有 151 支腳本、僅 40 支在索引 —— 一次補完 111 支是可觀的文件工作量，
而且一次寫完的表格多半是「為了通過檢查」而寫，不會有人讀。

owner 決定**逐步清**：存量記在 `.declaration_baseline.txt`，
每當有人把一支寫進索引就從基線移除一行。閘門每次執行都印剩餘數量 ——
**數字不動就代表沒有人在清**，這比一個永遠綠的閘門誠實。

⚠️ 基線是**債，不是豁免**。新增的腳本不在基線裡，會被真的擋下來。

## 用法

    python scripts/checks/declaration_gate.py

退出碼：0 全部表態（存量另計）/ 2 有新增未表態
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "checks" / ".shared-selfaudit"))

from script_declaration_gate import check_declarations  # noqa: E402

BASELINE = ROOT / "scripts" / "checks" / ".declaration_baseline.txt"

PERIPHERAL: dict[str, str] = {
    "declaration_gate.py": "閘門自身；存在理由寫在本檔 docstring，不需在索引重複",
}


def load_baseline() -> set[str]:
    if not BASELINE.exists():
        # 基線檔不見了不是「零存量」，是設定壞了 —— 出聲而不是靜靜放行
        print(f"✗ 找不到存量基線：{BASELINE.name} —— 無法判定，不視為通過")
        raise SystemExit(2)
    return {
        ln.strip()
        for ln in BASELINE.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("#")
    }


def main() -> int:
    baseline = load_baseline()
    cdir = ROOT / "scripts" / "checks"

    # 基線裡的檔案已經不存在 → 清單開始腐爛，該修剪。
    # 沒有這一步，基線會保留一堆早已刪除的名字，讓「剩餘數量」失真，
    # 而失真的進度指標比沒有指標更糟（看起來還有很多要清，實際上不是）。
    stale = sorted(n for n in baseline if not (cdir / n).exists())

    code, msgs = check_declarations(
        repo_root=ROOT,
        # 2026-08-10：主索引改為 scripts/checks/README.md。
        # 原本要求寫進 skills-inventory.md —— 那份是「Skills/Commands/Agents 清單」，
        # 塞 164 支檢核腳本進去會把它變成一份沒有人讀得完的東西，
        # 而讀不完的索引與沒有索引是同一件事。
        # README 按「誰在跑它」分組，回答的正是這份閘門想守住的問題。
        index_files=[
            "scripts/checks/README.md",
            "CLAUDE.md",
            ".claude/rules/skills-inventory.md",
        ],
        scopes=[("scripts/checks", "*.py"), ("scripts/checks", "*.sh")],
        peripheral=PERIPHERAL,
        grandfathered=baseline,
    )
    print("=== 腳本強制表態閘門（CK_Missive）===")
    for m in msgs:
        print(m)

    if stale:
        print(f"\n  🟡 基線含 {len(stale)} 個已不存在的檔案 —— 請從 "
              f"{BASELINE.name} 移除（進度指標會失真）：")
        for n in stale[:6]:
            print(f"      · {n}")
        if len(stale) > 6:
            print(f"      …另 {len(stale) - 6} 個")

    print()
    print(f"Status: [{'RED' if code >= 2 else 'GREEN'}]")
    if code == 0:
        if baseline:
            print("  註：GREEN 只代表「沒有新增未表態」。存量仍是債，")
            print(f"  清一支就從 {BASELINE.name} 移除一行。")
        else:
            print("  註：存量已於 2026-08-10 全數清空 —— 現在 GREEN 就是真的全部表態。")
            print("  新增腳本請寫進 scripts/checks/README.md 對應的「誰在跑它」分組。")
    return code


if __name__ == "__main__":
    sys.exit(main())

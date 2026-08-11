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


# 索引可能出現的位置（依優先序）。**不是**「這幾份都必須在」。
#
# 2026-08-11：本閘門是 daily step 0，而 daily 由**容器內** APScheduler 驅動，
# 容器只掛 scripts/ 與 backend/ —— CLAUDE.md 與 .claude/ 根本不在裡面。
# canonical 的判定是「任一索引檔不存在即無法判定(2)」，在單一環境下是對的，
# 但在這裡等於**每天必紅、每天推一則 LINE**，而紅的原因不是有人沒表態，
# 是這支檢核在排程實際執行的環境裡不可能通過。天天紅的告警等於沒有告警。
#
# 過濾放在薄包裝而不是改 canonical：那份是五個 repo 共用的，
# 而「本 repo 的檢核跑在容器裡」是 CK_Missive 特有的形態 ——
# 依 08-09 的分工，各 repo 特有的事留在自己的包裝。
INDEX_CANDIDATES = [
    "scripts/checks/README.md",   # 主索引（在 scripts/ 底下，容器內讀得到）
    "CLAUDE.md",                  # host only
    ".claude/rules/skills-inventory.md",  # host only
]


def resolve_index_files() -> list[str]:
    """回傳此環境實際讀得到的索引檔；一份都沒有就是設定壞了，出聲而非放行。"""
    present = [f for f in INDEX_CANDIDATES if (ROOT / f).exists()]
    missing = [f for f in INDEX_CANDIDATES if f not in present]
    if not present:
        print("✗ 所有索引文件都讀不到 —— 無法判定，不視為通過："
              + "、".join(INDEX_CANDIDATES))
        raise SystemExit(2)
    if missing:
        # 缺席要看得見。靜靜少讀一份索引，等於默默放寬判準。
        print(f"  ℹ 讀到 {len(present)}/{len(INDEX_CANDIDATES)} 份索引；"
              f"此環境不含：{'、'.join(missing)}")
    return present


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
        index_files=resolve_index_files(),
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

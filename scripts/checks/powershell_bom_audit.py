#!/usr/bin/env python3
"""
PowerShell UTF-8 BOM Audit (fitness step 54, L49 family 第 11 案)

掃 scripts/**/*.ps1，若含中文字元但無 UTF-8 BOM 即 RED。

觸發：5/28 owner 跑 install-task-scheduler.ps1 報 parser error line 104。
真因：Windows PowerShell 5.1 預設用 cp950 讀無 BOM 的 .ps1 檔 →
中文字元 decode 成 '?' 吃掉換行 → try/catch 結構崩 → silent parser error。

掃 20 個 ps1 全部都無 BOM 同型風險，是 chronic silent issue。

修法：所有含中文 .ps1 必須 UTF-8 with BOM (0xEF 0xBB 0xBF)。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
UTF8_BOM = b"\xef\xbb\xbf"
CHINESE_PATTERN = re.compile(r"[一-鿿]")


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="PowerShell UTF-8 BOM audit")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    print("=" * 72)
    print("[54/54] PowerShell UTF-8 BOM Audit (L49 family #11)")
    print("=" * 72)

    red_files = []
    total_chinese = 0

    #: ⚠️ 2026-08-27：原本**只掃 `scripts/`**，而 `.claude/hooks/` 底下有 3 支
    #: 含中文卻無 BOM —— 其中 `careful-guard.ps1`（攔截危險指令的安全守衛）
    #: **每次呼叫都解析失敗 exit 1**，30 天內 12,491 次一次都沒攔過任何東西。
    #: 而這支稽核同一時刻回「無 BOM: 0 🟢 GREEN」，**它判得沒錯 —— 它只是
    #: 看不到那個目錄**。hook 才是最需要這個保護的地方：它們每次工具呼叫
    #: 都跑，壞掉的症狀是一片安靜。
    _SCAN_DIRS = ["scripts", ".claude/hooks"]
    _targets = [f for d in _SCAN_DIRS for f in (REPO_ROOT / d).rglob("*.ps1")]
    for ps1 in _targets:
        try:
            content = ps1.read_bytes()
        except OSError:
            continue
        if not content:
            continue

        # 解碼看是否含中文
        try:
            text = content.decode("utf-8", errors="replace")
        except Exception:
            continue
        if not CHINESE_PATTERN.search(text):
            continue
        total_chinese += 1

        # 檢 BOM
        if not content.startswith(UTF8_BOM):
            rel = ps1.relative_to(REPO_ROOT).as_posix()
            red_files.append(rel)

    print(f"\n中文 .ps1 檔數: {total_chinese}")
    print(f"無 BOM (RED): {len(red_files)}")

    if red_files:
        print(f"\n🔴 RED — {len(red_files)} sites:")
        for f in red_files[:20]:
            print(f"  {f}")
        if len(red_files) > 20:
            print(f"  ... and {len(red_files) - 20} more")
        print("\n修法：")
        print("  PowerShell: [System.IO.File]::WriteAllText($path, $content,")
        print("              (New-Object System.Text.UTF8Encoding($true)))")
        print("  VSCode:    右下角 encoding → 'UTF-8 with BOM' → Save with Encoding")
        # 2026-08-10：原本非 --strict 時印 RED 卻 return 0 —— 呼叫端拿到的是綠燈。
        # 這與 08-07 在 doc_baseline_claim_audit 抓到的是同一家族（L83：
        # 「產出端說的話，與消費端實際收到的，是兩件事」），當時已立法依原生三態，
        # 這支漏改。RED 一律 exit 1，不再由旗標決定嚴重度。
        return 1

    print("\n🟢 GREEN — 所有含中文 .ps1 都有 UTF-8 BOM")
    return 0


if __name__ == "__main__":
    sys.exit(main())

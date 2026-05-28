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

    for ps1 in (REPO_ROOT / "scripts").rglob("*.ps1"):
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
        if args.strict:
            return 1
        return 0

    print("\n🟢 GREEN — 所有含中文 .ps1 都有 UTF-8 BOM")
    return 0


if __name__ == "__main__":
    sys.exit(main())

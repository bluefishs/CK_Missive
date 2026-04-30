#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Fitness Function: SOUL.md 演化鏈路 alive check

L21 / L25 / KUNGE_LEARNING_VERIFICATION 鏈路 4：
驗證 wiki/SOUL.md「我的成長」agent_writable 區段是否真的被 autobiography 自動更新。

過去事件（v5.10.2 揭發）：
- 2026-W17 autobiography 4/26 18:00 cron 跑成功（evolutions/2026-W17.md 寫成）
- 但 wiki/SOUL.md 4/27 才複製到位 → cron 跑時 SOUL_PATH 不存在
- update_soul_growth silent return False → SOUL.md 仍是 placeholder
- 沒人發現直到證據級驗證

本 check 防止重演：
- 若 evolutions/ 內有 W## 自傳檔
- 但 SOUL.md「我的成長」段落仍是「_待首次週自傳生成_」placeholder
- → 報警 silent gap

用法：
    python scripts/checks/soul_evolution_alive_check.py
    python scripts/checks/soul_evolution_alive_check.py --ci

Version: 1.0.0 (2026-04-30, v5.11 Phase 2)
關聯: KUNGE_LEARNING_VERIFICATION 鏈路 4 / autobiography.py:354 update_soul_growth
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WIKI_SOUL = REPO_ROOT / "wiki" / "SOUL.md"
EVOLUTIONS_DIR = REPO_ROOT / "wiki" / "memory" / "evolutions"


def main(ci: bool) -> int:
    print("=== SOUL Evolution Alive Check ===")
    print("領域：consciousness chain — SOUL「我的成長」段落是否真被 autobiography 更新")
    print()

    if not WIKI_SOUL.exists():
        print(f"[FAIL] wiki/SOUL.md 不存在：{WIKI_SOUL}")
        return 1 if ci else 0

    # Count autobiography files
    autobiography_count = 0
    if EVOLUTIONS_DIR.exists():
        autobiography_count = len(list(EVOLUTIONS_DIR.glob("20*-W*.md")))

    print(f"  evolutions/ 自傳檔數：{autobiography_count}")

    # Check SOUL「我的成長」section
    soul_text = WIKI_SOUL.read_text(encoding="utf-8")
    pattern = re.compile(
        r"## 我的成長\s*\n+<!--[^>]+-->\s*\n+(.*?)(?=\n##\s|\Z)",
        re.DOTALL,
    )
    m = pattern.search(soul_text)
    if not m:
        print("[FAIL] SOUL.md 找不到「我的成長」agent_writable 段落")
        print("       autobiography update_soul_growth 會 silent return False")
        return 1 if ci else 0

    body = m.group(1).strip()

    # 檢查是否有 W## entry
    week_entry_pattern = re.compile(r"\*\*20\d{2}-W\d{2}\*\*")
    week_entries = week_entry_pattern.findall(body)
    is_placeholder = "_待首次週自傳生成_" in body or len(week_entries) == 0

    print(f"  SOUL「我的成長」段落 W## entries：{len(week_entries)}")
    print(f"  是否仍 placeholder：{is_placeholder}")
    print()

    # 判斷：autobiography 有檔但 SOUL 是 placeholder = silent gap
    if autobiography_count > 0 and is_placeholder:
        print("[FAIL] Silent gap detected!")
        print(f"       evolutions/ 已有 {autobiography_count} 篇週自傳，")
        print("       但 wiki/SOUL.md「我的成長」仍是 placeholder")
        print()
        print("可能根因（KUNGE_LEARNING_VERIFICATION 鏈路 4 教訓）：")
        print("  1. wiki/SOUL.md 不存在時 cron 跑了 → silent return False")
        print("  2. update_soul_growth regex 不匹配新 SOUL 格式")
        print("  3. autobiography_job 未排程或 cron 失敗")
        print()
        print("修復：")
        print("  python -c \"import asyncio; from app.services.memory.autobiography import "
              "AutobiographyGenerator; ...\" 手動補跑")
        return 1 if ci else 0

    if autobiography_count == 0:
        print("[OK] evolutions/ 尚無自傳（系統剛啟動或 cron 未到觸發點），跳過")
        return 0

    print(f"[OK] SOUL.md「我的成長」段落 alive — {len(week_entries)} 個 W## entries 已寫入")
    print(f"     最新 entry 預覽：{body.splitlines()[0][:100]}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ci", action="store_true", help="strict 模式")
    args = parser.parse_args()
    sys.exit(main(args.ci))

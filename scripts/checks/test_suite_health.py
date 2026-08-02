#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""測試套件健康檢核 — 「它跑不跑得起來」也要有人問。

## 為什麼需要這一支（2026-08-03）

測試套件長期不能安全執行（打生產庫 + 連線耗盡），**沒有任何機制在問這件事** ——
是 owner 記在待辦裡，不是系統發現的。同期還有一個症狀相同的案例：
08-02 因站台改版重寫 ezbid parser，10 個測試當場全紅，但因為全套跑不起來，
那次修改**兩天內都沒有回歸保護**，直到套件修好才浮出來。

對照六階階梯（`SELF_AUDIT_EVOLUTION_STANDARD.md`）：測試是最底層的網，
而「網本身破了」沒有任何一階在看。這支補的就是那個洞。

## 為什麼是「基線比對」而不是「必須全綠」

現況有 44 個既有失敗（mock 耗盡、過時斷言等測試債）。要求全綠會讓這支
天天紅 → 變成第 4709 筆沒人看的告警，正是我們一路在治的告警疲勞。

所以比對的是**測試 id 集合**，不是數字：
  - 出現基線裡沒有的失敗 → RED（新引入的回歸，這才是要擋的）
  - 基線裡的失敗被修好   → YELLOW 提示更新基線（好消息也要看得到，
                            否則基線只會膨脹、永遠不收斂）
  - 只用數字比對會漏掉「修好一個、同時弄壞另一個」——總數不變但實際有回歸。

## 三態
  0 = GREEN（無新增失敗）
  1 = YELLOW（有失敗被修好，基線該更新）
  2 = RED（新增失敗／套件跑不起來／測試庫不存在）

用法：
  python scripts/checks/test_suite_health.py            # 檢核
  python scripts/checks/test_suite_health.py --update   # 重錄基線（修完債之後跑）
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
BASELINE = REPO / "backend" / "tests" / "known_failures.json"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def run_suite() -> tuple[set[str], str, int]:
    """跑全套，回傳 (失敗的 test id 集合, 摘要行, pytest returncode)。"""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=BACKEND, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=3600,
    )
    out = proc.stdout + proc.stderr
    # 注意過濾空字串：pytest 的 error summary 有時會有一行光禿禿的 "ERROR"，
    # 收進來會變成一個空的 test id 混在基線裡（首次建基線時就踩到了）。
    failed = {
        line[len(prefix):].split(" ")[0].strip()
        for line in out.splitlines()
        for prefix in ("FAILED ", "ERROR ")
        if line.startswith(prefix)
    }
    failed = {t for t in failed if t and "::" in t}
    summary = next(
        (l for l in reversed(out.splitlines()) if re.search(r"\d+ (passed|failed|error)", l)),
        "(無法解析 pytest 摘要)",
    )
    # collection 階段炸掉時 pytest 不會印 FAILED，只有 errors —— 那是最嚴重的情況
    if "error" in summary.lower() and not failed:
        failed.add("<collection-error>")
    return failed, summary.strip(), proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true", help="以本次結果重錄基線")
    args = ap.parse_args()

    print("=" * 66)
    print(" 測試套件健康檢核（跑全套，約 10 分鐘）")
    print("=" * 66)

    if not BACKEND.exists():
        print(f"  ✗ 找不到 backend 目錄: {BACKEND}")
        return 2

    try:
        failed, summary, rc = run_suite()
    except subprocess.TimeoutExpired:
        print("  ✗ RED：測試套件逾時未完成（>60 分鐘）")
        return 2

    print(f"  pytest: {summary}")

    # 套件根本跑不起來 —— 這比「有幾個測試紅」嚴重得多，要能區分開來
    if "<collection-error>" in failed:
        print("  ✗ RED：collection 階段即失敗，整套無法執行")
        print("    常見原因：測試資料庫不存在（跑 bash scripts/dev/setup-test-db.sh）")
        return 2
    if rc not in (0, 1):
        print(f"  ✗ RED：pytest 以非預期狀態結束（exit={rc}）")
        print("    exit=3 通常代表 conftest 護欄擋下了（測試庫與生產庫同名）")
        return 2

    if args.update:
        BASELINE.write_text(
            json.dumps({"known_failures": sorted(failed)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  基線已更新：{len(failed)} 項 → {BASELINE.relative_to(REPO)}")
        return 0

    if not BASELINE.exists():
        print(f"  ✗ RED：找不到基線檔 {BASELINE.relative_to(REPO)}")
        print("    首次建立請跑：python scripts/checks/test_suite_health.py --update")
        return 2

    known = set(json.loads(BASELINE.read_text(encoding="utf-8"))["known_failures"])
    new = sorted(failed - known)
    fixed = sorted(known - failed)

    print(f"  已知失敗 {len(known)} 項｜本次失敗 {len(failed)} 項"
          f"｜新增 {len(new)}｜已修好 {len(fixed)}")

    if new:
        print(f"\n  ✗ RED：新增 {len(new)} 項失敗（基線裡沒有＝這次弄壞的）")
        for t in new[:15]:
            print(f"     {t}")
        if len(new) > 15:
            print(f"     …另 {len(new) - 15} 項")
        return 2

    if fixed:
        print(f"\n  ⚠ YELLOW：{len(fixed)} 項既有失敗已修好，請重錄基線")
        for t in fixed[:10]:
            print(f"     {t}")
        print("     指令：python scripts/checks/test_suite_health.py --update")
        return 1

    print("\n  ✓ GREEN：無新增失敗（既有測試債維持在基線）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

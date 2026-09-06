#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""前端 vitest 套件健康檢核（weekly 114）—— 同 weekly 24 `test_suite_health.py` 的形狀，對象換成前端。

2026-09-06 之前前端 228 個測試檔**沒有任何排程或閘門在跑**（A111）：首次完整跑 254 失敗，
三個共同根因（barrel 部分 mock 沒跟上新 export／`shared-modules/sso-js` 自帶第二份 React／
`useResponsive` mock 漏 `responsiveValue`）修掉之後仍有數十筆是「畫面早就改了、測試沒跟」。
那些逐筆修是另一件事；這支先讓「**新增的失敗**」看得見——沒有基線的測試套件只會整片紅，
而整片紅與沒有訊號是同一個下場。

判準：
  RED    = 有基線外的新失敗，或套件根本沒跑起來（通過數 < 500、JSON 失敗數與解析數不一致）
  YELLOW = 基線裡有已經轉綠的（該從基線移除；名冊會過期）
  GREEN  = 失敗集合 ⊆ 基線

--update：以本次結果重錄基線（同 weekly 24 的三道守衛：跑不起來不寫、0 失敗要 --force、對得上 JSON 摘要才寫）。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402

REPO = repo_root()  # 不自算路徑（weekly 93）：自算算錯是靜默的，會讀到別的檔
FRONTEND = REPO / "frontend"
BASELINE = FRONTEND / "tests" / "known_failures.json"
MIN_PASSED = 500  # 2,900 支測試不可能只過個位數 —— 那是沒跑起來，不是全壞


def run_suite(out: Path) -> dict:
    cmd = ["npx", "vitest", "run", "--reporter=json", f"--outputFile={out}"]
    subprocess.run(cmd, cwd=FRONTEND, shell=(os.name == "nt"), capture_output=True, timeout=45 * 60)
    if not out.exists():
        raise RuntimeError("vitest 沒有產出 JSON（多半是啟動即失敗）")
    return json.loads(out.read_text(encoding="utf-8"))


def failed_ids(report: dict) -> set[str]:
    ids: set[str] = set()
    for suite in report.get("testResults", []):
        rel = Path(suite["name"]).resolve().relative_to(FRONTEND).as_posix()
        if suite.get("status") == "failed" and not suite.get("assertionResults"):
            ids.add(f"{rel}::<suite-error>")
        for a in suite.get("assertionResults", []):
            if a.get("status") == "failed":
                ids.add(f"{rel}::{a.get('fullName')}")
    return ids


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true", help="以本次結果重錄基線")
    ap.add_argument("--force", action="store_true", help="允許把基線寫成 0 項")
    ap.add_argument("--report", help="用既有的 vitest JSON 報告，不重跑")
    args = ap.parse_args()

    print("=" * 66)
    print(" 前端測試套件健康檢核（vitest 全套，約 10 分鐘）")
    print("=" * 66)
    try:
        if args.report:
            report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        else:
            with tempfile.TemporaryDirectory() as td:
                report = run_suite(Path(td) / "vitest.json")
    except subprocess.TimeoutExpired:
        print("  ✗ RED：vitest 逾時未完成（>45 分鐘）")
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ RED：{e}")
        return 2

    failed = failed_ids(report)
    n_pass = int(report.get("numPassedTests") or 0)
    n_fail = int(report.get("numFailedTests") or 0)
    n_suite_fail = sum(1 for s in report.get("testResults", []) if s.get("status") == "failed" and not s.get("assertionResults"))
    print(f"  vitest: {n_pass} passed / {n_fail} failed / {report.get('numTotalTests')} total；檔案 {report.get('numFailedTestSuites')} failed")

    if n_pass < MIN_PASSED:
        print(f"  ✗ RED：只有 {n_pass} 支通過 —— 套件沒跑起來（不是「全壞了」）")
        return 2
    parsed_assertion_fails = len(failed) - n_suite_fail
    if parsed_assertion_fails != n_fail:
        print(f"  ✗ RED：JSON 說 {n_fail} failed，而解析到 {parsed_assertion_fails} 項 —— 解析與摘要不一致，不可信")
        return 2

    if args.update:
        prev_n = len(json.loads(BASELINE.read_text(encoding="utf-8")).get("known_failures", [])) if BASELINE.exists() else 0
        if prev_n and not failed and not args.force:
            print(f"  ✗ RED：基線原有 {prev_n} 項，本次 0 項 —— 不寫入（確定歸零請加 --force）")
            return 2
        BASELINE.write_text(json.dumps({"known_failures": sorted(failed)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  基線已更新：{len(failed)} 項 → {BASELINE.relative_to(REPO)}")
        return 0

    if not BASELINE.exists():
        print(f"  ✗ RED：找不到基線 {BASELINE.relative_to(REPO)}；首次請跑 --update")
        return 2
    known = set(json.loads(BASELINE.read_text(encoding="utf-8"))["known_failures"])
    new = sorted(failed - known)
    fixed = sorted(known - failed)
    if new:
        print(f"  ✗ RED：基線外新增 {len(new)} 項失敗：")
        for t in new[:30]:
            print(f"     - {t}")
        return 2
    if fixed:
        print(f"  ⚠ YELLOW：基線裡 {len(fixed)} 項已轉綠，請以 --update 重錄（名冊會過期）：")
        for t in fixed[:15]:
            print(f"     - {t}")
        return 1
    print(f"  ✓ GREEN：失敗 {len(failed)} 項全在基線內（存量待清，不是新問題）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pre-push：只跑「與這次推送有關」的測試，對基線比對（A46 的快速版）。

A46 原案是把全套 467 秒接進 pre-push，被擱置的理由是太慢、且會因別的 repo 服務掛掉而擋住本 repo。
這支換一個問法：**推送範圍改了哪些檔，就跑哪些測試**——
  後端：改到的測試檔本身＋`backend/app/**/<stem>.py` 對應的 `tests/**/test_<stem>*.py`；
  前端：改到的測試檔本身＋`src/**/<Stem>.tsx` 對應的 `__tests__/**/<Stem>*.test.tsx`。
再把結果對兩份基線（`backend/tests/known_failures.json`／`frontend/tests/known_failures.json`）：
只有**基線外的失敗**才擋推送。找不到相關測試就放行（放行不等於綠——那是「沒有測試蓋到」，會印出來）。

用法：prepush_related_tests.py [--range <rev-range>]（預設 origin/main..HEAD；hook 從 stdin 讀不到就用預設）
退出碼：0 放行／2 擋下／不可用時（git 不在、node 不在）印原因並放行，不假裝驗過。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402

REPO = repo_root()  # 不自算路徑（weekly 93）：自算算錯是靜默的，會讀到別的檔
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def changed_files(rng: str) -> list[str]:
    out = _git("diff", "--name-only", rng)
    if not out.strip():  # range 解不出來（新分支、遠端沒有）⇒ 退回最近一次提交
        out = _git("diff", "--name-only", "HEAD~1..HEAD")
    return [l.strip().replace("\\", "/") for l in out.splitlines() if l.strip()]


def backend_targets(files: list[str]) -> list[str]:
    tests: set[str] = set()
    test_root = BACKEND / "tests"
    for f in files:
        if not f.startswith("backend/") or not f.endswith(".py"):
            continue
        rel = f[len("backend/"):]
        if rel.startswith("tests/") and Path(rel).name.startswith("test_"):
            tests.add(rel)
            continue
        stem = Path(rel).stem
        if stem in {"__init__", "main"} or len(stem) < 4:
            continue
        for t in test_root.rglob(f"test_{stem}*.py"):
            tests.add(t.relative_to(BACKEND).as_posix())
        for t in test_root.rglob(f"test_*{stem}.py"):
            tests.add(t.relative_to(BACKEND).as_posix())
    return sorted(t for t in tests if (BACKEND / t).exists())


def frontend_targets(files: list[str]) -> list[str]:
    tests: set[str] = set()
    src = FRONTEND / "src"
    for f in files:
        if not f.startswith("frontend/src/") or not re.search(r"\.(tsx?|ts)$", f):
            continue
        rel = f[len("frontend/"):]
        if ".test." in rel:
            tests.add(rel)
            continue
        stem = Path(rel).name.split(".")[0]
        if stem in {"index", "types"} or len(stem) < 4:
            continue
        for t in src.rglob(f"{stem}*.test.ts*"):
            tests.add(t.relative_to(FRONTEND).as_posix())
    return sorted(t for t in tests if (FRONTEND / t).exists())


def _known(path: Path) -> set[str]:
    try:
        return set(json.loads(path.read_text(encoding="utf-8")).get("known_failures", []))
    except Exception:
        return set()


def run_backend(tests: list[str]) -> tuple[list[str], str]:
    proc = subprocess.run([sys.executable, "-m", "pytest", *tests, "-q", "--no-header", "-rfE", "-p", "no:cacheprovider"],
                          cwd=BACKEND, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    out = proc.stdout + proc.stderr
    failed = {l.split(" ")[1].strip() for l in out.splitlines() if l.startswith(("FAILED ", "ERROR ")) and "::" in l}
    new = sorted(failed - _known(BACKEND / "tests" / "known_failures.json"))
    summary = next((l for l in reversed(out.splitlines()) if re.search(r"\d+ (passed|failed|error)", l)), "(無摘要)")
    if "error" in summary.lower() and not failed:
        new.append("<collection-error>")
    return new, summary.strip()


def _vitest(tests: list[str], extra: list[str]) -> tuple[set[str], str]:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "vitest.json"
        subprocess.run(["npx", "vitest", "run", *tests, *extra, "--reporter=json", f"--outputFile={out}"],
                       cwd=FRONTEND, shell=(os.name == "nt"), capture_output=True, timeout=900)
        if not out.exists():
            return {"<vitest-did-not-run>"}, "vitest 沒有產出報告"
        rep = json.loads(out.read_text(encoding="utf-8"))
    failed: set[str] = set()
    for s in rep.get("testResults", []):
        rel = Path(s["name"]).resolve().relative_to(FRONTEND).as_posix()
        if s.get("status") == "failed" and not s.get("assertionResults"):
            failed.add(f"{rel}::<suite-error>")
        for a in s.get("assertionResults", []):
            if a.get("status") == "failed":
                failed.add(f"{rel}::{a.get('fullName')}")
    return failed, f"{rep.get('numPassedTests')} passed / {rep.get('numFailedTests')} failed"


def run_frontend(tests: list[str]) -> tuple[list[str], str]:
    known = _known(FRONTEND / "tests" / "known_failures.json")
    failed, summary = _vitest(tests, [])
    new = sorted(failed - known)
    if new and "<vitest-did-not-run>" not in new:
        # 2026-09-06 實測：AdminDashboardPage／PageRender 幾支「renders page title」多檔並行時紅、單檔跑綠
        # ⇒ 檔案間互相干擾（同 worker 的模組狀態）或並行負載下逾時。只擋「單獨跑也紅」的：
        # 把基線外失敗所在的檔案關掉檔案並行再跑一次，還紅才算數。
        files = sorted({t.split("::", 1)[0] for t in new})
        print(f"[pre-push] 前端基線外 {len(new)} 項，重跑其所在 {len(files)} 檔（--no-file-parallelism）確認不是並行干擾…")
        failed2, summary2 = _vitest(files, ["--no-file-parallelism"])
        still = sorted((failed2 - known) & set(new))
        flaky = sorted(set(new) - set(still))
        if flaky:
            print(f"[pre-push] ⚠ {len(flaky)} 項單跑即綠（多檔並行才紅）——不擋，但那是測試隔離問題，記在 A111：")
            for t in flaky[:10]:
                print("     ~", t)
        new = still
        summary = f"{summary}；複跑 {summary2}"
    return new, summary


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--range", default="origin/main..HEAD")
    ap.add_argument("--dry-run", action="store_true", help="只列相關測試，不跑")
    args = ap.parse_args()

    files = changed_files(args.range)
    be, fe = backend_targets(files), frontend_targets(files)
    print(f"[pre-push] 範圍 {args.range}：改了 {len(files)} 檔 → 後端相關測試 {len(be)} 檔、前端 {len(fe)} 檔")
    if not be and not fe:
        print("[pre-push] 沒有相關測試可跑（這不是綠燈，是沒有測試蓋到）——放行")
        return 0
    if args.dry_run:
        for t in be + fe:
            print("   ", t)
        return 0
    rc = 0
    if be:
        new, summary = run_backend(be)
        print(f"[pre-push] 後端 {summary}")
        if new:
            rc = 2
            print(f"[pre-push] ✗ 後端基線外失敗 {len(new)} 項：")
            for t in new[:20]:
                print("     -", t)
    if fe:
        new, summary = run_frontend(fe)
        print(f"[pre-push] 前端 {summary}")
        if new:
            rc = 2
            print(f"[pre-push] ✗ 前端基線外失敗 {len(new)} 項：")
            for t in new[:20]:
                print("     -", t)
    if rc:
        print("[pre-push] 擋下。修好或（確定是既有問題）加進對應的 known_failures.json 再推；緊急略過：git push --no-verify")
    else:
        print("[pre-push] ✓ 相關測試在基線內，放行")
    return rc


if __name__ == "__main__":
    sys.exit(main())

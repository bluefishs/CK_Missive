#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Fitness Function: cron 外部執行檔依賴「沉默跳過」護欄（fitness step 76）

為何存在（2026-07-30 立法，觸發事件）：
  `cf_tunnel_verify` cron 呼叫 `verify-cloudflare-tunnel.ps1`，但 5/27 廢 PM2 改純
  Docker 後 Linux 容器內沒有 pwsh/powershell；原碼寫

      pwsh = shutil.which("pwsh") or shutil.which("powershell")
      if not pwsh:
          logger.warning(...); return        # ← 沉默跳過

  → **cron 事件記 success，實際什麼都沒驗**，公網鏈路監控實質失效數月。
  同一天另外查出 zbar/tesseract/libGL 缺失使發票辨識三路全滅也是同一家族（L49）。

  這是「沉默成功」最典型的形狀：外部依賴不存在時選擇 return 而非 raise，
  於是 watchdog（cron_outcome_freshness / tracked_job）看到的是成功。

偵測反模式：
  在 `@tracked_job(...)` 修飾的函式內，出現「檢查外部執行檔存在性」
  （`shutil.which(...)` / `Path(...).exists()` 對 script 路徑）後，
  該 not-found 分支**沒有 raise**（只 log + return / pass）。

正確作法（任一）：
  1. `raise RuntimeError(...)`／`FileNotFoundError(...)` — 讓 tracked_job 記 failure，
     watchdog 才抓得到（既有 fitness_daily / synthetic_baseline 等已如此）。
  2. 改用不依賴外部執行檔的原生實作（cf_tunnel_verify 已於 2026-07-30 改 httpx）。

baseline（2026-07-30 修後）：0 violation。新增任一 → RED（--ci exit 1）。
負向測試：把 cf_tunnel_verify 的舊版（logger.warning + return）貼回即會標紅。

對齊 lesson「防護腳本存在 ≠ 生效」：本檔須掛 run_fitness.sh（step 76）才算啟用。
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# Windows cp950 防護（L49.8 同族）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
TARGETS = [
    ROOT / "backend" / "app" / "core" / "scheduler.py",
]

# 「檢查外部執行檔/腳本是否存在」的訊號
BINARY_PROBE_SIGNALS = ("shutil.which", "which(")


def _is_tracked_job(node: ast.AST) -> bool:
    """函式是否被 @tracked_job(...) 修飾（＝會被 cron watchdog 記成功/失敗）。"""
    for dec in getattr(node, "decorator_list", []):
        src = ast.unparse(dec)
        if "tracked_job" in src:
            return True
    return False


def _branch_has_raise(node: ast.AST) -> bool:
    return any(isinstance(n, ast.Raise) for n in ast.walk(node))


def _branch_returns(node: ast.AST) -> bool:
    return any(isinstance(n, ast.Return) for n in ast.walk(node))


def audit_file(path: Path) -> list[tuple[str, int, str]]:
    """回傳 [(job_name, lineno, 摘要)]"""
    violations: list[tuple[str, int, str]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"⚠️  無法解析 {path}: {e}")
        return violations

    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _is_tracked_job(fn):
            continue

        # 該 job 內是否有「探測外部執行檔」
        body_src = ast.unparse(fn)
        if not any(sig in body_src for sig in BINARY_PROBE_SIGNALS):
            continue

        # 找所有 if 分支：若分支內 return 但沒有 raise → 沉默跳過
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            cond = ast.unparse(node.test)
            # 只看「找不到就處理」的分支（not X / X is None / not X.exists()）
            if not (cond.startswith("not ") or "is None" in cond):
                continue
            body_block = ast.Module(body=node.body, type_ignores=[])
            if _branch_returns(body_block) and not _branch_has_raise(body_block):
                violations.append((fn.name, node.lineno, f"if {cond}: → return（無 raise）"))
    return violations


def main(ci: bool) -> int:
    print("=== cron 外部執行檔依賴「沉默跳過」護欄 ===")
    all_v: list[tuple[Path, str, int, str]] = []
    checked = 0
    for p in TARGETS:
        if not p.exists():
            continue
        checked += 1
        for job, line, desc in audit_file(p):
            all_v.append((p, job, line, desc))

    print(f"檢查檔案: {checked}")
    if not all_v:
        print("✅ GREEN — 無 cron 在外部執行檔缺失時沉默跳過")
        return 0

    print(f"🔴 RED — {len(all_v)} 處 cron 依賴外部執行檔卻沉默跳過:")
    for p, job, line, desc in all_v:
        print(f"  - {p.relative_to(ROOT).as_posix()}:{line} job={job}  {desc}")
    print()
    print("修法：改 raise（讓 tracked_job 記 failure、watchdog 抓得到），")
    print("      或改用不依賴外部執行檔的原生實作（如 httpx 直呼）。")
    return 1 if ci else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ci", action="store_true", help="有違規時 exit 1")
    sys.exit(main(ap.parse_args().ci))

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 33 — React Query queryKey Drift Audit (L39)

防範 silent dead invalidate — invalidate 寫 key A，但 useQuery 用 key B，A≠B。

觸發事件：v6.10.1 (2026-05-20) 揭發
  - dispatch 158「公文 2 筆」chronic bug：5/18 第一次修 invalidate ['dispatch-orders']
    完全 silent dead — 真實 useQuery 用 queryKeys.taoyuanDispatch.orders() =
    ['taoyuan-dispatch-orders', ...]
  - 同型反模式 L39 + L29 (dict-key contract drift) + L28 (JSON-as-TEXT schema drift)
  - audit 揭發 12 個 silent dead invalidate（admin-users / adminUsers 等）

Detection 邏輯（按 first token prefix 比對）：
  1. 全 frontend/src/**/*.{ts,tsx} 抽 `invalidateQueries({ queryKey: ['xxx', ...] })` first token
  2. 抽 `useQuery({ queryKey: ['xxx', ...] })` first token
  3. queryConfig.ts 內定義的 SSOT prefix tokens
  4. invalidate first token NOT IN (useQuery tokens ∪ SSOT tokens) → silent dead

Exit codes:
  0 — current dead ≤ baseline
  1 — --ci strict mode 且 current > baseline (淨增加)

Usage:
  python scripts/checks/queryKey_drift_audit.py
  python scripts/checks/queryKey_drift_audit.py --ci
  python scripts/checks/queryKey_drift_audit.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# v6.13 (2026-05-31) L52 family 第 8 案修法:
# container 內 /app/frontend/src 不 mount (host-side only 設計)
# 修法: 若不存在，graceful skip exit 0 (不算 fail)
FRONTEND_SRC = PROJECT_ROOT / "frontend" / "src"
BASELINE_FILE = PROJECT_ROOT / "scripts" / "checks" / "queryKey_drift_baseline.json"

INVALIDATE_RE = re.compile(
    r"invalidateQueries\(\s*\{\s*queryKey:\s*\[\s*['\"]([\w\-]+)['\"]"
)
# v6.10.2 (2026-05-20) audit 自身修法：支援 useQuery<TypeParam>(...) 泛型格式
# 起因：5/20 揭發 mfa-status / profile / wiki-* 等 6 token 被誤標 dead，
#       實際對應 useQuery 用了 useQuery<MFAStatus>({...}) 泛型 — 原 regex 漏掃
USEQUERY_RE = re.compile(
    r"useQuery\s*(?:<[^>]+>)?\s*\(\s*\{\s*queryKey:\s*\[\s*['\"]([\w\-]+)['\"]"
)
SSOT_TOKEN_RE = re.compile(r"\[\s*['\"]([\w\-]+)['\"]")


def scan_frontend() -> Tuple[Dict[str, List[str]], Set[str], Set[str]]:
    """Returns (invalidate_tokens, useQuery_tokens, SSOT_tokens)."""
    inv_tokens: Dict[str, List[str]] = {}
    uq_tokens: Set[str] = set()

    if not FRONTEND_SRC.exists():
        # v6.13 (2026-05-31): container 內 frontend/src 未 mount 是設計 (host-side only)
        # 改 INFO 不算 fail，避免 fitness 假 ERROR
        print(f"[INFO] frontend/src not present (container env, host-side audit only): {FRONTEND_SRC}",
              file=sys.stderr)
        return inv_tokens, uq_tokens, set()

    for path in FRONTEND_SRC.rglob("*.ts"):
        if "node_modules" in str(path) or ".test." in path.name:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        for tok in INVALIDATE_RE.findall(content):
            inv_tokens.setdefault(tok, []).append(rel)
        for tok in USEQUERY_RE.findall(content):
            uq_tokens.add(tok)

    for path in FRONTEND_SRC.rglob("*.tsx"):
        if "node_modules" in str(path) or ".test." in path.name:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        for tok in INVALIDATE_RE.findall(content):
            inv_tokens.setdefault(tok, []).append(rel)
        for tok in USEQUERY_RE.findall(content):
            uq_tokens.add(tok)

    # SSOT — queryConfig.ts
    ssot_tokens: Set[str] = set()
    ssot_path = FRONTEND_SRC / "config" / "queryConfig.ts"
    if ssot_path.exists():
        try:
            qcontent = ssot_path.read_text(encoding="utf-8")
            ssot_tokens = set(SSOT_TOKEN_RE.findall(qcontent))
        except (OSError, UnicodeDecodeError):
            pass

    return inv_tokens, uq_tokens, ssot_tokens


def load_baseline() -> Dict:
    """Load baseline; first run → empty (default total=0)."""
    if not BASELINE_FILE.exists():
        return {"total_baseline": 0, "dead_tokens": []}
    try:
        with open(BASELINE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[WARN] baseline load failed: {exc}", file=sys.stderr)
        return {"total_baseline": 0, "dead_tokens": []}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fitness step 33 — React Query queryKey Drift Audit (L39)"
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="baseline-aware strict: current dead > baseline 即 exit 1（修一個減一個，禁淨增）",
    )
    parser.add_argument("--json", action="store_true", help="JSON 輸出")
    args = parser.parse_args()

    inv_tokens, uq_tokens, ssot_tokens = scan_frontend()
    real_query_tokens = uq_tokens | ssot_tokens
    dead = sorted(set(inv_tokens.keys()) - real_query_tokens)
    current_total = len(dead)

    baseline = load_baseline()
    baseline_total = baseline.get("total_baseline", 0)

    if args.json:
        report = {
            "invalidate_tokens_total": len(inv_tokens),
            "useQuery_tokens_total": len(uq_tokens),
            "ssot_tokens_total": len(ssot_tokens),
            "current_dead_total": current_total,
            "baseline_total": baseline_total,
            "dead_tokens": [
                {"token": t, "callers": inv_tokens[t][:3]} for t in dead
            ],
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if args.ci and current_total > baseline_total:
            return 1
        return 0

    # human format
    print("=" * 60)
    print("React Query queryKey Drift Audit (L39)")
    print(f"v6.10.1 / detect silent dead invalidate")
    print("=" * 60)
    print()
    print(f"  invalidate tokens: {len(inv_tokens)}")
    print(f"  useQuery tokens: {len(uq_tokens)}")
    print(f"  SSOT tokens: {len(ssot_tokens)}")
    print(f"  current dead invalidate: {current_total}")
    print(f"  baseline: {baseline_total}")
    print()

    if dead:
        print("-" * 60)
        print(f"SILENT DEAD invalidate tokens ({len(dead)}):")
        print("-" * 60)
        for tok in dead:
            callers = inv_tokens[tok][:3]
            print(f"  [X] [{tok}]")
            for c in callers:
                print(f"      <- {c}")
        print()
        print("Fix guidance:")
        print("  1. 找出 invalidate 想 invalidate 的真實 useQuery key")
        print("  2. 改 invalidate 用 queryKeys.<module>.<entity> SSOT")
        print("  3. 禁止散戶手寫 queryKey 字串陣列（如 ['xxx']）")
        print("  4. 修一個減一個，請更新 queryKey_drift_baseline.json")

    # CI enforce
    if args.ci:
        if current_total > baseline_total:
            print(
                f"\n[FAIL] dead invalidate 淨增加: {baseline_total} → {current_total} "
                f"(+{current_total - baseline_total})",
                file=sys.stderr,
            )
            return 1
        elif current_total < baseline_total:
            print(
                f"\n[INFO] dead invalidate 改善: {baseline_total} → {current_total} "
                f"(-{baseline_total - current_total}) — 請更新 baseline 鎖定改善"
            )
        else:
            print(f"\n[PASS] dead invalidate 持平 baseline {baseline_total}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

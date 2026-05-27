#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 21 — Alias RLS Coverage Audit (R4a, v6.9 / 2026-05-09).

靜態掃描 endpoints/，找出疑似有 user-scoped SQL filter 但**未** import
expand_user_alias / RLSFilter 的檔案。產出風險清單供 owner 評估是否漏覆蓋。

與 step 17 alias_rls_e2e_check 互補：
  - step 17：跑 DB 驗證 PUA 雙向展開（runtime check）
  - step 21：靜態掃描 SQL pattern（compile-time audit）

防 ADR-0025 半接通類事故 — 13 天 dormant 的根因之一是「endpoint 寫了 user_id ==
filter 但沒展開 alias group」，runtime 沒人觸發就無法察覺。靜態 audit 補這個
gap：任何 user filter 都該明確標示「已用 RLSFilter / expand_user_alias 包」或
「不需 RLS（admin endpoint）」。

Exit codes:
  0 — 無風險檔案 / strict 未觸發
  1 — strict mode (--ci) 且發現高風險未覆蓋的 user filter

Usage:
  python scripts/checks/alias_rls_coverage_audit.py
  python scripts/checks/alias_rls_coverage_audit.py --ci
  python scripts/checks/alias_rls_coverage_audit.py --json  # JSON 輸出供其他工具消費
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENDPOINTS_DIR = PROJECT_ROOT / "backend" / "app" / "api" / "endpoints"
# v6.10 P0-2: 同步掃 repository 與 service 層（解 detection 層級錯位）
REPOSITORIES_DIR = PROJECT_ROOT / "backend" / "app" / "repositories"
SERVICES_DIR = PROJECT_ROOT / "backend" / "app" / "services"

# user-scoped SQL filter patterns that imply RLS concern
# v6.10 P0-2 (2026-05-18): 擴大偵測範圍以解 detection coverage = 0% false-GREEN
# 原 v6.9 規則只匹配 endpoint 內直寫 `.user_id == current_user.X`，但實際 code
# 都先抽變數（uid = current_user.id）再傳給 service / repository → 0 命中。
# 新規則加入「變數型 user filter」+ Repository 層裸 user_id 比對。
_USER_FILTER_PATTERNS = [
    # ORM 直接比對 current_user / user 物件
    (r"\.user_id\s*==\s*(?:current_user|user)\.", "ORM user_id == current_user"),
    (r"\.created_by\s*==\s*(?:current_user|user)\.", "ORM created_by == current_user"),
    (r"\.assignee_id\s*==\s*(?:current_user|user)\.", "ORM assignee_id == current_user"),
    # ORM 變數比對（取出 uid/user_id 再傳）— P0-2 新增
    (r"\.user_id\s*==\s*(?:uid|user_id|current_uid|requester_id)\b", "ORM user_id == uid/var"),
    (r"\.created_by\s*==\s*(?:uid|user_id|current_uid|requester_id)\b", "ORM created_by == uid/var"),
    (r"\.assignee_id\s*==\s*(?:uid|user_id|current_uid|requester_id)\b", "ORM assignee_id == uid/var"),
    # 函數參數 user_id: int / user_id: UUID — 高度暗示有 user filter
    (r"def\s+\w+\([^)]*\buser_id\s*:\s*(?:int|UUID|str)", "func param user_id"),
    # Raw SQL where user_id =
    (r"WHERE\s+\w*user_id\s*=\s*:(?:current_user|user_id|uid)", "raw SQL user_id ="),
    # SQLAlchemy filter() / filter_by() 形式
    (r"\.filter_by\([^)]*user_id\s*=", "filter_by user_id"),
    (r"\.where\([^)]*user_id\s*==\s*", "select.where user_id =="),
]

# Tokens indicating proper RLS handling
# P0-A (2026-05-19): 加入 v6.10 P1 contracts 模組 token，認 RLSPort/DefaultRLSAdapter
# 為 RLS 真活 — calendar_repository.py 是 RLSPort 首個真 caller
_RLS_OK_TOKENS = [
    "expand_user_alias",
    "RLSFilter",
    "rls_filter",
    "apply_document_rls",
    "rls_canonical_id",
    # v6.10 P1 contracts layer（ADR-0036）
    "RLSPort",
    "DefaultRLSAdapter",
    "_alias_user_filter",
]

# Endpoints expected to be admin-only (no per-user RLS needed)
_ADMIN_ENDPOINT_HINTS = [
    "require_admin",
    "admin_only",
    "is_admin",
    "is_superuser",
]

# Files explicitly opted out of audit (reviewed manually)
_AUDIT_OPTOUT_FILES = {
    "auth/oauth.py",  # auth/login flow doesn't filter by user
    "auth/login_history.py",  # admin reviews all
    "debug.py",  # require_admin gated
    "health.py",  # no user filter
}


def _scan_file(path: Path) -> Dict:
    """Return audit result for a single endpoint file."""
    rel = path.relative_to(ENDPOINTS_DIR).as_posix()
    if rel in _AUDIT_OPTOUT_FILES:
        return {
            "file": rel,
            "status": "opt_out",
            "matches": [],
        }

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {"file": rel, "status": "unreadable", "matches": []}

    matches: List[Dict] = []
    for pattern, label in _USER_FILTER_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            line_no = text[: m.start()].count("\n") + 1
            matches.append({
                "pattern": label,
                "line": line_no,
                "snippet": text[max(0, m.start() - 30): m.end() + 30].replace("\n", "\\n"),
            })

    if not matches:
        return {"file": rel, "status": "no_user_filter", "matches": []}

    has_rls_token = any(token in text for token in _RLS_OK_TOKENS)
    has_admin_token = any(token in text for token in _ADMIN_ENDPOINT_HINTS)

    if has_rls_token:
        status = "ok_with_rls"
    elif has_admin_token:
        status = "ok_admin_only"
    else:
        status = "risk_unaudited"  # 真正的風險：有 user filter 但無 RLS / admin 標記

    return {
        "file": rel,
        "status": status,
        "matches": matches,
    }


def _walk_endpoints() -> List[Dict]:
    """Walk endpoints/ recursively and audit every .py."""
    results = []
    for path in sorted(ENDPOINTS_DIR.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        result = _scan_file(path)
        result["layer"] = "endpoint"
        results.append(result)
    return results


def _walk_repositories_and_services() -> List[Dict]:
    """v6.10 P0-2: 擴大 audit 到 repository + service 層。

    破口 2 根因：endpoint 都把 user_id 抽變數後傳到 service / repo 層，
    audit 只掃 endpoint 永遠 0 risks（false-GREEN）。實際裸 user_id ==
    比對發生在 repository 層（calendar/notification/ERP）。
    """
    results = []
    for base_dir, layer_name in ((REPOSITORIES_DIR, "repository"), (SERVICES_DIR, "service")):
        if not base_dir.exists():
            continue
        for path in sorted(base_dir.rglob("*.py")):
            if path.name in ("__init__.py", "base_repository.py"):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            matches: List[Dict] = []
            for pattern, label in _USER_FILTER_PATTERNS:
                for m in re.finditer(pattern, text, re.IGNORECASE):
                    line_no = text[: m.start()].count("\n") + 1
                    matches.append({
                        "pattern": label,
                        "line": line_no,
                        "snippet": text[max(0, m.start() - 20): m.end() + 30].replace("\n", "\\n"),
                    })
            if not matches:
                continue  # 沒 user filter 跳過
            has_rls = any(t in text for t in _RLS_OK_TOKENS)
            status = "ok_with_rls" if has_rls else "risk_unaudited"
            results.append({
                "file": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "layer": layer_name,
                "status": status,
                "matches": matches,
            })
    return results


def _format_human(results: List[Dict]) -> str:
    risks = [r for r in results if r["status"] == "risk_unaudited"]
    ok_rls = [r for r in results if r["status"] == "ok_with_rls"]
    ok_admin = [r for r in results if r["status"] == "ok_admin_only"]
    no_filter = [r for r in results if r["status"] == "no_user_filter"]
    opt_out = [r for r in results if r["status"] == "opt_out"]

    # v6.10 P0-2: 加 layer 分布 + detection coverage 指標（避免 false-GREEN）
    layer_counts: Dict[str, Dict[str, int]] = {}
    for r in results:
        layer = r.get("layer", "unknown")
        layer_counts.setdefault(layer, {"total": 0, "risks": 0, "ok": 0})
        layer_counts[layer]["total"] += 1
        if r["status"] == "risk_unaudited":
            layer_counts[layer]["risks"] += 1
        elif r["status"] == "ok_with_rls":
            layer_counts[layer]["ok"] += 1

    total_user_filter_files = len(ok_rls) + len(ok_admin) + len(risks)
    coverage_pct = (
        (len(ok_rls) + len(ok_admin)) / total_user_filter_files * 100
        if total_user_filter_files else 0.0
    )

    out = []
    out.append("=" * 60)
    out.append(f"Alias RLS Coverage Audit — sample size: {len(results)} files")
    out.append("v6.10 P0-2: 已擴大偵測到 repository + service 層 + 變數比對")
    out.append("=" * 60)
    out.append("")
    out.append(f"  ✅ Has RLS handling:      {len(ok_rls)}")
    out.append(f"  🛡 Admin-gated:           {len(ok_admin)}")
    out.append(f"  📭 No user filter:         {len(no_filter)}")
    out.append(f"  ➖ Opted out:              {len(opt_out)}")
    out.append(f"  ⚠️  Risk (unaudited):       {len(risks)}")
    out.append("")
    out.append(f"  📊 Detection coverage:    {total_user_filter_files} files with user filter")
    out.append(f"  📊 RLS coverage rate:     {coverage_pct:.1f}% ({len(ok_rls) + len(ok_admin)}/{total_user_filter_files})")
    out.append("")
    out.append("  By layer:")
    for layer, c in sorted(layer_counts.items()):
        out.append(f"     {layer:<12} total={c['total']:<4} ok={c['ok']:<4} risks={c['risks']}")
    out.append("")

    if risks:
        out.append("─" * 60)
        out.append("⚠️  Risk files (有 user filter 但無 RLS / admin 標記):")
        out.append("─" * 60)
        for r in risks:
            out.append(f"\n  📁 {r['file']}")
            for m in r["matches"][:3]:  # show first 3 matches
                out.append(f"     L{m['line']:4} | {m['pattern']}")
                out.append(f"          ...{m['snippet']}...")
        out.append("")
        out.append("修法建議：")
        out.append("  1. 若該 endpoint 應為 admin-only → 加 `require_admin()` dependency")
        out.append("  2. 若該 endpoint 應對 alias group 透明 → 用 RLSFilter / expand_user_alias")
        out.append("  3. 若 user filter 是其他語意（如 author, owner）→ 加 noqa 註解 + 註明")

    return "\n".join(out)


def _load_baseline() -> Dict[str, int]:
    """P0-E (2026-05-19) 讀取 baseline 鎖；不存在則回傳全 0（首跑安全）"""
    baseline_file = PROJECT_ROOT / "scripts" / "checks" / "alias_rls_baseline.json"
    if not baseline_file.exists():
        return {"total_baseline": 0}
    try:
        with open(baseline_file, encoding="utf-8") as f:
            data = json.load(f)
        b = data.get("baselines", {})
        return {
            "endpoint": b.get("endpoint", 0),
            "repository": b.get("repository", 0),
            "service": b.get("service", 0),
            "total_baseline": data.get("total_baseline", sum(b.values())),
        }
    except Exception as exc:
        print(f"[WARN] baseline 載入失敗，視同 0：{exc}", file=sys.stderr)
        return {"total_baseline": 0}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fitness step 21 — Alias RLS Coverage Audit (R4a)"
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="baseline-aware strict mode：current risks > baseline 才 exit 1（修一個減一個，禁淨增）",
    )
    parser.add_argument(
        "--strict-zero",
        action="store_true",
        help="(legacy) 任何 risk 即 exit 1 — 過嚴，僅供 v7.0 target ≤ 5 後啟用",
    )
    parser.add_argument("--json", action="store_true", help="JSON 輸出（供工具消費）")
    args = parser.parse_args()

    if not ENDPOINTS_DIR.exists():
        print(f"[ERROR] endpoints/ 不存在: {ENDPOINTS_DIR}", file=sys.stderr)
        return 1

    results = _walk_endpoints()
    # v6.10 P0-2: 同步掃 repository + service 層補上 detection 層級錯位
    results.extend(_walk_repositories_and_services())

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(_format_human(results))

    risks = [r for r in results if r["status"] == "risk_unaudited"]
    current_total = len(risks)

    # P0-E (2026-05-19): baseline-aware enforce — 防 silent 累積
    if args.ci:
        baseline = _load_baseline()
        baseline_total = baseline["total_baseline"]
        print(f"\n[baseline-lock] current={current_total} baseline={baseline_total}", file=sys.stderr)
        if current_total > baseline_total:
            print(
                f"[FAIL] alias_rls risks 淨增加：{baseline_total} → {current_total} "
                f"(+{current_total - baseline_total})\n"
                f"  修法：(a) 修 1 處 risk 即可同步降 baseline；"
                f"(b) 真新 user filter 必須先補 RLSFilter/expand_user_alias；"
                f"(c) 不可繞過 — 任何「我會晚點修」都會變 ADR-0025 第三次 dormant",
                file=sys.stderr,
            )
            return 1
        elif current_total < baseline_total:
            print(
                f"[INFO] alias_rls risks 改善：{baseline_total} → {current_total} "
                f"(-{baseline_total - current_total}) — 請更新 alias_rls_baseline.json",
                file=sys.stderr,
            )
        else:
            print(f"[PASS] alias_rls risks 持平 baseline {baseline_total}", file=sys.stderr)
        return 0

    # legacy: strict-zero mode
    if args.strict_zero and risks:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

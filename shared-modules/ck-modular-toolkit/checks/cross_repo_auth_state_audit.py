#!/usr/bin/env python3
"""cross_repo_auth_state_audit.py — fitness step 42 (L44 配套)

偵測跨 repo SSO frontend authentication state drift（L44 family）。

L44 事故觸發（2026-05-22）：
- ck-sso-js v1.0 內有 sessionStorage-permanent lock 邏輯
- 第一次 SSO 認證後寫 sessionStorage flag → 後續永久跳過 verify
- 跨 subdomain 切換時 cookie 不同 → 但 sessionStorage flag 仍存在
- → owner 切到 lvrland.cksurvey.tw 認證失敗（sessionStorage 來自 missive 但 cookie 是 lvrland）
- 修法 commit `bb1ca4ec`：v2.0 移除 session-permanent lock

判定邏輯：
1. 找所有 CK_* repos 內的 `ck-sso-js/sso-bridge.ts`（含 shared-modules + 各 repo 本地副本）
2. 比對 md5 雜湊 — 若不一致 = drift（owner 沒走範本同步流程）
3. 額外掃 onSuccess 模式：應用 `location.replace('/dashboard')` 而非 `location.reload()`
4. drift → RED；onSuccess 反模式 → YELLOW

Usage:
    python scripts/checks/cross_repo_auth_state_audit.py [--strict]

Exit codes:
    0 = green (no drift, no anti-pattern)
    1 = yellow (anti-pattern warnings only)
    2 = red (drift detected; --strict 時也會 exit 2)
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

# SSOT location for ck-sso-js
SSOT_PATH_RELATIVE = "shared-modules/ck-sso-js/src/sso-bridge.ts"

# 探測 CK_* repos 的父目錄
def _find_repos(start: Path) -> list[Path]:
    """Find CK_* repos starting from CK_Missive's parent."""
    parent = start.resolve().parent
    return sorted([
        p for p in parent.iterdir()
        if p.is_dir() and p.name.startswith(("CK_", "hermes"))
    ])


def _file_hash(path: Path) -> str:
    """Return md5 hash of file content."""
    if not path.exists() or not path.is_file():
        return ""
    return hashlib.md5(path.read_bytes()).hexdigest()


def _find_sso_bridge_in_repo(repo: Path) -> list[Path]:
    """Find all sso-bridge.ts files in a repo (SSOT + consumer copies)."""
    paths = []
    # SSOT
    ssot = repo / "shared-modules" / "ck-sso-js" / "src" / "sso-bridge.ts"
    if ssot.exists():
        paths.append(ssot)
    # consumer copies
    for candidate in [
        repo / "frontend" / "src" / "lib" / "ck-sso-js" / "sso-bridge.ts",
        repo / "frontend" / "src" / "lib" / "ck-sso" / "sso-bridge.ts",
    ]:
        if candidate.exists():
            paths.append(candidate)
    return paths


def _scan_onsuccess_patterns(file: Path) -> list[str]:
    """Detect onSuccess anti-patterns in a frontend login page."""
    patterns_bad = [
        re.compile(r"location\.reload\(\)"),                # L44: reload 不切 URL
        re.compile(r"window\.location\.href\s*=\s*['\"]/"),  # 應該用 location.replace 強制
    ]
    findings = []
    try:
        text = file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings
    for p in patterns_bad:
        for m in p.finditer(text):
            ln = text.count("\n", 0, m.start()) + 1
            findings.append(f"line {ln}: {m.group(0)}")
    return findings


def main() -> int:
    # Force UTF-8 stdout for Windows cp950 console
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit 2 on any warning")
    args = parser.parse_args()

    print("=" * 60)
    print("cross-repo SSO auth state SSOT audit (L44 配套)")
    print("v1.0 / detect ck-sso-js drift + onSuccess anti-pattern")
    print("=" * 60)

    repo_root = Path(__file__).resolve().parent.parent.parent
    repos = _find_repos(repo_root)

    if not repos:
        print("  no CK_* repos found")
        return 0

    # 1. Collect hash matrix
    matrix: dict[Path, str] = {}
    repo_to_files: dict[str, list[Path]] = defaultdict(list)
    for repo in repos:
        files = _find_sso_bridge_in_repo(repo)
        for f in files:
            matrix[f] = _file_hash(f)
            repo_to_files[repo.name].append(f)

    if not matrix:
        print("  no sso-bridge.ts found in any repo")
        return 0

    # 2. Drift analysis
    unique_hashes = set(matrix.values())
    drift = len(unique_hashes) > 1

    print(f"\n  repos with sso-bridge: {len([r for r, fs in repo_to_files.items() if fs])}")
    print(f"  total files:           {len(matrix)}")
    print(f"  unique md5:            {len(unique_hashes)}\n")

    if drift:
        print("  🔴 ck-sso-js DRIFT detected:")
        for f, h in sorted(matrix.items()):
            rel = f.relative_to(repo_root.parent)
            print(f"    {h[:8]}  {rel}")
        print("\n  → 不同的 md5 表示 owner 沒走範本同步流程（shared-modules → consumer copy）")
    else:
        h = next(iter(unique_hashes))
        print(f"  🟢 ck-sso-js aligned across all {len(matrix)} file(s) (md5={h[:8]})")

    # 3. onSuccess anti-pattern scan
    anti_patterns: dict[str, list[str]] = {}
    for repo in repos:
        login_page = repo / "frontend" / "src" / "pages" / "LoginPage.tsx"
        if login_page.exists():
            findings = _scan_onsuccess_patterns(login_page)
            if findings:
                anti_patterns[repo.name] = findings

    print()
    if anti_patterns:
        print(f"  🟡 onSuccess anti-patterns found in {len(anti_patterns)} repo(s):")
        for repo_name, findings in sorted(anti_patterns.items()):
            print(f"    {repo_name}:")
            for f in findings:
                print(f"      {f}")
        print("\n  💡 修法：onSuccess 應用 location.replace('/dashboard')")
        print("       避免 history stack 累積 + 強制重 mount Router")
    else:
        print(f"  🟢 no onSuccess anti-pattern in any LoginPage.tsx")

    if drift:
        print("\n💡 修法建議：")
        print("  1. 確定 shared-modules/ck-sso-js/src/sso-bridge.ts 為 SSOT")
        print("  2. 用 install.sh 重新同步各 consumer repo 的 lib/ck-sso-js/")
        print("  3. 或考慮改用 npm workspace / yarn link 取代 file copy")
        print("  4. 修法後重跑本 audit 應 GREEN")

    if drift:
        return 2
    if anti_patterns and args.strict:
        return 2
    if anti_patterns:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

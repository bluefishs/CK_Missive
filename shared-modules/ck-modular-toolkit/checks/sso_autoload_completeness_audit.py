#!/usr/bin/env python3
"""sso_autoload_completeness_audit.py — fitness step 46

驗證 consumer repo frontend SSO autoload 完整接通（next_session_resume #7）。

風險背景：
- 過去 frontend SSO 接通需手寫 ~50 行 boilerplate（attemptSSOBridge + state mgmt）
- shared-modules/ck-sso-js v1.1 已提供 useSSOBridge React hook 統一接口
- 但 consumer repo 可能漏配（沒裝 ck-sso-js / 沒用 hook / .env 缺 VITE_API_BASE_URL）
- 結果：SSO 看似配置但實際 silent fail（cookie 帶到但 frontend 不 verify）

判定邏輯（per consumer repo）：
1. 該 repo 有 frontend/src/lib/ck-sso-js/ 副本？
2. 該 repo 的 LoginPage.tsx（或入口頁）使用 useSSOBridge / attemptSSOBridge？
3. 該 repo 的 .env.example 宣告 VITE_API_BASE_URL？
4. 該 repo 的 .env.example 宣告 VITE_CK_SSO_ENABLED 或同等？

CONSUMER_REPOS（hardcoded list）：
- CK_lvrland_Webmap
- CK_PileMgmt

(CK_Missive 是 source repo，不算 consumer)
(CK_Website 是 SSO origin，不算 consumer)

Usage:
    python scripts/checks/sso_autoload_completeness_audit.py [--strict]

Exit codes:
    0 = green (all consumers complete)
    1 = yellow (some optional check missing)
    2 = red (critical: missing ck-sso-js or hook usage)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Consumer repos that should use ck-sso-js
CONSUMER_REPOS = [
    "CK_lvrland_Webmap",
    "CK_PileMgmt",
]

# Required checks
CHECKS = {
    "lib_present": "frontend/src/lib/ck-sso-js/sso-bridge.ts exists",
    "hook_used": "LoginPage uses useSSOBridge or attemptSSOBridge",
    "env_api_base": ".env.example declares VITE_API_BASE_URL",
    "env_sso_enabled": ".env.example declares CK_SSO_ENABLED or VITE_CK_SSO_ENABLED",
}


def _find_repo(parent: Path, name: str) -> Path | None:
    p = parent / name
    return p if p.exists() and p.is_dir() else None


def _check_lib_present(repo: Path) -> bool:
    candidates = [
        repo / "frontend" / "src" / "lib" / "ck-sso-js" / "sso-bridge.ts",
        repo / "frontend" / "src" / "lib" / "ck-sso" / "sso-bridge.ts",
    ]
    return any(c.exists() for c in candidates)


def _check_hook_used(repo: Path) -> bool:
    login_pages = list((repo / "frontend" / "src" / "pages").glob("Login*.tsx"))
    if not login_pages:
        return False
    patterns = [
        re.compile(r"\buseSSOBridge\b"),
        re.compile(r"\battemptSSOBridge\b"),
    ]
    for page in login_pages:
        try:
            text = page.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if any(p.search(text) for p in patterns):
            return True
    return False


def _check_env_var(repo: Path, var_patterns: list[str]) -> bool:
    env_files = [
        repo / ".env.example",
        repo / ".env.production.example",
        repo / "frontend" / ".env.example",
    ]
    for env_file in env_files:
        if not env_file.exists():
            continue
        try:
            text = env_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in var_patterns:
            if re.search(rf"^{pat}\s*=", text, re.MULTILINE):
                return True
    return False


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
    print("SSO autoload completeness audit (8 根因 #7)")
    print("v1.0 / verify consumer repos complete ck-sso-js integration")
    print("=" * 60)

    parent = REPO_ROOT.resolve().parent
    print(f"\n  consumer repos: {len(CONSUMER_REPOS)}\n")

    total_failures = 0
    severity = "GREEN"

    for repo_name in CONSUMER_REPOS:
        repo = _find_repo(parent, repo_name)
        if not repo:
            print(f"  ⚪ {repo_name}: repo not found, skipping")
            continue

        print(f"  Repo: {repo_name}")

        results = {
            "lib_present": _check_lib_present(repo),
            "hook_used": _check_hook_used(repo),
            "env_api_base": _check_env_var(repo, [
                r"VITE_API_BASE_URL", r"VITE_API_URL", r"REACT_APP_API_URL"
            ]),
            "env_sso_enabled": _check_env_var(repo, [
                r"CK_SSO_ENABLED", r"VITE_CK_SSO_ENABLED"
            ]),
        }

        for check_id, passed in results.items():
            indicator = "🟢" if passed else "🔴"
            desc = CHECKS[check_id]
            print(f"    {indicator} {desc}")

        # Severity
        critical_fail = not results["lib_present"] or not results["hook_used"]
        optional_fail = not results["env_api_base"] or not results["env_sso_enabled"]

        if critical_fail:
            severity = "RED"
            total_failures += 1
        elif optional_fail:
            if severity == "GREEN":
                severity = "YELLOW"

        print()

    print(f"  Final severity: {severity}")
    print(f"  Critical failures: {total_failures}/{len(CONSUMER_REPOS)}")

    if severity == "RED":
        print("\n💡 修法建議：")
        print("  1. cd D:/CKProject/CK_Missive/shared-modules/ck-sso-js")
        print("  2. bash install.sh --target=<consumer-frontend-dir> --framework=react")
        print("  3. Consumer LoginPage.tsx import { useSSOBridge } from '@/lib/ck-sso-js'")
        print("  4. consumer .env.example 補 VITE_API_BASE_URL + CK_SSO_ENABLED")
        print("  5. 重跑本 audit 應 GREEN")

    if severity == "RED":
        return 2
    if severity == "YELLOW" and args.strict:
        return 2
    if severity == "YELLOW":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

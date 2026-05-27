#!/usr/bin/env python3
"""subdomain_registry_audit.py — fitness step 45

偵測 subdomain registry SSOT drift（next_session_resume 8 大根因 #3）。

風險背景：
- 跨 repo 引用 subdomain（如 missive.cksurvey.tw）若 typo（如 pile vs pilemgmt）
  → CORS preflight 失敗 / 連線錯誤 / silent 404
- 沒有單一 SSOT 列出所有 subdomain → 新增/廢止時各 repo 不同步

判定邏輯：
1. 讀 configs/subdomain-registry.yaml 為 SSOT
2. Active subdomains 驗證公網 HTTP 真活（curl 200/2xx/3xx）
3. forbidden_typos 列表偵測：grep 所有 CK_* repos 是否有引用
4. 計算 forbidden_typo 出現次數 → RED
5. Active subdomain 公網不真活 → YELLOW（網路 / Tunnel issue）

Usage:
    python scripts/checks/subdomain_registry_audit.py [--strict]

Exit codes:
    0 = green (all active live + no forbidden typos in code)
    1 = yellow (some active subdomain 不真活，可能 tunnel issue)
    2 = red (forbidden typo found in code; --strict 時 yellow 也 exit 2)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = REPO_ROOT / "configs" / "subdomain-registry.yaml"


def _find_repos(start: Path) -> list[Path]:
    """Find CK_* repos starting from CK_Missive's parent."""
    parent = start.resolve().parent
    return sorted([
        p for p in parent.iterdir()
        if p.is_dir() and p.name.startswith(("CK_", "hermes"))
    ])


def _check_url_live(fqdn: str, expected: list[int] | int, timeout: int = 3) -> tuple[int, bool]:
    """Check if HTTPS endpoint is live; return (http_code, is_expected)."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout), "-o", "/dev/null",
             "-w", "%{http_code}", f"https://{fqdn}/"],
            capture_output=True, text=True, timeout=timeout + 2, encoding="utf-8", errors="replace",
        )
        code = int(result.stdout.strip() or 0)
    except Exception:
        code = 0

    expected_list = expected if isinstance(expected, list) else [expected]
    is_ok = code in expected_list or (code == 0 and 530 in expected_list)
    return code, is_ok


def _grep_in_repo(repo: Path, term: str) -> list[tuple[Path, int]]:
    """Find files in repo containing the literal term. Returns [(file, line_count)]."""
    hits: list[tuple[Path, int]] = []
    # Limit to source code files
    extensions = {".ts", ".tsx", ".js", ".jsx", ".py", ".yaml", ".yml", ".json", ".env"}
    skip_dirs = {"node_modules", ".git", "dist", "build", "__pycache__", ".pytest_cache"}

    for path in repo.rglob("*"):
        if any(part in skip_dirs for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix not in extensions and ".env" not in path.name:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Match term followed by `.cksurvey.tw` to avoid generic word matches
        search_term = f"{term}.cksurvey.tw"
        if search_term in text:
            count = text.count(search_term)
            hits.append((path, count))
    return hits


def main() -> int:
    # Force UTF-8 stdout for Windows cp950 console
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit 2 on any warning")
    parser.add_argument("--skip-live-check", action="store_true",
                        help="skip HTTPS reachability test (offline mode)")
    args = parser.parse_args()

    print("=" * 60)
    print("Subdomain registry SSOT audit (8 根因 #3)")
    print("v1.0 / detect typos + live status")
    print("=" * 60)

    if not REGISTRY_PATH.exists():
        print(f"  🔴 registry not found: {REGISTRY_PATH}")
        return 2

    try:
        registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  🔴 yaml parse error: {e}")
        return 2

    severity = "GREEN"

    # 1. Live check for active subdomains
    active = registry.get("subdomains", {}) or {}
    reserved = registry.get("reserved", {}) or {}
    redirects = registry.get("redirects", {}) or {}

    print(f"\n  active subdomains:  {len(active)}")
    print(f"  reserved:           {len(reserved)}")
    print(f"  redirects:          {len(redirects)}")
    print(f"  forbidden typos:    {len(registry.get('forbidden_typos', []))}\n")

    if not args.skip_live_check:
        print("  Live status check:")
        not_live: list[str] = []
        for name, info in sorted(active.items()):
            fqdn = info.get("fqdn", "")
            expected = info.get("expected_http", 200)
            code, ok = _check_url_live(fqdn, expected)
            indicator = "🟢" if ok else "🟡"
            print(f"    {indicator} {fqdn:<30} HTTP {code} (expected {expected})")
            if not ok:
                not_live.append(fqdn)
        if not_live and severity == "GREEN":
            severity = "YELLOW"
        # reserved (planned) — informational
        for name, info in sorted(reserved.items()):
            fqdn = info.get("fqdn", "")
            expected = info.get("expected_http", [200, 530])
            code, ok = _check_url_live(fqdn, expected)
            indicator = "🟢" if ok else "⚪"
            print(f"    {indicator} {fqdn:<30} HTTP {code} (reserved, expected {expected})")

    # 2. Forbidden typo scan across all repos
    forbidden = registry.get("forbidden_typos", []) or []
    repos = _find_repos(REPO_ROOT)

    print(f"\n  Forbidden typo scan across {len(repos)} repos:")
    typo_hits_total = 0
    for typo in forbidden:
        any_hit = False
        for repo in repos:
            hits = _grep_in_repo(repo, typo)
            if hits:
                any_hit = True
                for f, count in hits[:3]:  # limit per file
                    rel = f.relative_to(REPO_ROOT.parent)
                    print(f"    🔴 {typo}.cksurvey.tw found {count}x in {rel}")
                    typo_hits_total += count
        if not any_hit:
            print(f"    🟢 {typo}.cksurvey.tw: not referenced anywhere")

    if typo_hits_total > 0:
        severity = "RED"

    # 3. Summary
    print(f"\n  Final severity: {severity}")
    print(f"  Forbidden typo total occurrences: {typo_hits_total}")

    if severity == "RED":
        print("\n💡 修法建議：")
        print("  1. grep -rn <typo>.cksurvey.tw 找出引用")
        print("  2. 改用正確 subdomain（如 pile → pilemgmt）")
        print("  3. 加入 commit hook 偵測 forbidden typo")

    if severity == "RED":
        return 2
    if severity == "YELLOW" and args.strict:
        return 2
    if severity == "YELLOW":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""cross_repo_secret_audit.py — fitness step 41 (L41 配套)

偵測跨 repo 共用 secret drift（L41 family）。

L41 事故觸發（2026-05-15~21）：
- ck-sso-py signer 用 JWT secret A
- missive backend verifier 用 JWT secret B
- → SSO chain silent 401，dormant 6 天
- 6 天 dormant 直到 owner 比對才揭發

判定邏輯：
1. 掃所有 CK_* repos 的 .env / .env.example
2. 收集已知跨 repo 共用 secret keys（hard-coded list）：
   - CK_SSO_JWT_SECRET（L41 主角）
   - CK_SSO_ENABLED（flag 應該全部一致）
3. 對每個 key 收集所有 repo 的值
4. drift：同一 key 跨 repo 值不同 → RED
5. 為了安全，只印 sha256 hash 前 8 字元（不印實值）

Usage:
    python scripts/checks/cross_repo_secret_audit.py [--strict]

Exit codes:
    0 = green (no drift)
    1 = yellow (warnings; some repo missing key)
    2 = red (drift detected; --strict 時也會 exit 2)
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

# 跨 repo 應一致的 secret keys（white-list；新增請寫入並評估同步機制）
CROSS_REPO_SHARED_KEYS = {
    "CK_SSO_JWT_SECRET",      # L41 主角：ck-sso-py signer + 各 repo verifier 共用
    "CK_SSO_ENABLED",          # flag 應全部 True 或全部 False（部署門檻）
}

# 探測 CK_* repos 的父目錄
def _find_repos(start: Path) -> list[Path]:
    """Find CK_* repos starting from CK_Missive's parent."""
    parent = start.resolve().parent
    return sorted([
        p for p in parent.iterdir()
        if p.is_dir() and p.name.startswith(("CK_", "hermes"))
        and (p / ".env").exists()
    ])


_ENV_LINE = re.compile(r"^([A-Z_][A-Z0-9_]*)=(.*)$")


def _parse_env(env_file: Path, keys: set[str]) -> dict[str, str]:
    """Parse .env file and return only the requested keys."""
    out: dict[str, str] = {}
    try:
        content = env_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return out
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _ENV_LINE.match(line)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        # Strip surrounding quotes
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        # Strip inline comment
        if "#" in v and not v.startswith("$"):
            v = v.split("#", 1)[0].strip()
        if k in keys:
            out[k] = v
    return out


def _hash_prefix(value: str, length: int = 8) -> str:
    """Return sha256 hash prefix for safe comparison."""
    if not value:
        return "<empty>"
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:length]


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
    print("cross-repo secret SSOT audit (L41 配套)")
    print("v1.0 / detect shared secret drift across CK_* repos")
    print("=" * 60)

    repo_root = Path(__file__).resolve().parent.parent.parent
    repos = _find_repos(repo_root)

    if not repos:
        print("  no CK_* repos with .env found")
        return 0

    # Collect: key -> { repo_name: (value_hash_prefix, raw_present) }
    matrix: dict[str, dict[str, str]] = defaultdict(dict)
    missing: dict[str, list[str]] = defaultdict(list)

    for repo in repos:
        env_file = repo / ".env"
        env_vals = _parse_env(env_file, CROSS_REPO_SHARED_KEYS)
        for key in CROSS_REPO_SHARED_KEYS:
            if key in env_vals:
                matrix[key][repo.name] = _hash_prefix(env_vals[key])
            else:
                missing[key].append(repo.name)

    # Drift analysis
    red_drifts: list[str] = []
    yellow_missing: list[str] = []

    print(f"\n  repos scanned:  {len(repos)} ({', '.join(r.name for r in repos)})")
    print(f"  shared keys:    {len(CROSS_REPO_SHARED_KEYS)}\n")

    for key in sorted(CROSS_REPO_SHARED_KEYS):
        hashes = matrix.get(key, {})
        unique_hashes = set(hashes.values())
        if len(unique_hashes) > 1:
            red_drifts.append(key)
            print(f"  🔴 {key}: DRIFT detected — {len(unique_hashes)} unique values")
            for repo_name, h in sorted(hashes.items()):
                print(f"      {repo_name:<30}  sha256={h}")
        elif len(unique_hashes) == 1:
            (uniq,) = unique_hashes
            print(f"  🟢 {key}: aligned across {len(hashes)} repo(s) (sha256={uniq})")
        else:
            print(f"  ⚪ {key}: not found in any repo")

        if missing.get(key):
            yellow_missing.extend(f"{key}@{r}" for r in missing[key])
            print(f"      🟡 missing in: {', '.join(missing[key])}")

    print(f"\n  🔴 DRIFT:           {len(red_drifts)}")
    print(f"  🟡 missing entries: {len(yellow_missing)}")

    if red_drifts:
        print("\n💡 修法建議：")
        print("  1. 找出該 key 的「signer」(ck-sso-py / ck-auth) → 以 signer 為 SSOT")
        print("  2. 同步 signer 的值到所有「verifier」repos 的 .env")
        print("  3. 重啟所有 consumer service (docker compose restart backend)")
        print("  4. 用 curl + JWT decode 驗證 token 在所有 repo 都能 verify_auto 通過")
        print("  5. 修法後重跑本 audit 應 GREEN")

    if red_drifts:
        return 2
    if yellow_missing and args.strict:
        return 2
    if yellow_missing:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

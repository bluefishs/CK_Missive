#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 1 共享套件版本偏移 + 消費模式稽核（Phase 2 執行 gate / L80，2026-07-22）

模組化標準化的「執行強制」——把 advisory 變 blocking：偵測各 consumer vendored 的
ck-auth wheel 版本是否落後套件源（版本偏移＝「一次修全同步」破功）。

檢查：
  1. 套件源版本（shared-modules/ck-auth-py/pyproject.toml）
  2. 各 consumer repo 的 backend/vendor|api/vendor 內 ck_auth wheel 版本
  3. 偏移（consumer < 源）→ RED（--strict exit 1）
  4. 附報 ck_sso 消費模式（shim=import 單一源 / copy=各自複本）

用法：python scripts/checks/tier1_shared_package_audit.py [--strict]
跨 repo：以 ../<repo> 相對定位；缺席該 repo 標 SKIP。
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # L49.8 family
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]           # CK_Missive/
PROJECTS = ROOT.parent                                # D:/CKProject/
PKG_PYPROJECT = PROJECTS / "shared-modules" / "ck-auth-py" / "pyproject.toml"

# consumer repo → (vendor 目錄, ck_sso 檔) 相對各 repo root
CONSUMERS = {
    "CK_Missive":        ("backend/vendor", "backend/app/core/ck_sso.py"),
    "CK_DigitalTunnel":  ("api/vendor",     "api/src/auth/ck_sso.py"),
    "CK_lvrland_Webmap": ("backend/vendor", "backend/app/core/ck_sso.py"),
    "CK_PileMgmt":       ("backend/vendor", "backend/app/core/ck_sso.py"),
}

WHEEL_RE = re.compile(r"ck_auth-(\d+\.\d+\.\d+)-")


def _source_version():
    try:
        m = re.search(r'version\s*=\s*"(\d+\.\d+\.\d+)"', PKG_PYPROJECT.read_text(encoding="utf-8"))
        return m.group(1) if m else None
    except Exception:
        return None


def _vendored_version(repo, vendor_rel):
    d = PROJECTS / repo / vendor_rel
    if not d.exists():
        return None
    for whl in d.glob("ck_auth-*.whl"):
        m = WHEEL_RE.search(whl.name)
        if m:
            return m.group(1)
    return None


def _ck_sso_mode(repo, ck_sso_rel):
    p = PROJECTS / repo / ck_sso_rel
    if not p.exists():
        return "N/A"
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "?"
    return "shim(import ck_auth.sso)" if "from ck_auth.sso import" in txt else "copy(自有實作)"


def _ver_tuple(v):
    return tuple(int(x) for x in v.split("."))


def main() -> int:
    strict = "--strict" in sys.argv
    print("=== Tier 1 共享套件版本偏移 + 消費模式稽核 (Phase 2 / L80) ===")
    src = _source_version()
    print(f"套件源 ck-auth 版本: {src or '讀取失敗'}")
    print(f"{'repo':<20} {'vendored':<10} {'ck_sso 模式':<24} 判定")
    issues = []
    for repo, (vendor_rel, cksso_rel) in CONSUMERS.items():
        if not (PROJECTS / repo).exists():
            print(f"{repo:<20} {'-':<10} {'SKIP(repo 缺席)':<24}")
            continue
        vv = _vendored_version(repo, vendor_rel)
        mode = _ck_sso_mode(repo, cksso_rel)
        if vv is None:
            verdict = "⚪ 未 vendored（copy 態）" if mode.startswith("copy") else "🟡 shim 但無 wheel!"
            if mode.startswith("shim"):
                issues.append(f"{repo}: ck_sso 為 shim 但 vendor 無 ck_auth wheel（build 會失敗）")
        elif src and _ver_tuple(vv) < _ver_tuple(src):
            verdict = f"🔴 偏移（源 {src}）"
            issues.append(f"{repo}: vendored {vv} < 源 {src}（版本偏移，需換 wheel + rebuild）")
        else:
            verdict = "✅ 對齊"
        print(f"{repo:<20} {vv or '-':<10} {mode:<24} {verdict}")

    if issues:
        print("\n🔴 ISSUES:")
        for i in issues:
            print(f"  - {i}")
        print("\nOVERALL = RED")
        return 1 if strict else 0
    print("\nOVERALL = GREEN（無版本偏移；copy 態為漸進 rollout 中間狀態非錯誤）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

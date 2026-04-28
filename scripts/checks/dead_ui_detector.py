#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dead UI Detector — PLAYBOOK §6.5 Anti-pattern 落實

偵測「後端 endpoint 已實作但前端缺常數/UI」的 dead UI candidates。

排查鏈路：
  1. parse backend/app/api/routes.py 抓所有 (router_module, prefix, tags)
  2. 讀每個 router 模組找 @router.{get,post,...}('/path') decorators
  3. 組合 full path = api_prefix + router_prefix + endpoint_path
  4. parse frontend/src/api/endpoints/*.ts 抓所有 string literal endpoints
  5. cross-check：backend 有但前端無 → DEAD UI candidate

排除規則：
  - webhook（外部 callback，非 admin UI）
  - debug/health/public（內部用）
  - websocket（不走 REST endpoints）

L21 prevention 同類但對 UI 整合層。

Usage:
    python scripts/checks/dead_ui_detector.py
    python scripts/checks/dead_ui_detector.py --threshold 5
    python scripts/checks/dead_ui_detector.py --ci

Exit codes:
    0 — dead UI candidates 在閾值內
    1 — 候選超閾值（warning 模式仍 exit 0；--ci 才 exit 1）

Version: 1.0.0 (2026-04-28)
Refs: L10 (PLAYBOOK §6.5 Dead UI anti-pattern)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROUTES_FILE = Path("backend/app/api/routes.py")
ENDPOINTS_DIR = Path("backend/app/api/endpoints")
FRONTEND_ENDPOINTS_DIR = Path("frontend/src/api/endpoints")
FRONTEND_SRC_DIR = Path("frontend/src")
API_PREFIX = "/api"  # main.py: app.include_router(api_router, prefix="/api")

# 排除：非 admin/user UI 用途
EXCLUDE_PREFIX_KEYWORDS = [
    "webhook", "debug", "health", "public", "metrics", "deployment",
]
EXCLUDE_PATH_KEYWORDS = [
    "/test", "/ping", "/healthz",
    # /api/statistics/* 與 /api/dashboard/* 重複註冊（routes.py 兩 mount），前端只用 dashboard
    "/api/statistics/",
]


def parse_routes_includes(routes_text: str) -> list[tuple[str, str]]:
    """從 routes.py 抓所有 include_router 的 (module_name, prefix)"""
    includes = []
    # match: api_router.include_router(<module>.router, prefix="<p>", ...)
    # 也 match: api_router.include_router(<router_var>, prefix="<p>", ...)
    pattern = re.compile(
        r"api_router\.include_router\(\s*([\w_]+)(?:\.router)?\s*,[^)]*?prefix\s*=\s*['\"]([^'\"]+)['\"]",
        re.DOTALL,
    )
    for m in pattern.finditer(routes_text):
        module_name = m.group(1)
        prefix = m.group(2)
        includes.append((module_name, prefix))
    return includes


def find_router_module_file(module_name: str) -> Path | None:
    """從 module name 找對應的 .py 檔（可能是 endpoints/<m>.py 或 endpoints/<m>/__init__.py）"""
    direct = ENDPOINTS_DIR / f"{module_name}.py"
    if direct.exists():
        return direct
    pkg = ENDPOINTS_DIR / module_name / "__init__.py"
    if pkg.exists():
        return pkg
    # routers 也可能 alias 過（如 documents_router 來自 endpoints/documents/）
    for alt in [
        ENDPOINTS_DIR / module_name.replace("_router", "") / "__init__.py",
        ENDPOINTS_DIR / "ai" / f"{module_name}.py",
    ]:
        if alt.exists():
            return alt
    return None


ROUTE_DECORATOR = re.compile(
    r"@(?:router|app)\.(get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]",
)


def parse_endpoint_paths(file_path: Path) -> list[tuple[str, str]]:
    """從 router 模組檔抓所有 (method, path) — 含 sub-router 內含的"""
    endpoints = []
    if not file_path.exists():
        return endpoints
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return endpoints
    for m in ROUTE_DECORATOR.finditer(text):
        method = m.group(1).upper()
        path = m.group(2)
        endpoints.append((method, path))

    # 若是子目錄 __init__.py，可能 include 多個 sub-router
    if file_path.name == "__init__.py":
        # 也掃同目錄下其他 .py
        for sibling in file_path.parent.glob("*.py"):
            if sibling == file_path:
                continue
            try:
                stext = sibling.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for m in ROUTE_DECORATOR.finditer(stext):
                endpoints.append((m.group(1).upper(), m.group(2)))
    return endpoints


def collect_backend_endpoints() -> list[tuple[str, str, str]]:
    """收集所有 backend endpoint full path: list of (method, full_path, module)"""
    if not ROUTES_FILE.exists():
        print(f"❌ {ROUTES_FILE} not found", file=sys.stderr)
        sys.exit(2)
    routes_text = ROUTES_FILE.read_text(encoding="utf-8", errors="replace")
    includes = parse_routes_includes(routes_text)

    all_endpoints: list[tuple[str, str, str]] = []
    seen = set()
    for module, prefix in includes:
        # 排除非 UI 用途
        if any(k in prefix.lower() or k in module.lower() for k in EXCLUDE_PREFIX_KEYWORDS):
            continue
        file_path = find_router_module_file(module)
        if not file_path:
            continue
        for method, path in parse_endpoint_paths(file_path):
            full = f"{API_PREFIX}{prefix}{path}".rstrip("/")
            if any(k in full.lower() for k in EXCLUDE_PATH_KEYWORDS):
                continue
            key = (method, full)
            if key in seen:
                continue
            seen.add(key)
            all_endpoints.append((method, full, module))
    return all_endpoints


def collect_frontend_endpoints(scope: str = "src") -> set[str]:
    """掃 frontend 抓所有 path-like string literals.

    scope='endpoints' — 只掃 frontend/src/api/endpoints/*.ts (集中常數區)
    scope='src'       — 掃整個 frontend/src/ (含 services/hooks/components 內 hardcoded)
    """
    paths = set()
    target_dir = FRONTEND_ENDPOINTS_DIR if scope == "endpoints" else FRONTEND_SRC_DIR
    if not target_dir.exists():
        return paths
    string_pattern = re.compile(r"['\"`](/[a-zA-Z_][^'\"`]*?)['\"`]")
    glob_pattern = "*.ts" if scope == "endpoints" else "**/*.ts"
    files = list(target_dir.glob(glob_pattern))
    if scope == "src":
        files += list(target_dir.glob("**/*.tsx"))
    for ts_file in files:
        # 跳過 node_modules / dist / __tests__
        if any(p in str(ts_file) for p in ("node_modules", "dist", "__tests__", ".test.", ".spec.")):
            continue
        try:
            text = ts_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in string_pattern.finditer(text):
            raw = m.group(1)
            normalized = re.sub(r"\$\{[^}]+\}", "{}", raw)
            normalized = re.sub(r":[\w_]+", "{}", normalized)
            normalized = re.sub(r"\{[^}]+\}", "{}", normalized)
            paths.add(normalized.rstrip("/"))
    return paths


def normalize_for_match(path: str) -> str:
    """把 backend path 規範化方便匹配。

    重要：frontend axios baseURL=/api，所以前端字串不含 /api prefix。
    比對前 strip /api。
    """
    p = re.sub(r"\{[^}]+\}", "{}", path).rstrip("/")
    if p.startswith("/api/"):
        p = p[4:]  # /api/auth/bind → /auth/bind
    elif p == "/api":
        p = ""
    return p


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--threshold", type=int, default=10,
                        help="dead UI candidates 警告閾值（預設 10）")
    parser.add_argument("--ci", action="store_true", help="超閾值 exit 1")
    parser.add_argument("--show-all", action="store_true", help="列出全部，不只前 30")
    parser.add_argument("--scope", choices=("src", "endpoints"), default="src",
                        help="frontend 掃描範圍：src（全掃，預設）或 endpoints（只掃集中常數區）")
    args = parser.parse_args()

    print(f"=== Dead UI Detector (scope: frontend/src/{'**/*.{ts,tsx}' if args.scope=='src' else 'api/endpoints/*.ts'}) ===\n")

    backend = collect_backend_endpoints()
    frontend = collect_frontend_endpoints(scope=args.scope)

    print(f"📡 Backend endpoints (excluding webhook/debug/health/public): {len(backend)}")
    print(f"🖥  Frontend string literals (potential endpoints): {len(frontend)}\n")

    candidates = []  # (method, full_path, module) — 後端有但前端無
    for method, path, module in backend:
        norm = normalize_for_match(path)
        if norm not in frontend:
            candidates.append((method, path, module))

    candidates.sort(key=lambda x: (x[2], x[1]))

    print(f"⚠️  Dead UI candidates (後端有但前端 endpoints/*.ts 無): {len(candidates)}\n")

    if candidates:
        limit = len(candidates) if args.show_all else 30
        for method, path, module in candidates[:limit]:
            print(f"  {method:6} {path:60} ← {module}")
        if len(candidates) > limit:
            print(f"  ... 另 {len(candidates) - limit} 筆（用 --show-all 列全）")

    print()
    if len(candidates) > args.threshold:
        print(f"❌ 候選 {len(candidates)} 超閾值 {args.threshold}")
        print("\n建議修復路徑（PLAYBOOK §6.5）：")
        print("  1. 補 frontend/src/api/endpoints/<domain>.ts 加常數")
        print("  2. 寫 useQuery/useMutation hook 包裝")
        print("  3. 在對應 page 加按鈕/Drawer/Modal 觸發")
        print("\n或若該 endpoint 確實內部用：加入此 detector 的 EXCLUDE 清單")
        if args.ci:
            return 1
    elif candidates:
        print(f"🟡 候選 {len(candidates)} 筆（閾值 {args.threshold}）— 待 owner 評估")
    else:
        print("🎉 所有後端 endpoints 都有對應前端常數")

    return 0


if __name__ == "__main__":
    sys.exit(main())

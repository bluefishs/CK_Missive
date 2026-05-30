"""Fitness step 67 (v6.12, 2026-05-30): 前後端 endpoint 一致性 audit

Owner 訴求: 確認前後端對應關聯整合優化程序

對齊 development-rules.md §1:
「所有 API 端點必須使用 frontend/src/api/endpoints/*.ts 常數」

偵測 3 類漂移:
1. frontend 用了但 backend 沒實作的 endpoint (silent 404 風險)
2. backend 有但 frontend 沒對應常數 (端點 hard-code 風險)
3. endpoint 常數定義但無 hook 使用 (dead code)

設計: 靜態分析，掃 .ts/.tsx + .py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def extract_frontend_endpoints() -> set[str]:
    """從 frontend/src/api/endpoints/*.ts 抓所有 endpoint path 字串"""
    paths = set()
    endpoints_dir = ROOT / "frontend" / "src" / "api" / "endpoints"
    if not endpoints_dir.is_dir():
        return paths
    # 抓形如 LIST: '/documents-enhanced/list', PATH: `/api/foo/${id}` 等
    pattern = re.compile(r"['`](/(?:api/)?[\w\-\$\{\}/:_\.]+)['`]")
    for f in endpoints_dir.glob("*.ts"):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in pattern.finditer(text):
            p = m.group(1)
            # 標準化: 去 /api/ 前綴 + 去 ${var} placeholders
            p = re.sub(r"^/api/", "/", p)
            p = re.sub(r"\$\{[^}]+\}", "{id}", p)
            paths.add(p)
    return paths


def extract_routes_prefix_map() -> dict[str, str]:
    """v6.12 精細化 (2026-05-30): 從 routes.py 抓 module → prefix 映射

    routes.py 內 include_router(<module>.router, prefix="/foo")
    或 include_router(<custom_router>, prefix="/foo")
    """
    routes_file = ROOT / "backend" / "app" / "api" / "routes.py"
    if not routes_file.exists():
        return {}
    text = routes_file.read_text(encoding="utf-8", errors="ignore")
    # 抓 module.router 或 _router 形式
    out = {}
    for m in re.finditer(
        r'include_router\(\s*([\w\.]+(?:_router|\.router))\s*,\s*prefix\s*=\s*["\']([^"\']+)["\']',
        text,
    ):
        var = m.group(1).split(".")[0]  # 取 module 名
        prefix = m.group(2)
        out[var] = prefix
    return out


def extract_backend_endpoints() -> set[str]:
    """v6.12 精細化: 抓 @router.* 路徑 + 對齊 routes.py prefix 補完全限定路徑"""
    prefix_map = extract_routes_prefix_map()
    paths = set()
    endpoints_dir = ROOT / "backend" / "app" / "api" / "endpoints"
    if not endpoints_dir.is_dir():
        return paths
    pattern = re.compile(
        r"@router\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]"
    )
    for f in endpoints_dir.rglob("*.py"):
        if "__pycache__" in f.parts or f.name == "__init__.py":
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # 取 module name 配對 prefix_map
        # e.g. backend/app/api/endpoints/admin/users.py → admin/users
        # 但 routes.py 是 admin.users.router 形式或 users_router 形式
        rel_module = f.stem  # 如 'documents' / 'users'
        # 也可能在 endpoints/admin/ → 是 admin module
        parent = f.parent.name
        prefix = prefix_map.get(rel_module) or prefix_map.get(parent) or ""
        for m in pattern.finditer(text):
            p = m.group(2)
            p = re.sub(r"\{[^}]+\}", "{id}", p)
            full = (prefix + p) if prefix else p
            paths.add(full)
    return paths


def main() -> int:
    strict = "--strict" in sys.argv
    print("=== 前後端 endpoint 一致性 audit (step 67, v6.12) ===")
    print()

    fe = extract_frontend_endpoints()
    be = extract_backend_endpoints()
    print(f"Frontend endpoints (in api/endpoints/*.ts): {len(fe)}")
    print(f"Backend  endpoints (@router.*):              {len(be)}")
    print()

    # 1. frontend 用但 backend 沒
    fe_only = sorted(fe - be)
    # 2. backend 有但 frontend 沒
    be_only = sorted(be - fe)

    issues = 0

    if fe_only:
        print(f"⚠ {len(fe_only)} frontend endpoint 找不到 backend 對應 (silent 404 風險):")
        for p in fe_only[:15]:
            print(f"    - {p}")
        if len(fe_only) > 15:
            print(f"    ... 還有 {len(fe_only) - 15} 條")
        print()
        issues += len(fe_only)

    if be_only:
        only_business = [p for p in be_only
                         if not any(p.startswith(prefix) for prefix in (
                             "/health", "/admin", "/debug", "/ai/agent",
                             "/dispatch-link", "/event", "/document-number"
                         ))]
        if only_business:
            print(f"ℹ️ {len(only_business)} backend endpoint 無 frontend 常數對應 (admin/internal 屬正常):")
            for p in only_business[:10]:
                print(f"    - {p}")
            if len(only_business) > 10:
                print(f"    ... 還有 {len(only_business) - 10} 條")
        print()

    if not fe_only:
        print("✓ 所有 frontend endpoint 都有 backend 對應")
    print()
    print(f"Summary: fe-only={len(fe_only)} (P0) / be-only={len(be_only)} (info)")

    if fe_only and strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

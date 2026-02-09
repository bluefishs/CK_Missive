#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CK_Missive 架構驗證腳本

靜態分析前後端程式碼，檢查架構一致性與品質。
不需要啟動伺服器或匯入任何專案模組。

@version 1.0.0
@date 2026-02-09

用法:
  python scripts/verify_architecture.py              # 完整檢查
  python scripts/verify_architecture.py --check routes  # 僅檢查路由
  python scripts/verify_architecture.py --verbose       # 詳細輸出
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# =============================================================================
# 設定
# =============================================================================

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_SRC = PROJECT_ROOT / "frontend" / "src"
BACKEND_APP = PROJECT_ROOT / "backend" / "app"

# 統計結果
class Results:
    def __init__(self):
        self.passed: List[str] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def ok(self, msg: str):
        self.passed.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    def error(self, msg: str):
        self.errors.append(msg)

    def summary(self) -> int:
        total = len(self.passed) + len(self.warnings) + len(self.errors)
        print("\n" + "=" * 60)
        print(f"  架構驗證結果: {len(self.passed)} passed, "
              f"{len(self.warnings)} warnings, {len(self.errors)} errors "
              f"(共 {total} 項)")
        print("=" * 60)
        if self.errors:
            print("\n[ERRORS]")
            for e in self.errors:
                print(f"  X {e}")
        if self.warnings:
            print("\n[WARNINGS]")
            for w in self.warnings:
                print(f"  ! {w}")
        print()
        return 1 if self.errors else 0


results = Results()
verbose = False


def log(msg: str):
    if verbose:
        print(f"  . {msg}")


# =============================================================================
# 工具函數
# =============================================================================

def read_file(path: Path) -> str:
    """讀取檔案內容"""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        results.error(f"無法讀取 {path}: {e}")
        return ""


def find_files(directory: Path, pattern: str) -> List[Path]:
    """遞迴搜尋檔案"""
    return sorted(directory.rglob(pattern))


# =============================================================================
# Check 1: 前後端路由一致性
# =============================================================================

def check_routes():
    """檢查 types.ts ROUTES 常數 vs AppRouter.tsx 路由定義"""
    print("\n[1/7] 前後端路由一致性")
    print("-" * 40)

    types_file = FRONTEND_SRC / "router" / "types.ts"
    router_file = FRONTEND_SRC / "router" / "AppRouter.tsx"

    types_content = read_file(types_file)
    router_content = read_file(router_file)

    if not types_content or not router_content:
        return

    # 1a: 從 types.ts 提取 ROUTES 常數
    route_pattern = re.compile(r"(\w+):\s*'([^']+)'")
    routes_defined: Dict[str, str] = {}
    in_routes = False
    for line in types_content.splitlines():
        if "ROUTES = {" in line:
            in_routes = True
            continue
        if in_routes and "} as const" in line:
            break
        if in_routes:
            m = route_pattern.search(line)
            if m:
                routes_defined[m.group(1)] = m.group(2)

    # 1b: 從 AppRouter.tsx 提取 ROUTES.XXX 使用
    routes_used_in_router = set(re.findall(r"ROUTES\.(\w+)", router_content))

    # 1c: 比對
    defined_keys = set(routes_defined.keys())
    unused = defined_keys - routes_used_in_router
    undefined = routes_used_in_router - defined_keys

    # 排除已知的重導向路由（不需要在 AppRouter 中使用）
    known_unused = set()  # 可加入合理未使用的 key

    real_unused = unused - known_unused
    if real_unused:
        results.warn(
            f"types.ts 定義但 AppRouter 未使用的 ROUTES: "
            f"{', '.join(sorted(real_unused))}"
        )
    else:
        results.ok("所有 ROUTES 常數都有在 AppRouter 中使用")

    if undefined:
        results.error(
            f"AppRouter 使用但 types.ts 未定義的 ROUTES: "
            f"{', '.join(sorted(undefined))}"
        )
    else:
        results.ok("AppRouter 中的 ROUTES 引用全部有效")

    log(f"ROUTES 常數: {len(routes_defined)} 個, AppRouter 使用: {len(routes_used_in_router)} 個")

    return routes_defined


# =============================================================================
# Check 2: 導覽項目同步
# =============================================================================

def check_navigation_sync(routes_defined: Dict[str, str] | None):
    """檢查 init_navigation_data.py 中的路徑是否與 ROUTES 一致"""
    print("\n[2/7] 導覽項目同步")
    print("-" * 40)

    nav_file = BACKEND_APP / "scripts" / "init_navigation_data.py"
    content = read_file(nav_file)
    if not content:
        return

    # 提取所有 "path": "..." 值
    nav_paths = set(re.findall(r'"path":\s*"([^"]+)"', content))

    if routes_defined:
        frontend_paths = set(routes_defined.values())
        # 只比對靜態路徑（不含 :id 等參數）
        static_frontend = {p for p in frontend_paths if ":" not in p}

        nav_not_in_frontend = nav_paths - static_frontend
        # 排除已知的後端獨有路徑
        known_backend_only = {"/system", "/pure-calendar"}
        real_missing = nav_not_in_frontend - known_backend_only

        if real_missing:
            results.warn(
                f"導覽項目中有路徑在前端 ROUTES 找不到: "
                f"{', '.join(sorted(real_missing))}"
            )
        else:
            results.ok("導覽項目路徑與前端 ROUTES 一致")
    else:
        results.warn("無法比對導覽項目（ROUTES 提取失敗）")

    log(f"導覽項目路徑: {len(nav_paths)} 個")


# =============================================================================
# Check 3: API 端點前綴一致性
# =============================================================================

def check_api_prefix_consistency():
    """檢查前端 endpoints.ts 與後端 routes.py 的 API 前綴是否一致"""
    print("\n[3/7] API 端點前綴一致性")
    print("-" * 40)

    endpoints_file = FRONTEND_SRC / "api" / "endpoints.ts"
    routes_file = BACKEND_APP / "api" / "routes.py"

    fe_content = read_file(endpoints_file)
    be_content = read_file(routes_file)

    if not fe_content or not be_content:
        return

    # 前端: 提取所有路徑前綴 (第一個斜線後的路徑段)
    fe_paths = set(re.findall(r"'(/[a-z][a-z0-9\-]*/)", fe_content))
    fe_prefixes = set()
    for p in fe_paths:
        # 提取 /xxx/ 或 /xxx-yyy/ 格式
        parts = p.strip("/").split("/")
        if parts:
            fe_prefixes.add("/" + parts[0])

    # 後端: 提取 include_router 中的 prefix
    be_prefixes = set(re.findall(r'prefix="(/[^"]+)"', be_content))
    be_prefix_roots = set()
    for p in be_prefixes:
        parts = p.strip("/").split("/")
        if parts:
            be_prefix_roots.add("/" + parts[0])

    # 比對
    fe_only = fe_prefixes - be_prefix_roots
    be_only = be_prefix_roots - fe_prefixes

    # 排除已知差異
    # 後端獨有: debug(開發用), secure-site-management(內部), statistics(子路由)
    known_be_only = {"/debug", "/secure-site-management", "/statistics"}
    real_be_only = be_only - known_be_only

    # 前端獨有: 這些後端路由沒有在 routes.py 用 prefix= 定義，而是在各自的 router 中
    known_fe_only = {"/ai", "/deploy", "/health", "/taoyuan-dispatch"}
    fe_only = fe_only - known_fe_only

    if fe_only:
        results.warn(f"前端有但後端無的 API 前綴: {', '.join(sorted(fe_only))}")
    if real_be_only:
        results.warn(f"後端有但前端無的 API 前綴: {', '.join(sorted(real_be_only))}")
    if not fe_only and not real_be_only:
        results.ok("前後端 API 前綴一致")

    log(f"前端前綴: {len(fe_prefixes)} 個, 後端前綴: {len(be_prefix_roots)} 個")


# =============================================================================
# Check 4: 型別 SSOT 違規偵測
# =============================================================================

def check_type_ssot():
    """
    檢查型別 Single Source of Truth 規範：
    - 後端: Pydantic Schema 只能定義在 schemas/ 目錄
    - 前端: 業務型別只能定義在 types/api.ts
    """
    print("\n[4/7] 型別 SSOT 違規偵測")
    print("-" * 40)

    violations = []

    # 4a: 後端 — 檢查端點檔案中是否有本地 BaseModel 定義
    endpoint_dir = BACKEND_APP / "api" / "endpoints"
    for py_file in find_files(endpoint_dir, "*.py"):
        content = read_file(py_file)
        if not content:
            continue

        # 搜尋 class Xxx(BaseModel): 模式
        local_models = re.findall(
            r"^class\s+(\w+)\(.*?BaseModel.*?\):",
            content,
            re.MULTILINE,
        )
        if local_models:
            rel = py_file.relative_to(PROJECT_ROOT)
            violations.append(f"後端 {rel}: 本地 BaseModel [{', '.join(local_models)}]")

    # 4b: 前端 — 檢查 api/*.ts 中是否有本地 interface/type 定義
    api_dir = FRONTEND_SRC / "api"
    # 允許的檔案（這些檔案可以定義 API 專用型別）
    allowed_type_files = {
        "aiApi.ts",        # AI 搜尋歷史等專用型別
        "types.ts",        # API 通用型別（ErrorResponse, PaginationParams 等）
        "endpoints.ts",    # 端點常數
    }

    for ts_file in find_files(api_dir, "*.ts"):
        if ts_file.name in allowed_type_files:
            continue
        if ts_file.name == "endpoints.ts":
            continue  # endpoints 不會定義型別

        content = read_file(ts_file)
        if not content:
            continue

        # 搜尋 export interface Xxx { 或 export type Xxx = 模式
        # 排除 re-export（export type { Xxx } from）
        local_types = re.findall(
            r"^export\s+(?:interface|type)\s+(\w+)\s*[={]",
            content,
            re.MULTILINE,
        )
        if local_types:
            rel = ts_file.relative_to(PROJECT_ROOT)
            violations.append(f"前端 {rel}: 本地型別 [{', '.join(local_types)}]")

    if violations:
        for v in violations:
            results.warn(f"SSOT 違規: {v}")
    else:
        results.ok("型別 SSOT 規範通過（無違規）")

    log(f"檢查端點 .py: {len(list(find_files(endpoint_dir, '*.py')))} 個")


# =============================================================================
# Check 5: Schema-ORM 欄位基礎對齊
# =============================================================================

def check_schema_orm_alignment():
    """
    檢查 Pydantic Schema 中的欄位是否在 ORM 模型中存在。
    僅做基礎比對（欄位名稱），不做型別比對。
    """
    print("\n[5/7] Schema-ORM 欄位對齊")
    print("-" * 40)

    models_file = BACKEND_APP / "extended" / "models.py"
    schemas_dir = BACKEND_APP / "schemas"

    models_content = read_file(models_file)
    if not models_content:
        return

    # 5a: 提取 ORM 模型的 Column 欄位
    # 格式: field_name = Column(...) 或 field_name = mapped_column(...)
    orm_models: Dict[str, Set[str]] = {}
    current_model = None
    for line in models_content.splitlines():
        class_match = re.match(r"^class\s+(\w+)\(.*Base.*\):", line)
        if class_match:
            current_model = class_match.group(1)
            orm_models[current_model] = set()
            continue
        if current_model and re.match(r"^class\s", line):
            current_model = None
            continue
        if current_model:
            col_match = re.match(
                r"\s+(\w+)\s*=\s*(?:Column|mapped_column|relationship|deferred)\(",
                line,
            )
            if col_match:
                orm_models[current_model].add(col_match.group(1))

    # 5b: 提取 Pydantic Schema 欄位
    # 格式: field_name: type 或 field_name: Optional[type]
    schema_models: Dict[str, Set[str]] = {}
    for schema_file in find_files(schemas_dir, "*.py"):
        content = read_file(schema_file)
        if not content:
            continue
        current_schema = None
        for line in content.splitlines():
            class_match = re.match(r"^class\s+(\w+)\(.*\):", line)
            if class_match:
                current_schema = class_match.group(1)
                schema_models[current_schema] = set()
                continue
            if current_schema and re.match(r"^class\s", line):
                current_schema = None
                continue
            if current_schema:
                field_match = re.match(r"\s+(\w+)\s*:", line)
                if field_match:
                    field_name = field_match.group(1)
                    # 排除 model_config, Config, class Meta 等非欄位
                    if field_name not in ("model_config", "Config", "class_validators"):
                        schema_models[current_schema].add(field_name)

    # 5c: 嘗試匹配 Schema → ORM（啟發式：名稱相似）
    # 常見的命名慣例：DocumentBase → OfficialDocument, UserBase → User
    name_map = {
        "OfficialDocument": ["DocumentBase", "DocumentCreate", "DocumentUpdate", "DocumentResponse"],
        "ContractProject": ["ProjectBase", "ProjectCreate", "ProjectUpdate", "ProjectResponse"],
        "GovernmentAgency": ["AgencyBase", "AgencyCreate", "AgencyUpdate", "AgencyResponse"],
        "PartnerVendor": ["VendorBase", "VendorCreate", "VendorUpdate", "VendorResponse"],
        "User": ["UserBase", "UserCreate", "UserUpdate", "UserResponse"],
    }

    issues = []
    for orm_name, schema_names in name_map.items():
        if orm_name not in orm_models:
            continue
        orm_fields = orm_models[orm_name]
        for schema_name in schema_names:
            if schema_name not in schema_models:
                continue
            schema_fields = schema_models[schema_name]
            # 檢查 Schema 有但 ORM 沒有的欄位（可能的錯誤）
            extra = schema_fields - orm_fields
            # 排除常見的非 ORM 欄位
            non_orm_fields = {
                "id", "created_at", "updated_at", "model_config",
                "attachments", "events", "projects", "vendors",
                "staff", "permissions", "roles",
            }
            real_extra = extra - non_orm_fields
            if real_extra:
                issues.append(
                    f"{schema_name} 有但 {orm_name} 無: "
                    f"{', '.join(sorted(real_extra))}"
                )

    if issues:
        for issue in issues:
            results.warn(f"Schema-ORM 欄位差異: {issue}")
    else:
        results.ok("Schema-ORM 核心欄位對齊檢查通過")

    log(f"ORM 模型: {len(orm_models)} 個, Schema: {len(schema_models)} 個")


# =============================================================================
# Check 6: 前端元件匯出一致性
# =============================================================================

def check_frontend_exports():
    """
    檢查 pages/ 目錄中的元件是否都在 AppRouter 中使用。
    偵測孤立的頁面元件。
    """
    print("\n[6/7] 前端頁面元件使用率")
    print("-" * 40)

    router_file = FRONTEND_SRC / "router" / "AppRouter.tsx"
    router_content = read_file(router_file)
    if not router_content:
        return

    # 提取 AppRouter 中 lazy(() => import(...)) 的頁面模組
    imported_pages = set(re.findall(
        r"import\('\.\./(pages/\w+)'\)",
        router_content,
    ))

    # 掃描 pages/ 目錄中的所有頁面檔案
    pages_dir = FRONTEND_SRC / "pages"
    page_files = set()
    for f in pages_dir.iterdir():
        if f.is_file() and f.suffix == ".tsx" and not f.name.startswith("_"):
            page_files.add(f"pages/{f.stem}")

    # 比對
    unused_pages = page_files - imported_pages
    # 排除已知被整合的頁面
    known_integrated = {
        "pages/AISynonymManagementPage",  # 整合至 AIAssistantManagementPage Tab
        "pages/AIPromptManagementPage",   # 整合至 AIAssistantManagementPage Tab
        "pages/EntryPage",               # 重導向至 LoginPage (ROUTES.ENTRY)
        "pages/ApiDocsPage",             # 透過 ApiDocumentationPage 載入
    }
    real_unused = unused_pages - known_integrated

    if real_unused:
        results.warn(
            f"未在 AppRouter 中註冊的頁面元件 ({len(real_unused)} 個): "
            f"{', '.join(sorted(real_unused))}"
        )
    else:
        results.ok("所有頁面元件都已在 AppRouter 中註冊或標記為已整合")

    log(f"頁面元件: {len(page_files)} 個, AppRouter 導入: {len(imported_pages)} 個")


# =============================================================================
# Check 7: 後端模組匯入安全
# =============================================================================

def check_backend_imports():
    """
    檢查後端常見的匯入問題：
    - 端點檔案中的 wildcard import
    - 已刪除模組的殘留引用
    """
    print("\n[7/7] 後端模組匯入安全")
    print("-" * 40)

    issues = []

    # 7a: 檢查 wildcard import (from xxx import *)
    endpoint_dir = BACKEND_APP / "api" / "endpoints"
    for py_file in find_files(endpoint_dir, "*.py"):
        content = read_file(py_file)
        if not content:
            continue
        wildcards = re.findall(r"^from\s+\S+\s+import\s+\*", content, re.MULTILINE)
        if wildcards:
            rel = py_file.relative_to(PROJECT_ROOT)
            issues.append(f"Wildcard import: {rel}")

    # 7b: 檢查 schemas/__init__.py 中的 wildcard import
    schemas_init = BACKEND_APP / "schemas" / "__init__.py"
    if schemas_init.exists():
        content = read_file(schemas_init)
        wildcards = re.findall(r"^from\s+\S+\s+import\s+\*", content, re.MULTILINE)
        if wildcards:
            issues.append(f"Wildcard import: schemas/__init__.py ({len(wildcards)} 個)")

    # 7c: 檢查已棄用模組的引用
    deprecated_modules = [
        "base_service",  # v1.42.0 標記棄用
        "vendor_service_v2",  # 已刪除
    ]
    services_dir = BACKEND_APP / "services"
    for py_file in find_files(BACKEND_APP, "*.py"):
        content = read_file(py_file)
        if not content:
            continue
        for mod in deprecated_modules:
            if f"from" in content and mod in content:
                # 排除模組自身
                if py_file.stem == mod:
                    continue
                # 檢查是否有實際的 import 語句
                import_pattern = re.findall(
                    rf"^from\s+\S*{mod}\S*\s+import",
                    content,
                    re.MULTILINE,
                )
                if import_pattern:
                    rel = py_file.relative_to(PROJECT_ROOT)
                    issues.append(f"引用已棄用模組 {mod}: {rel}")

    if issues:
        for issue in issues:
            results.warn(issue)
    else:
        results.ok("後端模組匯入檢查通過（無 wildcard / 無棄用引用）")

    log(f"掃描 .py 檔案: {len(list(find_files(BACKEND_APP, '*.py')))} 個")


# =============================================================================
# 主程式
# =============================================================================

def run_all_checks():
    """執行所有檢查"""
    print("=" * 60)
    print("  CK_Missive 架構驗證 v1.0.0")
    print(f"  專案根目錄: {PROJECT_ROOT}")
    print("=" * 60)

    # 驗證專案結構
    if not FRONTEND_SRC.exists():
        print(f"[FATAL] 前端目錄不存在: {FRONTEND_SRC}")
        return 1
    if not BACKEND_APP.exists():
        print(f"[FATAL] 後端目錄不存在: {BACKEND_APP}")
        return 1

    routes_defined = check_routes()
    check_navigation_sync(routes_defined)
    check_api_prefix_consistency()
    check_type_ssot()
    check_schema_orm_alignment()
    check_frontend_exports()
    check_backend_imports()

    return results.summary()


def run_single_check(name: str):
    """執行單項檢查"""
    print("=" * 60)
    print(f"  CK_Missive 架構驗證 - {name}")
    print("=" * 60)

    check_map = {
        "routes": lambda: check_routes(),
        "navigation": lambda: check_navigation_sync(check_routes()),
        "api": check_api_prefix_consistency,
        "ssot": check_type_ssot,
        "schema": check_schema_orm_alignment,
        "pages": check_frontend_exports,
        "imports": check_backend_imports,
    }

    if name not in check_map:
        print(f"[ERROR] 未知的檢查項目: {name}")
        print(f"可用項目: {', '.join(check_map.keys())}")
        return 1

    check_map[name]()
    return results.summary()


def main():
    global verbose

    parser = argparse.ArgumentParser(
        description="CK_Missive 架構驗證腳本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
檢查項目:
  routes     - 前後端路由一致性 (types.ts vs AppRouter.tsx)
  navigation - 導覽項目同步 (init_navigation_data.py vs ROUTES)
  api        - API 端點前綴一致性 (endpoints.ts vs routes.py)
  ssot       - 型別 SSOT 違規偵測
  schema     - Schema-ORM 欄位基礎對齊
  pages      - 前端頁面元件使用率
  imports    - 後端模組匯入安全

範例:
  python scripts/verify_architecture.py                # 完整檢查
  python scripts/verify_architecture.py --check routes # 僅檢查路由
  python scripts/verify_architecture.py --verbose      # 詳細輸出
        """,
    )
    parser.add_argument(
        "--check",
        type=str,
        help="僅執行指定的檢查項目",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="顯示詳細輸出",
    )

    args = parser.parse_args()
    verbose = args.verbose

    if args.check:
        return run_single_check(args.check)
    else:
        return run_all_checks()


if __name__ == "__main__":
    sys.exit(main())

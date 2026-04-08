"""
導覽路徑驗證器
確保導覽項目的路徑與前端路由定義一致

自動同步機制 (v2.0):
  VALID_NAVIGATION_PATHS 在模組載入時從 init_navigation_data.py 動態收集，
  不再需要手動維護白名單。新增路由只需更新 init_navigation_data.py 即可。

@version 2.0.0
@date 2026-04-01
"""
from typing import Set, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def _build_valid_paths() -> Set[str]:
    """
    從 init_navigation_data.py 的 DEFAULT_NAVIGATION_ITEMS 自動收集有效路徑，
    合併固定的系統路由（認證、錯誤頁面等不在導覽中但屬有效路徑）。
    """
    paths: Set[str] = set()

    # 1. 從導覽初始資料收集（導覽樹的所有 path）
    try:
        from app.scripts.init_navigation_data import DEFAULT_NAVIGATION_ITEMS
        for item in DEFAULT_NAVIGATION_ITEMS:
            if item.get("path"):
                paths.add(item["path"])
            for child in item.get("children", []):
                if child.get("path"):
                    paths.add(child["path"])
                for grandchild in child.get("children", []):
                    if grandchild.get("path"):
                        paths.add(grandchild["path"])
    except ImportError:
        logger.warning("無法載入 init_navigation_data，使用空白名單")

    # 2. 固定的系統路由（不在導覽樹中但屬有效路徑）
    paths.update({
        "/", "/entry", "/login", "/register", "/forgot-password",
        "/mfa/verify", "/reset-password", "/verify-email",
        "/auth/line/callback", "/auth/line/bind-callback",
        "/404", "/google-auth-diagnostic", "/unified-form-demo",
        "/api-mapping", "/api/docs", "/pure-calendar",
        # ERP 子頁面
        "/erp", "/erp/quotations", "/erp/quotations/create",
        "/erp/invoices/summary-view", "/erp/ledger", "/erp/ledger/create",
        "/erp/operational", "/erp/operational/create",
        # 管理子頁面
        "/admin/code-graph", "/admin/case-nature",
        # 標案子頁面
        "/tender/dashboard",
        "/tender/org-ecosystem",
        "/tender/company-profile",
        # AI / Agent
        "/agent/dashboard", "/ai/code-graph",
        # 承攬案件別名
        "/projects",
    })

    return paths


# 模組載入時自動構建白名單
VALID_NAVIGATION_PATHS: Set[str] = _build_valid_paths()


def _matches_dynamic_route(path: str) -> bool:
    """
    檢查路徑是否匹配已知路由的動態版本。
    例如 /erp/vendor-accounts/123 匹配白名單中的 /erp/vendor-accounts。
    也支援多段如 /documents/42/edit, /staff/1/certifications/create。
    """
    if path in VALID_NAVIGATION_PATHS:
        return True

    parts = path.rstrip("/").split("/")
    for i in range(len(parts) - 1, 0, -1):
        prefix = "/".join(parts[:i])
        if prefix in VALID_NAVIGATION_PATHS:
            remaining = parts[i:]
            if all(
                seg.isdigit() or seg in ("edit", "detail", "create", "delete", "update")
                for seg in remaining
            ):
                return True
    return False


def validate_navigation_path(path: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    驗證導覽路徑是否有效

    Args:
        path: 要驗證的路徑，可為 None（群組項目沒有路徑）

    Returns:
        Tuple[bool, Optional[str]]: (是否有效, 錯誤訊息)
    """
    if path is None or path == "":
        return True, None

    if not path.startswith("/"):
        return False, f"路徑必須以 '/' 開頭，收到: '{path}'"

    if _matches_dynamic_route(path):
        return True, None

    suggestions = get_similar_paths(path)
    suggestion_text = f"，建議路徑: {', '.join(suggestions)}" if suggestions else ""
    return False, f"無效的導覽路徑: '{path}'{suggestion_text}"


def get_similar_paths(invalid_path: str) -> list:
    """根據無效路徑找出可能的正確路徑建議"""
    suggestions = []
    path_lower = invalid_path.lower()

    for valid_path in VALID_NAVIGATION_PATHS:
        valid_lower = valid_path.lower()
        invalid_keywords = set(path_lower.replace("/admin/", "/").replace("/", " ").split())
        valid_keywords = set(valid_lower.replace("/admin/", "/").replace("/", " ").split())
        if invalid_keywords & valid_keywords:
            suggestions.append(valid_path)

    return suggestions[:3]


def get_all_valid_paths() -> list:
    """獲取所有有效路徑列表（用於前端下拉選單）"""
    result = [{"path": None, "description": "（無 - 群組項目）"}]

    # 從 init_navigation_data 收集描述
    descriptions = {}
    try:
        from app.scripts.init_navigation_data import DEFAULT_NAVIGATION_ITEMS
        for item in DEFAULT_NAVIGATION_ITEMS:
            if item.get("path"):
                descriptions[item["path"]] = item.get("title", item["path"])
            for child in item.get("children", []):
                if child.get("path"):
                    descriptions[child["path"]] = child.get("title", child["path"])
                for grandchild in child.get("children", []):
                    if grandchild.get("path"):
                        descriptions[grandchild["path"]] = grandchild.get("title", grandchild["path"])
    except ImportError:
        pass

    skip = {"/", "/login", "/register", "/forgot-password", "/404",
            "/mfa/verify", "/reset-password", "/verify-email",
            "/auth/line/callback", "/auth/line/bind-callback"}

    for path in sorted(VALID_NAVIGATION_PATHS):
        if path in skip:
            continue
        result.append({
            "path": path,
            "description": descriptions.get(path, path)
        })

    return result


def sync_check_with_frontend() -> dict:
    """檢查後端路徑白名單狀態"""
    return {
        "total_paths": len(VALID_NAVIGATION_PATHS),
        "paths": sorted(VALID_NAVIGATION_PATHS),
        "auto_sync": True,
        "source": "init_navigation_data.py + system routes",
        "frontend_reference": "frontend/src/router/types.ts"
    }

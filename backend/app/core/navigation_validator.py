"""
導覽路徑驗證器
確保導覽項目的路徑與前端路由定義一致

@version 1.0.0
@date 2026-01-12
"""
from typing import Set, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# 有效路徑白名單
# 必須與前端 frontend/src/router/types.ts 中的 ROUTES 保持同步
# =============================================================================
VALID_NAVIGATION_PATHS: Set[str] = {
    # 基礎頁面
    "/",
    "/entry",
    "/login",
    "/register",
    "/forgot-password",

    # 主要功能頁面
    "/dashboard",
    "/documents",
    "/document-numbers",
    "/contract-cases",
    "/agencies",
    "/vendors",
    "/staff",
    "/projects",
    "/calendar",
    "/pure-calendar",
    "/reports",
    "/profile",
    "/settings",

    # 管理頁面
    "/admin/database",
    "/admin/user-management",
    "/admin/site-management",
    "/admin/permissions",
    "/admin/dashboard",
    "/admin/backup",
    "/admin/deployment",
    "/admin/ai-assistant",

    # AI 功能
    "/ai/knowledge-graph",

    # 系統頁面
    "/system",
    "/google-auth-diagnostic",
    "/unified-form-demo",
    "/api-mapping",
    "/api/docs",

    # 專案專區
    "/taoyuan/dispatch",
}

# 路徑描述對照表（用於錯誤訊息和前端下拉選單）
PATH_DESCRIPTIONS = {
    "/": "首頁",
    "/entry": "系統入口",
    "/dashboard": "儀表板",
    "/documents": "公文管理",
    "/document-numbers": "發文字號管理",
    "/contract-cases": "承攬計畫",
    "/agencies": "機關管理",
    "/vendors": "廠商管理",
    "/staff": "承辦同仁",
    "/projects": "專案管理",
    "/calendar": "行事曆",
    "/pure-calendar": "專案行事曆",
    "/reports": "統計報表",
    "/profile": "個人資料",
    "/settings": "系統設定",
    "/admin/database": "資料庫管理",
    "/admin/user-management": "使用者管理",
    "/admin/site-management": "網站管理",
    "/admin/permissions": "權限管理",
    "/admin/dashboard": "管理員面板",
    "/admin/backup": "備份管理",
    "/admin/deployment": "部署管理",
    "/admin/ai-assistant": "AI 助理管理",
    "/ai/knowledge-graph": "知識圖譜",
    "/system": "系統監控",
    "/google-auth-diagnostic": "Google認證診斷",
    "/unified-form-demo": "統一表單示例",
    "/api-mapping": "API對應表",
    "/api/docs": "API文件",
    "/taoyuan/dispatch": "桃園查估派工",
}


def validate_navigation_path(path: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    驗證導覽路徑是否有效

    Args:
        path: 要驗證的路徑，可為 None（群組項目沒有路徑）

    Returns:
        Tuple[bool, Optional[str]]: (是否有效, 錯誤訊息)
    """
    # None 或空字串是有效的（群組項目）
    if path is None or path == "":
        return True, None

    # 檢查路徑格式
    if not path.startswith("/"):
        return False, f"路徑必須以 '/' 開頭，收到: '{path}'"

    # 檢查是否在白名單中
    if path not in VALID_NAVIGATION_PATHS:
        suggestions = get_similar_paths(path)
        suggestion_text = f"，建議路徑: {', '.join(suggestions)}" if suggestions else ""
        return False, f"無效的導覽路徑: '{path}'{suggestion_text}"

    return True, None


def get_similar_paths(invalid_path: str) -> list:
    """
    根據無效路徑找出可能的正確路徑建議

    Args:
        invalid_path: 無效的路徑

    Returns:
        list: 可能的正確路徑列表
    """
    suggestions = []
    path_lower = invalid_path.lower()

    for valid_path in VALID_NAVIGATION_PATHS:
        # 檢查是否包含相同的關鍵字
        valid_lower = valid_path.lower()

        # 提取路徑中的關鍵字（去除 / 和 admin）
        invalid_keywords = set(path_lower.replace("/admin/", "/").replace("/", " ").split())
        valid_keywords = set(valid_lower.replace("/admin/", "/").replace("/", " ").split())

        # 如果有共同關鍵字，加入建議
        if invalid_keywords & valid_keywords:
            suggestions.append(valid_path)

    return suggestions[:3]  # 最多返回 3 個建議


def get_all_valid_paths() -> list:
    """
    獲取所有有效路徑列表（用於前端下拉選單）

    Returns:
        list: 包含 path 和 description 的字典列表
    """
    result = [{"path": None, "description": "（無 - 群組項目）"}]

    for path in sorted(VALID_NAVIGATION_PATHS):
        if path in ("/", "/login", "/register", "/forgot-password"):
            continue  # 跳過不適合作為導覽項目的路徑

        result.append({
            "path": path,
            "description": PATH_DESCRIPTIONS.get(path, path)
        })

    return result


def sync_check_with_frontend() -> dict:
    """
    檢查後端路徑白名單是否需要與前端同步
    此函數可用於開發時的一致性檢查

    Returns:
        dict: 檢查結果
    """
    return {
        "total_paths": len(VALID_NAVIGATION_PATHS),
        "paths": sorted(VALID_NAVIGATION_PATHS),
        "last_updated": "2026-01-12",
        "frontend_reference": "frontend/src/router/types.ts"
    }

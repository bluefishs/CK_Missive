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
    "/clients",
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
    "/admin/knowledge-base",
    "/admin/login-history",
    "/admin/security-center",
    "/admin/case-nature",

    # AI 功能
    "/ai/knowledge-graph",
    "/ai/skills-map",
    "/ai/code-wiki",
    "/ai/code-graph",
    "/ai/db-graph",
    "/ai/skill-evolution",
    "/ai/digital-twin",
    # 系統頁面
    "/system",
    "/google-auth-diagnostic",
    "/unified-form-demo",
    "/api-mapping",
    "/api/docs",

    # 專案專區
    "/taoyuan/dispatch",

    # PM 案件管理
    "/pm/cases",

    # ERP 財務管理
    "/erp",
    "/erp/quotations",
    "/erp/quotations/create",
    "/erp/expenses",
    "/erp/expenses/create",
    "/erp/ledger",
    "/erp/ledger/create",
    "/erp/financial-dashboard",
    "/erp/einvoice-sync",
    "/erp/vendor-accounts",
    "/erp/client-accounts",
    "/erp/invoices/summary-view",
    "/erp/assets",
    "/erp/assets/create",
    "/erp/operational",
    "/erp/operational/create",

    # Create 路由
    "/documents/create",
    "/contract-cases/create",
    "/agencies/create",
    "/vendors/create",
    "/clients/create",
    "/staff/create",
    "/calendar/event/new",
    "/taoyuan/dispatch/create",
    "/taoyuan/project/create",
    "/admin/user-management/create",

    # 管理頁面補齊
    "/admin/code-graph",

    # 認證/系統頁面
    "/mfa/verify",
    "/reset-password",
    "/verify-email",
    "/auth/line/callback",
    "/auth/line/bind-callback",
    "/404",
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
    "/admin/knowledge-base": "知識庫瀏覽器",
    "/admin/security-center": "資安管理中心",
    "/admin/case-nature": "作業性質代碼管理",
    "/admin/login-history": "登入歷史",
    "/ai/knowledge-graph": "公文圖譜",
    "/ai/skills-map": "Skills 能力圖譜",
    "/ai/code-wiki": "代碼圖譜（舊路由）",
    "/ai/code-graph": "代碼圖譜",
    "/ai/db-graph": "資料庫圖譜",
    "/ai/skill-evolution": "技能演化樹",
    "/system": "系統監控",
    "/google-auth-diagnostic": "Google認證診斷",
    "/unified-form-demo": "統一表單示例",
    "/api-mapping": "API對應表",
    "/api/docs": "API文件",
    "/taoyuan/dispatch": "桃園查估派工",
    "/pm/cases": "PM 案件管理",
    "/erp": "ERP 財務管理中心",
    "/erp/quotations": "ERP 報價管理",
    "/erp/quotations/create": "新增報價",
    "/erp/expenses": "費用報銷管理",
    "/erp/expenses/create": "新增費用報銷",
    "/erp/ledger": "統一帳本",
    "/erp/ledger/create": "新增帳本記錄",
    "/erp/financial-dashboard": "財務儀表板",
    "/erp/einvoice-sync": "電子發票同步",
    "/erp/vendor-accounts": "廠商帳款管理",
    "/erp/client-accounts": "委託單位帳款",
    "/erp/invoices/summary-view": "發票跨案件查詢",
    "/erp/assets": "資產管理",
    "/erp/assets/create": "新增資產",
    "/erp/operational": "營運帳目",
    "/erp/operational/create": "新增營運帳目",
    "/documents/create": "新增公文",
    "/contract-cases/create": "新增承攬案件",
    "/agencies/create": "新增機關",
    "/vendors/create": "新增廠商",
    "/clients/create": "新增委託單位",
    "/staff/create": "新增承辦同仁",
    "/calendar/event/new": "新增日曆事件",
    "/taoyuan/dispatch/create": "新增派工單",
    "/taoyuan/project/create": "新增工程",
    "/admin/user-management/create": "新增使用者",
    "/admin/code-graph": "代碼圖譜管理",
    "/mfa/verify": "MFA 驗證",
    "/reset-password": "重設密碼",
    "/verify-email": "Email 驗證",
    "/auth/line/callback": "LINE 登入回調",
    "/auth/line/bind-callback": "LINE 綁定回調",
    "/404": "頁面未找到",
}


def _matches_dynamic_route(path: str) -> bool:
    """
    檢查路徑是否匹配已知路由的動態版本。
    例如 /erp/vendor-accounts/123 匹配白名單中的 /erp/vendor-accounts。
    也支援多段如 /documents/42/edit, /staff/1/certifications/create。
    """
    # 精確匹配
    if path in VALID_NAVIGATION_PATHS:
        return True

    # 逐段縮短，檢查前綴是否在白名單中
    parts = path.rstrip("/").split("/")
    for i in range(len(parts) - 1, 0, -1):
        prefix = "/".join(parts[:i])
        if prefix in VALID_NAVIGATION_PATHS:
            # 確保剩餘部分看起來像動態段（數字 ID、edit、detail 等）
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
    # None 或空字串是有效的（群組項目）
    if path is None or path == "":
        return True, None

    # 檢查路徑格式
    if not path.startswith("/"):
        return False, f"路徑必須以 '/' 開頭，收到: '{path}'"

    # 精確匹配或動態路由匹配
    if _matches_dynamic_route(path):
        return True, None

    suggestions = get_similar_paths(path)
    suggestion_text = f"，建議路徑: {', '.join(suggestions)}" if suggestions else ""
    return False, f"無效的導覽路徑: '{path}'{suggestion_text}"


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
        "last_updated": "2026-04-01",
        "frontend_reference": "frontend/src/router/types.ts"
    }

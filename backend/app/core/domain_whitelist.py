"""
網域白名單與預設帳號設定

從 AuthService 提取的靜態工具函數。
用於 Google OAuth 登入時的網域驗證與新帳號預設設定。

Version: 1.0.0
Created: 2026-03-10
Extracted from: auth_service.py
"""

import json
import logging
from typing import List

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_allowed_domains() -> List[str]:
    """取得允許的 Google 網域清單"""
    domains_str = settings.GOOGLE_ALLOWED_DOMAINS or ""
    if not domains_str.strip():
        return []  # 空白表示允許所有
    return [d.strip().lower() for d in domains_str.split(",") if d.strip()]


def check_email_domain(email: str) -> bool:
    """
    檢查 email 是否在允許的網域內

    Returns:
        True 表示允許，False 表示拒絕
    """
    allowed_domains = get_allowed_domains()
    if not allowed_domains:
        return True  # 未設定白名單，允許所有

    email_domain = email.split("@")[-1].lower()
    is_allowed = email_domain in allowed_domains

    if not is_allowed:
        logger.warning(f"[AUTH] 網域被拒: {email_domain} 不在允許清單 {allowed_domains}")

    return is_allowed


def should_auto_activate() -> bool:
    """檢查新帳號是否應自動啟用"""
    return settings.AUTO_ACTIVATE_NEW_USER


def get_default_user_role() -> str:
    """取得新帳號預設角色"""
    return settings.DEFAULT_USER_ROLE or "user"


def get_default_permissions(role: str = None) -> str:
    """取得指定角色的預設權限（hardcoded fallback）。

    DEPRECATED — ADR-0034 後改為從 DB role_permissions 表讀取。
    本函數保留為 fallback：當 DB 不可達或 role 不存在時使用。

    優先順序（caller 需自行決定）：
    1. await RolePermissionsRepository.get_permissions(role) — 動態 SSOT
    2. get_default_permissions(role) — 本函數 fallback

    新建用戶請改用 `get_default_permissions_from_db(db, role)`（async）。
    """
    base_permissions = [
        "documents:read",
        "projects:read",
        "agencies:read",
        "vendors:read",
        "calendar:read",
    ]

    if role == "superuser":
        # superuser 用 wildcard，hasPermission 在前端短路
        return json.dumps(["*"])

    if role == "admin":
        admin_permissions = base_permissions + [
            "calendar:edit",
            "documents:create", "documents:edit", "documents:delete",
            "projects:create", "projects:edit", "projects:delete",
            "agencies:create", "agencies:edit", "agencies:delete",
            "vendors:create", "vendors:edit", "vendors:delete",
            "reports:view", "reports:export",
            "system_docs:read", "system_docs:create",
            "system_docs:edit", "system_docs:delete",
            "admin:users", "admin:settings",
            "admin:site_management", "admin:database",
        ]
        return json.dumps(admin_permissions)

    if role == "staff":
        return json.dumps(base_permissions + ["documents:create", "documents:edit"])

    return json.dumps(base_permissions)


async def get_default_permissions_from_db(db, role: str = None) -> str:
    """ADR-0034 — 從 DB role_permissions 表讀取（SSOT）。

    若 DB 查不到該 role → fallback 到 hardcoded `get_default_permissions(role)`。

    Args:
        db: AsyncSession
        role: 用戶角色

    Returns:
        JSON 序列化的 permission 字串
    """
    try:
        from app.repositories.role_permissions_repository import RolePermissionsRepository
        repo = RolePermissionsRepository(db)
        perms = await repo.get_permissions(role)
        if perms:
            return json.dumps(perms)
        logger.warning(
            "[ROLE-PERM] DB role_permissions 未找到 role=%s，fallback 到 hardcoded",
            role,
        )
    except Exception as e:
        logger.error(
            "[ROLE-PERM] DB lookup failed for role=%s: %s — fallback to hardcoded",
            role, e,
        )
    return get_default_permissions(role)

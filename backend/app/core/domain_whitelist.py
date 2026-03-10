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


def get_default_permissions() -> str:
    """取得新帳號預設權限"""
    default_permissions = [
        "documents:read",
        "projects:read",
        "agencies:read",
        "vendors:read",
        "calendar:read",
        "reports:view"
    ]
    return json.dumps(default_permissions)

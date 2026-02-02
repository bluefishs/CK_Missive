"""
認證模組共用依賴

提供 get_current_user、get_client_info、is_internal_ip、get_superuser_mock
供各子模組及外部匯入使用。
"""

import logging
import json
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.db.database import get_async_db
from app.core.auth_service import AuthService, security
from app.core.config import settings
from app.extended.models import User

logger = logging.getLogger(__name__)


def get_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """取得客戶端資訊"""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


def is_internal_ip(ip_address: Optional[str]) -> bool:
    """
    檢測是否為內網 IP
    內網 IP 範圍：
    - 10.x.x.x (Class A private)
    - 172.16-31.x.x (Class B private)
    - 192.168.x.x (Class C private)
    - localhost (127.0.0.1)
    """
    if not ip_address:
        return False

    import re as regex_module

    internal_patterns = [
        r"^10\.",
        r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",
        r"^192\.168\.",
        r"^127\.",
    ]

    return any(regex_module.match(pattern, ip_address) for pattern in internal_patterns)


def _get_dev_permissions() -> list[str]:
    """取得開發模式權限清單"""
    return [
        "documents:read",
        "documents:create",
        "documents:edit",
        "documents:delete",
        "projects:read",
        "projects:create",
        "projects:edit",
        "projects:delete",
        "agencies:read",
        "agencies:create",
        "agencies:edit",
        "agencies:delete",
        "vendors:read",
        "vendors:create",
        "vendors:edit",
        "vendors:delete",
        "calendar:read",
        "calendar:edit",
        "reports:view",
        "reports:export",
        "system_docs:read",
        "system_docs:create",
        "system_docs:edit",
        "system_docs:delete",
        "admin:users",
        "admin:settings",
        "admin:site_management",
        "admin:database",
    ]


def get_superuser_mock() -> User:
    """返回模擬的超級管理員使用者"""
    return User(
        id=1,
        email="superuser@dev.example",
        username="superuser",
        full_name="(Internal) SuperUser",
        is_active=True,
        is_admin=True,
        is_superuser=True,
        permissions=json.dumps(_get_dev_permissions()),
        role="superuser",
        auth_provider="internal",
        login_count=0,
        email_verified=True,
        created_at=datetime.utcnow(),
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    取得當前認證使用者 - 依賴注入函數

    權限控制說明：
    - 使用 settings.AUTH_DISABLED 環境變數控制開發模式
    - 生產環境必須設為 False
    - 開發模式下會返回模擬的超級管理員
    """
    if settings.AUTH_DISABLED:
        logger.warning("[AUTH] 開發模式 - 認證已停用，回傳模擬管理員使用者")
        dev_permissions = [
            "documents:read",
            "documents:create",
            "documents:edit",
            "documents:delete",
            "projects:read",
            "projects:create",
            "projects:edit",
            "projects:delete",
            "agencies:read",
            "agencies:create",
            "agencies:edit",
            "agencies:delete",
            "vendors:read",
            "vendors:create",
            "vendors:edit",
            "vendors:delete",
            "calendar:read",
            "calendar:edit",
            "reports:view",
            "reports:export",
            "system_docs:read",
            "system_docs:create",
            "system_docs:edit",
            "system_docs:delete",
            "admin:users",
            "admin:settings",
            "admin:site_management",
        ]

        return User(
            id=1,
            email="dev@example.com",
            username="dev-admin",
            full_name="開發者管理員",
            is_active=True,
            is_admin=True,
            is_superuser=True,
            permissions=json.dumps(dev_permissions),
            role="superuser",
            auth_provider="email",
            login_count=0,
            email_verified=True,
            created_at=datetime.utcnow(),
        )

    try:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未提供認證憑證",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials
        user = await AuthService.get_current_user_from_token(db, token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無效的認證憑證",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user
    except Exception as e:
        logger.error(f"get_current_user 發生錯誤: {e}")
        raise

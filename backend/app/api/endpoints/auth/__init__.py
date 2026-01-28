"""
認證模組

將原始 auth.py (752 行) 模組化為：
- common.py  - 共用依賴 (get_current_user, get_client_info 等)
- oauth.py   - OAuth 與登入端點 (/login, /google, /register)
- session.py - 會話管理端點 (/refresh, /logout, /check)
- profile.py - 個人資料端點 (/me, /profile/update, /password/change)

@version 3.0.0
@date 2026-01-28
"""

from fastapi import APIRouter

from .oauth import router as oauth_router
from .session import router as session_router
from .profile import router as profile_router

# 重要：re-export get_current_user 供外部模組匯入
from .common import get_current_user, get_client_info, is_internal_ip, get_superuser_mock

router = APIRouter()
router.include_router(oauth_router)
router.include_router(session_router)
router.include_router(profile_router)

__all__ = [
    "router",
    "get_current_user",
    "get_client_info",
    "is_internal_ip",
    "get_superuser_mock",
]

"""
認證模組

將原始 auth.py (752 行) 模組化為：
- common.py  - 共用依賴 (get_current_user, get_client_info 等)
- oauth.py   - OAuth 與登入端點 (/login, /google, /register)
- session.py - 會話管理端點 (/refresh, /logout, /check)
- sessions.py - 使用者 Session 管理端點 (/sessions, /sessions/revoke, /sessions/revoke-all)
- profile.py - 個人資料端點 (/me, /profile/update, /password/change)
- email_verify.py - Email 驗證端點 (/send-verification, /verify-email)
- mfa.py     - MFA 雙因素認證端點 (/mfa/setup, /mfa/verify, /mfa/disable, /mfa/validate)

@version 3.3.0
@date 2026-02-08
"""

from fastapi import APIRouter

from .oauth import router as oauth_router
from .session import router as session_router
from .sessions import router as sessions_router
from .profile import router as profile_router
from .password_reset import router as password_reset_router
from .login_history import router as login_history_router
from .email_verify import router as email_verify_router
from .mfa import router as mfa_router

# 重要：re-export get_current_user 供外部模組匯入
from .common import get_current_user, get_client_info, is_internal_ip, get_superuser_mock

router = APIRouter()
router.include_router(oauth_router)
router.include_router(session_router)
router.include_router(sessions_router)
router.include_router(profile_router)
router.include_router(password_reset_router)
router.include_router(login_history_router)
router.include_router(email_verify_router)
router.include_router(mfa_router)

__all__ = [
    "router",
    "get_current_user",
    "get_client_info",
    "is_internal_ip",
    "get_superuser_mock",
]

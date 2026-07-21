"""CK SSO Cookie 驗證 — re-export shim（2026-07-22 Phase 1）。

內容已遷入 Tier 1 共享套件 `ck_auth.sso`（import 式單一源，取代 4 repo copy）。
本檔降為薄 re-export，維持既有 `from app.core.ck_sso import ...` 呼叫點**零改**。
改 JWT/JWKS 驗證邏輯＝改 `shared-modules/ck-auth-py/src/ck_auth/sso.py` 一處 + bump 版本
+ consumer 換 wheel（見 docs/runbooks/tier1-shared-package-sop.md），不再逐 repo 改。

對應簽發端（同一 JWT 契約另一端）：CK_Website `functions/auth/_lib/jwt.ts`（RS256/HS256）。
"""

from ck_auth.sso import (  # noqa: F401  (re-export)
    CK_SSO_ALGORITHM_HS,
    CK_SSO_ALGORITHM_RS,
    CK_SSO_ISSUER,
    CKSSOEmployee,
    DEFAULT_JWKS_URL,
    JWKS_CACHE_TTL_SEC,
    JWKS_FETCH_TIMEOUT_SEC,
    clear_jwks_cache,
    get_jwks_cache_info,
    has_system_permission,
    verify_ck_sso_jwt,
    verify_ck_sso_jwt_auto,
    verify_ck_sso_jwt_rs256,
)

__all__ = [
    "CK_SSO_ALGORITHM_HS",
    "CK_SSO_ALGORITHM_RS",
    "CK_SSO_ISSUER",
    "CKSSOEmployee",
    "DEFAULT_JWKS_URL",
    "JWKS_CACHE_TTL_SEC",
    "JWKS_FETCH_TIMEOUT_SEC",
    "clear_jwks_cache",
    "get_jwks_cache_info",
    "has_system_permission",
    "verify_ck_sso_jwt",
    "verify_ck_sso_jwt_auto",
    "verify_ck_sso_jwt_rs256",
]

"""
CK SSO Cookie 驗證模組

驗證來自 www.cksurvey.tw 的 ck_employee / ck_employee_rs SSO JWT cookie。

對應端：Cloudflare Pages Functions `functions/auth/_lib/jwt.ts`（CK_Website repo）

v2.0 (2026-05-24) — ADR-0008 階段 2 落地：
    - 加 verify_ck_sso_jwt_rs256()：RS256 path + jwks fetch + in-memory cache
    - 加 verify_ck_sso_jwt_auto()：智能 dispatcher（優先 RS256，fallback HS256）
    - 保留 verify_ck_sso_jwt()：HS256 path 向後相容（W8 退場前仍可用）
    - 對應 CK_Website#0003 RS256 dual-sign 已 W2 production live (5/22)
    - 結構性根除 L41 secret drift 譜系

v1.2 (2026-05-22) — role claim deprecation (ADR-0002)
v1.1 (2026-05-21) — log debug→warning (L37 反模式修法)
v1.0 (2026-05-20) — HS256 only
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional

import jwt as pyjwt
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import PyJWTError

logger = logging.getLogger(__name__)

CK_SSO_ISSUER = "cksurvey.tw"
CK_SSO_ALGORITHM_HS = "HS256"
CK_SSO_ALGORITHM_RS = "RS256"
DEFAULT_JWKS_URL = "https://www.cksurvey.tw/.well-known/jwks.json"
JWKS_CACHE_TTL_SEC = 3600  # 1 hr
JWKS_FETCH_TIMEOUT_SEC = 5


@dataclass(frozen=True)
class CKSSOEmployee:
    """通過 SSO 驗證的員工身份（來自 ck_employee / ck_employee_rs cookie）

    v2.0：加 jti（給 ADR-0007 session blacklist 用，可選）
    """
    email: str
    name: str
    role: str  # platform_role；admin | hr | employee
    systems: tuple[str, ...]
    exp: int
    jti: Optional[str] = None  # v2.0: ADR-0007 session blacklist


# ─── JWKS in-memory cache（per process）──────────────────────
_jwks_cache: dict = {}
_jwks_cache_lock = threading.Lock()


def _fetch_jwks(jwks_url: str) -> Optional[dict]:
    """Fetch JWKS from URL with TTL cache. Returns None on failure (fail-open)."""
    now = time.time()
    with _jwks_cache_lock:
        cached = _jwks_cache.get(jwks_url)
        if cached and (now - cached["at"]) < JWKS_CACHE_TTL_SEC:
            return cached["data"]

    try:
        req = urllib.request.Request(jwks_url, headers={"User-Agent": "ck-sso-py/2.0"})
        with urllib.request.urlopen(req, timeout=JWKS_FETCH_TIMEOUT_SEC) as resp:
            if resp.status != 200:
                logger.warning("[CK_SSO_RS] jwks fetch non-200: %s %s", resp.status, jwks_url)
                return None
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning("[CK_SSO_RS] jwks fetch failed: %s: %s", type(e).__name__, e)
        return None

    with _jwks_cache_lock:
        _jwks_cache[jwks_url] = {"at": now, "data": data}
    return data


def _get_public_key_by_kid(jwks: dict, kid: str):
    """Extract public key matching kid from JWKS."""
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return RSAAlgorithm.from_jwk(json.dumps(key_data))
    return None


def verify_ck_sso_jwt_rs256(
    token: str,
    jwks_url: str = DEFAULT_JWKS_URL,
) -> Optional[CKSSOEmployee]:
    """
    驗證 RS256 簽章 JWT（ADR-0003 W2+，從 ck_employee_rs cookie 取得）。

    流程：
        1. 解 JWT header 取 kid
        2. 從 jwks_url fetch JWKS（in-memory cache 1hr）
        3. 用對應 kid 公鑰驗 RS256
        4. 驗 iss / exp / required claims
        5. return CKSSOEmployee 或 None

    Failure modes:
        - jwks fetch fail → return None（caller 可 fallback HS256）
        - kid 不在 jwks → return None
        - 其他驗證失敗 → return None + warning log
    """
    if not token:
        logger.warning("[CK_SSO_RS] verify aborted: empty token")
        return None

    try:
        unverified_header = pyjwt.get_unverified_header(token)
    except PyJWTError as e:
        logger.warning("[CK_SSO_RS] header parse failed: %s", e)
        return None

    kid = unverified_header.get("kid")
    if not kid:
        logger.warning("[CK_SSO_RS] JWT header missing kid (not RS256-signed?)")
        return None

    jwks = _fetch_jwks(jwks_url)
    if not jwks:
        return None  # caller fallback HS256

    public_key = _get_public_key_by_kid(jwks, kid)
    if not public_key:
        logger.warning("[CK_SSO_RS] kid=%s not in jwks (cache stale? rotate?)", kid)
        # 強制 refresh cache 後重試一次（key rotation 情境）
        with _jwks_cache_lock:
            _jwks_cache.pop(jwks_url, None)
        jwks = _fetch_jwks(jwks_url)
        if jwks:
            public_key = _get_public_key_by_kid(jwks, kid)
        if not public_key:
            logger.warning("[CK_SSO_RS] kid=%s still not in jwks after refresh", kid)
            return None

    try:
        payload = pyjwt.decode(
            token,
            public_key,
            algorithms=[CK_SSO_ALGORITHM_RS],
            issuer=CK_SSO_ISSUER,
            options={"require": ["sub", "name", "systems", "exp", "iss"]},
        )
    except pyjwt.ExpiredSignatureError as e:
        logger.warning("[CK_SSO_RS] JWT EXPIRED: %s", e)
        return None
    except pyjwt.InvalidSignatureError as e:
        logger.warning("[CK_SSO_RS] JWT SIGNATURE INVALID: %s (kid=%s)", e, kid)
        return None
    except pyjwt.InvalidIssuerError as e:
        logger.warning("[CK_SSO_RS] JWT ISSUER INVALID: %s", e)
        return None
    except PyJWTError as e:
        logger.warning("[CK_SSO_RS] JWT verify failed: %s: %s", type(e).__name__, e)
        return None

    return _payload_to_employee(payload, "RS")


def verify_ck_sso_jwt(token: str, secret: str) -> Optional[CKSSOEmployee]:
    """
    驗證 HS256 簽章 JWT（v1.x 既有，從 ck_employee cookie 取得）。

    v1.x 行為完全保留 — W8 退場前 4 子系統可繼續用。
    v2.0 新呼叫建議改用 verify_ck_sso_jwt_auto() 走 RS256 優先。

    Args:
        token: 從 ck_employee cookie 取出的 JWT 字串
        secret: CK_SSO_JWT_SECRET（需與 Cloudflare Pages JWT_SECRET 一致）

    Returns:
        CKSSOEmployee — 驗證成功
        None — 簽章錯誤 / 過期 / iss 不符 / 格式不對
    """
    if not token or not secret:
        logger.warning(
            "[CK_SSO] verify aborted: token_empty=%s secret_empty=%s",
            not token, not secret,
        )
        return None

    try:
        payload = pyjwt.decode(
            token,
            secret,
            algorithms=[CK_SSO_ALGORITHM_HS],
            issuer=CK_SSO_ISSUER,
            options={"require": ["sub", "name", "systems", "exp", "iss"]},
        )
    except pyjwt.ExpiredSignatureError as e:
        logger.warning("[CK_SSO] JWT EXPIRED: %s (需重新從 www.cksurvey.tw 登入)", e)
        return None
    except pyjwt.InvalidSignatureError as e:
        logger.warning(
            "[CK_SSO] JWT SIGNATURE INVALID: %s "
            "(可能：backend CK_SSO_JWT_SECRET 與 CF Pages JWT_SECRET 不一致)",
            e,
        )
        return None
    except pyjwt.InvalidIssuerError as e:
        logger.warning("[CK_SSO] JWT ISSUER INVALID: %s (期待 iss=%s)", e, CK_SSO_ISSUER)
        return None
    except pyjwt.MissingRequiredClaimError as e:
        logger.warning("[CK_SSO] JWT MISSING CLAIM: %s", e)
        return None
    except PyJWTError as e:
        logger.warning("[CK_SSO] JWT verify failed (other): %s: %s", type(e).__name__, e)
        return None

    return _payload_to_employee(payload, "HS")


def verify_ck_sso_jwt_auto(
    cookies: dict,
    secret: Optional[str] = None,
    jwks_url: str = DEFAULT_JWKS_URL,
) -> Optional[CKSSOEmployee]:
    """
    智能 dispatcher（v2.0 推薦）：

    1. 優先取 ck_employee_rs cookie → 用 RS256 path（jwks 公鑰）
    2. fallback 取 ck_employee cookie → 用 HS256 path（CK_SSO_JWT_SECRET）
    3. 兩個都失敗 → return None

    使用情境：
        - W2~W7 過渡期：兩 cookie 都會被 CF Pages 設，dispatcher 自然優先 RS256
        - W8+：CF Pages 只設 ck_employee_rs，HS path 自然 idle
        - secret=None：純 RS256 模式（W8+ 場景）

    Args:
        cookies: dict — 通常為 {cookie_name: value}
                例 FastAPI: request.cookies
        secret: HS256 secret（若仍要 fallback）；None = 強制 RS256-only
        jwks_url: 預設 https://www.cksurvey.tw/.well-known/jwks.json

    Returns:
        CKSSOEmployee 或 None
    """
    # 優先 RS256
    rs_token = cookies.get("ck_employee_rs")
    if rs_token:
        result = verify_ck_sso_jwt_rs256(rs_token, jwks_url=jwks_url)
        if result:
            logger.debug("[CK_SSO_AUTO] verified via RS256 path")
            return result
        logger.info("[CK_SSO_AUTO] RS256 cookie present but verify failed; trying HS256 fallback")

    # Fallback HS256
    hs_token = cookies.get("ck_employee")
    if hs_token and secret:
        result = verify_ck_sso_jwt(hs_token, secret)
        if result:
            logger.debug("[CK_SSO_AUTO] verified via HS256 path (fallback)")
            return result

    if not rs_token and not hs_token:
        logger.debug("[CK_SSO_AUTO] no SSO cookie present")
    return None


# ─── 共用 helper ────────────────────────────────────────────


def _payload_to_employee(payload: dict, alg_tag: str) -> Optional[CKSSOEmployee]:
    """JWT payload → CKSSOEmployee。alg_tag 'HS' or 'RS' 給 log。"""
    try:
        email = str(payload["sub"]).lower().strip()
        systems_raw = payload.get("systems") or []
        if not isinstance(systems_raw, list):
            logger.warning(
                "[CK_SSO_%s] payload.systems must be list, got %s",
                alg_tag, type(systems_raw).__name__,
            )
            return None
        systems = tuple(str(s) for s in systems_raw)

        # v1.2 (ADR-0002): platform_role 優先；role 為舊欄位 fallback；都缺則預設 employee
        role_value = payload.get("platform_role") or payload.get("role") or "employee"

        # v2.0: jti（ADR-0007 session blacklist 用，可選）
        jti = payload.get("jti")

        return CKSSOEmployee(
            email=email,
            name=str(payload["name"]),
            role=str(role_value),
            systems=systems,
            exp=int(payload["exp"]),
            jti=str(jti) if jti else None,
        )
    except (KeyError, TypeError, ValueError) as e:
        logger.warning(
            "[CK_SSO_%s] payload shape unexpected: %s: %s (keys=%s)",
            alg_tag, type(e).__name__, e,
            list(payload.keys()) if isinstance(payload, dict) else "N/A",
        )
        return None


def has_system_permission(employee: CKSSOEmployee, system: str) -> bool:
    """檢查員工是否有指定系統的權限（systems 清單包含 system）"""
    return system in employee.systems


# ─── v2.0 cache 管理 (testing / debug 用) ────────────────────


def clear_jwks_cache() -> None:
    """清 jwks cache（測試 / key rotation 後 force refresh 用）"""
    with _jwks_cache_lock:
        _jwks_cache.clear()


def get_jwks_cache_info() -> dict:
    """回 cache 內容摘要（debug 用）"""
    with _jwks_cache_lock:
        return {
            url: {"cached_at": entry["at"], "age_sec": time.time() - entry["at"], "keys_count": len(entry["data"].get("keys", []))}
            for url, entry in _jwks_cache.items()
        }

"""
CK SSO Cookie 驗證模組

驗證來自 www.cksurvey.tw 的 ck_employee SSO JWT cookie。

對應端：Cloudflare Pages Functions `functions/auth/_lib/jwt.ts`（CK_Website repo）
規格：
    - 演算法：HS256
    - issuer：cksurvey.tw
    - claims：sub (email) / name / role / systems / iat / exp / iss
    - 預設 TTL：4 小時（由簽發端控制，本端僅檢查 exp）

設計原則（依 ADR-0001 員工 SSO 策略）：
    - 「加成式」並存：不取代任何既有 Missive 認證機制
    - feature flag CK_SSO_ENABLED 控制（預設 False，灰度上線）
    - secret 透過 CK_SSO_JWT_SECRET 環境變數注入

v1.0 - 2026-05-20
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import jwt as pyjwt
from jwt.exceptions import PyJWTError

logger = logging.getLogger(__name__)

CK_SSO_ISSUER = "cksurvey.tw"
CK_SSO_ALGORITHM = "HS256"


@dataclass(frozen=True)
class CKSSOEmployee:
    """通過 SSO 驗證的員工身份（來自 ck_employee cookie）"""
    email: str
    name: str
    role: str
    systems: tuple[str, ...]
    exp: int


def verify_ck_sso_jwt(token: str, secret: str) -> Optional[CKSSOEmployee]:
    """
    驗證 CK SSO JWT。

    Args:
        token: 從 ck_employee cookie 取出的 JWT 字串
        secret: CK_SSO_JWT_SECRET（需與 Cloudflare Pages JWT_SECRET 一致）

    Returns:
        CKSSOEmployee 物件 — 驗證成功
        None — 簽章錯誤 / 過期 / iss 不符 / 格式不對 / 必要欄位缺失
    """
    if not token or not secret:
        return None

    try:
        payload = pyjwt.decode(
            token,
            secret,
            algorithms=[CK_SSO_ALGORITHM],
            issuer=CK_SSO_ISSUER,
            options={"require": ["sub", "name", "role", "systems", "exp", "iss"]},
        )
    except PyJWTError as e:
        logger.debug("[CK_SSO] JWT verify failed: %s", e)
        return None

    try:
        email = str(payload["sub"]).lower().strip()
        systems_raw = payload.get("systems") or []
        if not isinstance(systems_raw, list):
            return None
        systems = tuple(str(s) for s in systems_raw)

        return CKSSOEmployee(
            email=email,
            name=str(payload["name"]),
            role=str(payload["role"]),
            systems=systems,
            exp=int(payload["exp"]),
        )
    except (KeyError, TypeError, ValueError) as e:
        logger.debug("[CK_SSO] payload shape unexpected: %s", e)
        return None


def has_system_permission(employee: CKSSOEmployee, system: str) -> bool:
    """檢查員工是否有指定系統的權限（systems 清單包含 system）"""
    return system in employee.systems

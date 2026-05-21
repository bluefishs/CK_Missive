"""ck-sso-py v1.0 — verify_ck_sso_jwt unit tests (L41 教訓制度化)

鎖定 4 種 JWT exception 分別產出可見 logger.warning（非 silent debug）。
任一 exception 處理回退 logger.debug → 重蹈 L41 6 天 dormant 事故。

對應：
- CK_Missive#ck-sso-py v1.0 manifest §key_design_decisions
- Lesson L41 §修法第 1 條（verify_ck_sso_jwt 4 種 exception 各自 warning）
- SSO-IMPLEMENTATION-STATUS.md §跨 repo 套用 SOP Step 4 acceptance check 2

每個 consumer install 後跑此 test：4/4 PASS 才算 ck_sso.py 真活。
"""
import time
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest

from app.core.ck_sso import (
    CKSSOEmployee,
    has_system_permission,
    verify_ck_sso_jwt,
)


SECRET = "test_secret_64char_hex_d4479c601c5a086b27b853589b78751d04112bb46360"
ISSUER = "cksurvey.tw"


def _build_payload(**overrides):
    """組標準 payload，allow override 任意欄位"""
    base = {
        "iss": ISSUER,
        "sub": "test@cksurvey.tw",
        "name": "Test User",
        "role": "admin",
        "systems": ["missive", "lvrland", "pile"],
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    base.update(overrides)
    return base


def _sign(payload, secret=SECRET):
    return pyjwt.encode(payload, secret, algorithm="HS256")


# ─── 正向 cases ───────────────────────────────────────────────


def test_verify_ok_returns_employee():
    """正常 JWT → 回 CKSSOEmployee dataclass"""
    token = _sign(_build_payload())
    result = verify_ck_sso_jwt(token, SECRET)

    assert result is not None
    assert isinstance(result, CKSSOEmployee)
    assert result.email == "test@cksurvey.tw"
    assert result.name == "Test User"
    assert result.role == "admin"
    assert "missive" in result.systems
    assert "lvrland" in result.systems


def test_email_normalized_to_lowercase_trimmed():
    """email 自動 lowercase + strip"""
    token = _sign(_build_payload(sub="  USER@CKSURVEY.TW  "))
    result = verify_ck_sso_jwt(token, SECRET)

    assert result is not None
    assert result.email == "user@cksurvey.tw"


# ─── L41 reproduce: 4 種 JWT exception 各自 warning ────────


def test_signature_invalid_returns_none_with_warning(caplog):
    """L41 主因：secret drift → InvalidSignatureError → 必須 warning 級可見"""
    token = _sign(_build_payload(), secret="WRONG_SECRET")

    with caplog.at_level("WARNING", logger="app.core.ck_sso"):
        result = verify_ck_sso_jwt(token, SECRET)

    assert result is None
    # L41 必驗：log message 含「SIGNATURE INVALID」+「secret 不一致」提示
    assert any("SIGNATURE INVALID" in rec.message for rec in caplog.records), (
        f"L41 regression: missing SIGNATURE INVALID warning. "
        f"Got: {[r.message for r in caplog.records]}"
    )


def test_expired_token_returns_none_with_warning(caplog):
    """exp 已過 → ExpiredSignatureError → warning 級「EXPIRED」"""
    token = _sign(_build_payload(
        iat=int(time.time()) - 7200,
        exp=int(time.time()) - 3600,  # 1 小時前已過
    ))

    with caplog.at_level("WARNING", logger="app.core.ck_sso"):
        result = verify_ck_sso_jwt(token, SECRET)

    assert result is None
    assert any("EXPIRED" in rec.message for rec in caplog.records), (
        f"Expected EXPIRED warning. Got: {[r.message for r in caplog.records]}"
    )


def test_wrong_issuer_returns_none_with_warning(caplog):
    """iss != cksurvey.tw → InvalidIssuerError → warning 級「ISSUER INVALID」"""
    token = _sign(_build_payload(iss="evil.example.com"))

    with caplog.at_level("WARNING", logger="app.core.ck_sso"):
        result = verify_ck_sso_jwt(token, SECRET)

    assert result is None
    assert any("ISSUER INVALID" in rec.message for rec in caplog.records)


def test_missing_required_claim_returns_none_with_warning(caplog):
    """缺 required claim → MissingRequiredClaimError → warning 級「MISSING CLAIM」"""
    payload = _build_payload()
    del payload["systems"]  # 故意缺
    token = _sign(payload)

    with caplog.at_level("WARNING", logger="app.core.ck_sso"):
        result = verify_ck_sso_jwt(token, SECRET)

    assert result is None
    assert any("MISSING CLAIM" in rec.message for rec in caplog.records)


# ─── Guard against silent failures (L37/L41) ────────────────


def test_empty_token_returns_none_with_warning(caplog):
    """空 token → warning（不可 silent return）"""
    with caplog.at_level("WARNING", logger="app.core.ck_sso"):
        result = verify_ck_sso_jwt("", SECRET)
    assert result is None
    assert any("token_empty" in rec.message for rec in caplog.records)


def test_empty_secret_returns_none_with_warning(caplog):
    """空 secret → warning（misconfig 必須被觀察到）"""
    with caplog.at_level("WARNING", logger="app.core.ck_sso"):
        result = verify_ck_sso_jwt("dummy_token", "")
    assert result is None
    assert any("secret_empty" in rec.message for rec in caplog.records)


# ─── has_system_permission ──────────────────────────────────


def test_has_system_permission_true():
    emp = CKSSOEmployee(
        email="x@y.z", name="X", role="admin",
        systems=("missive", "lvrland"), exp=0,
    )
    assert has_system_permission(emp, "missive") is True
    assert has_system_permission(emp, "lvrland") is True


def test_has_system_permission_false():
    emp = CKSSOEmployee(
        email="x@y.z", name="X", role="admin",
        systems=("missive",), exp=0,
    )
    assert has_system_permission(emp, "pile") is False
    assert has_system_permission(emp, "kg") is False

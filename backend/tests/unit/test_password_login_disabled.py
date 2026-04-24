"""Regression test ADR-0033 — /api/auth/login 必須停用（回 410 Gone）

防止未來誤 revert / 重新開啟帳密登入端點。
若資安評估後需重啟，請同步刪除此測試並更新 ADR-0033。
"""
import inspect

from app.api.endpoints.auth import oauth


def test_login_endpoint_raises_410_gone():
    """帳密登入 endpoint 必須無條件 raise HTTPException(410)"""
    src = inspect.getsource(oauth.login_for_access_token)
    assert "HTTP_410_GONE" in src, (
        "ADR-0033: /api/auth/login 必須回 410 Gone；檢到實作已偏離政策"
    )


def test_login_endpoint_has_security_warning_log():
    """嘗試登入必須打 SECURITY 級 warning log（防黑箱）"""
    src = inspect.getsource(oauth.login_for_access_token)
    assert "[SECURITY]" in src, (
        "ADR-0033: 帳密登入嘗試必須 logger.warning [SECURITY]，供資安監控"
    )


def test_login_endpoint_writes_audit_event():
    """嘗試必須寫入 auth audit（event_type=LOGIN_BLOCKED_PASSWORD_DISABLED）"""
    src = inspect.getsource(oauth.login_for_access_token)
    assert "LOGIN_BLOCKED_PASSWORD_DISABLED" in src, (
        "ADR-0033: 必須寫入 LOGIN_BLOCKED_PASSWORD_DISABLED 審計事件"
    )


def test_login_endpoint_does_not_invoke_authenticate_user():
    """endpoint 執行程式碼不得再呼叫 authenticate_user（表示繞過停用旗標）

    判別：排除 # 註解行後檢查，以免註解提及也被誤判。
    """
    src = inspect.getsource(oauth.login_for_access_token)
    code_lines = [
        ln for ln in src.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    code_only = "\n".join(code_lines)
    assert "authenticate_user" not in code_only, (
        "ADR-0033: 停用 endpoint 執行程式碼內不應呼叫 authenticate_user"
    )

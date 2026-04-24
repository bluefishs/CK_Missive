"""
回歸測試：UserResponse.model_validate 不得觸發 aliases lazy-load

2026-04-21 公網 500 事故根因：
  oauth.py 呼叫 AuthService.generate_login_response
  → UserResponse.model_validate(user)
  → getattr(obj, 'aliases', None) 觸發 SQLAlchemy lazy-load
  → MissingGreenlet（session 已離開 async 上下文）
  → 500 "Google 登入失敗"

修復：schemas/auth.py 改用 __dict__.get('aliases') 只讀已載入的屬性
"""
from datetime import datetime
from types import SimpleNamespace

from app.schemas.auth import UserResponse


def _fake_user(**overrides):
    """模擬 ORM user，具備 __dict__ 以便 schema 透過 __dict__.get 讀取"""
    now = datetime.utcnow()
    defaults = dict(
        id=1,
        email="alice@example.com",
        username="alice",
        full_name="Alice",
        role="user",
        is_active=True,
        is_admin=False,
        google_id="g-1",
        auth_provider="google",
        password_hash=None,
        line_user_id=None,
        mfa_enabled=False,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_validate_without_aliases_attr_does_not_raise():
    """無 aliases 屬性時不得爆炸"""
    user = _fake_user()
    resp = UserResponse.model_validate(user)
    assert resp.email == "alice@example.com"
    assert resp.alias_count == 0
    # google_id 存在 → auth_providers 至少有 google
    assert "google" in resp.auth_providers


def test_validate_with_eager_loaded_aliases():
    """aliases 已 eager-load 時正常聚合"""
    alias = _fake_user(id=2, email="alice-line@example.com", google_id=None, line_user_id="U-123", auth_provider="line")
    user = _fake_user()
    user.aliases = [alias]

    resp = UserResponse.model_validate(user)
    assert resp.alias_count == 1
    assert "alice-line@example.com" in (resp.alias_emails or [])
    # merged 應同時含 google + line
    assert "google" in (resp.merged_auth_providers or [])
    assert "line" in (resp.merged_auth_providers or [])


def test_lazy_load_attribute_not_triggered():
    """
    關鍵 regression：即使 getattr(obj, 'aliases') 會 raise（模擬 lazy-load 失敗），
    schema 也不得訪問到它。
    """
    class BoomOnGetattr:
        """任何 getattr('aliases') 都會 raise，模擬 SQLAlchemy MissingGreenlet"""
        def __init__(self):
            now = datetime.utcnow()
            self.__dict__.update(
                id=3,
                email="bob@example.com",
                username="bob",
                full_name="Bob",
                role="user",
                is_active=True,
                is_admin=False,
                google_id="g-3",
                auth_provider="google",
                password_hash=None,
                line_user_id=None,
                mfa_enabled=False,
                created_at=now,
                updated_at=now,
            )

        def __getattr__(self, name):
            if name == "aliases":
                raise RuntimeError("MissingGreenlet (simulated)")
            raise AttributeError(name)

    user = BoomOnGetattr()
    resp = UserResponse.model_validate(user)  # 不得爆
    assert resp.alias_count == 0
    assert resp.email == "bob@example.com"

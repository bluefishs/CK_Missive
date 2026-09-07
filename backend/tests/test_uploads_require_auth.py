# -*- coding: utf-8 -*-
"""`/uploads/*` 必須登入（2026-09-08 D6）。

此前是 StaticFiles 掛載——沒有 dependency 掛點，「所有端點都要認證」對它不成立，
1,642 個附件公網未登入 200。這支鎖三件事：未登入 401、登入後拿得到、路徑穿越拿不到。
"""
import os
import pytest
import httpx

os.environ.setdefault("CK_LOGS_DIR", os.path.join(os.path.dirname(__file__), "_logs"))
from main import app, UPLOADS_DIR  # noqa: E402
from app.core.dependencies import get_current_user  # noqa: E402
from app.core.config import settings  # noqa: E402


@pytest.fixture
def sample_file():
    d = UPLOADS_DIR / "_test"; d.mkdir(parents=True, exist_ok=True)
    f = d / "hello.txt"; f.write_text("hi", encoding="utf-8")
    yield "_test/hello.txt"
    f.unlink(missing_ok=True)


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c
    app.dependency_overrides.clear()


class _U:
    id = 1; role = "staff"; is_active = True; username = "t"; permissions = []


@pytest.mark.asyncio
async def test_anonymous_gets_401(client, sample_file, monkeypatch):
    # host .env 是 AUTH_DISABLED=true（開發），require_auth 會直接放行；
    # 這支要驗的是公網態（.env.production AUTH_DISABLED=false）
    monkeypatch.setattr(settings, "AUTH_DISABLED", False)
    # ASGITransport 的 peer 是 127.0.0.1 ⇒ 會走「內網可信網段」mock 放行（設計如此）；
    # 帶 CF 標頭模擬公網請求，才是 1,642 個附件被讀到的那條路
    r = await client.get(f"/uploads/{sample_file}",
                         headers={"CF-Connecting-IP": "203.0.113.9", "CF-Ray": "test", "X-Forwarded-For": "203.0.113.9"})
    assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_logged_in_gets_file(client, sample_file):
    app.dependency_overrides[get_current_user] = lambda: _U()
    r = await client.get(f"/uploads/{sample_file}")
    assert r.status_code == 200 and r.text == "hi"


@pytest.mark.asyncio
async def test_traversal_is_404(client, sample_file):
    app.dependency_overrides[get_current_user] = lambda: _U()
    # `/uploads/../.env` 會被 client 先正規化成 `/.env`，到不了本路由——只測編碼變體
    for bad in ("/uploads/..%2F..%2F.env", "/uploads/%2e%2e/%2e%2e/.env", "/uploads/_test/..%2F..%2F.env"):
        r = await client.get(bad)
        assert r.status_code in (404, 400), bad
        assert "POSTGRES" not in r.text, bad

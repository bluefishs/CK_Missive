# -*- coding: utf-8 -*-
"""`/uploads/*`：未登入 401、附件層級 403／200、路徑穿越 404（L148／A116）。

此前是 StaticFiles 掛載——沒有 dependency 掛點，「所有端點都要認證」對它不成立，
1,642 個附件公網未登入 200。09-08 晚起改為依路徑前綴判「誰能讀哪一類」。
"""
import os

import httpx
import pytest

os.environ.setdefault("CK_LOGS_DIR", os.path.join(os.path.dirname(__file__), "_logs"))
from main import app  # noqa: E402
from app.api.endpoints import uploads as up  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.dependencies import get_current_user  # noqa: E402

PUBLIC = {"CF-Connecting-IP": "203.0.113.9", "CF-Ray": "test"}


def _mk(rel: str) -> str:
    f = up.UPLOADS_DIR / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("hi", encoding="utf-8")
    return rel


@pytest.fixture
def files():
    rels = [_mk("certifications/user_7/a.pdf"), _mk("certifications/user_8/b.pdf"),
            _mk("receipts/r.jpg"), _mk("2026/01/doc_123/x.pdf"), _mk("_test/hello.txt")]
    yield rels
    for r in rels:
        (up.UPLOADS_DIR / r).unlink(missing_ok=True)


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c
    app.dependency_overrides.clear()


class _U:
    def __init__(self, uid=7, role="staff", perms=()):
        self.id = uid; self.role = role; self.is_active = True; self.username = f"u{uid}"
        self.permissions = list(perms); self.is_admin = role == "admin"


def _as(user):
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.mark.asyncio
async def test_anonymous_gets_401(client, files, monkeypatch):
    # host .env 是 AUTH_DISABLED=true；ASGITransport 的 peer 是 127.0.0.1 會走內網 mock 放行（設計如此），
    # 帶 CF 標頭模擬公網、關掉 AUTH_DISABLED，才是 1,642 個附件被讀到的那條路
    monkeypatch.setattr(settings, "AUTH_DISABLED", False)
    r = await client.get("/uploads/certifications/user_7/a.pdf", headers=PUBLIC)
    assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_own_certificate_ok_others_403(client, files, monkeypatch):
    # 09-09 weekly 24：這支與整套一起跑時會 200≠403 —— 頁面能力快取的 _load 用全域 engine，
    # 前面的測試關掉事件迴圈後它撞到「Event loop is closed」，而載入失敗的設計是退回「只要求登入」（放行）。
    # 這支要驗的是「非本人、無 /staff 頁權限 ⇒ 403」這條規則，不該依賴活的選單表；
    # 與下面 test_page_permission_gates_receipts 同一做法，把 /staff 的宣告釘成固定值。
    async def fake_pages(path):
        return ["staff:view"] if path == "/staff" else []
    monkeypatch.setattr(up, "permissions_for_page", fake_pages)
    _as(_U(uid=7))
    r = await client.get("/uploads/certifications/user_7/a.pdf")
    assert r.status_code == 200 and r.text == "hi"
    assert "no-store" in r.headers.get("cache-control", "") and "private" in r.headers.get("cache-control", "")
    r = await client.get("/uploads/certifications/user_8/b.pdf")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_reads_anything(client, files):
    _as(_U(uid=1, role="admin"))
    for rel in files:
        assert (await client.get(f"/uploads/{rel}")).status_code == 200, rel


@pytest.mark.asyncio
async def test_page_permission_gates_receipts(client, files, monkeypatch):
    async def fake_pages(path):
        return ["reports:expenses:view"] if path == "/erp/expenses" else ["reports:einvoice:view"]
    monkeypatch.setattr(up, "permissions_for_page", fake_pages)
    _as(_U(uid=7, perms=()))
    assert (await client.get("/uploads/receipts/r.jpg")).status_code == 403
    _as(_U(uid=7, perms=("reports:expenses:view",)))
    assert (await client.get("/uploads/receipts/r.jpg")).status_code == 200


@pytest.mark.asyncio
async def test_document_attachment_follows_document_rls(client, files, monkeypatch):
    calls = []
    async def fake_access(db, document_id, user):
        calls.append(document_id); return document_id == 123 and user.id == 7
    import app.api.endpoints.files.common as fc
    monkeypatch.setattr(fc, "check_document_access", fake_access)
    _as(_U(uid=7))
    assert (await client.get("/uploads/2026/01/doc_123/x.pdf")).status_code == 200
    _as(_U(uid=9))
    assert (await client.get("/uploads/2026/01/doc_123/x.pdf")).status_code == 403
    assert calls == [123, 123]


@pytest.mark.asyncio
async def test_unknown_prefix_admin_only(client, files):
    _as(_U(uid=7))
    assert (await client.get("/uploads/_test/hello.txt")).status_code == 403


@pytest.mark.asyncio
async def test_traversal_is_404(client, files):
    _as(_U(uid=1, role="admin"))
    # `/uploads/../.env` 會被 client 先正規化成 `/.env`，到不了本路由——只測編碼變體
    for bad in ("/uploads/..%2F..%2F.env", "/uploads/%2e%2e/%2e%2e/.env", "/uploads/_test/..%2F..%2F.env"):
        r = await client.get(bad)
        assert r.status_code in (404, 400), bad
        assert "POSTGRES" not in r.text, bad

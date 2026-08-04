# -*- coding: utf-8 -*-
"""
共用測試 Fixtures
Shared Test Fixtures

用法:
    pytest tests/ -v
    pytest tests/unit/ -v
    pytest tests/integration/ -v

v2.0.0 - 2026-01-26
- 新增 mock service fixtures
- 新增依賴注入測試替換機制
- 新增 mock 認證 fixtures
"""
import asyncio
from typing import AsyncGenerator, Generator, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlsplit, urlunsplit

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport

import sys
import os

# 將 backend 目錄加入 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.database import Base
from main import app


# ============================================================
# 對外通知封鎖（安全網，2026-07-31）
# ============================================================

@pytest.fixture(autouse=True)
def _block_outbound_notifications(request):
    """禁止測試對真實 LINE / Telegram 推播。

    事故（2026-07-31）：跑 `tests/unit/test_scheduler_failure_alert.py` 時，
    owner 的 LINE **真的收到兩則**「⚠️ 排程失敗 test_job / 錯誤: Something broke」。

    根因是**過期的 mock**：該測試 patch 的是 `get_telegram_bot_service`，
    但 `send_failure_alert` 早在 v6.12 就改走 `IntegrationFacade.push_admin_alert`
    → patch 攔不到任何東西 → 真的送出去。
    （測試看起來是隔離的、其實不是 —— 與當日其他「訊號不等於事實」同型。）

    危害不只是噪音：LINE 免費月配額 200 則本來就吃緊，跑一次測試就可能吃掉數則。

    本 fixture 為 **autouse 安全網**：預設攔截所有對外推播路徑。
    確實需要驗證推播內容的測試，請自行 patch 更內層的物件，或標記
    `@pytest.mark.allow_outbound` 明確豁免（豁免必須是刻意的、看得見的）。
    """
    if request.node.get_closest_marker("allow_outbound"):
        yield
        return

    # 攔法演進（同日兩次修正，記錄以免第三次踩）：
    #   v1 patch `LineBotService.push_message` → 把**受測方法本身**換掉，
    #      打斷兩個原本就安全的服務層測試。
    #   v2 改 patch `_call_line_api` / `_call_telegram_api` → 仍然攔太深：
    #      `test_line_monthly_quota_shortcircuit` 正是在測 `_call_line_api`，
    #      而它自己已 patch 了 httpx，本來就安全。
    #   v3（現行）**不替換任何方法，改為抽掉對外憑證**：
    #      服務啟動時讀 env 取 token，沒有 token 就不可能送出。
    #      需要驗證推播行為的測試都會自備 token（如 `_make_service()` 內
    #      patch.dict LINE_CHANNEL_ACCESS_TOKEN），因此完全不受影響。
    #      唯一仍以 patch 攔住的是 `IntegrationFacade.push_admin_alert`
    #      —— 它是跨通道扇出、也正是 07-31 事故真正外送的那一層。
    #   v4（2026-08-04）補上 **digest 緩衝**：08-03 把 5 個 job 由 Telegram 改走
    #      `line_digest_buffer` 後，這張網就漏了 —— 它擋的是「送出去」，而 digest
    #      是「寫進正式 Redis、明早晨報才送」。實測跑一次 unit test 就把 6 則假
    #      告警塞進 owner 隔天的晨報，且 weekly 的 test_suite_health 每週跑全套
    #      ⇒ 檢核機制自己會污染正式輸出。改法同樣是抽掉抵達正式狀態的能力
    #      （`CK_NOTIFY_TEST_ISOLATION`：digest 只寫同進程 in-memory、月配額計數改用拋棄式 key）。
    blanked = {
        "LINE_CHANNEL_ACCESS_TOKEN": "", "LINE_CHANNEL_SECRET": "",
        "LINE_BOT_ENABLED": "false", "LINE_ADMIN_USER_IDS": "",
        "TELEGRAM_BOT_TOKEN": "", "TELEGRAM_ADMIN_CHAT_ID": "",
        "TELEGRAM_ADMIN_PUSH_ENABLED": "false",
        "PROACTIVE_LINE_PUSH_ENABLED": "false",
        "CK_NOTIFY_TEST_ISOLATION": "1",
    }
    env_patcher = patch.dict(os.environ, blanked)
    env_patcher.start()
    patchers = [env_patcher]
    try:
        p = patch(
            "app.services.contracts.facades.integration.IntegrationFacade.push_admin_alert",
            new=AsyncMock(return_value=False),
        )
        p.start()
        patchers.append(p)
    except (AttributeError, ModuleNotFoundError, ImportError):
        pass
    try:
        yield
    finally:
        for p in patchers:
            p.stop()
        # digest in-memory fallback 不跨測試殘留（否則後一個測試會看到前一個的條目）
        try:
            from app.services.integration import line_digest_buffer as _ldb
            _ldb.reset_memory_buffer()
        except (ImportError, ModuleNotFoundError, AttributeError):
            pass


# ============================================================
# 事件迴圈 Fixtures
# ============================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """建立 session 範圍的事件迴圈

    注意: pytest-asyncio >= 0.23 建議使用 loop_scope 設定，
    但為保持與現有測試的相容性，保留此 fixture。
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================
# 資料庫 Fixtures
# ============================================================

def _dbname(url: str) -> str:
    """取連線字串裡的資料庫名（不含 query）。"""
    return urlsplit(url).path.lstrip("/").split("?")[0]


def _resolve_test_db_url() -> str:
    """決定測試資料庫連線字串，並確保它不是生產庫。

    2026-08-03 查證（更正先前記載）：
      - `db_engine` 原本傳 `settings.DATABASE_URL`（psycopg2 sync driver）給
        `create_async_engine` → **engine 根本建不起來**，所有 db_session 測試
        一直是 error 而非失敗，也因此並沒有真的寫到生產庫。
      - 真正會打生產庫的是 `client` fixture：它跑真 app，端點經 `get_async_db`
        走 `app.db.database.engine`（正確的 asyncpg URL）→ 連的是 ck_documents。

    所以本函式解出的 URL 有兩個用途：db_engine 自己用，以及 override app 的
    `get_async_db`，讓走 HTTP 的測試也落在測試庫。

    護欄比「有沒有設定」更重要：**設定寫錯時必須拒絕執行，而不是預設回生產庫**。
    """
    prod = settings.DATABASE_URL
    raw = (settings.TEST_DATABASE_URL or "").strip()
    if not raw:
        parts = urlsplit(prod)
        raw = urlunsplit(parts._replace(path=parts.path.rstrip("/") + "_test"))

    if not _dbname(raw):
        pytest.exit("無法解析測試資料庫名稱，拒絕執行測試。", returncode=3)
    if _dbname(raw) == _dbname(prod):
        pytest.exit(
            f"TEST_DATABASE_URL 與 DATABASE_URL 指向同一個資料庫"
            f"（{_dbname(prod)}），拒絕對生產資料庫執行測試。",
            returncode=3,
        )
    return raw.replace("postgresql://", "postgresql+asyncpg://")


TEST_DB_URL = _resolve_test_db_url()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """測試用資料庫引擎（指向 <db>_test，非生產庫）。

    連線耗盡的成因是「每個測試各建一個 engine，每個 engine 自帶連線池」——
    池裡的連線在測試結束後仍被持有，測試一多就把 PostgreSQL 連線吃光。

    先試過改 session scope 讓 engine 只建一次，**失敗**：engine 綁在建立時的
    event loop，而 pytest-asyncio 預設每個測試一個 loop，第二個測試起就是
    `RuntimeError: Event loop is closed`。改 loop_scope 得動全套 4203 個測試的
    執行模型，風險不成比例。

    改用 NullPool：維持 function scope（不跨 loop），但連線用完即關、不進池，
    所以也不會累積。代價是每次查詢重新連線，對測試而言可接受。
    """
    engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _route_app_db_to_test_db(db_engine):
    """讓走 HTTP 的測試也落在測試庫。

    `client` fixture 跑的是真的 app，端點透過 `get_async_db` 取 session ——
    不覆寫的話那條路徑連的是 **生產庫**（`app.db.database.engine` 是模組級全域）。
    這才是「測試打生產」的實際路徑，`db_session` 反而因為 driver 不對而從未連上。

    autouse 的成本很低：engine 是 lazy 的，純 unit test 不會因此產生連線。
    """
    from app.db.database import get_async_db

    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        async with maker() as session:
            yield session

    app.dependency_overrides[get_async_db] = _override
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_async_db, None)


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """建立測試用資料庫會話

    注意: 此 fixture 使用實際資料庫，適合整合測試
    如需隔離環境，請使用 in-memory SQLite
    """
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def isolated_db_session() -> AsyncGenerator[AsyncSession, None]:
    """建立隔離的記憶體資料庫會話

    適合單元測試，每次測試後自動清理
    """
    # 使用 SQLite 記憶體資料庫
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    # 建立所有表格
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def mock_db_session() -> MagicMock:
    """建立 Mock 資料庫會話

    用於純單元測試，不需要實際資料庫連線

    使用範例:
        def test_something(mock_db_session):
            mock_db_session.execute.return_value.scalars.return_value.all.return_value = [...]
    """
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


# ============================================================
# HTTP 客戶端 Fixtures
# ============================================================

@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """建立測試用 HTTP 客戶端

    每次測試後清理 app 的 DB 連線池，避免 Event loop is closed 錯誤。
    因為 app 的 engine 是模組級全域變數，連線池跨測試共享，
    若前一個測試的 event loop 已關閉，殘留的連線會導致後續測試失敗。

    使用範例:
        async def test_list_documents(client):
            response = await client.post("/api/documents-enhanced/list")
            assert response.status_code == 200
    """
    from app.db.database import engine as app_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # 清理 app 的 DB 連線池，防止跨測試 event loop 衝突
    await app_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(mock_current_user) -> AsyncGenerator[AsyncClient, None]:
    """建立已認證的測試用 HTTP 客戶端

    自動覆蓋認證依賴，使用 mock_current_user。
    每次測試後清理 app 的 DB 連線池，避免 Event loop is closed 錯誤。
    """
    from app.api.endpoints.auth import get_current_user
    from app.extended.models import User
    from app.db.database import engine as app_engine

    # 建立 mock User 物件
    mock_user = MagicMock(spec=User)
    mock_user.id = mock_current_user["id"]
    mock_user.username = mock_current_user["username"]
    mock_user.email = mock_current_user["email"]
    mock_user.is_active = mock_current_user["is_active"]
    mock_user.is_admin = mock_current_user["is_admin"]
    mock_user.is_superuser = mock_current_user.get("is_superuser", False)
    mock_user.role = mock_current_user["role"]

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # 清理覆蓋
    app.dependency_overrides.clear()

    # 清理 app 的 DB 連線池，防止跨測試 event loop 衝突
    await app_engine.dispose()


# ============================================================
# Mock Service Fixtures
# ============================================================

@pytest.fixture
def mock_document_service():
    """建立 Mock DocumentService

    使用範例:
        def test_something(mock_document_service):
            mock_document_service.get_documents.return_value = {...}
    """
    from app.services.document_service import DocumentService

    service = MagicMock(spec=DocumentService)

    # 預設回傳值
    service.get_documents = AsyncMock(return_value={
        "items": [],
        "total": 0,
        "page": 1,
        "limit": 20,
        "total_pages": 0
    })
    service.get_document_by_id = AsyncMock(return_value=None)
    service.create_document = AsyncMock(return_value=None)
    service.get_document_with_extra_info = AsyncMock(return_value=None)
    service.import_documents_from_processed_data = AsyncMock()

    return service


@pytest.fixture
def mock_vendor_service():
    """建立 Mock VendorService"""
    from app.services.vendor_service import VendorService

    service = MagicMock(spec=VendorService)
    service.get_list = AsyncMock(return_value=[])
    service.get_count = AsyncMock(return_value=0)
    service.get_by_id = AsyncMock(return_value=None)
    service.create = AsyncMock(return_value=None)
    service.update = AsyncMock(return_value=None)
    service.delete = AsyncMock(return_value=True)

    return service


@pytest.fixture
def mock_project_service():
    """建立 Mock ProjectService"""
    from app.services.project_service import ProjectService

    service = MagicMock(spec=ProjectService)
    service.get_projects = AsyncMock(return_value={
        "items": [],
        "total": 0,
        "page": 1,
        "limit": 20
    })
    service.get_project_by_id = AsyncMock(return_value=None)
    service.create = AsyncMock(return_value=None)
    service.update = AsyncMock(return_value=None)
    service.delete = AsyncMock(return_value=True)

    return service


@pytest.fixture
def mock_agency_service():
    """建立 Mock AgencyService"""
    from app.services.agency_service import AgencyService

    service = MagicMock(spec=AgencyService)
    service.get_agencies = AsyncMock(return_value={
        "items": [],
        "total": 0,
        "page": 1,
        "limit": 20
    })
    service.get_by_id = AsyncMock(return_value=None)
    service.create = AsyncMock(return_value=None)
    service.update = AsyncMock(return_value=None)
    service.delete = AsyncMock(return_value=True)

    return service


# ============================================================
# 依賴注入覆蓋 Fixtures
# ============================================================

@pytest.fixture
def override_document_service(mock_document_service):
    """覆蓋 DocumentService 依賴注入

    使用範例:
        def test_api_endpoint(client, override_document_service, mock_document_service):
            mock_document_service.get_documents.return_value = {...}
            response = await client.post("/api/documents-enhanced/list")
    """
    from app.api.endpoints.documents.common import get_document_service

    app.dependency_overrides[get_document_service] = lambda: mock_document_service
    yield mock_document_service
    app.dependency_overrides.pop(get_document_service, None)


@pytest.fixture
def override_db_session(mock_db_session):
    """覆蓋資料庫 Session 依賴注入"""
    from app.db.database import get_async_db

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_async_db] = override_get_db
    yield mock_db_session
    app.dependency_overrides.pop(get_async_db, None)


# ============================================================
# 測試資料 Fixtures
# ============================================================

@pytest.fixture
def sample_document_data() -> dict:
    """範例公文資料"""
    return {
        "doc_number": "TEST-2026-001",
        "subject": "測試公文主旨",
        "doc_type": "函",
        "sender": "測試發文單位",
        "receiver": "測試受文單位",
        "status": "待處理",
        "category": "收文"
    }


@pytest.fixture
def sample_document_list() -> list:
    """範例公文列表資料"""
    return [
        {
            "id": 1,
            "auto_serial": "R0001",
            "doc_number": "府工測字第1140001234號",
            "doc_type": "函",
            "subject": "關於測繪作業事宜",
            "sender": "桃園市政府",
            "receiver": "乾坤測繪有限公司",
            "doc_date": "2026-01-08",
            "status": "待處理",
            "category": "收文"
        },
        {
            "id": 2,
            "auto_serial": "S0001",
            "doc_number": "乾坤測字第1140000001號",
            "doc_type": "函",
            "subject": "函覆測繪作業事宜",
            "sender": "乾坤測繪有限公司",
            "receiver": "桃園市政府",
            "doc_date": "2026-01-09",
            "status": "已發送",
            "category": "發文"
        }
    ]


@pytest.fixture
def sample_project_data() -> dict:
    """範例案件資料"""
    return {
        "project_name": "測試案件",
        "project_code": "TEST-P-001",
        "year": 2026,
        "client_agency": "測試委託單位",
        "status": "進行中"
    }


@pytest.fixture
def sample_vendor_data() -> dict:
    """範例廠商資料"""
    return {
        "vendor_name": "測試廠商",
        "vendor_code": "V-TEST-001",
        "contact_person": "測試聯絡人",
        "phone": "02-12345678"
    }


@pytest.fixture
def sample_agency_data() -> dict:
    """範例機關資料"""
    return {
        "agency_name": "桃園市政府工務局",
        "agency_code": "380110000G",
        "agency_short_name": "桃市工務局",
        "address": "桃園市桃園區縣府路1號"
    }


# ============================================================
# Mock 使用者 Fixtures
# ============================================================

@pytest.fixture
def mock_current_user() -> dict:
    """模擬當前登入使用者"""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "is_active": True,
        "is_admin": False,
        "is_superuser": False,
        "role": "user"
    }


@pytest.fixture
def mock_admin_user() -> dict:
    """模擬管理員使用者"""
    return {
        "id": 2,
        "username": "admin",
        "email": "admin@example.com",
        "is_active": True,
        "is_admin": True,
        "is_superuser": False,
        "role": "admin"
    }


@pytest.fixture
def mock_superuser() -> dict:
    """模擬超級管理員使用者"""
    return {
        "id": 3,
        "username": "superadmin",
        "email": "superadmin@example.com",
        "is_active": True,
        "is_admin": True,
        "is_superuser": True,
        "role": "superadmin"
    }


# ============================================================
# 輔助函數
# ============================================================

def assert_api_success(response_data: dict):
    """斷言 API 回應成功"""
    assert response_data.get("success") is True, f"API 回應失敗: {response_data}"


def assert_api_error(response_data: dict, expected_code: str = None):
    """斷言 API 回應錯誤"""
    assert response_data.get("success") is False, "預期 API 回應失敗"
    if expected_code:
        assert response_data.get("error_code") == expected_code


def assert_pagination(response_data: dict, expected_page: int = 1, expected_limit: int = 20):
    """斷言分頁資訊正確"""
    pagination = response_data.get("pagination", {})
    assert pagination.get("page") == expected_page, f"Expected page {expected_page}, got {pagination.get('page')}"
    assert pagination.get("limit") == expected_limit, f"Expected limit {expected_limit}, got {pagination.get('limit')}"
    assert "total" in pagination, "Missing 'total' in pagination"
    assert "total_pages" in pagination, "Missing 'total_pages' in pagination"


# ============================================================
# Pytest 配置
# ============================================================

def pytest_configure(config):
    """Pytest 配置"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "allow_outbound: 明確允許此測試對外推播（預設一律封鎖，見 _block_outbound_notifications）"
    )

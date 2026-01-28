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

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport

import sys
import os

# 將 backend 目錄加入 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.database import Base
from main import app


# ============================================================
# 事件迴圈 Fixtures
# ============================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """建立 session 範圍的事件迴圈"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================
# 資料庫 Fixtures
# ============================================================

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """建立測試用資料庫引擎"""
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )
    yield engine
    await engine.dispose()


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

    使用範例:
        async def test_list_documents(client):
            response = await client.post("/api/documents-enhanced/list")
            assert response.status_code == 200
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(mock_current_user) -> AsyncGenerator[AsyncClient, None]:
    """建立已認證的測試用 HTTP 客戶端

    自動覆蓋認證依賴，使用 mock_current_user
    """
    from app.api.endpoints.auth import get_current_user
    from app.extended.models import User

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
    service.get_vendors = AsyncMock(return_value={
        "items": [],
        "total": 0,
        "page": 1,
        "limit": 20
    })
    service.get_vendor_by_id = AsyncMock(return_value=None)
    service.create_vendor = AsyncMock(return_value=None)
    service.update_vendor = AsyncMock(return_value=None)
    service.delete_vendor = AsyncMock(return_value=True)

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
    service.create_project = AsyncMock(return_value=None)
    service.update_project = AsyncMock(return_value=None)
    service.delete_project = AsyncMock(return_value=True)

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
    service.get_agency_by_id = AsyncMock(return_value=None)
    service.create_agency = AsyncMock(return_value=None)
    service.update_agency = AsyncMock(return_value=None)
    service.delete_agency = AsyncMock(return_value=True)

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

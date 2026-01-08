# -*- coding: utf-8 -*-
"""
共用測試 Fixtures
Shared Test Fixtures

用法:
    pytest tests/ -v
    pytest tests/unit/ -v
    pytest tests/integration/ -v
"""
import asyncio
from typing import AsyncGenerator, Generator

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


# ============================================================
# 測試資料 Fixtures
# ============================================================

@pytest.fixture
def sample_document_data() -> dict:
    """範例公文資料"""
    return {
        "doc_number": "TEST-2026-001",
        "subject": "測試公文主旨",
        "doc_type": "收文",
        "sender": "測試發文單位",
        "receiver": "測試受文單位",
        "status": "待處理"
    }


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


# ============================================================
# Mock Fixtures
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
        "role": "user"
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

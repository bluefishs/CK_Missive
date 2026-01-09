# -*- coding: utf-8 -*-
"""
模型與資料庫 Schema 一致性測試
Model-Database Schema Consistency Tests

執行方式：
    pytest tests/test_schema_consistency.py -v
"""
import pytest
import asyncio
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.extended.models import Base


# 關鍵表格列表（必須驗證的表格）
CRITICAL_TABLES = [
    "documents",
    "document_attachments",
    "contract_projects",
    "users",
    "partner_vendors",
    "government_agencies",
]


@pytest.fixture
def event_loop():
    """建立事件迴圈"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_engine():
    """建立資料庫引擎"""
    # 將 DATABASE_URL 轉換為 asyncpg 驅動
    db_url = settings.DATABASE_URL
    if "postgresql://" in db_url and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    elif "psycopg2" in db_url:
        db_url = db_url.replace("psycopg2", "asyncpg")

    engine = create_async_engine(db_url, echo=False)
    yield engine
    await engine.dispose()


class TestSchemaConsistency:
    """Schema 一致性測試類別"""

    @pytest.mark.asyncio
    async def test_critical_tables_exist(self, db_engine):
        """測試關鍵表格是否存在於資料庫"""
        async with db_engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
            """))
            db_tables = {row.table_name for row in result}

        for table in CRITICAL_TABLES:
            assert table in db_tables, f"關鍵表格 '{table}' 在資料庫中不存在"

    @pytest.mark.asyncio
    async def test_model_tables_exist(self, db_engine):
        """測試所有模型定義的表格是否存在"""
        async with db_engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """))
            db_tables = {row.table_name for row in result}

        model_tables = set(Base.metadata.tables.keys())
        missing_tables = model_tables - db_tables

        if missing_tables:
            pytest.fail(f"以下模型表格在資料庫中不存在: {missing_tables}")

    @pytest.mark.asyncio
    async def test_document_attachments_columns(self, db_engine):
        """測試 document_attachments 表格欄位"""
        async with db_engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'document_attachments'
            """))
            db_columns = {row.column_name for row in result}

        # 預期的欄位
        expected_columns = {
            "id", "document_id", "file_name", "file_path",
            "file_size", "mime_type", "created_at", "updated_at"
        }

        missing = expected_columns - db_columns
        if missing:
            pytest.fail(f"document_attachments 缺少欄位: {missing}")

    @pytest.mark.asyncio
    async def test_documents_columns(self, db_engine):
        """測試 documents 表格欄位"""
        async with db_engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'documents'
            """))
            db_columns = {row.column_name for row in result}

        # 關鍵欄位
        critical_columns = {
            "id", "doc_number", "subject", "sender", "receiver",
            "doc_date", "status", "created_at", "updated_at"
        }

        missing = critical_columns - db_columns
        if missing:
            pytest.fail(f"documents 缺少關鍵欄位: {missing}")


def test_no_duplicate_models():
    """測試是否有重複的模型定義"""
    import warnings

    # 嘗試導入已廢棄的模型檔案，應該產生警告
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            from app.extended.models.document import DocumentAttachment as DeprecatedModel
            # 應該收到 DeprecationWarning
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) > 0, "已廢棄的模型應該產生 DeprecationWarning"
        except ImportError:
            pass  # 如果檔案不存在則通過


def test_model_imports():
    """測試主要模型可以正確導入"""
    try:
        from app.extended.models import (
            OfficialDocument,
            DocumentAttachment,
            ContractProject,
            User,
            PartnerVendor,
            GovernmentAgency
        )
        assert OfficialDocument is not None
        assert DocumentAttachment is not None
        assert ContractProject is not None
        assert User is not None
    except ImportError as e:
        pytest.fail(f"模型導入失敗: {e}")

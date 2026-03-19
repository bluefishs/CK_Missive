"""
admin_service 管理後台服務單元測試

測試範圍：
- _validate_read_only_sql SQL 安全驗證
- validate_table_name 表格名稱驗證
- ALLOWED_TABLES 白名單
- AdminService.get_table_data 安全邊界
- AdminService.execute_read_only_query 安全邊界
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from app.services.admin_service import (
    _validate_read_only_sql,
    validate_table_name,
    ALLOWED_TABLES,
    AdminService,
)


class TestValidateReadOnlySql:
    """SQL 安全驗證"""

    def test_simple_select(self):
        # 不應拋出例外
        _validate_read_only_sql("SELECT * FROM users")

    def test_select_with_where(self):
        _validate_read_only_sql("SELECT id, name FROM users WHERE id = 1")

    def test_with_clause(self):
        _validate_read_only_sql("WITH cte AS (SELECT * FROM users) SELECT * FROM cte")

    def test_explain_allowed(self):
        _validate_read_only_sql("EXPLAIN SELECT * FROM users")

    def test_insert_blocked(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("INSERT INTO users (name) VALUES ('test')")
        assert exc_info.value.status_code == 403

    def test_update_blocked(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("UPDATE users SET name = 'test'")
        assert exc_info.value.status_code == 403

    def test_delete_blocked(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("DELETE FROM users WHERE id = 1")
        assert exc_info.value.status_code == 403

    def test_drop_blocked(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("DROP TABLE users")
        assert exc_info.value.status_code == 403

    def test_multi_statement_blocked(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("SELECT 1; DROP TABLE users")
        assert exc_info.value.status_code == 403

    def test_cte_injection_blocked(self):
        """CTE 注入：WITH x AS (INSERT ...) SELECT ..."""
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql(
                "WITH x AS (INSERT INTO users (name) VALUES ('hack')) SELECT * FROM x"
            )
        assert exc_info.value.status_code == 403

    def test_empty_query_blocked(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("")
        assert exc_info.value.status_code == 400

    def test_comment_hiding_blocked(self):
        """SQL 註解中隱藏的 DML"""
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("SELECT 1 /* hidden */ ; DELETE FROM users")
        assert exc_info.value.status_code == 403

    def test_string_literal_not_blocked(self):
        """字串中的 INSERT 不應被誤判"""
        _validate_read_only_sql("SELECT * FROM users WHERE name LIKE '%INSERT%'")

    def test_truncate_blocked(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("TRUNCATE TABLE users")
        assert exc_info.value.status_code == 403

    def test_grant_blocked(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("GRANT ALL ON users TO public")
        assert exc_info.value.status_code == 403


class TestValidateTableName:
    """表格名稱驗證"""

    def test_valid_name(self):
        assert validate_table_name("users") is True

    def test_valid_name_with_underscore(self):
        assert validate_table_name("contract_projects") is True

    def test_valid_name_starts_with_underscore(self):
        assert validate_table_name("_internal") is True

    def test_invalid_with_dash(self):
        assert validate_table_name("user-table") is False

    def test_invalid_with_space(self):
        assert validate_table_name("user table") is False

    def test_invalid_with_semicolon(self):
        assert validate_table_name("users;DROP") is False

    def test_invalid_starts_with_digit(self):
        assert validate_table_name("1users") is False

    def test_invalid_empty(self):
        assert validate_table_name("") is False

    def test_sql_injection_attempt(self):
        assert validate_table_name("users; DROP TABLE users--") is False


class TestAllowedTables:
    """白名單正確性"""

    def test_core_tables_present(self):
        assert 'users' in ALLOWED_TABLES
        assert 'contract_projects' in ALLOWED_TABLES
        assert 'government_agencies' in ALLOWED_TABLES

    def test_document_tables_present(self):
        assert 'documents' in ALLOWED_TABLES
        assert 'document_attachments' in ALLOWED_TABLES

    def test_knowledge_graph_tables_present(self):
        assert 'canonical_entities' in ALLOWED_TABLES
        assert 'entity_aliases' in ALLOWED_TABLES

    def test_system_tables_not_exposed(self):
        # PostgreSQL 內部表不應在白名單中
        assert 'pg_class' not in ALLOWED_TABLES
        assert 'pg_user' not in ALLOWED_TABLES


class TestAdminServiceGetTableData:
    """get_table_data 安全邊界"""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        return AdminService(mock_db)

    @pytest.mark.asyncio
    async def test_invalid_table_name_rejected(self, service):
        with pytest.raises(HTTPException) as exc_info:
            await service.get_table_data("users;DROP")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_non_whitelisted_table_rejected(self, service):
        with pytest.raises(HTTPException) as exc_info:
            await service.get_table_data("pg_shadow")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_limit_capped_at_500(self, service, mock_db):
        """limit 上界為 500"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.execute.return_value.scalar = MagicMock(return_value=0)

        # 不應拋出例外，limit 被截斷
        result = await service.get_table_data("users", limit=1000)
        assert result["pageSize"] == 500


class TestAdminServiceExecuteQuery:
    """execute_read_only_query 安全邊界"""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        return AdminService(mock_db)

    @pytest.mark.asyncio
    async def test_empty_query_rejected(self, service):
        with pytest.raises(HTTPException) as exc_info:
            await service.execute_read_only_query({"query": ""})
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_dml_query_rejected(self, service):
        with pytest.raises(HTTPException) as exc_info:
            await service.execute_read_only_query(
                {"query": "DELETE FROM users WHERE id = 1"}
            )
        assert exc_info.value.status_code == 403

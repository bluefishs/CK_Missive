"""
SQL 注入多層防禦 — 單元測試

測試 admin_service._validate_read_only_sql() 的安全性

共 20 test cases
"""

import pytest
from fastapi import HTTPException

from app.services.admin_service import _validate_read_only_sql


class TestValidReadOnlyQueries:
    """合法 SELECT 查詢應通過驗證"""

    def test_simple_select(self):
        _validate_read_only_sql("SELECT * FROM documents")

    def test_select_with_where(self):
        _validate_read_only_sql("SELECT id, subject FROM documents WHERE id = 1")

    def test_select_with_join(self):
        _validate_read_only_sql(
            "SELECT d.id, a.name FROM documents d "
            "JOIN government_agencies a ON d.sender_id = a.id"
        )

    def test_select_with_subquery(self):
        _validate_read_only_sql(
            "SELECT * FROM documents WHERE id IN (SELECT document_id FROM attachments)"
        )

    def test_cte_select_only(self):
        _validate_read_only_sql(
            "WITH recent AS (SELECT * FROM documents WHERE doc_date > '2024-01-01') "
            "SELECT * FROM recent"
        )

    def test_explain_select(self):
        _validate_read_only_sql("EXPLAIN SELECT * FROM documents")

    def test_trailing_semicolon(self):
        _validate_read_only_sql("SELECT 1;")

    def test_string_with_forbidden_keyword(self):
        """字串內的 INSERT 不應被誤判"""
        _validate_read_only_sql(
            "SELECT * FROM documents WHERE subject LIKE '%INSERT%'"
        )

    def test_string_with_delete_keyword(self):
        """字串內的 DELETE 不應被誤判"""
        _validate_read_only_sql(
            "SELECT * FROM documents WHERE subject = 'DELETE THIS'"
        )


class TestBlockedQueries:
    """危險查詢應被阻擋"""

    def test_direct_insert(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("INSERT INTO documents (subject) VALUES ('test')")
        assert exc_info.value.status_code == 403

    def test_direct_update(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("UPDATE documents SET subject = 'hacked'")
        assert exc_info.value.status_code == 403

    def test_direct_delete(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("DELETE FROM documents WHERE id = 1")
        assert exc_info.value.status_code == 403

    def test_drop_table(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("DROP TABLE documents")
        assert exc_info.value.status_code == 403

    def test_cte_injection(self):
        """CTE 注入攻擊: WITH ... AS (INSERT ...) SELECT ..."""
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql(
                "WITH x AS (INSERT INTO documents (subject) VALUES ('pwned') RETURNING *) "
                "SELECT * FROM x"
            )
        assert exc_info.value.status_code == 403
        assert "禁止" in exc_info.value.detail

    def test_multi_statement(self):
        """多重語句攻擊"""
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("SELECT 1; DROP TABLE documents")
        assert exc_info.value.status_code == 403
        assert "多重" in exc_info.value.detail

    def test_comment_obfuscation(self):
        """利用註解藏 DML"""
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql(
                "SELECT /* comment */ 1; DELETE FROM documents"
            )
        assert exc_info.value.status_code == 403

    def test_truncate(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("TRUNCATE documents")
        assert exc_info.value.status_code == 403

    def test_grant(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("GRANT ALL ON documents TO public")
        assert exc_info.value.status_code == 403

    def test_copy(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("COPY documents TO '/tmp/dump.csv'")
        assert exc_info.value.status_code == 403

    def test_empty_query(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_read_only_sql("")
        assert exc_info.value.status_code == 400

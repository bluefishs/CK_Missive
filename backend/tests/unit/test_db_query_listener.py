# -*- coding: utf-8 -*-
"""
TDD: DB Query Event Listener

驗證：
1. detect_operation 正確分類 SQL 語句
2. SELECT → "select", INSERT → "insert", etc.
3. 未知語句 → "other"
"""
import pytest


def test_detect_select():
    from app.core.db_query_listener import detect_operation
    assert detect_operation("SELECT * FROM documents WHERE id = 1") == "select"


def test_detect_insert():
    from app.core.db_query_listener import detect_operation
    assert detect_operation("INSERT INTO documents (title) VALUES ('test')") == "insert"


def test_detect_update():
    from app.core.db_query_listener import detect_operation
    assert detect_operation("UPDATE documents SET title = 'x' WHERE id = 1") == "update"


def test_detect_delete():
    from app.core.db_query_listener import detect_operation
    assert detect_operation("DELETE FROM documents WHERE id = 1") == "delete"


def test_detect_with_comment():
    from app.core.db_query_listener import detect_operation
    assert detect_operation("/* sqlalchemy */ SELECT 1") == "select"


def test_detect_unknown():
    from app.core.db_query_listener import detect_operation
    assert detect_operation("SET LOCAL hnsw.ef_search = 100") == "other"


def test_detect_case_insensitive():
    from app.core.db_query_listener import detect_operation
    assert detect_operation("select 1") == "select"

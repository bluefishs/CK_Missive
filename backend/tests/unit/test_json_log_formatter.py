# -*- coding: utf-8 -*-
"""
TDD: JSON Log Formatter 測試

驗證 Loki-compatible JSON 日誌格式：
1. 每行是合法 JSON
2. 包含必要欄位：timestamp, level, message, logger
3. request_id 從 ContextVar 正確注入
4. 中文訊息正確編碼（非 escape）
5. Exception 格式化包含 traceback
"""
import json
import logging
import pytest


@pytest.fixture
def json_formatter():
    from app.core.json_log_formatter import JsonLogFormatter
    return JsonLogFormatter()


@pytest.fixture
def log_record():
    """建立 standard LogRecord"""
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="測試訊息",
        args=(),
        exc_info=None,
    )
    return record


def test_format_returns_valid_json(json_formatter, log_record):
    """格式化結果應為合法 JSON"""
    result = json_formatter.format(log_record)
    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_format_includes_required_fields(json_formatter, log_record):
    """應包含 timestamp, level, message, logger 欄位"""
    result = json.loads(json_formatter.format(log_record))
    assert "timestamp" in result
    assert "level" in result
    assert "message" in result
    assert "logger" in result
    assert result["level"] == "INFO"
    assert result["message"] == "測試訊息"
    assert result["logger"] == "app.test"


def test_format_preserves_chinese(json_formatter, log_record):
    """中文應直接出現，非 Unicode escape"""
    result = json_formatter.format(log_record)
    assert "測試訊息" in result
    assert "\\u" not in result.split('"message"')[1].split(",")[0]


def test_format_includes_request_id(json_formatter, log_record):
    """有 request_id ContextVar 時應包含"""
    from app.core.middleware import request_id_var
    token = request_id_var.set("abc123")
    try:
        result = json.loads(json_formatter.format(log_record))
        assert result.get("request_id") == "abc123"
    finally:
        request_id_var.reset(token)


def test_format_exception_includes_traceback(json_formatter):
    """有 exception 時應包含 traceback"""
    try:
        raise ValueError("test error")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="app.test", level=logging.ERROR,
            pathname="test.py", lineno=1,
            msg="發生錯誤", args=(), exc_info=sys.exc_info(),
        )

    result = json.loads(json_formatter.format(record))
    assert "exception" in result
    assert "ValueError" in result["exception"]

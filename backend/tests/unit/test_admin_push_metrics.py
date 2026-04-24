"""
測試 admin_push_metrics（P0-2, ADR-0027 配套）
"""
from prometheus_client import CollectorRegistry

from app.core.admin_push_metrics import AdminPushMetrics


def _make():
    # 獨立 registry 避免 test 間狀態污染
    return AdminPushMetrics(registry=CollectorRegistry())


def test_success_resets_consecutive_failures():
    m = _make()
    m.record_failure("line", reason="http_500")
    m.record_failure("line", reason="http_500")
    # 2 次失敗後 gauge 應為 2
    assert m._fail_counter["line"] == 2
    m.record_success("line")
    assert m._fail_counter["line"] == 0


def test_consecutive_failures_accumulate_per_channel():
    m = _make()
    m.record_failure("line", reason="timeout")
    m.record_failure("telegram", reason="blocked")
    m.record_failure("line", reason="timeout")
    assert m._fail_counter["line"] == 2
    assert m._fail_counter["telegram"] == 1


def test_alert_threshold_error_log(caplog):
    import logging
    m = _make()
    with caplog.at_level(logging.ERROR):
        m.record_failure("line", reason="http_500")
        m.record_failure("line", reason="http_500")
        m.record_failure("line", reason="http_500")  # 第 3 次觸發 error log

    error_logs = [r for r in caplog.records if r.levelno >= logging.ERROR and "admin_push" in r.getMessage()]
    assert len(error_logs) >= 1
    assert "line" in error_logs[0].getMessage()

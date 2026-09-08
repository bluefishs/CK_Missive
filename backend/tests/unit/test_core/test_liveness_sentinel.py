# -*- coding: utf-8 -*-
"""A127-④ 活體哨兵的判準鎖。

要守住的三件事：
1. 503 也算活著 —— 否則 DB 暫時掛了會把 backend 殺進無限重啟。
2. 單次無回應不殺、連續達門檻才殺。
3. 中途恢復要歸零 —— 「3 次裡壞 2 次」不等於「連續 3 次」。
"""
import io
import urllib.error

from app.core import liveness_sentinel as ls


def _http_error(code: int):
    return urllib.error.HTTPError("http://127.0.0.1:8001/health", code, "x", {}, io.BytesIO(b""))


def test_http_503_counts_as_alive(monkeypatch):
    def fake_urlopen(url, timeout):
        raise _http_error(503)
    monkeypatch.setattr(ls.urllib.request, "urlopen", fake_urlopen)
    assert ls.probe_once("http://127.0.0.1:8001/health", 1) is True


def test_timeout_counts_as_dead(monkeypatch):
    def fake_urlopen(url, timeout):
        raise TimeoutError("timed out")
    monkeypatch.setattr(ls.urllib.request, "urlopen", fake_urlopen)
    assert ls.probe_once("http://127.0.0.1:8001/health", 1) is False


def test_should_exit_threshold():
    assert ls.should_exit(2, 3) is False
    assert ls.should_exit(3, 3) is True
    assert ls.should_exit(5, 0) is False  # 門檻 0 = 永不退出（等於停用）


def test_consecutive_failures_then_exit():
    exits = []
    results = iter([False, False, False])
    s = ls.LivenessSentinel("u", max_failures=3, exit_fn=exits.append, probe=lambda u, t: next(results))
    assert s.tick() is False and s.failures == 1
    assert s.tick() is False and s.failures == 2
    assert s.tick() is True and exits == [ls.EXIT_CODE]


def test_recovery_resets_counter():
    exits = []
    results = iter([False, False, True, False, False])
    s = ls.LivenessSentinel("u", max_failures=3, exit_fn=exits.append, probe=lambda u, t: next(results))
    s.tick(); s.tick()
    assert s.failures == 2
    s.tick()
    assert s.failures == 0
    s.tick(); s.tick()
    assert s.failures == 2 and exits == []


def test_env_disable(monkeypatch):
    monkeypatch.setenv("LIVENESS_SENTINEL_ENABLED", "false")
    assert ls.is_enabled() is False
    assert ls.start_from_env() is None

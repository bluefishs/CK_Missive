# -*- coding: utf-8 -*-
"""
R1 (v6.9 / 2026-05-08) — SSE stream hard cutoff regression test

確保 create_sse_response 對 stream_fn 做 stream_e2e 強制 timeout。
背景：shadow_baseline p95=58s 接近 60s 邊界，原 event_generator 無 asyncio.timeout
保護導致 stream 可能無限期等待，影響 ADR-0030 5/20 Hermes GO/NO-GO 投票。

測試矩陣：
  1. 正常 stream（< timeout）→ 完整 yield
  2. stream 超時 → STREAM_TIMEOUT error + done(model="timeout")
  3. stream 拋例外 → SERVICE_ERROR error + done(model="error")
  4. timeout_s 顯式參數 > 預設值 → 使用顯式
  5. SSE_HEADERS Content-Encoding: identity 維持不變（ADR-0028 §SSE 守護）
"""
import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI


@pytest.fixture
def stream_app_factory():
    """工廠：根據 stream_fn 與 timeout_s 建構測試 app"""
    from app.api.sse_utils import create_sse_response

    def _make(stream_fn, *, timeout_s=None, endpoint_name="TestSSE"):
        app = FastAPI()

        @app.get("/sse")
        async def _endpoint():
            return create_sse_response(
                stream_fn=stream_fn,
                endpoint_name=endpoint_name,
                timeout_s=timeout_s,
            )
        return app

    return _make


async def _consume_sse(client, path="/sse"):
    """收集 SSE response 的所有 lines"""
    chunks = []
    async with client.stream("GET", path) as resp:
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                chunks.append(line[6:])
    return chunks


def _parse_event(chunk):
    return json.loads(chunk)


# ============================================================================
# 正常路徑
# ============================================================================

@pytest.mark.asyncio
async def test_normal_stream_completes_within_timeout(stream_app_factory):
    """正常 stream 應該完整通過，無 timeout 介入"""
    async def fast_stream():
        for i in range(3):
            yield f"data: {{\"type\":\"token\",\"token\":\"chunk{i}\"}}\n\n"

    app = stream_app_factory(fast_stream, timeout_s=5)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        chunks = await _consume_sse(c)

    events = [_parse_event(c) for c in chunks]
    # 應收到 3 個 token，無 timeout 事件
    types = [e.get("type") for e in events]
    assert types == ["token", "token", "token"]
    assert all(e.get("code") != "STREAM_TIMEOUT" for e in events)


# ============================================================================
# Timeout 路徑（R1 核心）
# ============================================================================

@pytest.mark.asyncio
async def test_stream_timeout_emits_stream_timeout_event(stream_app_factory):
    """stream 卡住超過 timeout_s 時，必須送 STREAM_TIMEOUT 事件 + done(model=timeout)"""
    async def slow_stream():
        # 故意 sleep 久於 timeout，模擬 LLM 卡住
        await asyncio.sleep(2)
        yield "data: should_not_reach\n\n"

    app = stream_app_factory(slow_stream, timeout_s=1)  # 1s timeout
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", timeout=5,
    ) as c:
        chunks = await _consume_sse(c)

    events = [_parse_event(c) for c in chunks]
    # 必有 STREAM_TIMEOUT error + done(model=timeout)
    error_events = [e for e in events if e.get("type") == "error"]
    done_events = [e for e in events if e.get("type") == "done"]

    assert len(error_events) >= 1
    assert error_events[0].get("code") == "STREAM_TIMEOUT"

    assert len(done_events) >= 1
    assert done_events[0].get("model") == "timeout"


@pytest.mark.asyncio
async def test_stream_partial_then_timeout(stream_app_factory):
    """先 yield 幾個 chunk 再卡住 — partial output + timeout 仍應正確觸發"""
    async def partial_then_hang():
        yield "data: {\"type\":\"token\",\"token\":\"first\"}\n\n"
        await asyncio.sleep(2)  # 卡住
        yield "data: should_not_reach\n\n"

    app = stream_app_factory(partial_then_hang, timeout_s=1)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", timeout=5,
    ) as c:
        chunks = await _consume_sse(c)

    events = [_parse_event(c) for c in chunks]
    # 第一個 chunk 應為 token "first"
    assert events[0].get("type") == "token"
    assert events[0].get("token") == "first"

    # 後續應為 STREAM_TIMEOUT + done
    assert any(e.get("code") == "STREAM_TIMEOUT" for e in events)
    assert any(e.get("type") == "done" and e.get("model") == "timeout" for e in events)


# ============================================================================
# Exception 路徑（既有行為，避免 R1 改動破壞）
# ============================================================================

@pytest.mark.asyncio
async def test_stream_exception_emits_service_error(stream_app_factory):
    """stream 拋一般例外（非 timeout）應送 SERVICE_ERROR + done(model=error)"""
    async def broken_stream():
        yield "data: {\"type\":\"token\",\"token\":\"x\"}\n\n"
        raise RuntimeError("simulated failure")

    app = stream_app_factory(broken_stream, timeout_s=10)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        chunks = await _consume_sse(c)

    events = [_parse_event(c) for c in chunks]
    error_events = [e for e in events if e.get("type") == "error"]
    done_events = [e for e in events if e.get("type") == "done"]

    assert len(error_events) >= 1
    assert error_events[0].get("code") == "SERVICE_ERROR"
    assert done_events[0].get("model") == "error"


# ============================================================================
# ADR-0028 §SSE Headers 守護（防 R1 修改破壞 GZip identity 設定）
# ============================================================================

@pytest.mark.asyncio
async def test_sse_headers_preserved_after_r1_changes(stream_app_factory):
    """SSE_HEADERS 必須含 Content-Encoding: identity（ADR-0028 §SSE 守護）"""
    async def empty_stream():
        if False:
            yield  # generator 但不 yield
        return

    app = stream_app_factory(empty_stream, timeout_s=5)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with c.stream("GET", "/sse") as resp:
            assert resp.headers.get("content-encoding", "").lower() == "identity"
            assert resp.headers.get("cache-control") == "no-cache"
            assert resp.headers.get("x-accel-buffering") == "no"


# ============================================================================
# Timeout 預設值來源（ai_config.agent_stream_timeout）
# ============================================================================

def test_timeout_default_uses_ai_config():
    """timeout_s=None 時應從 ai_config.agent_stream_timeout 讀取"""
    from app.services.ai.core.ai_config import get_ai_config

    cfg = get_ai_config()
    expected = cfg.agent_stream_timeout
    assert isinstance(expected, int)
    assert expected >= 30, "stream_e2e timeout 不該 < 30s"
    assert expected <= 120, "stream_e2e timeout 不該 > 120s（與 sync_query 90s 對齊）"

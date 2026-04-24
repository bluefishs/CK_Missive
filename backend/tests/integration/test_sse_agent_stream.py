"""
SSE E2E smoke test：驗證 /api/ai/agent/query/stream 能即時送達 events
（防 GZipMiddleware 或 proxy 再度 buffer → 坤哥「無回應」事故）

事故：2026-04-21 前端 ChatTab embed 無回應
根因：GZipMiddleware 對 text/event-stream 啟用壓縮緩衝
修復：SSE_HEADERS 加 Content-Encoding: identity
本測試：活體 HTTP 請求，驗證 4 個屬性
  1. HTTP 200
  2. Content-Encoding = identity（防 GZip 介入）
  3. 30s 內拿到第一個 event（防 buffer 卡住）
  4. 30s 內收齊 done event（防 stream 斷線）
"""
import asyncio
import json
import os
import time

import httpx
import pytest


BACKEND_URL = os.getenv("TEST_BACKEND_URL", "http://localhost:8001")
SSE_PATH = "/api/ai/agent/query/stream"


def _backend_reachable() -> bool:
    """若 backend 未開（CI 無 PM2），跳過此 integration 測試"""
    try:
        import urllib.request
        urllib.request.urlopen(f"{BACKEND_URL}/health", timeout=2)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _backend_reachable(),
    reason="backend 未運行，integration 測試需要 PM2 ck-backend online",
)


@pytest.mark.asyncio
async def test_sse_content_encoding_is_identity():
    """回應頭必須含 Content-Encoding: identity，Starlette GZipMiddleware 才會跳過"""
    async with httpx.AsyncClient(timeout=15) as client:
        async with client.stream(
            "POST", f"{BACKEND_URL}{SSE_PATH}",
            json={"question": "hello"},
        ) as r:
            assert r.status_code == 200, f"SSE endpoint status={r.status_code}"
            enc = r.headers.get("content-encoding", "")
            assert enc == "identity", (
                f"Content-Encoding={enc!r}, 應為 'identity' 防 GZip 緩衝"
            )
            ct = r.headers.get("content-type", "")
            assert ct.startswith("text/event-stream"), ct


@pytest.mark.asyncio
async def test_sse_first_event_within_10s():
    """第一個 event 必須在 10s 內送達（防 backend yield 前卡住）"""
    t0 = time.time()
    first_byte_t = None
    async with httpx.AsyncClient(timeout=30) as client:
        async with client.stream(
            "POST", f"{BACKEND_URL}{SSE_PATH}",
            json={"question": "hello"},
        ) as r:
            async for line in r.aiter_lines():
                if line.startswith("data:"):
                    first_byte_t = time.time()
                    break
    assert first_byte_t is not None, "沒收到任何 SSE event"
    gap = first_byte_t - t0
    assert gap < 10, f"首 event 延遲 {gap:.1f}s 超過 10s 閾值"


@pytest.mark.asyncio
async def test_sse_receives_done_within_30s():
    """30s 內必須收到 done event（防 synthesis 超時或 stream 斷）"""
    t0 = time.time()
    events = []
    done_received = False

    async with httpx.AsyncClient(timeout=35) as client:
        async with client.stream(
            "POST", f"{BACKEND_URL}{SSE_PATH}",
            json={"question": "hello"},
        ) as r:
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                try:
                    evt = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                events.append(evt.get("type"))
                if evt.get("type") == "done":
                    done_received = True
                    break
                if time.time() - t0 > 30:
                    break

    assert done_received, (
        f"30s 內未收到 done event，實際收到: {events}"
    )
    total = time.time() - t0
    assert total < 30, f"stream 總耗時 {total:.1f}s 超過 30s"

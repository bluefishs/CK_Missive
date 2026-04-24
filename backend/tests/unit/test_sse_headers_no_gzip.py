"""
回歸測試：SSE response 必須跳過 GZipMiddleware

事故 2026-04-21：坤哥聊天板塊前端「無回應」。
根因：GZipMiddleware (minimum_size=1000) 對 text/event-stream 啟用壓縮，
      每個 SSE chunk 被累積壓縮緩衝，直到 stream 結束才 flush，
      導致前端 fetch.getReader() 在串流期間收不到任何 event。
修復：SSE_HEADERS 加 Content-Encoding: identity，Starlette GZipMiddleware
      會尊重已設定的 Content-Encoding 而跳過壓縮。
"""
from app.api.sse_utils import SSE_HEADERS


def test_sse_headers_has_identity_encoding():
    """Content-Encoding: identity 必須存在，防 GZipMiddleware 介入"""
    assert SSE_HEADERS.get("Content-Encoding") == "identity"


def test_sse_headers_no_cache():
    """no-cache 防中介層（CF/browser）快取 SSE"""
    assert SSE_HEADERS.get("Cache-Control") == "no-cache"


def test_sse_headers_nginx_no_buffering():
    """X-Accel-Buffering: no 防 nginx/CF proxy 緩衝"""
    assert SSE_HEADERS.get("X-Accel-Buffering") == "no"


def test_sse_headers_keep_alive():
    """keep-alive 避免短連線關閉"""
    assert SSE_HEADERS.get("Connection") == "keep-alive"

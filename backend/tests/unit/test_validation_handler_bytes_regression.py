# -*- coding: utf-8 -*-
"""
regression（2026-07-22）— validation_exception_handler malformed body（bytes）→ 422 非 500

malformed body（非 JSON，如缺 Content-Type）時 pydantic error["input"] 可能是 raw bytes，
直接放進 detail → JSONResponse 序列化爆 TypeError: bytes not JSON serializable → 500。
應回 422。修＝bytes/bytearray 先解碼為 str。

執行：pytest tests/unit/test_validation_handler_bytes_regression.py
"""
import json
import os
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.exceptions import validation_exception_handler


@pytest.mark.asyncio
async def test_bytes_input_serializes_to_422_not_500():
    """error input 為 bytes 時，handler 回 422 且 body 可 JSON 序列化（不爆 TypeError）。"""
    request = Mock()
    request.url.path = "/api/auth/refresh"
    request.headers = {}
    exc = Mock()
    exc.errors = Mock(return_value=[
        {"loc": ("body",), "msg": "invalid JSON", "input": b"garbage\xff bytes"},
    ])

    resp = await validation_exception_handler(request, exc)

    assert resp.status_code == 422
    # body 必須能被 JSON 解析（若含 bytes 會在 render 時爆）
    payload = json.loads(resp.body)
    assert payload is not None


@pytest.mark.asyncio
async def test_normal_input_unaffected():
    request = Mock()
    request.url.path = "/api/x"
    request.headers = {}
    exc = Mock()
    exc.errors = Mock(return_value=[
        {"loc": ("body", "field"), "msg": "required", "input": {"a": 1}},
    ])
    resp = await validation_exception_handler(request, exc)
    assert resp.status_code == 422
    assert json.loads(resp.body) is not None

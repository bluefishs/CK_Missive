# -*- coding: utf-8 -*-
"""欄位超長要回可讀的 400，不是沉默的 500（2026-08-05 回歸鎖）。

起因：owner 儲存派工單聯絡備註時連續 **5 次** HTTP 500 ——
真因是 `contact_note` 為 VARCHAR(500) 而內容約 1,200 字，
但畫面上只有「伺服器內部錯誤」。**他按了五次，因為沒有任何訊息說哪裡不對。**

「欄位太長」是使用者改得動的事，屬 400。但同樣重要的是**不能把真故障也降級**
—— 一個把所有 DB 錯誤都變 400 的處理器，會讓真正的資料庫故障看起來像使用者輸入問題。
"""
from __future__ import annotations

import json
from unittest.mock import Mock

import pytest
from asyncpg.exceptions import StringDataRightTruncationError, UndefinedColumnError
from sqlalchemy.exc import DBAPIError

from app.core.exceptions import db_constraint_exception_handler


def _request():
    req = Mock()
    req.method = "POST"
    req.url = Mock(path="/api/taoyuan-dispatch/dispatch/159/update")
    req.headers = {}
    return req


def _dbapi(orig, statement=""):
    exc = DBAPIError(statement, {}, orig)
    return exc


@pytest.mark.asyncio
async def test_too_long_becomes_readable_400():
    exc = _dbapi(
        StringDataRightTruncationError("value too long for type character varying(500)"),
        "UPDATE taoyuan_dispatch_orders SET contact_note=$1::VARCHAR WHERE id = $2",
    )
    resp = await db_constraint_exception_handler(_request(), exc)
    assert resp.status_code == 400
    msg = json.loads(resp.body)["error"]["message"]
    # 必須講出**哪個欄位**與**上限多少** —— 只說「輸入有誤」等於沒說
    assert "contact_note" in msg
    assert "500" in msg


@pytest.mark.asyncio
async def test_other_db_errors_stay_500():
    """真故障不得被降級成 400。

    把所有 DB 錯誤都當成使用者輸入問題，會讓「欄位不存在」這種程式缺陷
    看起來像是使用者打錯字 —— 那比沒有這個處理器更糟。
    """
    exc = _dbapi(
        UndefinedColumnError('column "deadline" does not exist'),
        "SELECT COUNT(*) FROM documents WHERE deadline < NOW()",
    )
    resp = await db_constraint_exception_handler(_request(), exc)
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_missing_field_name_still_returns_400():
    """SQL 裡認不出欄位名時仍要回 400，只是訊息較籠統 —— 不能退回 500。"""
    exc = _dbapi(
        StringDataRightTruncationError("value too long for type character varying(50)"),
        "",  # 取不到欄位名
    )
    resp = await db_constraint_exception_handler(_request(), exc)
    assert resp.status_code == 400
    assert "超過欄位長度上限" in json.loads(resp.body)["error"]["message"]


def test_contact_note_has_no_length_limit_in_schema():
    """長度限制有三處（DB / ORM / Pydantic），改一處不算改完。

    2026-08-05 實際踩到：DB 與 ORM 都放寬了，UPDATE **成功寫入**，
    但回應序列化時 Pydantic 的 max_length=500 擋下 →
    「資料已經存進去了卻回錯誤」，使用者以為沒存成功而反覆重按。
    與 2026-07-30 核銷「無法存檔實為已存檔」同一族。
    """
    from app.extended.models.taoyuan import TaoyuanDispatchOrder
    from app.schemas.taoyuan.dispatch import DispatchOrderBase
    from sqlalchemy import Text

    # Pydantic：不得有長度上限
    field = DispatchOrderBase.model_fields["contact_note"]
    limits = [
        getattr(m, "max_length", None) for m in field.metadata
        if getattr(m, "max_length", None) is not None
    ]
    assert not limits, f"contact_note 不該有長度上限，實際 max_length={limits}"

    # ORM：必須是 Text（非 String(n)）
    col = TaoyuanDispatchOrder.__table__.c.contact_note
    assert isinstance(col.type, Text), f"contact_note 應為 Text，實際 {col.type}"
    assert getattr(col.type, "length", None) is None

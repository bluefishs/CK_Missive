# -*- coding: utf-8 -*-
"""頁面能力宣告的唯一來源（2026-09-07 收斂 B）。

owner：「感覺整個系統四分五裂」。病灶之一：**同一個頁面要什麼權限，有三份宣告** ——
選單（`site_navigation_items.permission_required`）、路由守衛（今天起讀選單，算同一份）、
**API**（各 router 掛載時硬寫在 Python 裡）。改了選單，API 不動；改了 API，選單不動。

## 收斂

**選單表是唯一來源。** 選單管理頁改一次，選單、路由、API 三邊同時生效。
程式碼裡只留一件事：**哪個 API 前綴屬於哪個頁面**（那是路由結構，本來就只能寫在程式裡）。

| 層 | 從哪裡讀 |
|---|---|
| 選單顯示 | 選單表（原本就是） |
| 路由守衛 | 選單表（09-07 起） |
| API | `require_page_permission("/erp/ledger")` → 查快取的選單表 |

## 為什麼是快取而不是每次查 DB

權限檢查在每個請求上跑，逐次查表是不必要的成本。快取在**啟動時**載入，
選單管理頁儲存時呼叫 `refresh()`；另有 60 秒的保底 TTL，讓直接改 DB 的情況
也不會永遠失效。

## 失效方向（刻意設計）

* 頁面在選單表裡**沒有宣告**（`[]` 或找不到）⇒ **只要求登入**，不擋。
  這一層執行的是既有宣告，不自己發明限制 —— 與路由守衛同一原則。
* 快取載入失敗 ⇒ 記 ERROR，該次請求退回「只要求登入」。鎖住整個系統比多放一次更糟；
  真正的邊界仍在角色與資料層。

⚠️ 這**不是**萬用權限層：坤哥、通知、AI 助理等本來就服務所有同仁的端點
**不該**接這個（它們沒有對應的受限頁面）。
"""
from __future__ import annotations

import json
import logging
import time
from typing import Iterable

from fastapi import Depends

from app.core.dependencies import get_current_user, is_superuser_user

logger = logging.getLogger(__name__)

_TTL_SECONDS = 60
_cache: dict[str, list[str]] = {}
_loaded_at: float = 0.0
#: 程式碼裡引用過的頁面路徑。refresh 時對照選單表：路徑打錯（或選單改了路徑）
#: 會讓那支 API 安靜退回「只要求登入」—— 失效方向是放行，所以一定要出聲。
_referenced_pages: set[str] = set()


async def _load() -> dict[str, list[str]]:
    """{path: [permission codes]}，只收啟用中且有路徑的項目。"""
    from sqlalchemy import select
    from app.db.database import AsyncSessionLocal
    from app.extended.models.system import SiteNavigationItem as N

    out: dict[str, list[str]] = {}
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(N.path, N.permission_required).where(N.is_enabled.is_(True), N.path.isnot(None))
        )).all()
    for path, req in rows:
        codes: list[str] = []
        if req:
            try:
                parsed = json.loads(req) if isinstance(req, str) else req
                codes = [str(c) for c in parsed] if isinstance(parsed, list) else [str(parsed)]
            except Exception:
                codes = [str(req)]
        out[str(path).strip()] = [c for c in codes if c]
    return out


async def refresh() -> int:
    """重載快取；選單管理頁儲存後呼叫。回傳載入的頁面數。"""
    global _cache, _loaded_at
    try:
        _cache = await _load()
        _loaded_at = time.monotonic()
        logger.info("[capabilities] 頁面能力快取重載：%d 頁", len(_cache))
        missing = sorted(p for p in _referenced_pages if p not in _cache)
        if missing:
            logger.warning("[capabilities] %d 個被 API 引用的頁面在選單表裡沒有啟用中的宣告，"
                           "這些 API 目前只要求登入：%s", len(missing), "、".join(missing))
    except Exception:  # noqa: BLE001 —— 載入失敗不該讓服務起不來；退回只要求登入
        logger.error("[capabilities] 頁面能力快取載入失敗，本輪退回只要求登入", exc_info=True)
    return len(_cache)


async def permissions_for_page(path: str) -> list[str]:
    """該頁面在選單表宣告的權限碼；沒有宣告回空 list。"""
    if not _cache or time.monotonic() - _loaded_at > _TTL_SECONDS:
        await refresh()
    return list(_cache.get(path, []))


def require_page_permission(*pages: str):
    """FastAPI 依賴：登入者須持有**任一**指定頁面所宣告的權限。

    多個頁面時取聯集 —— 給「一支 API 被兩個頁面共用」的情況
    （例如 `/api/ai/graph/stats` 同時被 ERP 圖譜與 RAG 圖譜用）。
    """
    _referenced_pages.update(pages)

    async def _dep(current_user=Depends(get_current_user)):
        from app.core.auth_service import AuthService
        from app.core.exceptions import ForbiddenException

        if is_superuser_user(current_user):
            return current_user
        required: list[str] = []
        for p in pages:
            required.extend(await permissions_for_page(p))
        if not required:
            # 頁面沒有宣告 ⇒ 只要求登入（不自己發明限制）
            return current_user
        if any(AuthService.check_permission(current_user, code) for code in required):
            return current_user
        raise ForbiddenException(
            f"需要 {' 或 '.join(sorted(set(required)))} 其中之一的權限（由選單「{'、'.join(pages)}」宣告）"
        )
    return _dep

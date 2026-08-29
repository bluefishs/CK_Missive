#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""業務資料量健康檢查（L43 防禦）—— 兩個 health 端點共用的唯一實作。

## 為什麼抽出來

2026-08-29 實查：系統有**兩個** health 端點，而它們的強度差很多。

    /health       （main.py）        DB ping + 業務量檢查 + pool 狀態
    /api/health   （endpoints/health.py）  **靜態 dict，完全不碰 DB**

而**公網走的是後者** —— `https://missive.cksurvey.tw/api/health`
回的是 `{"status":"healthy","timestamp":…,"service":…}`，
**postgres 掛掉它一樣回 healthy**。

L43（2026-05-21 volume mount drift）的修法寫著
「所有面向公網的服務 `/health` endpoint 必須包含業務量檢查」，
機制是「cloudflared healthcheck fail → 流量不打進空殼 instance」。
那個防禦**只做在 `/health` 上，而公網探的是 `/api/health`**
⇒ 同一個事故形態在另一條路徑上原封不動地留著。

⚠️ 而且它騙過的不只是監控：**我自己整天用 `/api/health` 當部署後的驗證**，
那個 200 比我以為的弱得多。

## 這個模組的定位

業務量檢查只留一份實作，兩個端點都呼叫它。
`/health/liveness` 維持「不碰 DB」—— 那是**故意的**（程序活著嗎），
與「系統可用嗎」是兩個問題，不該合併。
"""
import os
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

#: 業務資料檢查 cache（防 /health 每秒 COUNT(*) 打 DB）
_business_data_cache: dict = {"checked_at": 0.0, "result": None}


async def check_business_data_present(db: AsyncSession) -> dict[str, Any]:
    """檢查核心業務表是否有預期最低資料量。

    2026-05-21 事故防禦（L43 volume mount drift）：
    若 docker volume 掛到空殼 / fresh DB / 大規模刪除，container 仍會 "healthy"
    （DB connected、alembic head 推進不需資料），導致業務 API 全 500 但監控無感。

    可透過 env 調整：
    - HEALTH_BUSINESS_CHECK_ENABLED (default true)
    - HEALTH_MIN_DOCUMENTS (default 100)
    - HEALTH_MIN_KG_ENTITIES (default 1000)
    - HEALTH_BUSINESS_CACHE_TTL_S (default 30)
    """
    enabled = os.getenv("HEALTH_BUSINESS_CHECK_ENABLED", "true").lower() == "true"
    if not enabled:
        return {"ok": True, "skipped": True}

    cache_ttl = int(os.getenv("HEALTH_BUSINESS_CACHE_TTL_S", "30"))
    now = time.time()
    cached = _business_data_cache.get("result")
    if cached is not None and (now - _business_data_cache["checked_at"]) < cache_ttl:
        return cached

    min_docs = int(os.getenv("HEALTH_MIN_DOCUMENTS", "100"))
    min_kg = int(os.getenv("HEALTH_MIN_KG_ENTITIES", "1000"))

    try:
        docs = await db.scalar(text("SELECT COUNT(*) FROM documents"))
        kg = await db.scalar(text("SELECT COUNT(*) FROM canonical_entities"))
    except Exception as e:
        result = {
            "ok": False,
            "reason": f"core_tables_query_failed: {type(e).__name__}",
            "error_detail": str(e)[:200],
        }
        _business_data_cache.update({"checked_at": now, "result": result})
        return result

    ok = (docs or 0) >= min_docs and (kg or 0) >= min_kg
    result = {
        "ok": ok,
        "documents": docs,
        "canonical_entities": kg,
        "thresholds": {"documents": min_docs, "canonical_entities": min_kg},
    }
    if not ok:
        result["reason"] = "row_count_below_threshold"
    _business_data_cache.update({"checked_at": now, "result": result})
    return result

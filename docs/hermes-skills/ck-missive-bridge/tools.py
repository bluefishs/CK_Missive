# -*- coding: utf-8 -*-
"""
CK_Missive Bridge — Hermes native tool registration.

部署位置: ~/.hermes/skills/ck-missive-bridge/tools.py
載入時機: Hermes CLI 啟動時由 skill_commands.py 掃描並呼叫 register_all()。

設計：
  - 從 Missive /agent/tools/manifest 端點動態抓取 ToolSpec v1.0 清單
  - 每個 tool 註冊為獨立 Hermes tool（非單一 bridge call）
  - 共用 HTTP handler，統一 auth + timeout + retry

依賴：
  hermes >= 0.9.x (tools.registry)
  httpx
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

import httpx

logger = logging.getLogger("hermes.ck_missive")

MISSIVE_BASE = os.environ.get("MISSIVE_BASE_URL", "http://host.docker.internal:8001")
MISSIVE_TOKEN = os.environ.get("MISSIVE_API_TOKEN", "")
TIMEOUT_S = float(os.environ.get("MISSIVE_TIMEOUT_S", "60"))


# Missive 每個 tool 對應到哪個 HTTP endpoint（與 manifest endpoints map 一致）
_TOOL_ENDPOINT_MAP = {
    "document_search": "/api/ai/rag/query",
    "dispatch_search": "/api/ai/agent/query_sync",
    "entity_search": "/api/ai/graph/entity",
    "entity_detail": "/api/ai/graph/entity",
    "semantic_similar": "/api/ai/rag/query",
    "system_statistics": "/api/ai/agent/query_sync",
    "federated_search": "/api/ai/federation/search",
    "federated_contribute": "/api/ai/federation/contribute",
}


def _fetch_manifest() -> Dict[str, Any]:
    """Fetch manifest via POST（Missive 資安政策：所有端點採 POST）。"""
    url = f"{MISSIVE_BASE}/api/ai/agent/tools"
    headers = {"X-Service-Token": MISSIVE_TOKEN} if MISSIVE_TOKEN else {}
    with httpx.Client(timeout=10.0) as client:
        r = client.post(url, headers=headers, json={})
        r.raise_for_status()
        return r.json()


def _make_handler(tool_name: str):
    endpoint = _TOOL_ENDPOINT_MAP.get(tool_name, "/api/ai/agent/query_sync")

    def handler(args: Dict[str, Any], **ctx) -> str:
        url = f"{MISSIVE_BASE}{endpoint}"
        headers = {
            "Authorization": f"Bearer {MISSIVE_TOKEN}",
            "Content-Type": "application/json",
            "X-Channel": ctx.get("channel", "hermes"),
            "X-Hermes-Session": ctx.get("session_id", ""),
        }
        try:
            with httpx.Client(timeout=TIMEOUT_S) as client:
                r = client.post(url, headers=headers, json=args)
                r.raise_for_status()
                return json.dumps(r.json(), ensure_ascii=False)
        except httpx.TimeoutException:
            return json.dumps({"error": "timeout", "tool": tool_name}, ensure_ascii=False)
        except httpx.HTTPStatusError as e:
            return json.dumps(
                {"error": "http", "status": e.response.status_code, "tool": tool_name},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.exception("ck_missive tool %s failed", tool_name)
            return json.dumps({"error": "internal", "message": str(e)}, ensure_ascii=False)

    return handler


def _check_missive_up() -> bool:
    """Health probe via POST（Missive 資安政策）。

    若 /api/health 未實作 POST，fallback 視為可用（由 manifest fetch 再驗）。
    """
    try:
        with httpx.Client(timeout=3.0) as c:
            r = c.post(f"{MISSIVE_BASE}/api/health", json={})
            return r.status_code in (200, 405)  # 405 表示端點存在
    except Exception:
        return False


def register_all(registry) -> int:
    """Hermes skill loader entry — 將 Missive manifest 內所有 tool 註冊到 registry。"""
    try:
        manifest = _fetch_manifest()
    except Exception as e:
        logger.warning("無法取得 Missive manifest，略過註冊：%s", e)
        return 0

    count = 0
    for tool in manifest.get("tools", []):
        name = tool["name"]
        registry.register(
            name=f"missive_{name}",
            toolset="ck_missive",
            schema={
                "name": f"missive_{name}",
                "description": tool["description"],
                "parameters": tool["inputSchema"],
            },
            handler=_make_handler(name),
            check_fn=_check_missive_up,
        )
        count += 1
    logger.info("ck_missive: registered %d tools from manifest", count)
    return count

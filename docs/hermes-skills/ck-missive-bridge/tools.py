# -*- coding: utf-8 -*-
"""
CK_Missive Bridge — Hermes native tool registration (v2.0).

部署位置: ~/.hermes/skills/ck-missive-bridge/tools.py
載入時機: Hermes CLI 啟動時由 skill_commands.py 掃描並呼叫 register_all()。

設計：
  - 從 Missive /agent/tools/manifest 端點動態抓取 ToolSpec 清單
  - 每個 tool 註冊為獨立 Hermes tool（非單一 bridge call）
  - 若 manifest 不可達，fallback 到 _STATIC_TOOLS 靜態註冊
  - 共用 HTTP handler，統一 auth + timeout + retry

v2.0 變更：
  - 擴充 endpoint map（KG entity/neighbors/shortest-path/timeline）
  - 新增 1 次自動 retry（timeout / 5xx）
  - 新增 X-Hermes-Session header
  - 新增 fallback static tools（manifest 不可達時仍能用）

依賴：
  hermes >= 0.9.x (tools.registry)
  httpx
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List

import httpx

logger = logging.getLogger("hermes.ck_missive")

MISSIVE_BASE = os.environ.get("MISSIVE_BASE_URL", "http://host.docker.internal:8001")
MISSIVE_TOKEN = os.environ.get("MISSIVE_API_TOKEN", "")
TIMEOUT_S = float(os.environ.get("MISSIVE_TIMEOUT_S", "60"))
MAX_RETRIES = 1


# ── Endpoint map ──────────────────────────────────────────
# tool_name → Missive HTTP endpoint (POST only per security policy)

_TOOL_ENDPOINT_MAP = {
    # RAG / semantic search
    "document_search": "/api/ai/rag/query",
    "semantic_similar": "/api/ai/rag/query",
    # General agent query (公文 + 案件 + ERP + 標案)
    "dispatch_search": "/api/ai/agent/query_sync",
    "system_statistics": "/api/ai/agent/query_sync",
    # Knowledge Graph — direct endpoints
    "entity_search": "/api/v1/ai/graph/entity/search",
    "entity_detail": "/api/v1/ai/graph/entity/detail",
    "entity_neighbors": "/api/v1/ai/graph/entity/neighbors",
    "entity_shortest_path": "/api/v1/ai/graph/entity/shortest-path",
    "entity_timeline": "/api/v1/ai/graph/entity/timeline",
    "unified_search": "/api/v1/ai/graph/unified-search",
    # KG Federation
    "federated_search": "/api/ai/federation/search",
    "federated_contribute": "/api/ai/federation/contribute",
    # Documents & Projects (direct CRUD — requires Bearer auth)
    "document_list": "/api/v1/documents-enhanced/list",
    "project_list": "/api/v1/projects/list",
    "project_detail": "/api/v1/projects/{id}/detail",
}


# ── Static fallback tools ─────────────────────────────────
# Used when Missive manifest is unreachable

_STATIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "dispatch_search",
        "description": "通用領域查詢：公文、承攬案件、報價、標案、行事曆、統計。傳入自然語言問題，回傳結構化答案。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "使用者的問題（繁體中文佳）",
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "document_search",
        "description": "公文語意搜尋（RAG + pgvector 768D）。依關鍵字或語意查找相關公文，回傳摘要與來源。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜尋關鍵字或自然語言描述",
                },
                "top_k": {
                    "type": "integer",
                    "description": "回傳筆數上限（預設 5）",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "entity_search",
        "description": "知識圖譜實體搜尋。搜尋人名、公司、機關等實體，回傳 normalized 結果。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "實體名稱或關鍵字",
                },
                "entity_type": {
                    "type": "string",
                    "description": "實體類型篩選（person/company/government/project）",
                    "enum": ["person", "company", "government", "project"],
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "entity_neighbors",
        "description": "查詢知識圖譜中某實體的鄰居（K-hop 關係展開）。找出與指定實體相關的所有人、公司、機關、案件。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "實體 ID",
                },
                "hops": {
                    "type": "integer",
                    "description": "展開深度（預設 1）",
                    "default": 1,
                },
            },
            "required": ["entity_id"],
        },
    },
    {
        "name": "entity_shortest_path",
        "description": "查詢知識圖譜中兩個實體之間的最短路徑。找出 A 和 B 之間的關係鏈。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_id": {
                    "type": "string",
                    "description": "起點實體 ID",
                },
                "target_id": {
                    "type": "string",
                    "description": "終點實體 ID",
                },
            },
            "required": ["source_id", "target_id"],
        },
    },
    {
        "name": "federated_search",
        "description": "KG 聯邦跨域搜尋。同時搜尋 Missive + LvrLand + Tunnel 三個知識圖譜。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜尋關鍵字",
                },
                "domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "限定搜尋的 domain（預設全部）",
                },
            },
            "required": ["query"],
        },
    },
]


# ── HTTP helpers ──────────────────────────────────────────

def _make_headers(ctx: Dict[str, Any]) -> Dict[str, str]:
    """Build request headers with auth + tracing."""
    headers = {
        "Content-Type": "application/json",
        "X-Channel": ctx.get("channel", "hermes"),
        "X-Hermes-Session": ctx.get("session_id", ""),
    }
    if MISSIVE_TOKEN:
        headers["Authorization"] = f"Bearer {MISSIVE_TOKEN}"
        headers["X-Service-Token"] = MISSIVE_TOKEN
    return headers


def _post_with_retry(url: str, headers: Dict, payload: Dict, retries: int = MAX_RETRIES) -> httpx.Response:
    """POST with automatic retry on timeout / 5xx."""
    last_exc = None
    for attempt in range(1 + retries):
        try:
            with httpx.Client(timeout=TIMEOUT_S) as client:
                r = client.post(url, headers=headers, json=payload)
                if r.status_code < 500:
                    return r
                if attempt < retries:
                    time.sleep(1.0)
                    continue
                return r
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_exc = e
            if attempt < retries:
                time.sleep(1.0)
                continue
    raise last_exc  # type: ignore[misc]


# ── Handler factory ───────────────────────────────────────

def _make_handler(tool_name: str):
    endpoint = _TOOL_ENDPOINT_MAP.get(tool_name, "/api/ai/agent/query_sync")

    def handler(args: Dict[str, Any], **ctx) -> str:
        # Replace path params like {id}
        resolved = endpoint
        for key, val in args.items():
            resolved = resolved.replace(f"{{{key}}}", str(val))

        url = f"{MISSIVE_BASE}{resolved}"
        headers = _make_headers(ctx)
        try:
            r = _post_with_retry(url, headers, args)
            r.raise_for_status()
            return json.dumps(r.json(), ensure_ascii=False)
        except httpx.TimeoutException:
            return json.dumps(
                {"error": "timeout", "tool": tool_name, "message": "查詢逾時，請稍後再試"},
                ensure_ascii=False,
            )
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            msg = {
                401: "通道認證失效，請聯繫管理員",
                403: "無權限存取此資源",
                404: "查無此資料",
                500: "後端暫時異常，已記錄",
                504: "查詢逾時，請稍後再試",
            }.get(status, f"HTTP {status}")
            return json.dumps(
                {"error": "http", "status": status, "tool": tool_name, "message": msg},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.exception("ck_missive tool %s failed", tool_name)
            return json.dumps(
                {"error": "internal", "tool": tool_name, "message": str(e)},
                ensure_ascii=False,
            )

    return handler


# ── Health probe ──────────────────────────────────────────

def _check_missive_up() -> bool:
    """Health probe — GET /api/health (fallback to POST if 405)."""
    try:
        with httpx.Client(timeout=3.0) as c:
            r = c.get(f"{MISSIVE_BASE}/api/health")
            if r.status_code in (200, 405):
                return True
            # Fallback: POST
            r = c.post(f"{MISSIVE_BASE}/api/health", json={})
            return r.status_code in (200, 405)
    except Exception:
        return False


# ── Manifest loader ───────────────────────────────────────

def _fetch_manifest() -> Dict[str, Any]:
    """Fetch tool manifest from Missive (POST per security policy)."""
    url = f"{MISSIVE_BASE}/api/ai/agent/tools"
    headers = {"Content-Type": "application/json"}
    if MISSIVE_TOKEN:
        headers["X-Service-Token"] = MISSIVE_TOKEN
    with httpx.Client(timeout=10.0) as client:
        r = client.post(url, headers=headers, json={})
        r.raise_for_status()
        return r.json()


# ── Registration entry point ──────────────────────────────

def register_all(registry) -> int:
    """Hermes skill loader entry — register Missive tools into Hermes registry.

    Strategy:
    1. Try dynamic manifest (all tools from Missive)
    2. Fallback to static tools if manifest unreachable
    """
    tools_to_register: List[Dict[str, Any]] = []

    # Try dynamic manifest first
    try:
        manifest = _fetch_manifest()
        tools_to_register = manifest.get("tools", [])
        logger.info("ck_missive: fetched %d tools from manifest", len(tools_to_register))
    except Exception as e:
        logger.warning("ck_missive: manifest unreachable (%s), using static fallback", e)
        tools_to_register = _STATIC_TOOLS

    count = 0
    for tool in tools_to_register:
        name = tool["name"]
        registry.register(
            name=f"missive_{name}",
            toolset="ck_missive",
            schema={
                "name": f"missive_{name}",
                "description": tool.get("description", name),
                "parameters": tool.get("inputSchema", tool.get("parameters", {})),
            },
            handler=_make_handler(name),
            check_fn=_check_missive_up,
        )
        count += 1

    logger.info("ck_missive: registered %d tools total", count)
    return count

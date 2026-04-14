"""
CK-AaaP Tool Manifest 端點 — Plugin Contract v1.1

提供 CK_Missive 的工具清冊，供 NemoClaw 動態工具發現使用。
回傳格式遵循 CK-AaaP ToolSpec Standard v1.0。
工具定義基於 MCP Server 已有的 7 個工具轉換而來。

Version: 1.0.0
Created: 2026-04-01
"""

import logging

from fastapi import APIRouter, Depends, Request

router = APIRouter(prefix="/agent", tags=["AI-工具清冊"])

logger = logging.getLogger(__name__)

TOOL_MANIFEST = {
    "version": "1.2",
    "serverName": "ck_missive",
    "compat": {
        "ck_aaap": "1.0",
        "hermes_agent": ">=0.9",  # ADR-0014
        "mcp": "2024-11-05",
    },
    # Hermes 端讀此區塊自動註冊 tool，不需硬編碼路徑
    "hermes": {
        "acp_endpoint": "/api/hermes/acp",
        "feedback_endpoint": "/api/hermes/feedback",
        "min_hermes_version": "0.9.0",
        "tool_prefix": "missive_",
        "recommended_llm": "gemma4:8b-q4",
    },
    "endpoints": {
        "document_search": "/api/ai/rag/query",
        "dispatch_search": "/api/ai/agent/query_sync",
        "entity_search": "/api/ai/graph/entity",
        "entity_detail": "/api/ai/graph/entity",
        "semantic_similar": "/api/ai/rag/query",
        "system_statistics": "/api/ai/agent/query_sync",
        "federated_search": "/api/ai/federation/search",
        "federated_contribute": "/api/ai/federation/contribute",
    },
    "auth": {
        "type": "bearer",
        "header": "X-Service-Token",
        "env_var": "MCP_SERVICE_TOKEN",
    },
    "tools": [
        {
            "name": "document_search",
            "description": "公文搜尋（向量+關鍵字混合），支援發文者、收文者、文號、日期範圍篩選",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜尋關鍵字或自然語言查詢",
                    },
                    "sender": {
                        "type": "string",
                        "description": "發文機關篩選",
                    },
                    "receiver": {
                        "type": "string",
                        "description": "受文機關篩選",
                    },
                    "doc_type": {
                        "type": "string",
                        "description": "文別篩選（函、令、公告等）",
                    },
                    "date_from": {
                        "type": "string",
                        "format": "date",
                        "description": "起始日期",
                    },
                    "date_to": {
                        "type": "string",
                        "format": "date",
                        "description": "結束日期",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "category": "query",
            "permission": "read",
            "estimatedLatency": "medium",
            "tags": ["document", "search", "fulltext", "semantic"],
        },
        {
            "name": "dispatch_search",
            "description": "派工單搜尋，查詢派工紀錄與進度追蹤",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜尋關鍵字",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed", "all"],
                        "default": "all",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "category": "query",
            "permission": "read",
            "estimatedLatency": "medium",
            "tags": ["dispatch", "search", "progress"],
        },
        {
            "name": "entity_search",
            "description": "知識圖譜實體搜尋，查詢人員、機關、地點等實體",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "實體名稱或關鍵字",
                    },
                    "entity_type": {
                        "type": "string",
                        "enum": ["person", "organization", "location", "project", "all"],
                        "default": "all",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "category": "query",
            "permission": "read",
            "estimatedLatency": "fast",
            "tags": ["entity", "knowledge_graph", "search"],
        },
        {
            "name": "entity_detail",
            "description": "實體詳情查詢，取得實體的關係網路與相關公文",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "integer",
                        "description": "實體 ID",
                    },
                },
                "required": ["entity_id"],
                "additionalProperties": False,
            },
            "category": "query",
            "permission": "read",
            "estimatedLatency": "fast",
            "tags": ["entity", "detail", "relationship"],
        },
        {
            "name": "semantic_similar",
            "description": "語意相似公文搜尋，基於向量 embedding 找出內容相近的公文",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "參考文字或公文摘要",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 5,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "category": "query",
            "permission": "read",
            "estimatedLatency": "medium",
            "tags": ["semantic", "similar", "embedding", "vector"],
        },
        {
            "name": "system_statistics",
            "description": "系統統計數據：公文總數、實體數、近期活動趨勢",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "category": "query",
            "permission": "read",
            "estimatedLatency": "fast",
            "tags": ["statistics", "dashboard", "overview"],
        },
        {
            "name": "federated_search",
            "description": "跨域聯邦搜尋，跨 Missive/LvrLand/Tunnel 搜尋相關實體",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜尋關鍵字",
                    },
                    "source_projects": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["ck_missive", "ck_lvrland", "ck_tunnel"],
                        },
                        "description": "限定來源專案（不填則搜尋全部）",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "category": "query",
            "permission": "read",
            "estimatedLatency": "medium",
            "tags": ["federation", "cross_domain", "search"],
        },
        {
            "name": "federated_contribute",
            "description": "聯邦知識圖譜實體貢獻，其他插件向 KG Hub 同步實體",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "canonical_name": {"type": "string"},
                                "entity_type": {"type": "string"},
                                "source_project": {"type": "string"},
                                "external_id": {"type": "string"},
                            },
                            "required": ["canonical_name", "entity_type", "source_project"],
                        },
                        "description": "待貢獻的實體陣列",
                    },
                },
                "required": ["entities"],
                "additionalProperties": False,
            },
            "category": "mutation",
            "permission": "write",
            "estimatedLatency": "medium",
            "tags": ["federation", "contribute", "knowledge_graph"],
        },
    ],
}


@router.post(
    "/tools",
    summary="工具清冊 (Plugin Contract v1.2) — POST（資安政策）",
)
async def get_tools():
    """回傳 CK_Missive 的工具清冊，供 NemoClaw / Hermes 動態工具發現使用。

    資安規範：所有端點採 POST（含無狀態查詢）。
    """
    return TOOL_MANIFEST

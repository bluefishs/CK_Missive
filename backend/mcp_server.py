"""
CK_Missive MCP Server — Model Context Protocol 服務

將 7 個 Agent 工具暴露為 MCP Tools，供 Claude Desktop、OpenClaw 等 MCP 客戶端存取。
MCP 透過 stdio 通訊，存取控制由父 process（Claude Desktop / OpenClaw）負責。

啟動方式:
    cd backend
    python mcp_server.py

Claude Desktop 配置 (claude_desktop_config.json):
    {
        "mcpServers": {
            "ck-missive": {
                "command": "python",
                "args": ["<YOUR_PROJECT_ROOT>/backend/mcp_server.py"],
                "env": {
                    "DATABASE_URL": "postgresql://...",
                    "MCP_SERVICE_TOKEN": "your-token-here"
                }
            }
        }
    }

@version 1.3.0
@date 2026-03-07
"""

import asyncio
import atexit
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

# 確保 backend/ 在 import path 中
_backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_backend_dir))

# 載入 .env（從專案根目錄）
from dotenv import load_dotenv

_project_root = _backend_dir.parent
load_dotenv(_project_root / ".env", override=True)

# Windows UTF-8 保護
os.environ.setdefault("PYTHONUTF8", "1")

from mcp.server.fastmcp import FastMCP
from app.services.ai.ai_config import get_ai_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("mcp_server")

# ============================================================================
# 常數
# ============================================================================

_MAX_QUESTION_LENGTH = 500
_MAX_QUERY_LENGTH = 200

# ============================================================================
# MCP Server 初始化
# ============================================================================

mcp = FastMCP(
    "ck-missive",
    instructions="CK_Missive 公文管理系統 — 公文搜尋、派工單查詢、知識圖譜、語意相似度",
)

# ============================================================================
# 資料庫連線（獨立於 FastAPI，輕量連線池供 MCP 獨立 process 使用）
# ============================================================================

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

_db_url = os.getenv("DATABASE_URL")
if not _db_url:
    logger.error("DATABASE_URL 環境變數未設定，MCP Server 無法啟動")
    sys.exit(1)
_async_db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://")

_mcp_pool_size = int(os.getenv("MCP_POOL_SIZE", "3"))
_mcp_max_overflow = int(os.getenv("MCP_MAX_OVERFLOW", "5"))

_engine = create_async_engine(
    _async_db_url,
    pool_pre_ping=True,
    pool_size=_mcp_pool_size,
    max_overflow=_mcp_max_overflow,
    pool_recycle=300,
    pool_timeout=30,
    connect_args={
        "server_settings": {
            "application_name": "ck_missive_mcp",
            "statement_timeout": "30000",
        },
        "command_timeout": 60,
    },
)

_async_session = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def _dispose_engine():
    """在程式結束時清理 DB engine"""
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_engine.dispose())
        loop.close()
    except Exception:
        pass  # Safe to ignore at shutdown


atexit.register(_dispose_engine)


async def _execute_tool(tool_name: str, params: dict[str, Any]) -> str:
    """執行工具並回傳 JSON 字串"""
    async with _async_session() as db:
        from app.services.ai.agent_tools import AgentToolExecutor
        from app.services.ai.ai_config import get_ai_config
        from app.core.ai_connector import get_ai_connector
        from app.services.ai.embedding_manager import EmbeddingManager

        executor = AgentToolExecutor(db, get_ai_connector(), EmbeddingManager(), get_ai_config())
        result = await executor.execute(tool_name, params)
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def _validate_str(value: Optional[str], max_len: int, name: str) -> Optional[str]:
    """驗證字串參數長度"""
    if value is not None and len(value) > max_len:
        raise ValueError(f"{name} 超過最大長度 {max_len}")
    return value


# ============================================================================
# MCP Tools — 7 個工具
# ============================================================================


@mcp.tool()
async def search_documents(
    keywords: list[str] | None = None,
    sender: str | None = None,
    receiver: str | None = None,
    doc_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 5,
) -> str:
    """搜尋公文資料庫。支援關鍵字、發文/受文單位、日期範圍、公文類型等條件。

    Args:
        keywords: 搜尋關鍵字列表，例如 ["道路", "測量"]
        sender: 發文單位（模糊匹配），例如 "桃園市政府"
        receiver: 受文單位（模糊匹配）
        doc_type: 公文類型：函/令/公告/書函/開會通知單/簽
        date_from: 起始日期 YYYY-MM-DD
        date_to: 結束日期 YYYY-MM-DD
        limit: 最大結果數（預設 5，最大 10）

    Returns:
        JSON 格式的公文搜尋結果，含 documents 陣列和 total 總數
    """
    _validate_str(sender, _MAX_QUERY_LENGTH, "sender")
    _validate_str(receiver, _MAX_QUERY_LENGTH, "receiver")
    _validate_str(doc_type, 50, "doc_type")

    params = {}
    if keywords:
        params["keywords"] = [k[:_MAX_QUERY_LENGTH] for k in keywords[:10]]
    if sender:
        params["sender"] = sender
    if receiver:
        params["receiver"] = receiver
    if doc_type:
        params["doc_type"] = doc_type
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    params["limit"] = min(limit, 10)

    return await _execute_tool("search_documents", params)


@mcp.tool()
async def search_dispatch_orders(
    dispatch_no: str | None = None,
    search: str | None = None,
    work_type: str | None = None,
    limit: int = 5,
) -> str:
    """搜尋桃園市政府工務局派工單紀錄。支援派工單號、工程名稱、作業類別等條件。

    Args:
        dispatch_no: 派工單號（模糊匹配），例如 "014"
        search: 關鍵字搜尋（同時搜尋派工單號 + 工程名稱）
        work_type: 作業類別：地形測量/控制測量/協議價購/用地取得
        limit: 最大結果數（預設 5，最大 20）

    Returns:
        JSON 格式的派工單列表 + 關聯公文
    """
    _validate_str(dispatch_no, 50, "dispatch_no")
    _validate_str(search, _MAX_QUERY_LENGTH, "search")
    _validate_str(work_type, 50, "work_type")

    params = {}
    if dispatch_no:
        params["dispatch_no"] = dispatch_no
    if search:
        params["search"] = search
    if work_type:
        params["work_type"] = work_type
    params["limit"] = min(limit, 20)

    return await _execute_tool("search_dispatch_orders", params)


@mcp.tool()
async def search_entities(
    query: str,
    entity_type: str | None = None,
    limit: int = 5,
) -> str:
    """在知識圖譜中搜尋實體（機關、人員、專案、地點等）。

    Args:
        query: 搜尋文字，例如 "桃園市政府"（最長 200 字）
        entity_type: 篩選實體類型：org/person/project/location/topic/date
        limit: 最大結果數（預設 5，最大 20）

    Returns:
        JSON 格式的實體搜尋結果
    """
    _validate_str(query, _MAX_QUERY_LENGTH, "query")

    params = {"query": query}
    if entity_type:
        params["entity_type"] = entity_type
    params["limit"] = min(limit, 20)

    return await _execute_tool("search_entities", params)


@mcp.tool()
async def get_entity_detail(entity_id: int) -> str:
    """取得知識圖譜中某個實體的詳細資訊，包含別名、關係、關聯公文。

    Args:
        entity_id: 實體 ID（從 search_entities 結果取得）

    Returns:
        JSON 格式的實體詳情（含 relationships 和 documents）
    """
    return await _execute_tool("get_entity_detail", {"entity_id": entity_id})


@mcp.tool()
async def find_similar(document_id: int, limit: int = 5) -> str:
    """根據指定公文 ID 查找語意相似的公文（基於 pgvector 向量相似度）。

    Args:
        document_id: 公文 ID（從 search_documents 結果取得）
        limit: 最大結果數（預設 5，最大 10）

    Returns:
        JSON 格式的相似公文列表（含 similarity 分數 0~1）
    """
    return await _execute_tool("find_similar", {
        "document_id": document_id,
        "limit": min(limit, 10),
    })


@mcp.tool()
async def get_statistics() -> str:
    """取得系統統計資訊：知識圖譜實體/關係數量、高頻實體排行等。

    Returns:
        JSON 格式的統計資料
    """
    return await _execute_tool("get_statistics", {})


# ============================================================================
# 非串流問答工具（供 OpenClaw 等外部系統呼叫）
# ============================================================================


@mcp.tool()
async def ask_question(
    question: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    """向 CK_Missive AI 助理提問。系統會自動選擇合適的工具搜尋公文、派工單、知識圖譜等資料並回答。

    Args:
        question: 問題（1-500 字），例如 "最近有哪些關於道路工程的公文？"
        history: 對話歷史（可選），格式 [{"role": "user", "content": "..."},
                 {"role": "assistant", "content": "..."}]

    Returns:
        JSON 格式的 AI 回答，含 answer + sources + tools_used
    """
    if not question or len(question) > _MAX_QUESTION_LENGTH:
        return json.dumps(
            {"error": f"question 長度須為 1-{_MAX_QUESTION_LENGTH} 字"},
            ensure_ascii=False,
        )

    from app.services.ai.agent_orchestrator import AgentOrchestrator

    async def _run_query():
        async with _async_session() as db:
            orchestrator = AgentOrchestrator(db)
            answer_tokens = []
            sources = []
            tools_used = []

            async for event_str in orchestrator.stream_agent_query(
                question=question, history=history
            ):
                if not event_str.startswith("data: "):
                    continue
                try:
                    event = json.loads(event_str[6:])
                except (json.JSONDecodeError, IndexError):
                    continue

                event_type = event.get("type")
                if event_type == "token":
                    answer_tokens.append(event.get("token", ""))
                elif event_type == "sources":
                    sources = event.get("sources", [])
                elif event_type == "tool_result":
                    tools_used.append(event.get("tool", ""))
                elif event_type == "error":
                    return json.dumps({
                        "error": event.get("error", "未知錯誤"),
                        "code": event.get("code", ""),
                    }, ensure_ascii=False)

            answer = "".join(answer_tokens)
            result = {"answer": answer}
            if sources:
                result["sources"] = sources
            if tools_used:
                result["tools_used"] = tools_used
            return json.dumps(result, ensure_ascii=False, indent=2, default=str)

    try:
        _timeout = get_ai_config().agent_sync_query_timeout
        return await asyncio.wait_for(_run_query(), timeout=_timeout)
    except asyncio.TimeoutError:
        _timeout = get_ai_config().agent_sync_query_timeout
        return json.dumps(
            {"error": f"查詢逾時（{_timeout} 秒）", "code": "TIMEOUT"},
            ensure_ascii=False,
        )


# ============================================================================
# MCP Resources — 系統資訊 + 知識圖譜瀏覽 + 公文瀏覽
# ============================================================================


@mcp.resource("ck-missive://system/info")
async def get_system_info() -> str:
    """CK_Missive 系統基本資訊"""
    return json.dumps({
        "name": "CK_Missive 公文管理系統",
        "version": os.getenv("PROJECT_VERSION", "3.1"),
        "description": "企業級公文管理系統，具備公文管理、派工追蹤、知識圖譜、AI 問答功能",
        "tools_count": 7,
        "resources_count": 6,
        "prompts_count": 3,
        "tools": [
            "search_documents — 公文搜尋（向量+關鍵字混合）",
            "search_dispatch_orders — 派工單搜尋",
            "search_entities — 知識圖譜實體搜尋",
            "get_entity_detail — 實體詳情（關係+公文）",
            "find_similar — 語意相似公文",
            "get_statistics — 系統統計",
            "ask_question — AI 問答（自動選工具，支援多輪對話）",
        ],
    }, ensure_ascii=False, indent=2)


@mcp.resource("ck-missive://stats/overview")
async def get_stats_overview() -> str:
    """系統統計概覽：知識圖譜實體/關係數量、公文總數、高頻實體排行"""
    return await _execute_tool("get_statistics", {})


@mcp.resource("ck-missive://entities/top")
async def get_top_entities_resource() -> str:
    """知識圖譜中提及次數最多的前 20 個實體"""
    async with _async_session() as db:
        from app.services.ai.graph_query_service import GraphQueryService
        svc = GraphQueryService(db)
        entities = await svc.get_top_entities(limit=20)
        return json.dumps(
            {"entities": entities, "count": len(entities)},
            ensure_ascii=False, indent=2, default=str,
        )


@mcp.resource("ck-missive://entities/{entity_id}")
async def get_entity_resource(entity_id: int) -> str:
    """取得特定知識圖譜實體的完整資料（別名、關係、關聯公文）"""
    return await _execute_tool("get_entity_detail", {"entity_id": entity_id})


@mcp.resource("ck-missive://entities/{entity_id}/neighbors")
async def get_entity_neighbors_resource(entity_id: int) -> str:
    """取得實體的 2-hop 鄰居圖（節點 + 邊）"""
    async with _async_session() as db:
        from app.services.ai.graph_query_service import GraphQueryService
        svc = GraphQueryService(db)
        result = await svc.get_neighbors(entity_id, max_hops=2, limit=50)
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.resource("ck-missive://documents/{doc_id}/similar")
async def get_similar_documents_resource(doc_id: int) -> str:
    """取得與指定公文語意最相似的 5 篇公文"""
    return await _execute_tool("find_similar", {"document_id": doc_id, "limit": 5})


# ============================================================================
# MCP Prompts — 預設查詢模板
# ============================================================================


@mcp.prompt()
def document_search(topic: str) -> str:
    """搜尋特定主題的公文並分析關鍵時程與相關機關

    Args:
        topic: 搜尋主題，例如「道路工程」「土地測量」「都市計畫」
    """
    return (
        f"請搜尋與「{topic}」相關的公文，列出：\n"
        f"1. 公文清單（含文號、主旨、日期）\n"
        f"2. 關鍵時程與截止日\n"
        f"3. 涉及的主要機關\n"
        f"4. 若有派工單關聯，請一併列出"
    )


@mcp.prompt()
def entity_exploration(entity_name: str) -> str:
    """深入分析知識圖譜中某個實體的完整關聯網路

    Args:
        entity_name: 實體名稱，例如「桃園市政府工務局」「道路養護工程處」
    """
    return (
        f"請分析「{entity_name}」的完整關聯網路：\n"
        f"1. 先在知識圖譜中搜尋此實體\n"
        f"2. 取得其詳細資料（別名、關係）\n"
        f"3. 列出所有關聯的機關、專案和公文\n"
        f"4. 整理為時間軸呈現互動歷程"
    )


@mcp.prompt()
def dispatch_overview(project_name: str) -> str:
    """查詢特定工程的派工單與公文關聯全貌

    Args:
        project_name: 工程名稱，例如「中壢區道路工程」「龜山區測量」
    """
    return (
        f"請查詢「{project_name}」相關的完整資訊：\n"
        f"1. 搜尋相關派工單紀錄\n"
        f"2. 搜尋相關公文\n"
        f"3. 整理派工單與公文的對應關係\n"
        f"4. 列出作業進度與待辦事項"
    )


# ============================================================================
# 入口點
# ============================================================================

if __name__ == "__main__":
    if not os.getenv("MCP_SERVICE_TOKEN"):
        logger.warning(
            "MCP_SERVICE_TOKEN 未設定。"
            "MCP Server 透過 stdio 通訊，存取控制由父 process 負責。"
        )
    logger.info("Starting CK_Missive MCP Server (7 tools, 6 resources, 3 prompts)...")
    mcp.run()

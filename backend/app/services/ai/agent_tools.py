"""
Agent 工具模組 — 6 個工具定義與實作

工具清單：
- search_documents: 向量+SQL 混合公文搜尋 + Hybrid Reranking
- search_dispatch_orders: 派工單搜尋 (桃園工務局)
- search_entities: 知識圖譜實體搜尋
- get_entity_detail: 實體詳情 (關係+關聯公文)
- find_similar: 語意相似公文
- get_statistics: 圖譜 / 公文統計

Extracted from agent_orchestrator.py v1.8.0
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ============================================================================
# Tool 定義 — LLM 看到的工具描述
# ============================================================================

TOOL_DEFINITIONS = [
    {
        "name": "search_documents",
        "description": "搜尋公文資料庫，支援關鍵字、發文單位、受文單位、日期範圍、公文類型等條件。回傳匹配的公文列表。",
        "parameters": {
            "keywords": {"type": "array", "description": "搜尋關鍵字列表"},
            "sender": {"type": "string", "description": "發文單位 (模糊匹配)"},
            "receiver": {"type": "string", "description": "受文單位 (模糊匹配)"},
            "doc_type": {"type": "string", "description": "公文類型 (函/令/公告/書函/開會通知單/簽等)"},
            "date_from": {"type": "string", "description": "起始日期 YYYY-MM-DD"},
            "date_to": {"type": "string", "description": "結束日期 YYYY-MM-DD"},
            "limit": {"type": "integer", "description": "最大結果數 (預設5, 最大10)"},
        },
    },
    {
        "name": "search_entities",
        "description": "在知識圖譜中搜尋實體（機關、人員、專案、地點等）。回傳匹配的正規化實體列表。",
        "parameters": {
            "query": {"type": "string", "description": "搜尋文字"},
            "entity_type": {"type": "string", "description": "篩選實體類型: org/person/project/location/topic/date"},
            "limit": {"type": "integer", "description": "最大結果數 (預設5)"},
        },
    },
    {
        "name": "get_entity_detail",
        "description": "取得知識圖譜中某個實體的詳細資訊，包含別名、關係、關聯公文。適合深入了解特定機關、人員或專案。",
        "parameters": {
            "entity_id": {"type": "integer", "description": "實體 ID (從 search_entities 取得)"},
        },
    },
    {
        "name": "find_similar",
        "description": "根據指定公文 ID 查找語意相似的公文。適合找出相關或類似主題的公文。",
        "parameters": {
            "document_id": {"type": "integer", "description": "公文 ID (從 search_documents 取得)"},
            "limit": {"type": "integer", "description": "最大結果數 (預設5)"},
        },
    },
    {
        "name": "search_dispatch_orders",
        "description": "搜尋派工單紀錄（桃園市政府工務局委託案件）。支援派工單號、工程名稱、作業類別等條件。適合查詢「派工單號XXX」「道路工程派工」「測量作業」等問題。",
        "parameters": {
            "dispatch_no": {"type": "string", "description": "派工單號 (模糊匹配，如 '014' 會匹配 '115年_派工單號014')"},
            "search": {"type": "string", "description": "關鍵字搜尋 (同時搜尋派工單號 + 工程名稱)"},
            "work_type": {"type": "string", "description": "作業類別 (如 地形測量/控制測量/協議價購/用地取得 等)"},
            "limit": {"type": "integer", "description": "最大結果數 (預設5, 最大20)"},
        },
    },
    {
        "name": "get_statistics",
        "description": "取得系統統計資訊：知識圖譜實體/關係數量、高頻實體排行等。適合回答「系統有多少」「最常見的」之類的問題。",
        "parameters": {},
    },
]

TOOL_DEFINITIONS_STR = json.dumps(TOOL_DEFINITIONS, ensure_ascii=False, indent=2)

VALID_TOOL_NAMES = {t["name"] for t in TOOL_DEFINITIONS}

# LLM 自然語言 entity_type → DB 欄位值對照
ENTITY_TYPE_MAP = {
    "organization": "org", "organisation": "org", "機關": "org",
    "人員": "person", "人": "person",
    "專案": "project", "案件": "project",
    "地點": "location", "地址": "location",
    "主題": "topic", "議題": "topic",
    "日期": "date", "時間": "date",
}


class AgentToolExecutor:
    """Agent 工具執行器 — 封裝 6 個工具的實作邏輯"""

    def __init__(self, db: AsyncSession, ai_connector, embedding_mgr, config):
        self.db = db
        self.ai = ai_connector
        self.embedding_mgr = embedding_mgr
        self.config = config

    async def execute_parallel(
        self, calls: List[Dict[str, Any]], tool_timeout: float,
    ) -> List[Dict[str, Any]]:
        """
        並行執行多個工具（每個工具獨立 db session + 超時保護）。

        用於 LLM 規劃回傳 2+ 個無相依工具呼叫時，省去串行等待。
        每個工具建立獨立 AsyncSession，避免 SQLAlchemy 並發存取限制。
        """
        from app.db.database import AsyncSessionLocal

        async def _run_one(call: Dict[str, Any]) -> Dict[str, Any]:
            tool_name = call.get("name", "")
            params = call.get("params", {})
            try:
                async with AsyncSessionLocal() as session:
                    executor = AgentToolExecutor(
                        session, self.ai, self.embedding_mgr, self.config,
                    )
                    return await asyncio.wait_for(
                        executor.execute(tool_name, params),
                        timeout=tool_timeout,
                    )
            except asyncio.TimeoutError:
                logger.warning("Tool %s timed out (%ds) in parallel", tool_name, tool_timeout)
                return {"error": f"工具執行超時 ({tool_timeout}s)", "count": 0}
            except Exception as e:
                logger.error("Tool %s failed in parallel: %s", tool_name, e)
                return {"error": str(e), "count": 0}

        results = await asyncio.gather(*[_run_one(c) for c in calls])
        return list(results)

    async def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """路由工具呼叫至對應實作"""
        dispatch_map = {
            "search_documents": self._search_documents,
            "search_dispatch_orders": self._search_dispatch_orders,
            "search_entities": self._search_entities,
            "get_entity_detail": self._get_entity_detail,
            "find_similar": self._find_similar,
            "get_statistics": self._get_statistics,
        }

        handler = dispatch_map.get(tool_name)
        if not handler:
            return {"error": f"未知工具: {tool_name}", "count": 0}

        return await handler(params)

    async def _search_documents(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋公文 — 向量+SQL搜尋 + Hybrid Reranking"""
        from app.services.ai.search_entity_expander import expand_search_terms, flatten_expansions
        from app.services.ai.reranker import rerank_documents
        from app.repositories.query_builders.document_query_builder import DocumentQueryBuilder

        keywords = params.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [keywords]
        original_keywords = list(keywords)

        # 同義詞/實體擴展 (強化查詢召回率)
        if keywords:
            try:
                expansions = await expand_search_terms(self.db, keywords)
                keywords = flatten_expansions(expansions)
            except Exception as e:
                logger.debug("Synonym expansion failed, using original keywords: %s", e)

        qb = DocumentQueryBuilder(self.db)

        if keywords:
            qb = qb.with_keywords_full(keywords)
        if params.get("sender"):
            qb = qb.with_sender_like(params["sender"])
        if params.get("receiver"):
            qb = qb.with_receiver_like(params["receiver"])
        if params.get("doc_type"):
            qb = qb.with_doc_type(params["doc_type"])

        date_from, date_to = None, None
        if params.get("date_from"):
            try:
                date_from = datetime.strptime(params["date_from"], "%Y-%m-%d").date()
            except ValueError:
                pass
        if params.get("date_to"):
            try:
                date_to = datetime.strptime(params["date_to"], "%Y-%m-%d").date()
            except ValueError:
                pass
        if date_from or date_to:
            qb = qb.with_date_range(date_from, date_to)

        if keywords:
            relevance_text = " ".join(keywords)
            try:
                query_embedding = await self.embedding_mgr.get_embedding(
                    relevance_text, self.ai
                )
                if query_embedding:
                    qb = qb.with_relevance_order(relevance_text)
                    qb = qb.with_semantic_search(
                        query_embedding,
                        weight=self.config.hybrid_semantic_weight,
                    )
                else:
                    qb = qb.with_relevance_order(relevance_text)
            except Exception:
                qb = qb.with_relevance_order(relevance_text)
        else:
            qb = qb.order_by("updated_at", descending=True)

        limit = min(int(params.get("limit", 5)), 10)
        fetch_limit = min(limit * 2, 20)
        qb = qb.limit(fetch_limit)

        documents, total = await qb.execute_with_count()

        docs = []
        for doc in documents:
            docs.append({
                "id": doc.id,
                "doc_number": doc.doc_number or "",
                "subject": doc.subject or "",
                "doc_type": doc.doc_type or "",
                "category": doc.category or "",
                "sender": doc.sender or "",
                "receiver": doc.receiver or "",
                "doc_date": str(doc.doc_date) if doc.doc_date else "",
                "status": doc.status or "",
                "similarity": 0,
            })

        # Hybrid Reranking (向量+關鍵字覆蓋度)
        if docs and original_keywords:
            docs = rerank_documents(docs, original_keywords)
            docs = docs[:limit]
        else:
            docs = docs[:limit]

        return {"documents": docs, "total": total, "count": len(docs)}

    async def _search_dispatch_orders(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋派工單紀錄"""
        from app.repositories.taoyuan.dispatch_order_repository import DispatchOrderRepository

        dispatch_no = params.get("dispatch_no", "")
        search = params.get("search", "")
        work_type = params.get("work_type")
        limit = min(int(params.get("limit", 5)), 20)

        repo = DispatchOrderRepository(self.db)

        if dispatch_no:
            search_term = dispatch_no.strip()
            items, total = await repo.filter_dispatch_orders(
                search=search_term,
                work_type=work_type,
                limit=limit,
            )
        elif search:
            items, total = await repo.filter_dispatch_orders(
                search=search.strip(),
                work_type=work_type,
                limit=limit,
            )
        else:
            items, total = await repo.filter_dispatch_orders(
                work_type=work_type,
                limit=limit,
                sort_by="id",
                sort_order="desc",
            )

        dispatch_orders = []
        dispatch_ids = []
        for item in items:
            dispatch_orders.append({
                "id": item.id,
                "dispatch_no": item.dispatch_no or "",
                "project_name": item.project_name or "",
                "work_type": item.work_type or "",
                "sub_case_name": item.sub_case_name or "",
                "case_handler": item.case_handler or "",
                "survey_unit": item.survey_unit or "",
                "deadline": item.deadline or "",
                "created_at": str(item.created_at) if item.created_at else "",
            })
            dispatch_ids.append(item.id)

        # 查詢關聯公文（透過 taoyuan_dispatch_document_link）
        linked_docs: List[Dict[str, Any]] = []
        if dispatch_ids:
            try:
                from sqlalchemy import select
                from app.extended.models import (
                    OfficialDocument,
                    TaoyuanDispatchDocumentLink,
                )

                stmt = (
                    select(
                        TaoyuanDispatchDocumentLink.dispatch_order_id,
                        OfficialDocument.id,
                        OfficialDocument.doc_number,
                        OfficialDocument.subject,
                        OfficialDocument.doc_type,
                        OfficialDocument.doc_date,
                    )
                    .join(
                        OfficialDocument,
                        OfficialDocument.id == TaoyuanDispatchDocumentLink.document_id,
                    )
                    .where(
                        TaoyuanDispatchDocumentLink.dispatch_order_id.in_(dispatch_ids)
                    )
                )
                result = await self.db.execute(stmt)
                for row in result.fetchall():
                    linked_docs.append({
                        "dispatch_order_id": row[0],
                        "document_id": row[1],
                        "doc_number": row[2] or "",
                        "subject": row[3] or "",
                        "doc_type": row[4] or "",
                        "doc_date": str(row[5]) if row[5] else "",
                    })
            except Exception as e:
                logger.debug("Failed to fetch linked documents for dispatch orders: %s", e)

        return {
            "dispatch_orders": dispatch_orders,
            "linked_documents": linked_docs,
            "total": total,
            "count": len(dispatch_orders),
        }

    async def _search_entities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋知識圖譜實體"""
        from app.services.ai.graph_query_service import GraphQueryService

        svc = GraphQueryService(self.db)
        query = params.get("query", "")
        entity_type = params.get("entity_type")
        # 正規化 entity_type：LLM 可能產生 "organization" 等自然語言名稱
        if entity_type:
            entity_type = ENTITY_TYPE_MAP.get(entity_type.lower(), entity_type)
        limit = min(int(params.get("limit", 5)), 20)

        entities = await svc.search_entities(query, entity_type=entity_type, limit=limit)
        return {"entities": entities, "count": len(entities)}

    async def _get_entity_detail(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """取得實體詳情"""
        from app.services.ai.graph_query_service import GraphQueryService

        entity_id = params.get("entity_id")
        if not entity_id:
            return {"error": "缺少 entity_id 參數", "count": 0}

        svc = GraphQueryService(self.db)
        detail = await svc.get_entity_detail(int(entity_id))

        if not detail:
            return {"error": f"找不到實體 ID={entity_id}", "count": 0}

        return {
            "entity": detail,
            "count": 1,
            "documents": detail.get("documents", []),
            "relationships": detail.get("relationships", []),
        }

    async def _find_similar(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查找語意相似公文"""
        from app.extended.models import OfficialDocument
        from sqlalchemy import select

        doc_id = params.get("document_id")
        if not doc_id:
            return {"error": "缺少 document_id 參數", "count": 0}

        result = await self.db.execute(
            select(OfficialDocument).where(OfficialDocument.id == int(doc_id))
        )
        source_doc = result.scalar_one_or_none()
        if not source_doc or source_doc.embedding is None:
            return {"error": f"公文 ID={doc_id} 不存在或無向量", "count": 0}

        embedding_col = OfficialDocument.embedding
        distance_expr = embedding_col.cosine_distance(source_doc.embedding)
        similarity_expr = (1 - distance_expr).label("similarity")

        limit = min(int(params.get("limit", 5)), 10)

        stmt = (
            select(
                OfficialDocument.id,
                OfficialDocument.doc_number,
                OfficialDocument.subject,
                OfficialDocument.doc_type,
                OfficialDocument.sender,
                OfficialDocument.doc_date,
                similarity_expr,
            )
            .where(embedding_col.isnot(None))
            .where(OfficialDocument.id != int(doc_id))
            .where(distance_expr <= self.config.agent_find_similar_threshold)
            .order_by(distance_expr)
            .limit(limit)
        )

        rows = (await self.db.execute(stmt)).all()
        docs = [
            {
                "id": row.id,
                "doc_number": row.doc_number or "",
                "subject": row.subject or "",
                "doc_type": row.doc_type or "",
                "sender": row.sender or "",
                "doc_date": str(row.doc_date) if row.doc_date else "",
                "similarity": round(float(row.similarity), 4),
            }
            for row in rows
        ]

        return {"documents": docs, "count": len(docs)}

    async def _get_statistics(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        """取得圖譜統計 + 高頻實體"""
        from app.services.ai.graph_query_service import GraphQueryService

        svc = GraphQueryService(self.db)
        stats = await svc.get_graph_stats()
        top_entities = await svc.get_top_entities(limit=10)

        return {
            "stats": stats,
            "top_entities": top_entities,
            "count": 1,
        }

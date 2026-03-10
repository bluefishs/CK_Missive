"""
Agent 工具模組 — 6 個工具定義與實作

工具清單：
- search_documents: 向量+SQL 混合公文搜尋 + Hybrid Reranking + 圖增強鄰域擴展
- search_dispatch_orders: 派工單搜尋 (桃園工務局)
- search_entities: 知識圖譜實體搜尋
- get_entity_detail: 實體詳情 (關係+關聯公文)
- find_similar: 語意相似公文
- get_statistics: 圖譜 / 公文統計

Version: 1.1.0 - GraphRAG Phase 1: 圖增強鄰域擴展
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
# Tool 定義 — 由 ToolRegistry 統一管理（SSOT）
# tool_registry.py 不匯入本模組，無循環匯入風險
# ============================================================================

from app.services.ai.tool_registry import get_tool_registry as _get_tool_registry

_registry = _get_tool_registry()

TOOL_DEFINITIONS = _registry.get_definitions()
TOOL_DEFINITIONS_STR = _registry.get_definitions_json()
VALID_TOOL_NAMES = _registry.valid_tool_names

# dispatch_map 鍵集合（模組載入時一次性定義，供一致性檢查）
_DISPATCH_KEYS = {
    "search_documents",
    "search_dispatch_orders",
    "search_entities",
    "get_entity_detail",
    "find_similar",
    "get_statistics",
}
if _DISPATCH_KEYS != VALID_TOOL_NAMES:
    raise RuntimeError(
        f"dispatch_map keys {_DISPATCH_KEYS} != registry tools {VALID_TOOL_NAMES}"
    )

# LLM 自然語言 entity_type → DB 欄位值對照
ENTITY_TYPE_MAP = {
    "organization": "org", "organisation": "org", "機關": "org",
    "人員": "person", "人": "person",
    "專案": "project", "案件": "project",
    "地點": "location", "地址": "location",
    "主題": "topic", "議題": "topic",
    "日期": "date", "時間": "date",
    # Code Graph (v1.80.0)
    "模組": "py_module", "module": "py_module",
    "類別": "py_class", "class": "py_class",
    "函數": "py_function", "function": "py_function", "方法": "py_function",
    "資料表": "db_table", "table": "db_table",
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
                return {"error": "工具執行失敗", "count": 0}

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

        # 統一詞彙擴展管道（SynonymExpander + 知識圖譜）
        if keywords:
            try:
                expansions = await expand_search_terms(self.db, keywords)
                keywords = flatten_expansions(expansions)
            except Exception as e:
                logger.debug("Search term expansion failed, using original keywords: %s", e)

        qb = DocumentQueryBuilder(self.db)

        if keywords:
            qb = qb.with_keywords_full(keywords)
        if params.get("sender"):
            from app.services.ai.synonym_expander import SynonymExpander
            sender = SynonymExpander.expand_agency(params["sender"])
            qb = qb.with_sender_like(sender)
        if params.get("receiver"):
            from app.services.ai.synonym_expander import SynonymExpander
            receiver = SynonymExpander.expand_agency(params["receiver"])
            qb = qb.with_receiver_like(receiver)
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

        # GraphRAG Phase 1: 圖增強鄰域擴展
        # 從搜尋結果的文件 → 知識圖譜實體 → 1-hop 鄰域文件 → 合併擴展
        if docs and len(docs) < limit:
            try:
                expanded = await self._expand_via_knowledge_graph(
                    [d["id"] for d in docs],
                    max_extra=limit - len(docs),
                )
                if expanded:
                    existing_ids = {d["id"] for d in docs}
                    for doc in expanded:
                        if doc["id"] not in existing_ids:
                            docs.append(doc)
                            existing_ids.add(doc["id"])
                        if len(docs) >= limit:
                            break
            except Exception as e:
                logger.debug("Graph expansion skipped: %s", e)

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

    # ========================================================================
    # GraphRAG Phase 1: 圖增強鄰域擴展
    # ========================================================================

    async def _expand_via_knowledge_graph(
        self, doc_ids: List[int], max_extra: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        從已知文件出發，透過知識圖譜鄰域擴展找出相關文件。

        流程：
        1. doc_ids → document_entity_mentions → canonical_entity_ids
        2. canonical_entity_ids → 1-hop 鄰居實體
        3. 鄰居實體 → document_entity_mentions → 新文件
        4. 回傳未在原始結果中的文件
        """
        from sqlalchemy import select, and_, func as sa_func
        from app.extended.models import (
            OfficialDocument,
            DocumentEntityMention,
            EntityRelationship,
        )

        if not doc_ids:
            return []

        # Step 1: 找出原始文件中提及的正規化實體 (取平均信心度最高的前 10 個)
        mention_stmt = (
            select(DocumentEntityMention.canonical_entity_id)
            .where(DocumentEntityMention.document_id.in_(doc_ids))
            .group_by(DocumentEntityMention.canonical_entity_id)
            .order_by(
                sa_func.avg(DocumentEntityMention.confidence).desc()
            )
            .limit(10)
        )
        mention_result = await self.db.execute(mention_stmt)
        entity_ids = [row[0] for row in mention_result.all()]

        if not entity_ids:
            return []

        # Step 2: 1-hop 鄰居實體 (透過 entity_relationships, 雙向)
        neighbor_stmt = (
            select(EntityRelationship.target_entity_id)
            .where(
                EntityRelationship.source_entity_id.in_(entity_ids),
                EntityRelationship.invalidated_at.is_(None),
            )
            .union_all(
                select(EntityRelationship.source_entity_id)
                .where(
                    EntityRelationship.target_entity_id.in_(entity_ids),
                    EntityRelationship.invalidated_at.is_(None),
                )
            )
            .limit(20)
        )
        neighbor_result = await self.db.execute(neighbor_stmt)
        all_entity_ids = set(entity_ids)
        for row in neighbor_result.all():
            all_entity_ids.add(row[0])

        # Step 3: 鄰居實體 → 關聯文件 (排除原始文件)
        expanded_doc_stmt = (
            select(
                OfficialDocument.id,
                OfficialDocument.doc_number,
                OfficialDocument.subject,
                OfficialDocument.doc_type,
                OfficialDocument.category,
                OfficialDocument.sender,
                OfficialDocument.receiver,
                OfficialDocument.doc_date,
                OfficialDocument.status,
            )
            .join(
                DocumentEntityMention,
                DocumentEntityMention.document_id == OfficialDocument.id,
            )
            .where(
                and_(
                    DocumentEntityMention.canonical_entity_id.in_(all_entity_ids),
                    OfficialDocument.id.notin_(doc_ids),
                )
            )
            .group_by(OfficialDocument.id)
            .order_by(OfficialDocument.doc_date.desc().nullslast())
            .limit(max_extra)
        )
        expanded_result = await self.db.execute(expanded_doc_stmt)

        return [
            {
                "id": row.id,
                "doc_number": row.doc_number or "",
                "subject": row.subject or "",
                "doc_type": row.doc_type or "",
                "category": row.category or "",
                "sender": row.sender or "",
                "receiver": row.receiver or "",
                "doc_date": str(row.doc_date) if row.doc_date else "",
                "status": row.status or "",
                "similarity": 0,
                "_source": "graph_expansion",
            }
            for row in expanded_result.all()
        ]

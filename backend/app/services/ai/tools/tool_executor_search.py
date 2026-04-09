"""
搜尋類工具執行器

包含工具：
- search_documents: 向量+SQL 混合公文搜尋 + Hybrid Reranking + 圖增強鄰域擴展
- search_dispatch_orders: 派工單搜尋

知識圖譜/相似度搜尋已拆分至 tool_executor_kg_search.py：
- search_entities, find_similar, find_correspondence

Extracted from agent_tools.py v1.3.0
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# LLM 自然語言 entity_type → DB 欄位值對照
ENTITY_TYPE_MAP = {
    "organization": "org", "organisation": "org", "機關": "org",
    "人員": "person", "人": "person",
    "專案": "project", "案件": "project",
    "地點": "location", "地址": "location",
    "日期": "date", "時間": "date",
    # Code Graph (v1.80.0)
    "模組": "py_module", "module": "py_module",
    "類別": "py_class", "class": "py_class",
    "函數": "py_function", "function": "py_function", "方法": "py_function",
    "資料表": "db_table", "table": "db_table",
}


class SearchToolExecutor:
    """搜尋類工具執行器"""

    def __init__(self, db: AsyncSession, ai_connector, embedding_mgr, config):
        self.db = db
        self.ai = ai_connector
        self.embedding_mgr = embedding_mgr
        self.config = config

    async def search_documents(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋公文 — 向量+SQL搜尋 + Hybrid Reranking"""
        from app.services.ai.search.search_entity_expander import expand_search_terms, flatten_expansions
        from app.services.ai.search.reranker import rerank_documents
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
            from app.services.ai.search.synonym_expander import SynonymExpander
            sender = SynonymExpander.expand_agency(params["sender"])
            qb = qb.with_sender_like(sender)
        if params.get("receiver"):
            from app.services.ai.search.synonym_expander import SynonymExpander
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

        limit = min(int(params.get("limit", 20)), 50)
        fetch_limit = min(limit * 2, 100)
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
                from app.services.ai.tools.tool_executor_kg_search import expand_via_knowledge_graph
                expanded = await expand_via_knowledge_graph(
                    self.db,
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

    async def search_dispatch_orders(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋派工單紀錄（含 Redis 快取 5 分鐘）"""
        import re as _re
        import json as _json
        from app.repositories.taoyuan.dispatch_order_repository import DispatchOrderRepository

        dispatch_no = params.get("dispatch_no", "")
        search = params.get("search", "")
        work_type = params.get("work_type")
        limit = min(int(params.get("limit", 50)), 100)

        # Redis 快取（同一查詢 5 分鐘內不重查 DB）
        cache_key = f"agent:tool_cache:dispatch:{dispatch_no or search}:{work_type}:{limit}"
        try:
            from app.core.redis_client import get_redis
            redis = await get_redis()
            if redis:
                cached = await redis.get(cache_key)
                if cached:
                    logger.debug("Dispatch cache hit: %s", cache_key[:50])
                    return _json.loads(cached)
        except Exception:
            pass

        # 防 LLM 數字幻覺：從原始問題二次提取派工單號做校正
        original_q = params.get("_original_question", "")
        if original_q and dispatch_no:
            m = _re.search(r'派工單[號]?\s*(\d{2,4})', original_q)
            if not m:
                m = _re.search(r'(?:^|\D)0*(\d{2,3})(?:\D|$)', original_q)
            if m:
                extracted = m.group(1).lstrip('0') or '0'
                provided = dispatch_no.strip().lstrip('0') or '0'
                if extracted != provided:
                    logger.warning("派工單號校正: LLM=%s → 原文=%s", dispatch_no, m.group(1))
                    dispatch_no = m.group(1)

        repo = DispatchOrderRepository(self.db)

        if dispatch_no:
            search_term = dispatch_no.strip()
            # 純數字 (如 "001") → 自動加最新年度前綴 (如 "115年_派工單號001")
            if search_term.isdigit() and len(search_term) <= 3:
                roc_year = datetime.now().year - 1911  # 民國年
                search_term = f"{roc_year}年_派工單號{search_term.zfill(3)}"
                logger.info("派工單號自動補全: %s → %s", dispatch_no.strip(), search_term)
            items, total = await repo.filter_dispatch_orders(
                search=search_term,
                work_type=work_type,
                limit=limit,
                sort_by="id",
                sort_order="desc",
            )
        elif search:
            items, total = await repo.filter_dispatch_orders(
                search=search.strip(),
                work_type=work_type,
                limit=limit,
                sort_by="id",
                sort_order="desc",
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

        result = {
            "dispatch_orders": dispatch_orders,
            "linked_documents": linked_docs,
            "total": total,
            "count": len(dispatch_orders),
        }

        # 寫入 Redis 快取 (5 分鐘)
        try:
            from app.core.redis_client import get_redis
            redis = await get_redis()
            if redis and result.get("count", 0) > 0:
                await redis.setex(cache_key, 300, _json.dumps(result, default=str, ensure_ascii=False))
        except Exception:
            pass

        return result


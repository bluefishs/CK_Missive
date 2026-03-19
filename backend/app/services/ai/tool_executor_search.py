"""
搜尋類工具執行器

包含工具：
- search_documents: 向量+SQL 混合公文搜尋 + Hybrid Reranking + 圖增強鄰域擴展
- search_dispatch_orders: 派工單搜尋
- search_entities: 知識圖譜實體搜尋
- find_similar: 語意相似公文
- find_correspondence: 派工單收發文對照查詢

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

    async def search_dispatch_orders(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋派工單紀錄"""
        from app.repositories.taoyuan.dispatch_order_repository import DispatchOrderRepository

        dispatch_no = params.get("dispatch_no", "")
        search = params.get("search", "")
        work_type = params.get("work_type")
        limit = min(int(params.get("limit", 10)), 20)

        repo = DispatchOrderRepository(self.db)

        if dispatch_no:
            search_term = dispatch_no.strip()
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

        return {
            "dispatch_orders": dispatch_orders,
            "linked_documents": linked_docs,
            "total": total,
            "count": len(dispatch_orders),
        }

    async def search_entities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋知識圖譜實體"""
        from app.services.ai.graph_query_service import GraphQueryService

        svc = GraphQueryService(self.db)
        query = params.get("query", "")
        entity_type = params.get("entity_type")
        # 正規化 entity_type：LLM 可能產生 "organization" 等自然語言名稱
        if entity_type:
            entity_type = ENTITY_TYPE_MAP.get(entity_type.lower(), entity_type)
        limit = min(int(params.get("limit", 10)), 20)

        entities = await svc.search_entities(query, entity_type=entity_type, limit=limit)
        return {"entities": entities, "count": len(entities)}

    async def find_similar(self, params: Dict[str, Any]) -> Dict[str, Any]:
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

    async def find_correspondence(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查詢派工單的收發文對應關係"""
        from collections import defaultdict
        from app.extended.models import (
            TaoyuanDispatchDocumentLink, DocumentEntityMention,
            CanonicalEntity, TaoyuanWorkRecord,
        )
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        dispatch_id = params.get("dispatch_id")
        if not dispatch_id:
            return {"error": "缺少 dispatch_id 參數", "count": 0}

        dispatch_id = int(dispatch_id)

        try:
            # 1. 取得關聯公文
            links_result = await self.db.execute(
                select(TaoyuanDispatchDocumentLink)
                .options(selectinload(TaoyuanDispatchDocumentLink.document))
                .where(TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id)
            )
            links = links_result.scalars().all()

            incoming: list[dict] = []
            outgoing: list[dict] = []
            all_doc_ids: list[int] = []
            for link in links:
                doc = link.document
                info = {
                    "doc_id": link.document_id,
                    "doc_number": doc.doc_number if doc else None,
                    "subject": doc.subject if doc else None,
                    "doc_date": str(doc.doc_date) if doc and doc.doc_date else None,
                }
                all_doc_ids.append(link.document_id)
                if link.link_type == "company_outgoing":
                    outgoing.append(info)
                else:
                    incoming.append(info)

            if not all_doc_ids:
                return {
                    "message": "此派工單尚無關聯公文",
                    "incoming_count": 0,
                    "outgoing_count": 0,
                    "pairs": [],
                    "count": 0,
                }

            # 2. 查詢公文實體提及
            mentions_result = await self.db.execute(
                select(DocumentEntityMention).where(
                    DocumentEntityMention.document_id.in_(all_doc_ids),
                )
            )
            mentions = mentions_result.scalars().all()
            doc_entities: dict[int, set[int]] = defaultdict(set)
            entity_names: dict[int, str] = {}
            for m in mentions:
                doc_entities[m.document_id].add(m.canonical_entity_id)

            # 取得實體名稱
            all_entity_ids = set()
            for ents in doc_entities.values():
                all_entity_ids.update(ents)
            if all_entity_ids:
                ent_result = await self.db.execute(
                    select(CanonicalEntity.id, CanonicalEntity.canonical_name)
                    .where(CanonicalEntity.id.in_(all_entity_ids))
                )
                for eid, ename in ent_result.all():
                    entity_names[eid] = ename

            # 3. 建立配對
            pairs = []
            for in_doc in incoming:
                in_ents = doc_entities.get(in_doc["doc_id"], set())
                for out_doc in outgoing:
                    out_ents = doc_entities.get(out_doc["doc_id"], set())
                    shared = in_ents & out_ents
                    if not shared:
                        continue
                    score = len(shared) / max(len(in_ents | out_ents), 1)
                    confidence = "high" if score >= 0.3 else "medium"
                    pairs.append({
                        "incoming": in_doc,
                        "outgoing": out_doc,
                        "confidence": confidence,
                        "score": round(score, 3),
                        "shared_entities": [entity_names.get(eid, str(eid)) for eid in list(shared)[:5]],
                    })

            pairs.sort(key=lambda p: p["score"], reverse=True)

            return {
                "incoming_count": len(incoming),
                "outgoing_count": len(outgoing),
                "pairs": pairs[:10],
                "count": len(pairs),
            }
        except Exception as e:
            logger.error("find_correspondence failed: %s", e)
            return {"error": "收發文對照查詢失敗", "count": 0}

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

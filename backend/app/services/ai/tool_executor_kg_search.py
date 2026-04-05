"""
知識圖譜與相似度搜尋工具執行器

包含工具：
- search_entities: 知識圖譜實體搜尋
- find_similar: 語意相似公文
- find_correspondence: 派工單收發文對照查詢

輔助函數：
- expand_via_knowledge_graph: 圖增強鄰域擴展 (供 search_documents 呼叫)

Extracted from tool_executor_search.py v1.3.0
"""

import logging
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.tool_executor_search import ENTITY_TYPE_MAP

logger = logging.getLogger(__name__)


class KGSearchExecutor:
    """知識圖譜與相似度搜尋工具執行器"""

    def __init__(self, db: AsyncSession, ai_connector, embedding_mgr, config):
        self.db = db
        self.ai = ai_connector
        self.embedding_mgr = embedding_mgr
        self.config = config

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


async def expand_via_knowledge_graph(
    db: AsyncSession, doc_ids: List[int], max_extra: int = 3,
) -> List[Dict[str, Any]]:
    """
    從已知文件出發，透過知識圖譜鄰域擴展找出相關文件。

    流程：
    1. doc_ids -> document_entity_mentions -> canonical_entity_ids
    2. canonical_entity_ids -> 1-hop 鄰居實體
    3. 鄰居實體 -> document_entity_mentions -> 新文件
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
    mention_result = await db.execute(mention_stmt)
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
    neighbor_result = await db.execute(neighbor_stmt)
    all_entity_ids = set(entity_ids)
    for row in neighbor_result.all():
        all_entity_ids.add(row[0])

    # Step 3: 鄰居實體 -> 關聯文件 (排除原始文件)
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
    expanded_result = await db.execute(expanded_doc_stmt)

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

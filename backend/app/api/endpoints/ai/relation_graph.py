"""
AI 關聯圖譜 & 語意相似推薦 API 端點

- 關聯圖譜：根據公文 ID 列表，查詢相關的專案、機關，回傳節點與邊
- 語意相似：根據單筆公文的 embedding，用 pgvector cosine_distance 推薦相似公文

Version: 1.1.0
Created: 2026-02-24
Updated: 2026-02-24 - 新增語意相似推薦 API
"""

import logging
import os
from typing import Dict, List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth, get_async_db
from app.extended.models import (
    User,
    OfficialDocument,
    ContractProject,
)
from app.schemas.ai import (
    RelationGraphRequest,
    RelationGraphResponse,
    GraphNode,
    GraphEdge,
    SemanticSimilarRequest,
    SemanticSimilarItem,
    SemanticSimilarResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/document/relation-graph", response_model=RelationGraphResponse)
async def get_relation_graph(
    request: RelationGraphRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    取得公文關聯圖譜

    根據公文 ID 列表，查詢：
    1. 公文本身（節點）
    2. 同機關/同專案的關聯公文（節點 + 邊）
    3. 所屬承攬案件（節點 + 邊）
    4. 發文/受文機關（節點 + 邊）
    """
    doc_ids = request.document_ids
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    seen_nodes: Set[str] = set()
    seen_edges: Set[str] = set()

    def add_node(node: GraphNode):
        if node.id not in seen_nodes:
            seen_nodes.add(node.id)
            nodes.append(node)

    def add_edge(edge: GraphEdge):
        key = f"{edge.source}->{edge.target}:{edge.type}"
        if key not in seen_edges:
            seen_edges.add(key)
            edges.append(edge)

    # 1. 查詢指定公文
    result = await db.execute(
        select(OfficialDocument).where(OfficialDocument.id.in_(doc_ids))
    )
    documents = result.scalars().all()

    if not documents:
        return RelationGraphResponse(nodes=[], edges=[])

    # 收集關聯 ID
    project_ids: Set[int] = set()
    agency_names: Dict[str, str] = {}  # name -> node_id

    for doc in documents:
        node_id = f"doc_{doc.id}"
        add_node(GraphNode(
            id=node_id,
            type="document",
            label=doc.subject[:30] if doc.subject else doc.doc_number or f"公文#{doc.id}",
            category=doc.doc_type or doc.category,
            doc_number=doc.doc_number,
            status=doc.status,
        ))

        if doc.contract_project_id:
            project_ids.add(doc.contract_project_id)

        # 機關節點
        if doc.sender:
            sender_key = doc.sender.strip()
            if sender_key:
                ag_id = f"agency_{hash(sender_key) % 100000}"
                agency_names[sender_key] = ag_id
                add_node(GraphNode(id=ag_id, type="agency", label=sender_key))
                add_edge(GraphEdge(source=ag_id, target=node_id, label="發文", type="sends"))

        if doc.receiver:
            receiver_key = doc.receiver.strip()
            if receiver_key:
                ag_id = f"agency_{hash(receiver_key) % 100000}"
                agency_names[receiver_key] = ag_id
                add_node(GraphNode(id=ag_id, type="agency", label=receiver_key))
                add_edge(GraphEdge(source=node_id, target=ag_id, label="受文", type="receives"))

    # 2. 查詢承攬案件
    if project_ids:
        proj_result = await db.execute(
            select(ContractProject).where(ContractProject.id.in_(list(project_ids)))
        )
        projects = proj_result.scalars().all()
        for proj in projects:
            proj_node_id = f"project_{proj.id}"
            add_node(GraphNode(
                id=proj_node_id,
                type="project",
                label=proj.project_name[:25] if proj.project_name else f"專案#{proj.id}",
            ))
            # 連接公文到專案
            for doc in documents:
                if doc.contract_project_id == proj.id:
                    add_edge(GraphEdge(
                        source=f"doc_{doc.id}",
                        target=proj_node_id,
                        label="所屬專案",
                        type="belongs_to",
                    ))

    # 3. 查詢同專案的其他公文（擴展關聯，限 20 筆）
    if project_ids:
        related_result = await db.execute(
            select(OfficialDocument)
            .where(OfficialDocument.contract_project_id.in_(list(project_ids)))
            .where(OfficialDocument.id.notin_(doc_ids))
            .order_by(OfficialDocument.doc_date.desc().nullslast())
            .limit(20)
        )
        related_docs = related_result.scalars().all()
        for rdoc in related_docs:
            rdoc_node_id = f"doc_{rdoc.id}"
            add_node(GraphNode(
                id=rdoc_node_id,
                type="document",
                label=rdoc.subject[:30] if rdoc.subject else rdoc.doc_number or f"公文#{rdoc.id}",
                category=rdoc.doc_type or rdoc.category,
                doc_number=rdoc.doc_number,
                status=rdoc.status,
            ))
            if rdoc.contract_project_id:
                add_edge(GraphEdge(
                    source=rdoc_node_id,
                    target=f"project_{rdoc.contract_project_id}",
                    label="同專案",
                    type="belongs_to",
                ))

    # 4. 查詢公文間的收發關聯（同文號前綴配對）
    doc_numbers = [d.doc_number for d in documents if d.doc_number]
    if doc_numbers:
        for i, d1 in enumerate(documents):
            for d2 in documents[i + 1:]:
                if d1.doc_number and d2.doc_number:
                    # 同發文單位收發配對
                    if d1.sender and d2.receiver and d1.sender.strip() == d2.receiver.strip():
                        add_edge(GraphEdge(
                            source=f"doc_{d1.id}",
                            target=f"doc_{d2.id}",
                            label="收發配對",
                            type="reply",
                        ))

    logger.info(
        f"關聯圖譜: {len(doc_ids)} 筆公文 → {len(nodes)} 節點, {len(edges)} 邊"
    )

    return RelationGraphResponse(nodes=nodes, edges=edges)


@router.post("/document/semantic-similar", response_model=SemanticSimilarResponse)
async def get_semantic_similar(
    request: SemanticSimilarRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    取得語意相似公文推薦

    根據指定公文的 embedding 向量，使用 pgvector cosine_distance
    找出語意最相近的其他公文。需要 PGVECTOR_ENABLED=true。
    """
    doc_id = request.document_id
    limit = request.limit

    # 檢查 pgvector 是否啟用
    pgvector_enabled = os.environ.get("PGVECTOR_ENABLED", "false").lower() == "true"
    if not pgvector_enabled:
        logger.info("語意相似推薦: pgvector 未啟用，回傳空結果")
        return SemanticSimilarResponse(source_id=doc_id, similar_documents=[])

    try:
        # 取得來源公文的 embedding
        source_result = await db.execute(
            select(
                OfficialDocument.id,
                OfficialDocument.embedding,
            ).where(OfficialDocument.id == doc_id)
        )
        source_row = source_result.first()

        if not source_row:
            raise HTTPException(status_code=404, detail="公文不存在")

        source_embedding = source_row.embedding
        if source_embedding is None:
            logger.info(f"語意相似推薦: 公文 #{doc_id} 無 embedding，回傳空結果")
            return SemanticSimilarResponse(source_id=doc_id, similar_documents=[])

        # 轉為 list (pgvector ORM 方法需要)
        if not isinstance(source_embedding, list):
            source_embedding = list(source_embedding)

        # 使用 cosine_distance 查詢相似公文
        distance_expr = OfficialDocument.embedding.cosine_distance(source_embedding)
        similarity_expr = (1 - distance_expr).label("similarity")

        similar_result = await db.execute(
            select(
                OfficialDocument.id,
                OfficialDocument.doc_number,
                OfficialDocument.subject,
                OfficialDocument.category,
                OfficialDocument.sender,
                OfficialDocument.doc_date,
                similarity_expr,
            )
            .where(OfficialDocument.id != doc_id)
            .where(OfficialDocument.embedding.isnot(None))
            .order_by(distance_expr)
            .limit(limit)
        )
        rows = similar_result.all()

        similar_documents = [
            SemanticSimilarItem(
                id=row.id,
                doc_number=row.doc_number,
                subject=row.subject,
                category=row.category,
                sender=row.sender,
                doc_date=str(row.doc_date) if row.doc_date else None,
                similarity=round(float(row.similarity), 4),
            )
            for row in rows
            if row.similarity >= 0.3  # 過濾低相似度
        ]

        logger.info(
            f"語意相似推薦: 公文 #{doc_id} → {len(similar_documents)} 筆相似公文"
        )

        return SemanticSimilarResponse(
            source_id=doc_id,
            similar_documents=similar_documents,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"語意相似推薦查詢失敗: {e}", exc_info=True)
        return SemanticSimilarResponse(source_id=doc_id, similar_documents=[])

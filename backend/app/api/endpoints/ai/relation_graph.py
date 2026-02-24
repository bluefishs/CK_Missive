"""
AI 關聯圖譜 & 語意相似推薦 API 端點

- 關聯圖譜：根據公文 ID 列表，查詢相關的專案、機關，回傳節點與邊
- 語意相似：根據單筆公文的 embedding，用 pgvector cosine_distance 推薦相似公文

Version: 2.0.0
Created: 2026-02-24
Updated: 2026-02-24 - 業務邏輯遷移至 RelationGraphService
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import require_auth, get_service
from app.extended.models import User
from app.schemas.ai import (
    RelationGraphRequest,
    RelationGraphResponse,
    SemanticSimilarRequest,
    SemanticSimilarResponse,
)
from app.services.ai.relation_graph_service import RelationGraphService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/document/relation-graph", response_model=RelationGraphResponse)
async def get_relation_graph(
    request: RelationGraphRequest,
    current_user: User = Depends(require_auth()),
    service: RelationGraphService = Depends(get_service(RelationGraphService)),
):
    """
    取得公文關聯圖譜

    根據公文 ID 列表，查詢：
    1. 公文本身（節點）
    2. 同機關/同專案的關聯公文（節點 + 邊）
    3. 所屬承攬案件（節點 + 邊）
    4. 發文/受文機關（節點 + 邊）
    """
    nodes, edges = await service.build_relation_graph(request.document_ids)
    return RelationGraphResponse(nodes=nodes, edges=edges)


@router.post("/document/semantic-similar", response_model=SemanticSimilarResponse)
async def get_semantic_similar(
    request: SemanticSimilarRequest,
    current_user: User = Depends(require_auth()),
    service: RelationGraphService = Depends(get_service(RelationGraphService)),
):
    """
    取得語意相似公文推薦

    根據指定公文的 embedding 向量，使用 pgvector cosine_distance
    找出語意最相近的其他公文。需要 PGVECTOR_ENABLED=true。
    """
    result = await service.get_semantic_similar(request.document_id, request.limit)

    if result is None:
        # pgvector 未啟用或公文不存在
        # 檢查是否公文不存在
        from sqlalchemy import select
        from app.extended.models import OfficialDocument
        doc_check = await service.db.execute(
            select(OfficialDocument.id).where(OfficialDocument.id == request.document_id)
        )
        if not doc_check.first():
            raise HTTPException(status_code=404, detail="公文不存在")
        # pgvector 未啟用
        logger.info("語意相似推薦: pgvector 未啟用，回傳空結果")
        return SemanticSimilarResponse(source_id=request.document_id, similar_documents=[])

    logger.info(
        f"語意相似推薦: 公文 #{request.document_id} → {len(result)} 筆相似公文"
    )
    return SemanticSimilarResponse(
        source_id=request.document_id,
        similar_documents=result,
    )

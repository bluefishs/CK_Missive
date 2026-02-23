"""
Embedding 批次管線 API 端點

提供 embedding 覆蓋率統計和批次觸發功能。

Version: 1.0.0
Created: 2026-02-24
"""

import logging
import os
import time

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin, get_async_db
from app.extended.models import User, OfficialDocument
from app.schemas.ai import (
    EmbeddingStatsResponse,
    EmbeddingBatchRequest,
    EmbeddingBatchResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

PGVECTOR_ENABLED = os.getenv("PGVECTOR_ENABLED", "false").lower() == "true"


@router.post("/embedding/stats", response_model=EmbeddingStatsResponse)
async def get_embedding_stats(
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """取得 Embedding 覆蓋率統計"""
    if not PGVECTOR_ENABLED:
        return EmbeddingStatsResponse(pgvector_enabled=False)

    total_result = await db.execute(
        select(func.count(OfficialDocument.id))
    )
    total = total_result.scalar() or 0

    with_result = await db.execute(
        select(func.count(OfficialDocument.id))
        .where(OfficialDocument.embedding.isnot(None))
    )
    with_emb = with_result.scalar() or 0

    without_emb = total - with_emb
    coverage = (with_emb / total * 100) if total > 0 else 0.0

    return EmbeddingStatsResponse(
        total_documents=total,
        with_embedding=with_emb,
        without_embedding=without_emb,
        coverage_percent=round(coverage, 2),
        pgvector_enabled=True,
    )


@router.post("/embedding/batch", response_model=EmbeddingBatchResponse)
async def run_embedding_batch(
    request: EmbeddingBatchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    觸發 Embedding 批次管線

    在背景執行，立即回傳啟動狀態。
    使用管理員權限。
    """
    if not PGVECTOR_ENABLED:
        return EmbeddingBatchResponse(
            success=False,
            message="pgvector 未啟用 (PGVECTOR_ENABLED=false)",
        )

    # 先計算待處理數量
    without_result = await db.execute(
        select(func.count(OfficialDocument.id))
        .where(OfficialDocument.embedding.is_(None))
    )
    without_count = without_result.scalar() or 0

    if without_count == 0:
        return EmbeddingBatchResponse(
            success=True,
            message="所有公文已有 embedding，無需處理",
        )

    actual_limit = min(request.limit, without_count)

    # 背景執行批次管線
    background_tasks.add_task(
        _run_batch_pipeline,
        limit=actual_limit,
        batch_size=request.batch_size,
    )

    logger.info(
        f"Embedding 批次管線已啟動: limit={actual_limit}, "
        f"batch_size={request.batch_size}, 觸發者={current_user.full_name}"
    )

    return EmbeddingBatchResponse(
        success=True,
        message=f"批次管線已在背景啟動，預計處理 {actual_limit} 筆公文",
    )


async def _run_batch_pipeline(limit: int, batch_size: int):
    """背景執行的批次 embedding 管線"""
    from app.core.ai_connector import get_ai_connector
    from app.db.database import AsyncSessionLocal
    from app.scripts.backfill_embeddings import (
        get_documents_without_embedding,
        build_embedding_text,
    )

    connector = get_ai_connector()
    start_time = time.time()
    success_count = 0
    error_count = 0
    skip_count = 0

    try:
        health = await connector.check_health()
        if not health.get("ollama", {}).get("available", False):
            logger.error("Embedding 批次管線: Ollama 不可用，中止")
            return

        async with AsyncSessionLocal() as db:
            documents = await get_documents_without_embedding(db, limit)
            total = len(documents)
            logger.info(f"Embedding 批次管線: 開始處理 {total} 筆公文")

            for i, doc in enumerate(documents, 1):
                text = build_embedding_text(doc)
                if not text.strip():
                    skip_count += 1
                    continue

                try:
                    embedding = await connector.generate_embedding(text)
                    if embedding is None:
                        error_count += 1
                        continue

                    doc.embedding = embedding
                    success_count += 1

                except Exception as e:
                    logger.error(f"公文 #{doc.id} embedding 失敗: {e}")
                    error_count += 1

                if i % batch_size == 0:
                    await db.commit()

            if success_count > 0:
                await db.commit()

        elapsed = time.time() - start_time
        logger.info(
            f"Embedding 批次管線完成: "
            f"成功={success_count}, 失敗={error_count}, 跳過={skip_count}, "
            f"耗時={elapsed:.1f}s"
        )

    except Exception as e:
        logger.error(f"Embedding 批次管線異常: {e}")

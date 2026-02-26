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
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin, get_async_db
from app.extended.models import User
from app.schemas.ai import (
    EmbeddingStatsResponse,
    EmbeddingBatchRequest,
    EmbeddingBatchResponse,
)
from app.services.ai.embedding_manager import EmbeddingManager

logger = logging.getLogger(__name__)

router = APIRouter()


def _pgvector_enabled() -> bool:
    """Runtime 判斷 pgvector 是否啟用（避免模組層級常數在 .env 載入前被評估）"""
    return os.getenv("PGVECTOR_ENABLED", "false").lower() == "true"


@router.post("/embedding/stats", response_model=EmbeddingStatsResponse)
async def get_embedding_stats(
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """取得 Embedding 覆蓋率統計"""
    if not _pgvector_enabled():
        return EmbeddingStatsResponse(pgvector_enabled=False)

    stats = await EmbeddingManager.get_coverage_stats(db)

    return EmbeddingStatsResponse(
        total_documents=stats["total"],
        with_embedding=stats["with_embedding"],
        without_embedding=stats["without_embedding"],
        coverage_percent=stats["coverage"],
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
    if not _pgvector_enabled():
        return EmbeddingBatchResponse(
            success=False,
            message="pgvector 未啟用 (PGVECTOR_ENABLED=false)",
        )

    # 先計算待處理數量（委託 service 層）
    stats = await EmbeddingManager.get_coverage_stats(db)
    without_count = stats["without_embedding"]

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
    """
    背景執行的批次 embedding 管線

    使用 Ollama /api/embed 的陣列模式，每次送出 batch_size 筆文字
    一次取得所有 embedding，大幅減少 HTTP 往返次數。
    若整批失敗，自動回退為逐筆處理該批次。
    """
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
            logger.info("Embedding 批次管線: 開始處理 %s 筆公文", total)

            # 依 batch_size 分批處理
            for batch_start in range(0, total, batch_size):
                batch_docs = documents[batch_start:batch_start + batch_size]

                # 準備文字，記錄有效文件與跳過的文件
                texts = []
                valid_docs = []
                for doc in batch_docs:
                    text = build_embedding_text(doc)
                    if not text.strip():
                        skip_count += 1
                        continue
                    texts.append(text)
                    valid_docs.append(doc)

                if not texts:
                    continue

                # 嘗試批次 embedding
                embeddings = await connector.generate_embeddings_batch(texts)

                # 檢查是否整批失敗（全部為 None）
                all_failed = all(e is None for e in embeddings)

                if all_failed and len(texts) > 0:
                    # 回退：逐筆處理本批次
                    logger.warning(
                        "批次 embedding 全部失敗，回退逐筆處理 (batch %s~%s)",
                        batch_start, batch_start + len(batch_docs),
                    )
                    for doc, text in zip(valid_docs, texts):
                        try:
                            emb = await connector.generate_embedding(text)
                            if emb is None:
                                error_count += 1
                                continue
                            doc.embedding = emb
                            success_count += 1
                        except Exception as e:
                            logger.error("公文 #%s embedding 失敗: %s", doc.id, e)
                            error_count += 1
                else:
                    # 正常批次結果
                    for doc, emb in zip(valid_docs, embeddings):
                        if emb is not None:
                            doc.embedding = emb
                            success_count += 1
                        else:
                            error_count += 1

                # 每批 commit 一次
                await db.commit()

                logger.info(
                    "Embedding 批次進度: %s/%s (成功=%s, 失敗=%s, 跳過=%s)",
                    min(batch_start + batch_size, total), total,
                    success_count, error_count, skip_count,
                )

        elapsed = time.time() - start_time
        logger.info(
            "Embedding 批次管線完成: 成功=%s, 失敗=%s, 跳過=%s, 耗時=%.1fs",
            success_count, error_count, skip_count, elapsed,
        )

    except Exception as e:
        logger.error("Embedding 批次管線異常: %s", e)

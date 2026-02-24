"""
AI 實體提取 API 端點

提供公文 NER 實體提取、批次管線和覆蓋率統計。

Version: 1.0.0
Created: 2026-02-24
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin, require_auth, get_async_db
from app.extended.models import User, OfficialDocument, DocumentEntity
from app.schemas.ai import (
    EntityExtractRequest,
    EntityExtractResponse,
    EntityBatchRequest,
    EntityBatchResponse,
    EntityStatsResponse,
)
from app.services.ai.entity_extraction_service import (
    extract_entities_for_document,
    get_entity_stats,
    get_pending_extraction_count,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/entity/extract", response_model=EntityExtractResponse)
async def extract_document_entities(
    request: EntityExtractRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """對單筆公文執行 NER 實體提取"""
    result = await extract_entities_for_document(
        db=db,
        doc_id=request.document_id,
        force=request.force,
        commit=True,
    )

    return EntityExtractResponse(
        success=not result.get("error"),
        document_id=request.document_id,
        entities_count=result.get("entities_count", 0),
        relations_count=result.get("relations_count", 0),
        skipped=result.get("skipped", False),
        reason=result.get("reason"),
        error=result.get("error"),
    )


@router.post("/entity/batch", response_model=EntityBatchResponse)
async def run_entity_batch(
    request: EntityBatchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db),
):
    """
    批次實體提取（背景執行）

    在背景逐筆處理尚未提取實體的公文。
    """
    # 計算待處理數量（委託 service 層）
    pending_count = await get_pending_extraction_count(db, force=request.force)

    if pending_count == 0:
        return EntityBatchResponse(
            success=True,
            message="所有公文已完成實體提取，無需處理",
        )

    actual_limit = min(request.limit, pending_count)

    background_tasks.add_task(
        _run_batch_extraction,
        limit=actual_limit,
        force=request.force,
    )

    logger.info(
        f"實體提取批次已啟動: limit={actual_limit}, force={request.force}, "
        f"觸發者={current_user.full_name}"
    )

    return EntityBatchResponse(
        success=True,
        message=f"批次管線已在背景啟動，預計處理 {actual_limit} 筆公文",
        total_processed=actual_limit,
    )


@router.post("/entity/stats", response_model=EntityStatsResponse)
async def get_entity_extraction_stats(
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
):
    """取得實體提取覆蓋率統計"""
    stats = await get_entity_stats(db)
    return EntityStatsResponse(**stats)


async def _run_batch_extraction(limit: int, force: bool):
    """背景批次實體提取（含 API 限速保護）"""
    import time
    import asyncio
    from app.db.database import AsyncSessionLocal

    start_time = time.time()
    success_count = 0
    error_count = 0
    skip_count = 0
    consecutive_failures = 0

    try:
        async with AsyncSessionLocal() as db:
            # 取得待處理公文 ID
            if force:
                result = await db.execute(
                    select(OfficialDocument.id)
                    .order_by(OfficialDocument.created_at.desc().nullslast())
                    .limit(limit)
                )
            else:
                extracted_subq = (
                    select(func.distinct(DocumentEntity.document_id))
                    .scalar_subquery()
                )
                result = await db.execute(
                    select(OfficialDocument.id)
                    .where(OfficialDocument.id.notin_(extracted_subq))
                    .order_by(OfficialDocument.created_at.desc().nullslast())
                    .limit(limit)
                )

            doc_ids = [row[0] for row in result.all()]
            total = len(doc_ids)

            for i, doc_id in enumerate(doc_ids, 1):
                try:
                    res = await extract_entities_for_document(db, doc_id, force=force)
                    if res.get("skipped"):
                        skip_count += 1
                    elif res.get("error"):
                        error_count += 1
                        consecutive_failures += 1
                    else:
                        entities_count = res.get("entities_count", 0)
                        if entities_count > 0:
                            success_count += 1
                            consecutive_failures = 0
                        else:
                            # AI 回傳空結果（服務不可用），不計為成功
                            skip_count += 1
                            consecutive_failures += 1
                except Exception as e:
                    logger.error(f"公文 #{doc_id} 實體提取異常: {e}")
                    error_count += 1
                    consecutive_failures += 1

                # 每 10 筆 commit 一次
                if i % 10 == 0:
                    await db.commit()
                    logger.info(
                        f"實體提取進度: {i}/{total} "
                        f"(成功={success_count}, 跳過={skip_count}, 失敗={error_count})"
                    )

                # AI 服務限速保護：每筆間隔 2.5 秒（Groq 免費額度 30 req/min）
                await asyncio.sleep(2.5)

                # 連續失敗 20 筆則中止，避免浪費 API 額度
                if consecutive_failures >= 20:
                    logger.warning(
                        f"連續 {consecutive_failures} 筆提取失敗，中止批次。"
                        f"已處理 {i}/{total}，請檢查 AI 服務狀態。"
                    )
                    break

            await db.commit()

        elapsed = time.time() - start_time
        logger.info(
            f"實體提取批次完成: 成功={success_count}, 失敗={error_count}, "
            f"跳過={skip_count}, 耗時={elapsed:.1f}s"
        )

    except Exception as e:
        logger.error(f"實體提取批次異常: {e}", exc_info=True)

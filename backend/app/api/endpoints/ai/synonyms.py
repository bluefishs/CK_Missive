"""
AI 同義詞管理 API 端點

Version: 2.0.0
Created: 2026-02-08
Updated: 2026-02-11 - 遷移至 Repository 層

端點:
- POST /ai/synonyms/list - 列出所有同義詞群組（支援分類篩選）
- POST /ai/synonyms/create - 新增同義詞群組
- POST /ai/synonyms/update - 更新同義詞群組
- POST /ai/synonyms/delete - 刪除同義詞群組
- POST /ai/synonyms/reload - 重新載入同義詞到記憶體（hot reload）
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_db, require_admin
from app.extended.models import User
from app.repositories import AISynonymRepository
from app.schemas.ai import (
    AISynonymCreate,
    AISynonymUpdate,
    AISynonymResponse,
    AISynonymListRequest,
    AISynonymListResponse,
    AISynonymDeleteRequest,
    AISynonymReloadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/synonyms")


@router.post("/list", response_model=AISynonymListResponse)
async def list_synonyms(
    request: AISynonymListRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin()),
) -> AISynonymListResponse:
    """
    列出所有同義詞群組

    支援依分類與啟用狀態篩選。
    """
    repo = AISynonymRepository(db)

    synonyms = await repo.list_filtered(
        category=request.category,
        is_active=request.is_active,
    )
    categories = await repo.get_all_categories()

    items = [AISynonymResponse.model_validate(s) for s in synonyms]

    return AISynonymListResponse(
        items=items,
        total=len(items),
        categories=categories,
    )


@router.post("/create", response_model=AISynonymResponse)
async def create_synonym(
    request: AISynonymCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin()),
) -> AISynonymResponse:
    """
    新增同義詞群組

    words 欄位以逗號分隔多個同義詞。
    """
    # 清理 words：去除前後空白
    cleaned_words = ", ".join(
        w.strip() for w in request.words.split(",") if w.strip()
    )
    if not cleaned_words:
        raise HTTPException(status_code=400, detail="同義詞列表不可為空")

    repo = AISynonymRepository(db)
    synonym = await repo.create({
        "category": request.category.strip(),
        "words": cleaned_words,
        "is_active": request.is_active,
    })

    logger.info(
        f"管理員 {current_user.username} 新增同義詞群組: "
        f"category={synonym.category}, words={synonym.words}"
    )

    return AISynonymResponse.model_validate(synonym)


@router.post("/update", response_model=AISynonymResponse)
async def update_synonym(
    request: AISynonymUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin()),
) -> AISynonymResponse:
    """
    更新同義詞群組
    """
    # 驗證 words 非空
    cleaned_words = None
    if request.words is not None:
        cleaned_words = ", ".join(
            w.strip() for w in request.words.split(",") if w.strip()
        )
        if not cleaned_words:
            raise HTTPException(status_code=400, detail="同義詞列表不可為空")

    repo = AISynonymRepository(db)
    synonym = await repo.update_synonym(
        request.id,
        category=request.category.strip() if request.category is not None else None,
        words=cleaned_words,
        is_active=request.is_active,
    )

    if not synonym:
        raise HTTPException(status_code=404, detail=f"找不到 ID={request.id} 的同義詞群組")

    await db.commit()

    logger.info(
        f"管理員 {current_user.username} 更新同義詞群組 ID={synonym.id}: "
        f"category={synonym.category}, words={synonym.words}"
    )

    return AISynonymResponse.model_validate(synonym)


@router.post("/delete")
async def delete_synonym(
    request: AISynonymDeleteRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin()),
) -> dict:
    """
    刪除同義詞群組
    """
    repo = AISynonymRepository(db)
    synonym = await repo.get_by_id(request.id)

    if not synonym:
        raise HTTPException(status_code=404, detail=f"找不到 ID={request.id} 的同義詞群組")

    category = synonym.category
    words = synonym.words
    await repo.delete(request.id)

    logger.info(
        f"管理員 {current_user.username} 刪除同義詞群組 ID={request.id}: "
        f"category={category}, words={words}"
    )

    return {"success": True, "message": f"已刪除同義詞群組 (ID={request.id})"}


@router.post("/reload", response_model=AISynonymReloadResponse)
async def reload_synonyms(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin()),
) -> AISynonymReloadResponse:
    """
    重新載入同義詞到記憶體

    從資料庫讀取所有啟用的同義詞群組，重建 AIPromptManager 的快取。
    """
    from app.services.ai.ai_prompt_manager import AIPromptManager

    try:
        repo = AISynonymRepository(db)
        db_synonyms = await repo.get_active_synonyms()

        # 使用 AIPromptManager 重建查找索引
        total_words = AIPromptManager.reload_synonyms_from_db(db_synonyms)

        logger.info(
            f"管理員 {current_user.username} 重新載入同義詞: "
            f"{len(db_synonyms)} 群組, {total_words} 詞彙"
        )

        return AISynonymReloadResponse(
            success=True,
            total_groups=len(db_synonyms),
            total_words=total_words,
            message=f"已重新載入 {len(db_synonyms)} 個同義詞群組，共 {total_words} 個詞彙",
        )
    except Exception as e:
        logger.error(f"重新載入同義詞失敗: {e}")
        return AISynonymReloadResponse(
            success=False,
            total_groups=0,
            total_words=0,
            message=f"重新載入失敗: {str(e)}",
        )

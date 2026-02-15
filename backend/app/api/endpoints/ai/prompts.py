"""
AI Prompt 版本管理 API 端點

Version: 2.0.0
Created: 2026-02-08
Updated: 2026-02-11 - 遷移至 Repository 層

端點:
- POST /ai/prompts/list - 列出所有 prompt 版本
- POST /ai/prompts/create - 新增 prompt 版本
- POST /ai/prompts/activate - 啟用指定版本
- POST /ai/prompts/compare - 比較兩個版本的差異
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_db, require_admin
from app.extended.models import AIPromptVersion
from app.repositories import AIPromptRepository
from app.schemas.ai import (
    PromptVersionItem,
    PromptListRequest,
    PromptListResponse,
    PromptCreateRequest,
    PromptCreateResponse,
    PromptActivateRequest,
    PromptActivateResponse,
    PromptCompareRequest,
    PromptDiff,
    PromptCompareResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prompts", tags=["AI Prompts"])


# ============================================================================
# 工具函數
# ============================================================================

# 支援的功能名稱
SUPPORTED_FEATURES = ["summary", "classify", "keywords", "search_intent", "match_agency"]


def _model_to_item(model: AIPromptVersion) -> PromptVersionItem:
    """將 ORM 模型轉換為回應項目"""
    return PromptVersionItem(
        id=model.id,
        feature=model.feature,
        version=model.version,
        system_prompt=model.system_prompt,
        user_template=model.user_template,
        is_active=model.is_active,
        description=model.description,
        created_by=model.created_by,
        created_at=model.created_at.isoformat() if model.created_at else None,
    )


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/list", response_model=PromptListResponse)
async def list_prompt_versions(
    request: PromptListRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_admin()),
) -> PromptListResponse:
    """
    列出所有 prompt 版本

    支援按 feature 篩選。需要管理員權限。
    """
    repo = AIPromptRepository(db)
    versions = await repo.list_by_feature(feature=request.feature)
    items = [_model_to_item(v) for v in versions]

    return PromptListResponse(
        items=items,
        total=len(items),
        features=SUPPORTED_FEATURES,
    )


@router.post("/create", response_model=PromptCreateResponse)
async def create_prompt_version(
    request: PromptCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_admin()),
) -> PromptCreateResponse:
    """
    新增 prompt 版本

    自動計算版本號（該 feature 最大版本號 + 1）。
    如果 activate=True，會自動停用同 feature 的其他版本。
    需要管理員權限。
    """
    # 驗證 feature 名稱
    if request.feature not in SUPPORTED_FEATURES:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的功能名稱: {request.feature}，支援: {', '.join(SUPPORTED_FEATURES)}"
        )

    repo = AIPromptRepository(db)

    # 計算新版本號
    new_version = await repo.get_next_version(request.feature)

    # 如果要啟用，先停用同 feature 的其他版本
    if request.activate:
        await repo.deactivate_feature(request.feature)

    # 建立新版本
    created_by = getattr(current_user, 'email', None) or getattr(current_user, 'username', 'system')
    new_prompt = await repo.create({
        "feature": request.feature,
        "version": new_version,
        "system_prompt": request.system_prompt,
        "user_template": request.user_template,
        "is_active": request.activate,
        "description": request.description,
        "created_by": created_by,
    })

    # 如果啟用了新版本，清除 DocumentAIService 的快取
    if request.activate:
        _invalidate_prompt_cache()

    logger.info(
        f"新增 prompt 版本: feature={request.feature}, "
        f"version={new_version}, active={request.activate}, "
        f"created_by={created_by}"
    )

    return PromptCreateResponse(
        success=True,
        item=_model_to_item(new_prompt),
        message=f"已新增 {request.feature} v{new_version}" + (" 並啟用" if request.activate else ""),
    )


@router.post("/activate", response_model=PromptActivateResponse)
async def activate_prompt_version(
    request: PromptActivateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_admin()),
) -> PromptActivateResponse:
    """
    啟用指定 prompt 版本

    自動停用同 feature 的其他版本。需要管理員權限。
    """
    repo = AIPromptRepository(db)
    target = await repo.activate_version(request.id)

    if not target:
        raise HTTPException(status_code=404, detail=f"找不到 Prompt 版本 ID={request.id}")

    # 清除快取
    _invalidate_prompt_cache()

    logger.info(
        f"啟用 prompt 版本: feature={target.feature}, "
        f"version={target.version}, id={target.id}"
    )

    return PromptActivateResponse(
        success=True,
        message=f"已啟用 {target.feature} v{target.version}",
        activated=_model_to_item(target),
    )


@router.post("/compare", response_model=PromptCompareResponse)
async def compare_prompt_versions(
    request: PromptCompareRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_admin()),
) -> PromptCompareResponse:
    """
    比較兩個 prompt 版本的差異

    需要管理員權限。
    """
    repo = AIPromptRepository(db)
    version_a = await repo.get_by_id(request.id_a)
    version_b = await repo.get_by_id(request.id_b)

    if not version_a:
        raise HTTPException(status_code=404, detail=f"找不到 Prompt 版本 ID={request.id_a}")
    if not version_b:
        raise HTTPException(status_code=404, detail=f"找不到 Prompt 版本 ID={request.id_b}")

    # 計算差異
    diffs: List[PromptDiff] = []

    diffs.append(PromptDiff(
        field="system_prompt",
        value_a=version_a.system_prompt,
        value_b=version_b.system_prompt,
        changed=version_a.system_prompt != version_b.system_prompt,
    ))

    diffs.append(PromptDiff(
        field="user_template",
        value_a=version_a.user_template,
        value_b=version_b.user_template,
        changed=version_a.user_template != version_b.user_template,
    ))

    diffs.append(PromptDiff(
        field="description",
        value_a=version_a.description,
        value_b=version_b.description,
        changed=version_a.description != version_b.description,
    ))

    return PromptCompareResponse(
        version_a=_model_to_item(version_a),
        version_b=_model_to_item(version_b),
        diffs=diffs,
    )


def _invalidate_prompt_cache() -> None:
    """清除 AIPromptManager 的 prompt 快取，強制重新載入"""
    try:
        from app.services.ai.ai_prompt_manager import AIPromptManager
        AIPromptManager.invalidate_prompt_cache()
    except Exception as e:
        logger.warning(f"清除 Prompt 快取失敗: {e}")

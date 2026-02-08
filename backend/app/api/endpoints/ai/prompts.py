"""
AI Prompt 版本管理 API 端點

Version: 1.0.0
Created: 2026-02-08

端點:
- POST /ai/prompts/list - 列出所有 prompt 版本
- POST /ai/prompts/create - 新增 prompt 版本
- POST /ai/prompts/activate - 啟用指定版本
- POST /ai/prompts/compare - 比較兩個版本的差異
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_db, require_admin
from app.extended.models import AIPromptVersion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prompts", tags=["AI Prompts"])


# ============================================================================
# Request / Response Models
# ============================================================================


class PromptVersionItem(BaseModel):
    """Prompt 版本項目"""
    id: int
    feature: str
    version: int
    system_prompt: str
    user_template: Optional[str] = None
    is_active: bool
    description: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None


class PromptListRequest(BaseModel):
    """列出 prompt 版本請求"""
    feature: Optional[str] = Field(None, description="按功能名稱篩選")


class PromptListResponse(BaseModel):
    """列出 prompt 版本回應"""
    items: List[PromptVersionItem]
    total: int
    features: List[str] = Field(description="所有可用的功能名稱")


class PromptCreateRequest(BaseModel):
    """新增 prompt 版本請求"""
    feature: str = Field(..., description="功能名稱")
    system_prompt: str = Field(..., min_length=1, description="系統提示詞")
    user_template: Optional[str] = Field(None, description="使用者提示詞模板")
    description: Optional[str] = Field(None, description="版本說明")
    activate: bool = Field(False, description="是否立即啟用")


class PromptCreateResponse(BaseModel):
    """新增 prompt 版本回應"""
    success: bool
    item: PromptVersionItem
    message: str


class PromptActivateRequest(BaseModel):
    """啟用 prompt 版本請求"""
    id: int = Field(..., description="要啟用的版本 ID")


class PromptActivateResponse(BaseModel):
    """啟用 prompt 版本回應"""
    success: bool
    message: str
    activated: PromptVersionItem


class PromptCompareRequest(BaseModel):
    """比較 prompt 版本請求"""
    id_a: int = Field(..., description="版本 A 的 ID")
    id_b: int = Field(..., description="版本 B 的 ID")


class PromptDiff(BaseModel):
    """版本差異"""
    field: str
    value_a: Optional[str] = None
    value_b: Optional[str] = None
    changed: bool


class PromptCompareResponse(BaseModel):
    """比較 prompt 版本回應"""
    version_a: PromptVersionItem
    version_b: PromptVersionItem
    diffs: List[PromptDiff]


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
    query = select(AIPromptVersion).order_by(
        AIPromptVersion.feature,
        AIPromptVersion.version.desc(),
    )

    if request.feature:
        query = query.where(AIPromptVersion.feature == request.feature)

    result = await db.execute(query)
    versions = result.scalars().all()

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

    # 計算新版本號
    max_version_query = (
        select(AIPromptVersion.version)
        .where(AIPromptVersion.feature == request.feature)
        .order_by(AIPromptVersion.version.desc())
        .limit(1)
    )
    max_version_result = await db.execute(max_version_query)
    max_version = max_version_result.scalar()
    new_version = (max_version or 0) + 1

    # 如果要啟用，先停用同 feature 的其他版本
    if request.activate:
        await db.execute(
            update(AIPromptVersion)
            .where(AIPromptVersion.feature == request.feature)
            .values(is_active=False)
        )

    # 建立新版本
    created_by = getattr(current_user, 'email', None) or getattr(current_user, 'username', 'system')
    new_prompt = AIPromptVersion(
        feature=request.feature,
        version=new_version,
        system_prompt=request.system_prompt,
        user_template=request.user_template,
        is_active=request.activate,
        description=request.description,
        created_by=created_by,
    )
    db.add(new_prompt)
    await db.commit()
    await db.refresh(new_prompt)

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
    # 查詢目標版本
    target = await db.get(AIPromptVersion, request.id)
    if not target:
        raise HTTPException(status_code=404, detail=f"找不到 Prompt 版本 ID={request.id}")

    # 停用同 feature 的所有版本
    await db.execute(
        update(AIPromptVersion)
        .where(AIPromptVersion.feature == target.feature)
        .values(is_active=False)
    )

    # 啟用目標版本
    target.is_active = True
    await db.commit()
    await db.refresh(target)

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
    version_a = await db.get(AIPromptVersion, request.id_a)
    version_b = await db.get(AIPromptVersion, request.id_b)

    if not version_a:
        raise HTTPException(status_code=404, detail=f"找不到 Prompt 版本 ID={request.id_a}")
    if not version_b:
        raise HTTPException(status_code=404, detail=f"找不到 Prompt 版本 ID={request.id_b}")

    # 計算差異
    diffs: List[PromptDiff] = []

    # system_prompt 差異
    diffs.append(PromptDiff(
        field="system_prompt",
        value_a=version_a.system_prompt,
        value_b=version_b.system_prompt,
        changed=version_a.system_prompt != version_b.system_prompt,
    ))

    # user_template 差異
    diffs.append(PromptDiff(
        field="user_template",
        value_a=version_a.user_template,
        value_b=version_b.user_template,
        changed=version_a.user_template != version_b.user_template,
    ))

    # description 差異
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
    """清除 DocumentAIService 的 prompt 快取，強制重新載入"""
    try:
        from app.services.ai.document_ai_service import DocumentAIService
        DocumentAIService._prompts = None
        DocumentAIService._db_prompt_cache = None
        DocumentAIService._db_prompts_loaded = False
        logger.info("已清除 Prompt 快取")
    except Exception as e:
        logger.warning(f"清除 Prompt 快取失敗: {e}")

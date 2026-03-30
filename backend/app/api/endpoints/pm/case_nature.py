"""作業性質代碼管理 API"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_db, require_auth, require_admin
from app.extended.models import User
from app.repositories.case_nature_repository import CaseNatureRepository
from app.schemas.pm.case_nature import (
    CaseNatureCodeCreate,
    CaseNatureCodeUpdate,
    CaseNatureCodeResponse,
    CaseNatureOption,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/case-nature", tags=["作業性質代碼"])


@router.post("/list", response_model=List[CaseNatureCodeResponse])
async def list_case_natures(
    body: dict = {},
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    """列出所有作業性質代碼 (含停用)"""
    repo = CaseNatureRepository(db)
    items = await repo.get_all(include_inactive=True)
    return [CaseNatureCodeResponse.model_validate(item) for item in items]


@router.post("/options", response_model=List[CaseNatureOption])
async def get_case_nature_options(
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_auth()),
):
    """取得啟用的作業性質下拉選項"""
    repo = CaseNatureRepository(db)
    items = await repo.get_all(include_inactive=False)
    return [
        CaseNatureOption(value=f"{item.code}{item.label}", label=f"{item.code}{item.label}")
        for item in items
    ]


@router.post("/create", response_model=CaseNatureCodeResponse)
async def create_case_nature(
    data: CaseNatureCodeCreate,
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_admin()),
):
    """新增作業性質代碼"""
    repo = CaseNatureRepository(db)

    existing = await repo.get_by_code(data.code)
    if existing:
        raise HTTPException(status_code=409, detail=f"代碼 {data.code} 已存在")

    item = await repo.create(data.model_dump())
    await db.commit()
    logger.info("[CASE_NATURE] created: code=%s label=%s", data.code, data.label)
    return CaseNatureCodeResponse.model_validate(item)


@router.post("/update", response_model=CaseNatureCodeResponse)
async def update_case_nature(
    body: dict,
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_admin()),
):
    """更新作業性質代碼

    Body: { "id": 1, "label": "新標籤", "description": "...", "sort_order": 5, "is_active": true }
    """
    repo = CaseNatureRepository(db)
    item_id = body.get("id")
    if not item_id:
        raise HTTPException(status_code=422, detail="缺少 id")

    update_data = CaseNatureCodeUpdate(**{k: v for k, v in body.items() if k != "id"})
    item = await repo.update(item_id, update_data.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="代碼不存在")

    await db.commit()
    logger.info("[CASE_NATURE] updated: id=%d", item_id)
    return CaseNatureCodeResponse.model_validate(item)


@router.post("/delete")
async def delete_case_nature(
    body: dict,
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(require_admin()),
):
    """停用作業性質代碼 (soft delete)"""
    repo = CaseNatureRepository(db)
    item_id = body.get("id")
    if not item_id:
        raise HTTPException(status_code=422, detail="缺少 id")

    success = await repo.soft_delete(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="代碼不存在")

    await db.commit()
    logger.info("[CASE_NATURE] deactivated: id=%d", item_id)
    return {"success": True, "message": "已停用"}

"""
桃園派工系統 - 作業歷程 API

包含端點：
- /workflow/list - 作業歷程列表（依派工單）
- /workflow/by-project - 作業歷程列表（依工程）
- /workflow/create - 建立作業紀錄
- /workflow/{record_id} - 取得單筆作業紀錄
- /workflow/{record_id}/update - 更新作業紀錄
- /workflow/{record_id}/delete - 刪除作業紀錄
- /workflow/summary/{project_id} - 工程歷程總覽

@version 1.0.0
@date 2026-02-13
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.core.dependencies import require_auth
from app.schemas.taoyuan.workflow import (
    WorkRecordCreate,
    WorkRecordUpdate,
    WorkRecordResponse,
    WorkRecordListResponse,
    ProjectWorkflowSummary,
    WorkflowSummaryResponse,
    BatchUpdateRequest,
    BatchUpdateResponse,
)
from app.services.taoyuan import WorkRecordService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_work_record_service(
    db: AsyncSession = Depends(get_async_db),
) -> WorkRecordService:
    """依賴注入：取得 WorkRecordService"""
    return WorkRecordService(db)


# =========================================================================
# 列表查詢
# =========================================================================


@router.post("/workflow/list", response_model=WorkRecordListResponse, summary="作業歷程列表（依派工單）")
async def list_work_records(
    dispatch_order_id: int = Body(..., embed=True),
    page: int = Body(1),
    page_size: int = Body(50),
    service: WorkRecordService = Depends(get_work_record_service),
    current_user=Depends(require_auth()),
):
    """依派工單 ID 查詢作業歷程"""
    items, total = await service.list_by_dispatch_order(
        dispatch_order_id=dispatch_order_id,
        page=page,
        limit=page_size,
    )

    return WorkRecordListResponse(
        items=[WorkRecordResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/workflow/by-project", response_model=WorkRecordListResponse, summary="作業歷程列表（依工程）")
async def list_work_records_by_project(
    project_id: int = Body(..., embed=True),
    page: int = Body(1),
    page_size: int = Body(50),
    service: WorkRecordService = Depends(get_work_record_service),
    current_user=Depends(require_auth()),
):
    """依工程項次 ID 查詢作業歷程（含派工單資訊）"""
    items, total = await service.list_by_project(
        project_id=project_id,
        page=page,
        limit=page_size,
    )

    # 填入 dispatch_subject
    response_items = []
    for item in items:
        resp = WorkRecordResponse.model_validate(item)
        if item.dispatch_order:
            resp.dispatch_subject = item.dispatch_order.project_name
        response_items.append(resp)

    return WorkRecordListResponse(
        items=response_items,
        total=total,
        page=page,
        page_size=page_size,
    )


# =========================================================================
# 靜態路由（必須在 {record_id} 之前，避免路由衝突）
# =========================================================================


@router.post("/workflow/create", response_model=WorkRecordResponse, summary="建立作業紀錄")
async def create_work_record(
    data: WorkRecordCreate,
    service: WorkRecordService = Depends(get_work_record_service),
    current_user=Depends(require_auth()),
):
    """建立新的作業紀錄"""
    record = await service.create_record(data)
    await service.db.commit()

    # 重新載入含關聯公文
    record = await service.get_record(record.id)
    return WorkRecordResponse.model_validate(record)


@router.post("/workflow/batch-update", response_model=BatchUpdateResponse, summary="批量更新批次歸屬")
async def batch_update_records(
    data: BatchUpdateRequest,
    service: WorkRecordService = Depends(get_work_record_service),
    current_user=Depends(require_auth()),
):
    """批量更新作業紀錄的結案批次（batch_no + batch_label）"""
    updated = await service.update_batch(
        record_ids=data.record_ids,
        batch_no=data.batch_no,
        batch_label=data.batch_label,
    )
    await service.db.commit()

    return BatchUpdateResponse(
        updated_count=updated,
        batch_no=data.batch_no,
        batch_label=data.batch_label,
    )


# =========================================================================
# 歷程總覽（靜態路由，必須在 {record_id} 之前）
# =========================================================================


@router.post("/workflow/summary/{project_id}", response_model=ProjectWorkflowSummary, summary="工程歷程總覽")
async def get_workflow_summary(
    project_id: int,
    service: WorkRecordService = Depends(get_work_record_service),
    current_user=Depends(require_auth()),
):
    """取得工程的歷程總覽（含里程碑進度、關聯公文統計）"""
    summary = await service.get_workflow_summary(project_id)
    if not summary:
        raise HTTPException(status_code=404, detail="工程項次不存在")

    return ProjectWorkflowSummary(**summary)


# =========================================================================
# 動態路由（{record_id} 在所有靜態路由之後）
# =========================================================================


@router.post("/workflow/{record_id}", response_model=WorkRecordResponse, summary="取得單筆作業紀錄")
async def get_work_record(
    record_id: int,
    service: WorkRecordService = Depends(get_work_record_service),
    current_user=Depends(require_auth()),
):
    """取得作業紀錄詳情"""
    record = await service.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="作業紀錄不存在")

    return WorkRecordResponse.model_validate(record)


@router.post("/workflow/{record_id}/update", response_model=WorkRecordResponse, summary="更新作業紀錄")
async def update_work_record(
    record_id: int,
    data: WorkRecordUpdate,
    service: WorkRecordService = Depends(get_work_record_service),
    current_user=Depends(require_auth()),
):
    """更新作業紀錄"""
    record = await service.update_record(record_id, data)
    if not record:
        raise HTTPException(status_code=404, detail="作業紀錄不存在")

    await service.db.commit()

    # 重新載入含關聯公文
    record = await service.get_record(record_id)
    return WorkRecordResponse.model_validate(record)


@router.post("/workflow/{record_id}/delete", summary="刪除作業紀錄")
async def delete_work_record(
    record_id: int,
    service: WorkRecordService = Depends(get_work_record_service),
    current_user=Depends(require_auth()),
):
    """刪除作業紀錄"""
    success = await service.delete_record(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="作業紀錄不存在")

    await service.db.commit()
    return {"success": True, "message": "刪除成功", "deleted_id": record_id}

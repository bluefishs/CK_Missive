"""
桃園派工系統 - 工程-派工關聯 API

以工程為主體的關聯操作

包含端點：
- /project/{project_id}/dispatch-links - 查詢工程關聯的派工單
- /project/{project_id}/link-dispatch - 將工程關聯到派工單
- /project/{project_id}/unlink-dispatch/{link_id} - 移除工程與派工的關聯
- /projects/batch-dispatch-links - 批次查詢多筆工程的派工關聯
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .common import (
    get_async_db, require_auth,
    TaoyuanProject, TaoyuanDispatchOrder, TaoyuanDispatchProjectLink,
    TaoyuanDispatchDocumentLink, TaoyuanDocumentProjectLink
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/project/{project_id}/dispatch-links", summary="查詢工程關聯的派工單")
async def get_project_dispatch_links(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
):
    """
    以工程為主體，查詢該工程關聯的所有派工單
    用於「工程資訊」Tab 顯示已關聯的派工
    """
    result = await db.execute(
        select(TaoyuanDispatchProjectLink)
        .options(selectinload(TaoyuanDispatchProjectLink.dispatch_order))
        .where(TaoyuanDispatchProjectLink.taoyuan_project_id == project_id)
    )
    links = result.scalars().all()

    dispatch_orders = []
    for link in links:
        if link.dispatch_order:
            dispatch_orders.append({
                'link_id': link.id,
                'dispatch_order_id': link.dispatch_order.id,
                'dispatch_no': link.dispatch_order.dispatch_no,
                'project_name': link.dispatch_order.project_name,
                'work_type': link.dispatch_order.work_type,
            })

    return {
        "success": True,
        "project_id": project_id,
        "dispatch_orders": dispatch_orders,
        "total": len(dispatch_orders)
    }


@router.post("/project/{project_id}/link-dispatch", summary="將工程關聯到派工單")
async def link_dispatch_to_project(
    project_id: int,
    dispatch_order_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
):
    """
    以工程為主體，將工程關聯到指定的派工單

    自動同步邏輯：
    1. 建立派工-工程關聯
    2. 查詢派工關聯的所有公文
    3. 為每個公文建立工程關聯（自動同步）
    """
    # 檢查工程是否存在
    proj = await db.execute(select(TaoyuanProject).where(TaoyuanProject.id == project_id))
    if not proj.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="工程不存在")

    # 檢查派工單是否存在
    order_result = await db.execute(
        select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.id == dispatch_order_id)
    )
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="派工單不存在")

    # 檢查是否已存在關聯
    existing = await db.execute(
        select(TaoyuanDispatchProjectLink).where(
            TaoyuanDispatchProjectLink.taoyuan_project_id == project_id,
            TaoyuanDispatchProjectLink.dispatch_order_id == dispatch_order_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="此關聯已存在")

    # Step 1: 建立派工-工程關聯
    link = TaoyuanDispatchProjectLink(
        dispatch_order_id=dispatch_order_id,
        taoyuan_project_id=project_id
    )
    db.add(link)
    await db.flush()  # 確保獲得 ID

    # Step 2: 查詢派工關聯的所有公文及其 link_type
    doc_links_result = await db.execute(
        select(
            TaoyuanDispatchDocumentLink.document_id,
            TaoyuanDispatchDocumentLink.link_type
        )
        .where(TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_order_id)
    )
    doc_links = doc_links_result.all()

    # Step 3: 為每個公文建立工程關聯（自動同步）
    auto_linked_count = 0
    for doc_id, doc_link_type in doc_links:
        # 檢查公文-工程關聯是否已存在
        existing_doc_proj = await db.execute(
            select(TaoyuanDocumentProjectLink).where(
                TaoyuanDocumentProjectLink.document_id == doc_id,
                TaoyuanDocumentProjectLink.taoyuan_project_id == project_id
            )
        )

        if not existing_doc_proj.scalar_one_or_none():
            # 建立新的公文-工程直接關聯
            doc_project_link = TaoyuanDocumentProjectLink(
                document_id=doc_id,
                taoyuan_project_id=project_id,
                link_type=doc_link_type or 'agency_incoming',
                notes=f"自動同步自派工單 {order.dispatch_no}"
            )
            db.add(doc_project_link)
            auto_linked_count += 1
            logger.info(f"自動同步公文-工程關聯: 公文 {doc_id} -> 工程 {project_id}")

    # Step 4: 一次事務提交
    await db.commit()
    await db.refresh(link)

    return {
        "success": True,
        "message": "關聯成功",
        "link_id": link.id,
        "auto_sync": {
            "document_count": len(doc_links),
            "auto_linked_count": auto_linked_count,
            "message": f"已自動同步 {auto_linked_count} 個公文的工程關聯" if auto_linked_count > 0 else None
        }
    }


@router.post("/project/{project_id}/unlink-dispatch/{link_id}", summary="移除工程與派工的關聯")
async def unlink_dispatch_from_project(
    project_id: int,
    link_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
):
    """
    移除工程與派工的關聯

    參數說明：
    - project_id: TaoyuanProject.id（工程 ID）
    - link_id: TaoyuanDispatchProjectLink.id（關聯記錄 ID，非工程 ID）

    反向清理邏輯：
    - 同時刪除自動建立的公文-工程關聯（notes 包含 "自動同步自派工單"）
    """
    result = await db.execute(
        select(TaoyuanDispatchProjectLink).where(
            TaoyuanDispatchProjectLink.id == link_id,
            TaoyuanDispatchProjectLink.taoyuan_project_id == project_id
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        # 提供更詳細的錯誤訊息以便調試
        link_by_id = await db.execute(
            select(TaoyuanDispatchProjectLink).where(TaoyuanDispatchProjectLink.id == link_id)
        )
        existing_link = link_by_id.scalar_one_or_none()

        if existing_link:
            raise HTTPException(
                status_code=404,
                detail=f"關聯不存在：link_id={link_id} 對應的工程 ID 是 {existing_link.taoyuan_project_id}，而非傳入的 {project_id}"
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"關聯記錄 ID {link_id} 不存在。請確認傳入的是 link_id（關聯記錄 ID），而非工程 ID"
            )

    dispatch_order_id = link.dispatch_order_id

    # Step 1: 取得派工單號（用於匹配自動同步的記錄）
    order_result = await db.execute(
        select(TaoyuanDispatchOrder.dispatch_no).where(
            TaoyuanDispatchOrder.id == dispatch_order_id
        )
    )
    dispatch_no = order_result.scalar_one_or_none()

    # Step 2: 刪除自動建立的公文-工程關聯
    auto_deleted_count = 0
    if dispatch_no:
        # 查詢該派工單關聯的所有公文
        doc_links_result = await db.execute(
            select(TaoyuanDispatchDocumentLink.document_id).where(
                TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_order_id
            )
        )
        doc_ids = [row[0] for row in doc_links_result.all()]

        # 刪除自動建立的公文-工程關聯
        for doc_id in doc_ids:
            auto_link_result = await db.execute(
                select(TaoyuanDocumentProjectLink).where(
                    TaoyuanDocumentProjectLink.document_id == doc_id,
                    TaoyuanDocumentProjectLink.taoyuan_project_id == project_id,
                    TaoyuanDocumentProjectLink.notes.like(f"%自動同步自派工單 {dispatch_no}%")
                )
            )
            auto_link = auto_link_result.scalar_one_or_none()
            if auto_link:
                await db.delete(auto_link)
                auto_deleted_count += 1
                logger.info(f"反向清理公文-工程關聯: 公文 {doc_id} <- 工程 {project_id}")

    # Step 3: 刪除派工-工程關聯
    await db.delete(link)
    await db.commit()

    return {
        "success": True,
        "message": "移除關聯成功",
        "auto_cleanup": {
            "deleted_count": auto_deleted_count,
            "message": f"已同時清理 {auto_deleted_count} 個自動建立的公文-工程關聯" if auto_deleted_count > 0 else None
        }
    }


@router.post("/projects/batch-dispatch-links", summary="批次查詢多筆工程的派工關聯")
async def get_batch_project_dispatch_links(
    project_ids: List[int],
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
):
    """
    批次查詢多筆工程的派工關聯
    用於「工程資訊」Tab 一次載入所有工程的關聯狀態
    """
    result = await db.execute(
        select(TaoyuanDispatchProjectLink)
        .options(selectinload(TaoyuanDispatchProjectLink.dispatch_order))
        .where(TaoyuanDispatchProjectLink.taoyuan_project_id.in_(project_ids))
    )
    links = result.scalars().all()

    # 按工程 ID 分組
    links_by_project = {}
    for link in links:
        proj_id = link.taoyuan_project_id
        if proj_id not in links_by_project:
            links_by_project[proj_id] = []
        if link.dispatch_order:
            links_by_project[proj_id].append({
                'link_id': link.id,
                'dispatch_order_id': link.dispatch_order.id,
                'dispatch_no': link.dispatch_order.dispatch_no,
                'project_name': link.dispatch_order.project_name,
            })

    return {
        "success": True,
        "links": links_by_project
    }

"""
桃園派工系統 - 公文→派工關聯 (反向) API

包含端點：
- /document/{document_id}/dispatch-links - 查詢公文關聯的派工單
- /document/{document_id}/link-dispatch - 將公文關聯到派工單
- /document/{document_id}/unlink-dispatch/{link_id} - 移除公文與派工的關聯
- /documents/batch-dispatch-links - 批次查詢多筆公文的派工關聯
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from .common import (
    get_async_db, require_auth,
    TaoyuanDispatchOrder, TaoyuanDispatchDocumentLink, Document,
)

router = APIRouter()


@router.post("/document/{document_id}/dispatch-links", summary="查詢公文關聯的派工單")
async def get_document_dispatch_links(
    document_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
):
    """
    以公文為主體，查詢該公文關聯的所有派工單
    用於「函文紀錄」Tab 顯示已關聯的派工
    """
    result = await db.execute(
        select(TaoyuanDispatchDocumentLink)
        .options(selectinload(TaoyuanDispatchDocumentLink.dispatch_order))
        .where(TaoyuanDispatchDocumentLink.document_id == document_id)
    )
    links = result.scalars().all()

    # 批次預載所有相關派工單的公文關聯（避免 N+1 查詢）
    order_ids = [link.dispatch_order.id for link in links if link.dispatch_order]
    order_doc_map: dict[int, dict[str, str | None]] = {}
    if order_ids:
        all_doc_links_result = await db.execute(
            select(TaoyuanDispatchDocumentLink)
            .options(selectinload(TaoyuanDispatchDocumentLink.document))
            .where(TaoyuanDispatchDocumentLink.dispatch_order_id.in_(order_ids))
        )
        all_doc_links = all_doc_links_result.scalars().all()

        for doc_link in all_doc_links:
            if not doc_link.document:
                continue
            oid = doc_link.dispatch_order_id
            if oid not in order_doc_map:
                order_doc_map[oid] = {'agency': None, 'company': None}
            if doc_link.link_type == 'agency_incoming' and not order_doc_map[oid]['agency']:
                order_doc_map[oid]['agency'] = doc_link.document.doc_number
            elif doc_link.link_type == 'company_outgoing' and not order_doc_map[oid]['company']:
                order_doc_map[oid]['company'] = doc_link.document.doc_number

    dispatch_orders = []
    for link in links:
        if link.dispatch_order:
            order = link.dispatch_order
            doc_nums = order_doc_map.get(order.id, {})

            dispatch_orders.append({
                'link_id': link.id,
                'link_type': link.link_type,
                'dispatch_order_id': order.id,
                'dispatch_no': order.dispatch_no,
                'project_name': order.project_name,
                'work_type': order.work_type,
                'sub_case_name': order.sub_case_name,
                'deadline': order.deadline,
                'case_handler': order.case_handler,
                'survey_unit': order.survey_unit,
                'contact_note': order.contact_note,
                'cloud_folder': order.cloud_folder,
                'project_folder': order.project_folder,
                'agency_doc_number': doc_nums.get('agency'),
                'company_doc_number': doc_nums.get('company'),
                'created_at': order.created_at.isoformat() if order.created_at else None,
            })

    return {
        "success": True,
        "document_id": document_id,
        "dispatch_orders": dispatch_orders,
        "total": len(dispatch_orders)
    }


@router.post("/document/{document_id}/link-dispatch", summary="將公文關聯到派工單")
async def link_dispatch_to_document(
    document_id: int,
    dispatch_order_id: int,
    link_type: str = 'agency_incoming',
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
):
    """
    以公文為主體，將公文關聯到指定的派工單

    link_type:
    - agency_incoming: 機關來函（機關發文）
    - company_outgoing: 乾坤發文
    """
    # 檢查公文是否存在
    doc = await db.execute(select(Document).where(Document.id == document_id))
    if not doc.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="公文不存在")

    # 檢查派工單是否存在
    order = await db.execute(
        select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.id == dispatch_order_id)
    )
    if not order.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="派工單不存在")

    # 檢查是否已存在關聯
    existing = await db.execute(
        select(TaoyuanDispatchDocumentLink).where(
            TaoyuanDispatchDocumentLink.document_id == document_id,
            TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_order_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="此關聯已存在")

    # 建立關聯
    link = TaoyuanDispatchDocumentLink(
        dispatch_order_id=dispatch_order_id,
        document_id=document_id,
        link_type=link_type
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)

    return {
        "success": True,
        "message": "關聯成功",
        "link_id": link.id
    }


@router.post("/document/{document_id}/unlink-dispatch/{link_id}", summary="移除公文與派工的關聯")
async def unlink_dispatch_from_document(
    document_id: int,
    link_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
):
    """
    移除公文與派工的關聯

    參數說明：
    - document_id: OfficialDocument.id（公文 ID）
    - link_id: TaoyuanDispatchDocumentLink.id（關聯記錄 ID，非派工單 ID）
    """
    result = await db.execute(
        select(TaoyuanDispatchDocumentLink).where(
            TaoyuanDispatchDocumentLink.id == link_id,
            TaoyuanDispatchDocumentLink.document_id == document_id
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        # 提供更詳細的錯誤訊息
        link_by_id = await db.execute(
            select(TaoyuanDispatchDocumentLink).where(TaoyuanDispatchDocumentLink.id == link_id)
        )
        existing_link = link_by_id.scalar_one_or_none()
        if existing_link:
            raise HTTPException(
                status_code=404,
                detail=f"關聯不存在：link_id={link_id} 對應的公文 ID 是 {existing_link.document_id}，而非傳入的 {document_id}"
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"關聯記錄 ID {link_id} 不存在。請確認傳入的是 link_id（關聯記錄 ID），而非派工單 ID"
            )

    await db.delete(link)
    await db.commit()
    return {"success": True, "message": "移除關聯成功"}


@router.post("/documents/batch-dispatch-links", summary="批次查詢多筆公文的派工關聯")
async def get_batch_document_dispatch_links(
    document_ids: List[int],
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
):
    """
    批次查詢多筆公文的派工關聯
    用於「函文紀錄」Tab 一次載入所有公文的關聯狀態
    """
    result = await db.execute(
        select(TaoyuanDispatchDocumentLink)
        .options(selectinload(TaoyuanDispatchDocumentLink.dispatch_order))
        .where(TaoyuanDispatchDocumentLink.document_id.in_(document_ids))
    )
    links = result.scalars().all()

    # 按公文 ID 分組
    links_by_doc = {}
    for link in links:
        doc_id = link.document_id
        if doc_id not in links_by_doc:
            links_by_doc[doc_id] = []
        if link.dispatch_order:
            links_by_doc[doc_id].append({
                'link_id': link.id,
                'link_type': link.link_type,
                'dispatch_order_id': link.dispatch_order.id,
                'dispatch_no': link.dispatch_order.dispatch_no,
                'project_name': link.dispatch_order.project_name,
            })

    return {
        "success": True,
        "links": links_by_doc
    }

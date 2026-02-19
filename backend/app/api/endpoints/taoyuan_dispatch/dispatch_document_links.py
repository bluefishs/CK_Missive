"""
桃園派工系統 - 派工-公文關聯 API

包含端點：
- /dispatch/{dispatch_id}/link-document - 關聯公文到派工單
- /dispatch/{dispatch_id}/unlink-document/{link_id} - 移除公文關聯
- /dispatch/{dispatch_id}/documents - 取得派工單關聯公文
- /dispatch/search-linkable-documents - 搜尋可關聯的桃園派工公文
- /document/{document_id}/dispatch-links - 查詢公文關聯的派工單
- /document/{document_id}/link-dispatch - 將公文關聯到派工單
- /document/{document_id}/unlink-dispatch/{link_id} - 移除公文與派工的關聯
- /documents/batch-dispatch-links - 批次查詢多筆公文的派工關聯
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from .common import (
    get_async_db, require_auth,
    TaoyuanDispatchOrder, TaoyuanDispatchDocumentLink, Document,
    DispatchDocumentLinkCreate
)
from app.schemas.taoyuan.links import SearchLinkableDocumentsRequest
from app.utils.doc_helpers import OUTGOING_DOC_PREFIX

# 桃園派工專案 ID (固定為桃園市府委外查估案)
TAOYUAN_PROJECT_ID = 21

router = APIRouter()


@router.post(
    "/dispatch/search-linkable-documents",
    summary="搜尋可關聯的桃園派工公文"
)
async def search_linkable_documents(
    request: SearchLinkableDocumentsRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
):
    """
    搜尋可關聯的桃園派工公文

    此 API 專門用於派工單公文關聯，只回傳：
    - contract_project_id = 21 (桃園查估派工專案) 的公文
    - 根據 link_type 過濾公文字號前綴：
      - agency_incoming: 桃工用字第、桃工、府工、府養 等政府機關字號
      - company_outgoing: 乾坤 開頭的公司發文

    搜尋範圍：
    - 公文字號 (doc_number)
    - 主旨 (subject)

    Args:
        keyword: 搜尋關鍵字
        limit: 回傳筆數上限 (預設 20)
        exclude_document_ids: 排除的公文 ID 列表 (已關聯的公文)
        link_type: 關聯類型 ('agency_incoming' | 'company_outgoing')

    Returns:
        符合條件的公文列表
    """
    keyword = request.keyword.strip()
    if not keyword:
        return {"success": True, "items": [], "total": 0}

    # 構建查詢：限定 contract_project_id
    query = (
        select(Document)
        .where(Document.contract_project_id == TAOYUAN_PROJECT_ID)
        .where(
            or_(
                Document.doc_number.ilike(f"%{keyword}%"),
                Document.subject.ilike(f"%{keyword}%")
            )
        )
    )

    # 根據 link_type 過濾公文字號前綴
    if request.link_type == 'agency_incoming':
        # 機關來函：排除公司發文前綴的公文
        query = query.where(
            or_(
                Document.doc_number.is_(None),
                ~Document.doc_number.startswith(OUTGOING_DOC_PREFIX)
            )
        )
    elif request.link_type == 'company_outgoing':
        # 公司發文：只顯示公司發文前綴的公文
        query = query.where(Document.doc_number.startswith(OUTGOING_DOC_PREFIX))

    # 排除已關聯的公文
    if request.exclude_document_ids:
        query = query.where(Document.id.notin_(request.exclude_document_ids))

    # 排序並限制筆數
    query = query.order_by(Document.doc_date.desc()).limit(request.limit)

    result = await db.execute(query)
    documents = result.scalars().all()

    # 轉換為回應格式
    items = [
        {
            "id": doc.id,
            "doc_number": doc.doc_number,
            "subject": doc.subject,
            "doc_date": str(doc.doc_date) if doc.doc_date else None,
            "category": doc.category,
            "sender": doc.sender,
            "receiver": doc.receiver,
        }
        for doc in documents
    ]

    return {
        "success": True,
        "items": items,
        "total": len(items)
    }


@router.post("/dispatch/{dispatch_id}/link-document", summary="關聯公文到派工單")
async def link_document_to_dispatch(
    dispatch_id: int,
    data: DispatchDocumentLinkCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
):
    """關聯公文到派工單"""
    # 檢查派工單
    order = await db.execute(
        select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.id == dispatch_id)
    )
    if not order.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="派工紀錄不存在")

    # 檢查公文
    doc = await db.execute(select(Document).where(Document.id == data.document_id))
    if not doc.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="公文不存在")

    link = TaoyuanDispatchDocumentLink(
        dispatch_order_id=dispatch_id,
        document_id=data.document_id,
        link_type=data.link_type
    )
    db.add(link)
    await db.commit()
    return {"success": True, "message": "關聯成功"}


@router.post("/dispatch/{dispatch_id}/unlink-document/{link_id}", summary="移除公文關聯")
async def unlink_document_from_dispatch(
    dispatch_id: int,
    link_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
):
    """
    移除派工單的公文關聯

    參數說明：
    - dispatch_id: TaoyuanDispatchOrder.id（派工單 ID）
    - link_id: TaoyuanDispatchDocumentLink.id（關聯記錄 ID，非公文 ID）
    """
    result = await db.execute(
        select(TaoyuanDispatchDocumentLink).where(
            TaoyuanDispatchDocumentLink.id == link_id,
            TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id
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
                detail=f"關聯不存在：link_id={link_id} 對應的派工單 ID 是 {existing_link.dispatch_order_id}，而非傳入的 {dispatch_id}"
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"關聯記錄 ID {link_id} 不存在。請確認傳入的是 link_id（關聯記錄 ID），而非公文 ID"
            )

    await db.delete(link)
    await db.commit()
    return {"success": True, "message": "移除關聯成功"}


@router.post("/dispatch/{dispatch_id}/documents", summary="取得派工單關聯公文")
async def get_dispatch_documents(
    dispatch_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
):
    """取得派工單關聯的公文歷程"""
    result = await db.execute(
        select(TaoyuanDispatchDocumentLink)
        .options(selectinload(TaoyuanDispatchDocumentLink.document))
        .where(TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id)
    )
    links = result.scalars().all()

    agency_docs = []
    company_docs = []

    for link in links:
        doc_info = {
            'id': link.document.id,
            'doc_number': link.document.doc_number,
            'doc_date': link.document.doc_date,
            'subject': link.document.subject,
            'sender': link.document.sender,
            'receiver': link.document.receiver
        }
        if link.link_type == 'agency_incoming':
            agency_docs.append(doc_info)
        else:
            company_docs.append(doc_info)

    return {
        "success": True,
        "agency_documents": agency_docs,
        "company_documents": company_docs
    }


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

    dispatch_orders = []
    for link in links:
        if link.dispatch_order:
            order = link.dispatch_order

            # 從關聯表取得機關/乾坤函文文號（而非舊的 agency_doc_id/company_doc_id）
            agency_doc_number = None
            company_doc_number = None

            # 查詢該派工單的所有公文關聯
            doc_links_result = await db.execute(
                select(TaoyuanDispatchDocumentLink)
                .options(selectinload(TaoyuanDispatchDocumentLink.document))
                .where(TaoyuanDispatchDocumentLink.dispatch_order_id == order.id)
            )
            doc_links = doc_links_result.scalars().all()

            for doc_link in doc_links:
                if doc_link.document:
                    if doc_link.link_type == 'agency_incoming':
                        # 機關來函：取最新一筆（或所有，這裡簡化取第一筆找到的）
                        if not agency_doc_number:
                            agency_doc_number = doc_link.document.doc_number
                    elif doc_link.link_type == 'company_outgoing':
                        # 乾坤發文：取最新一筆
                        if not company_doc_number:
                            company_doc_number = doc_link.document.doc_number

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
                'agency_doc_number': agency_doc_number,
                'company_doc_number': company_doc_number,
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

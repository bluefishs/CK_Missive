"""
桃園派工系統 - 派工→公文關聯 CRUD API

包含端點：
- /dispatch/search-linkable-documents - 搜尋可關聯的桃園派工公文
- /dispatch/{dispatch_id}/link-document - 關聯公文到派工單
- /dispatch/{dispatch_id}/unlink-document/{link_id} - 移除公文關聯
- /dispatch/{dispatch_id}/documents - 取得派工單關聯公文
"""
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
from app.core.constants import TAOYUAN_PROJECT_ID

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
    - 指定 contract_project_id 的公文（預設 TAOYUAN_PROJECT_ID）
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

    # 構建查詢：限定 contract_project_id（支援動態專案切換）
    effective_project_id = request.contract_project_id or TAOYUAN_PROJECT_ID
    query = (
        select(Document)
        .where(Document.contract_project_id == effective_project_id)
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

    # 排序並分頁
    query = query.order_by(Document.doc_date.desc())
    if request.offset > 0:
        query = query.offset(request.offset)
    query = query.limit(request.limit)

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
        "total": len(items),
        "has_more": len(items) == request.limit,
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

    # 檢查是否已存在關聯（防止重複關聯）
    existing = await db.execute(
        select(TaoyuanDispatchDocumentLink).where(
            TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id,
            TaoyuanDispatchDocumentLink.document_id == data.document_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"success": True, "message": "此關聯已存在，已跳過"}

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
    """取得派工單關聯的公文歷程（按日期排序）"""
    result = await db.execute(
        select(TaoyuanDispatchDocumentLink)
        .options(selectinload(TaoyuanDispatchDocumentLink.document))
        .where(TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id)
    )
    links = result.scalars().all()

    agency_docs = []
    company_docs = []

    for link in links:
        if not link.document:
            continue
        doc_info = {
            'id': link.document.id,
            'doc_number': link.document.doc_number,
            'doc_date': link.document.doc_date,
            'subject': link.document.subject,
            'sender': link.document.sender,
            'receiver': link.document.receiver,
            'confidence': link.confidence,
        }
        if link.link_type == 'agency_incoming':
            agency_docs.append(doc_info)
        else:
            company_docs.append(doc_info)

    # 按日期排序（最新在前）
    def sort_key(d):
        return d.get('doc_date') or ''
    agency_docs.sort(key=sort_key, reverse=True)
    company_docs.sort(key=sort_key, reverse=True)

    return {
        "success": True,
        "agency_documents": agency_docs,
        "company_documents": company_docs,
        "total": len(agency_docs) + len(company_docs),
    }

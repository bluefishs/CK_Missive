"""
桃園派工系統 - 派工-公文關聯 API

包含端點：
- /dispatch/{dispatch_id}/link-document - 關聯公文到派工單
- /dispatch/{dispatch_id}/unlink-document/{link_id} - 移除公文關聯
- /dispatch/{dispatch_id}/documents - 取得派工單關聯公文
- /dispatch/{dispatch_id}/entity-similarity - 知識圖譜實體配對建議
- /dispatch/{dispatch_id}/correspondence-suggestions - NER 驅動公文對照建議
- /dispatch/{dispatch_id}/confirm-correspondence - 確認收發文對應並寫入知識圖譜
- /dispatch/search-linkable-documents - 搜尋可關聯的桃園派工公文
- /document/{document_id}/dispatch-links - 查詢公文關聯的派工單
- /document/{document_id}/link-dispatch - 將公文關聯到派工單
- /document/{document_id}/unlink-dispatch/{link_id} - 移除公文與派工的關聯
- /documents/batch-dispatch-links - 批次查詢多筆公文的派工關聯
"""
import logging
from collections import defaultdict
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, tuple_
from sqlalchemy.orm import selectinload
from .common import (
    get_async_db, require_auth,
    TaoyuanDispatchOrder, TaoyuanDispatchDocumentLink, Document,
    DispatchDocumentLinkCreate
)
from app.schemas.taoyuan.links import SearchLinkableDocumentsRequest, ConfirmCorrespondenceRequest
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


@router.post(
    "/dispatch/{dispatch_id}/entity-similarity",
    summary="知識圖譜實體配對建議",
)
async def get_entity_similarity(
    dispatch_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_auth()),
):
    """
    利用知識圖譜實體共現分析，計算派工單關聯公文間的語意相似度。

    回傳來文/發文兩兩間共享的 canonical entity 數量及詳情，
    供前端 buildCorrespondenceMatrix Phase 2 加權使用。
    """
    logger = logging.getLogger(__name__)

    try:
        from app.extended.models import DocumentEntityMention

        # 1. 取得該派工單所有關聯的公文
        result = await db.execute(
            select(TaoyuanDispatchDocumentLink)
            .options(selectinload(TaoyuanDispatchDocumentLink.document))
            .where(TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id)
        )
        links = result.scalars().all()

        if not links:
            return {"success": True, "pairs": [], "total_entities": 0}

        # 分類來文/發文 document IDs
        incoming_ids: list[int] = []
        outgoing_ids: list[int] = []
        for link in links:
            if link.link_type == "company_outgoing":
                outgoing_ids.append(link.document_id)
            else:
                incoming_ids.append(link.document_id)

        all_doc_ids = incoming_ids + outgoing_ids
        if not all_doc_ids:
            return {"success": True, "pairs": [], "total_entities": 0}

        # 2. 查詢所有相關公文的實體提及
        mentions_result = await db.execute(
            select(DocumentEntityMention).where(
                DocumentEntityMention.document_id.in_(all_doc_ids)
            )
        )
        mentions = mentions_result.scalars().all()

        # 建立 document_id → set[canonical_entity_id] 映射
        doc_entities: dict[int, set] = defaultdict(set)
        entity_names: dict[int, str] = {}
        for m in mentions:
            doc_entities[m.document_id].add(m.canonical_entity_id)
            entity_names[m.canonical_entity_id] = m.mention_text

        # 3. 計算來文/發文間的實體交集
        pairs = []
        for in_id in incoming_ids:
            in_ents = doc_entities.get(in_id, set())
            if not in_ents:
                continue
            for out_id in outgoing_ids:
                out_ents = doc_entities.get(out_id, set())
                if not out_ents:
                    continue
                shared = in_ents & out_ents
                if shared:
                    union_size = len(in_ents | out_ents)
                    pairs.append({
                        "incoming_doc_id": in_id,
                        "outgoing_doc_id": out_id,
                        "shared_entity_count": len(shared),
                        "jaccard": round(len(shared) / union_size, 3) if union_size else 0,
                        "shared_entities": [
                            entity_names.get(eid, f"entity#{eid}")
                            for eid in list(shared)[:10]
                        ],
                    })

        # 按 shared_entity_count 降序
        pairs.sort(key=lambda p: p["shared_entity_count"], reverse=True)

        total_entities = len({eid for ents in doc_entities.values() for eid in ents})

        return {
            "success": True,
            "pairs": pairs,
            "total_entities": total_entities,
            "incoming_count": len(incoming_ids),
            "outgoing_count": len(outgoing_ids),
        }

    except Exception as e:
        logger.error("實體相似度計算失敗: %s", e)
        return {"success": False, "pairs": [], "total_entities": 0}


@router.post(
    "/dispatch/{dispatch_id}/correspondence-suggestions",
    summary="NER 驅動公文對照建議",
)
async def get_correspondence_suggestions(
    dispatch_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_auth()),
):
    """
    利用派工單實體連結 (taoyuan_dispatch_entity_link) 和
    公文實體提及 (document_entity_mentions) 做 NER 驅動的來文/發文配對建議。

    相比 entity-similarity 端點，本端點：
    1. 使用預計算的派工單實體（非即時 Jaccard）
    2. 回傳分級信心度 (confirmed/high/medium/low)
    3. 包含具體實體名稱作為匹配理由
    """
    logger = logging.getLogger(__name__)

    try:
        from app.extended.models import (
            TaoyuanDispatchEntityLink, DocumentEntityMention,
            CanonicalEntity, TaoyuanWorkRecord, EntityRelationship,
        )

        # 1. 取得派工單的正規化實體集合
        dispatch_entities_result = await db.execute(
            select(
                TaoyuanDispatchEntityLink.canonical_entity_id,
                CanonicalEntity.canonical_name,
                CanonicalEntity.entity_type,
            )
            .join(CanonicalEntity,
                  CanonicalEntity.id == TaoyuanDispatchEntityLink.canonical_entity_id)
            .where(TaoyuanDispatchEntityLink.dispatch_order_id == dispatch_id)
        )
        dispatch_entity_rows = dispatch_entities_result.all()
        dispatch_entity_ids = {r[0] for r in dispatch_entity_rows}
        dispatch_entity_names = {r[0]: (r[1], r[2]) for r in dispatch_entity_rows}

        if not dispatch_entity_ids:
            return {
                "success": True,
                "suggestions": [],
                "dispatch_entities": [],
                "message": "此派工單尚未建立實體連結",
            }

        # 2. 取得關聯公文及其分類
        links_result = await db.execute(
            select(TaoyuanDispatchDocumentLink)
            .options(selectinload(TaoyuanDispatchDocumentLink.document))
            .where(TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id)
        )
        links = links_result.scalars().all()

        incoming_ids: list[int] = []
        outgoing_ids: list[int] = []
        doc_info: dict[int, dict] = {}
        for link in links:
            doc = link.document
            info = {
                "doc_id": link.document_id,
                "link_type": link.link_type,
                "doc_number": doc.doc_number if doc else None,
                "subject": doc.subject if doc else None,
                "doc_date": str(doc.doc_date) if doc and doc.doc_date else None,
            }
            doc_info[link.document_id] = info
            if link.link_type == "company_outgoing":
                outgoing_ids.append(link.document_id)
            else:
                incoming_ids.append(link.document_id)

        all_doc_ids = incoming_ids + outgoing_ids
        if not all_doc_ids:
            return {
                "success": True,
                "suggestions": [],
                "dispatch_entities": [
                    {"id": eid, "name": name, "type": etype}
                    for eid, (name, etype) in dispatch_entity_names.items()
                ],
            }

        # 3. 查詢關聯公文的實體提及（只看派工單有的實體）
        mentions_result = await db.execute(
            select(DocumentEntityMention).where(
                DocumentEntityMention.document_id.in_(all_doc_ids),
                DocumentEntityMention.canonical_entity_id.in_(dispatch_entity_ids),
            )
        )
        mentions = mentions_result.scalars().all()

        doc_entities: dict[int, set[int]] = defaultdict(set)
        for m in mentions:
            doc_entities[m.document_id].add(m.canonical_entity_id)

        # 4. 查詢已有 parent_record_id 鏈的配對（Phase 1 confirmed）
        work_records_result = await db.execute(
            select(TaoyuanWorkRecord).where(
                TaoyuanWorkRecord.dispatch_order_id == dispatch_id,
                TaoyuanWorkRecord.parent_record_id.isnot(None),
            )
        )
        confirmed_chains = work_records_result.scalars().all()
        confirmed_pairs: set[tuple[int, int]] = set()
        for wr in confirmed_chains:
            if wr.document_id and wr.parent_record_id:
                # 查詢 parent 的 document_id
                parent_result = await db.execute(
                    select(TaoyuanWorkRecord.document_id).where(
                        TaoyuanWorkRecord.id == wr.parent_record_id
                    )
                )
                parent_doc_id = parent_result.scalar()
                if parent_doc_id:
                    confirmed_pairs.add((parent_doc_id, wr.document_id))
                    confirmed_pairs.add((wr.document_id, parent_doc_id))

        # 4.5 查詢圖譜中已有的 correspondence 關係（Phase 2.5 增強）
        # 找出各公文實體之間的 correspondence 邊，用於信心度加分
        graph_boosted_pairs: set[tuple[int, int]] = set()
        all_entity_ids = set()
        for eid_set in doc_entities.values():
            all_entity_ids.update(eid_set)
        if all_entity_ids:
            corr_rels_result = await db.execute(
                select(
                    EntityRelationship.source_entity_id,
                    EntityRelationship.target_entity_id,
                ).where(
                    EntityRelationship.relation_type == "correspondence",
                    EntityRelationship.source_entity_id.in_(all_entity_ids),
                    EntityRelationship.target_entity_id.in_(all_entity_ids),
                )
            )
            for src, tgt in corr_rels_result.all():
                graph_boosted_pairs.add((src, tgt))
                graph_boosted_pairs.add((tgt, src))

        # 5. 建立配對建議
        suggestions = []
        for in_id in incoming_ids:
            in_ents = doc_entities.get(in_id, set())
            for out_id in outgoing_ids:
                out_ents = doc_entities.get(out_id, set())
                shared = in_ents & out_ents

                # 判斷信心度
                if (in_id, out_id) in confirmed_pairs:
                    confidence = "confirmed"
                    score = 1.0
                elif shared:
                    # 考慮實體類型權重: location 權重最高
                    location_count = sum(
                        1 for eid in shared
                        if dispatch_entity_names.get(eid, ('', ''))[1] == 'location'
                    )
                    base_score = len(shared) / max(len(in_ents | out_ents), 1)
                    score = min(base_score + location_count * 0.1, 1.0)

                    # Phase 2.5: 圖譜 correspondence 邊加分
                    has_graph_link = any(
                        (a, b) in graph_boosted_pairs
                        for a in in_ents for b in out_ents
                    )
                    if has_graph_link:
                        score = min(score + 0.15, 1.0)

                    confidence = "high" if score >= 0.3 else "medium"
                else:
                    # 無共享實體 → 低信心
                    score = 0.0
                    confidence = "low"

                if confidence == "low" and not shared:
                    continue  # 跳過無任何實體交集的配對

                shared_names = [
                    dispatch_entity_names.get(eid, (f"entity#{eid}", ''))[0]
                    for eid in list(shared)[:10]
                ]

                suggestions.append({
                    "incoming_doc_id": in_id,
                    "outgoing_doc_id": out_id,
                    "confidence": confidence,
                    "score": round(score, 3),
                    "shared_entity_count": len(shared),
                    "shared_entities": shared_names,
                    "incoming_doc": doc_info.get(in_id),
                    "outgoing_doc": doc_info.get(out_id),
                })

        # 按 score 降序排列
        suggestions.sort(key=lambda s: s["score"], reverse=True)

        return {
            "success": True,
            "suggestions": suggestions,
            "dispatch_entities": [
                {"id": eid, "name": name, "type": etype}
                for eid, (name, etype) in dispatch_entity_names.items()
            ],
            "stats": {
                "incoming_count": len(incoming_ids),
                "outgoing_count": len(outgoing_ids),
                "total_suggestions": len(suggestions),
                "confirmed": sum(1 for s in suggestions if s["confidence"] == "confirmed"),
                "high": sum(1 for s in suggestions if s["confidence"] == "high"),
                "medium": sum(1 for s in suggestions if s["confidence"] == "medium"),
            },
        }

    except Exception as e:
        logger.error("公文對照建議計算失敗: %s", e)
        return {"success": False, "suggestions": [], "dispatch_entities": []}


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


@router.post(
    "/dispatch/{dispatch_id}/confirm-correspondence",
    summary="確認收發文對應並寫入知識圖譜",
)
async def confirm_correspondence(
    dispatch_id: int,
    request: ConfirmCorrespondenceRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_auth()),
):
    """
    確認收發文對應配對，將關係寫入知識圖譜。

    對每組 incoming↔outgoing 配對：
    1. 查找兩份公文共享的 CanonicalEntity（透過 DocumentEntityMention）
    2. 為共享實體建立或更新 EntityRelationship (relation_type='correspondence')
    3. 失效圖譜快取
    """
    logger = logging.getLogger(__name__)

    try:
        from app.extended.models import (
            CanonicalEntity, DocumentEntityMention, EntityRelationship,
        )
        from app.services.ai.graph_helpers import invalidate_graph_cache

        if not request.pairs:
            return {
                "success": True,
                "confirmed_count": 0,
                "relationships_created": 0,
                "relationships_updated": 0,
            }

        # ----------------------------------------------------------------
        # Phase 1: 批次預載所有相關公文的 canonical_entity_id
        # 將 O(2N) 查詢合併為 1 次
        # ----------------------------------------------------------------
        valid_pairs = []
        all_doc_ids = set()
        for pair in request.pairs:
            incoming_doc_id = pair.get("incoming_doc_id")
            outgoing_doc_id = pair.get("outgoing_doc_id")
            if not incoming_doc_id or not outgoing_doc_id:
                logger.warning("跳過無效配對: incoming=%s, outgoing=%s", incoming_doc_id, outgoing_doc_id)
                continue
            valid_pairs.append((incoming_doc_id, outgoing_doc_id))
            all_doc_ids.update([incoming_doc_id, outgoing_doc_id])

        if not valid_pairs:
            return {"success": True, "confirmed_count": 0, "relationships_created": 0, "relationships_updated": 0}

        # 一次查詢所有 document → canonical_entity_id 映射
        mentions_result = await db.execute(
            select(
                DocumentEntityMention.document_id,
                DocumentEntityMention.canonical_entity_id,
            ).where(
                DocumentEntityMention.document_id.in_(all_doc_ids),
                DocumentEntityMention.canonical_entity_id.isnot(None),
            )
        )
        doc_entity_map: dict[int, set[int]] = {}
        for doc_id, entity_id in mentions_result.all():
            doc_entity_map.setdefault(doc_id, set()).add(entity_id)

        # ----------------------------------------------------------------
        # Phase 2: 收集所有需要的 (source, target) 對
        # ----------------------------------------------------------------
        needed_pairs: list[tuple[int, int, int]] = []  # (source_id, target_id, incoming_doc_id)
        pair_plan: list[tuple[set[int], set[int], int, int]] = []  # (shared, fallback, in_id, out_id)

        for incoming_doc_id, outgoing_doc_id in valid_pairs:
            in_ents = doc_entity_map.get(incoming_doc_id, set())
            out_ents = doc_entity_map.get(outgoing_doc_id, set())
            shared = in_ents & out_ents

            if not shared:
                if in_ents and out_ents:
                    src = next(iter(in_ents))
                    tgt = next(iter(out_ents))
                    needed_pairs.append((src, tgt, incoming_doc_id))
            else:
                for eid in shared:
                    needed_pairs.append((eid, eid, incoming_doc_id))
                shared_list = list(shared)
                if len(shared_list) >= 2:
                    needed_pairs.append((shared_list[0], shared_list[1], incoming_doc_id))

            pair_plan.append((shared, in_ents | out_ents, incoming_doc_id, outgoing_doc_id))

        # ----------------------------------------------------------------
        # Phase 3: 批次查詢既有 correspondence 關係 → O(1) 查詢
        # ----------------------------------------------------------------
        existing_rels_map: dict[tuple[int, int], EntityRelationship] = {}
        if needed_pairs:
            st_pairs = [(s, t) for s, t, _ in needed_pairs]
            unique_pairs = list(set(st_pairs))
            # 批次查詢：所有相關的 correspondence 關係
            existing_result = await db.execute(
                select(EntityRelationship).where(
                    EntityRelationship.relation_type == "correspondence",
                    tuple_(
                        EntityRelationship.source_entity_id,
                        EntityRelationship.target_entity_id,
                    ).in_(unique_pairs),
                )
            )
            for rel in existing_result.scalars().all():
                existing_rels_map[(rel.source_entity_id, rel.target_entity_id)] = rel

        # ----------------------------------------------------------------
        # Phase 4: 批次建立/更新關係 (純記憶體操作，最後一次 commit)
        # ----------------------------------------------------------------
        relationships_created = 0
        relationships_updated = 0
        confirmed_count = 0

        for incoming_doc_id, outgoing_doc_id in valid_pairs:
            in_ents = doc_entity_map.get(incoming_doc_id, set())
            out_ents = doc_entity_map.get(outgoing_doc_id, set())
            shared = in_ents & out_ents

            def _upsert_rel(source_id: int, target_id: int, doc_id: int) -> None:
                nonlocal relationships_created, relationships_updated
                key = (source_id, target_id)
                existing = existing_rels_map.get(key)
                if existing:
                    existing.document_count = (existing.document_count or 1) + 1
                    existing.weight = (existing.weight or 1.0) + 1.0
                    relationships_updated += 1
                else:
                    rel = EntityRelationship(
                        source_entity_id=source_id,
                        target_entity_id=target_id,
                        relation_type="correspondence",
                        relation_label="收發文對應",
                        weight=1.0,
                        document_count=1,
                        first_document_id=doc_id,
                    )
                    db.add(rel)
                    existing_rels_map[key] = rel
                    relationships_created += 1

            if not shared:
                if in_ents and out_ents:
                    _upsert_rel(next(iter(in_ents)), next(iter(out_ents)), incoming_doc_id)
                confirmed_count += 1
                continue

            for eid in shared:
                _upsert_rel(eid, eid, incoming_doc_id)

            shared_list = list(shared)
            if len(shared_list) >= 2:
                _upsert_rel(shared_list[0], shared_list[1], incoming_doc_id)

            confirmed_count += 1

        await db.commit()

        # 失效圖譜快取
        await invalidate_graph_cache()

        logger.info(
            "收發文對應確認完成: dispatch=%d, confirmed=%d, created=%d, updated=%d",
            dispatch_id, confirmed_count, relationships_created, relationships_updated,
        )

        return {
            "success": True,
            "confirmed_count": confirmed_count,
            "relationships_created": relationships_created,
            "relationships_updated": relationships_updated,
        }

    except Exception as e:
        logger.error("收發文對應確認失敗: %s", e)
        return {
            "success": False,
            "confirmed_count": 0,
            "relationships_created": 0,
            "relationships_updated": 0,
        }


@router.post(
    "/dispatch/{dispatch_id}/rebuild-correspondence",
    summary="重建派工單的公文對照矩陣",
)
async def rebuild_correspondence(
    dispatch_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_auth()),
):
    """
    重建派工單的公文對照矩陣：

    1. 取得該派工單所有已關聯的公文
    2. 對每份公文重新執行自動關聯邏輯
    3. 回傳更新後的關聯統計
    """
    logger = logging.getLogger(__name__)

    try:
        from app.services.document_dispatch_linker_service import DocumentDispatchLinkerService

        # 1. 確認派工單存在
        order_result = await db.execute(
            select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.id == dispatch_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="派工紀錄不存在")

        # 2. 取得目前所有關聯公文 ID
        existing_links_result = await db.execute(
            select(TaoyuanDispatchDocumentLink)
            .options(selectinload(TaoyuanDispatchDocumentLink.document))
            .where(TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id)
        )
        existing_links = existing_links_result.scalars().all()
        existing_doc_ids = {link.document_id for link in existing_links}

        # 3. 對每份已關聯的公文重新執行自動關聯
        linker = DocumentDispatchLinkerService(db)
        new_links_count = 0
        for link in existing_links:
            if link.document:
                await linker.auto_link_to_dispatch_orders(link.document)

        # 4. 統計新增的關聯
        updated_links_result = await db.execute(
            select(TaoyuanDispatchDocumentLink).where(
                TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id
            )
        )
        updated_links = updated_links_result.scalars().all()
        updated_doc_ids = {link.document_id for link in updated_links}
        new_links_count = len(updated_doc_ids - existing_doc_ids)

        await db.commit()

        logger.info(
            "重建公文對照矩陣完成: dispatch_id=%d, 既有=%d, 新增=%d, 總計=%d",
            dispatch_id, len(existing_doc_ids), new_links_count, len(updated_doc_ids),
        )

        return {
            "success": True,
            "dispatch_id": dispatch_id,
            "existing_count": len(existing_doc_ids),
            "new_links_count": new_links_count,
            "total_count": len(updated_doc_ids),
            "message": f"重建完成：既有 {len(existing_doc_ids)} 筆，新增 {new_links_count} 筆",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("重建公文對照矩陣失敗: dispatch_id=%d, error=%s", dispatch_id, e)
        return {
            "success": False,
            "message": f"重建失敗: {str(e)}",
        }


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

"""
桃園派工系統 - 派工紀錄 CRUD API

包含端點：
- /dispatch/list - 派工紀錄列表
- /dispatch/import-template - 下載匯入範本
- /dispatch/import - 匯入派工紀錄
- /dispatch/next-dispatch-no - 取得下一個派工單號
- /dispatch/create - 建立派工紀錄
- /dispatch/{dispatch_id}/update - 更新派工紀錄
- /dispatch/{dispatch_id}/detail - 取得派工紀錄詳情
- /dispatch/{dispatch_id}/delete - 刪除派工紀錄
- /dispatch/match-documents - 匹配公文歷程
- /dispatch/{dispatch_id}/detail-with-history - 詳情含公文歷程
"""
import re
import io
from datetime import datetime
from typing import Optional, List
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from .common import (
    get_async_db, require_auth,
    TaoyuanProject, TaoyuanDispatchOrder, TaoyuanDispatchProjectLink,
    TaoyuanDispatchDocumentLink, Document,
    DispatchOrderCreate, DispatchOrderUpdate, DispatchOrderSchema,
    DispatchOrderListQuery, DispatchOrderListResponse,
    TaoyuanProjectSchema, LinkedProjectItem, ExcelImportResult, PaginationMeta
)

router = APIRouter()


@router.post("/dispatch/list", response_model=DispatchOrderListResponse, summary="派工紀錄列表")
async def list_dispatch_orders(
    query: DispatchOrderListQuery,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """查詢派工紀錄列表"""
    from app.extended.models import TaoyuanDispatchAttachment

    stmt = select(TaoyuanDispatchOrder).options(
        selectinload(TaoyuanDispatchOrder.agency_doc),
        selectinload(TaoyuanDispatchOrder.company_doc),
        selectinload(TaoyuanDispatchOrder.project_links).selectinload(TaoyuanDispatchProjectLink.project),
        selectinload(TaoyuanDispatchOrder.document_links).selectinload(TaoyuanDispatchDocumentLink.document),
        selectinload(TaoyuanDispatchOrder.attachments)
    )

    conditions = []
    if query.contract_project_id:
        conditions.append(TaoyuanDispatchOrder.contract_project_id == query.contract_project_id)
    if query.work_type:
        conditions.append(TaoyuanDispatchOrder.work_type == query.work_type)
    if query.search:
        search_pattern = f"%{query.search}%"
        conditions.append(or_(
            TaoyuanDispatchOrder.dispatch_no.ilike(search_pattern),
            TaoyuanDispatchOrder.project_name.ilike(search_pattern)
        ))

    if conditions:
        stmt = stmt.where(and_(*conditions))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    sort_column = getattr(TaoyuanDispatchOrder, query.sort_by, TaoyuanDispatchOrder.id)
    if query.sort_order == "desc":
        stmt = stmt.order_by(sort_column.desc())
    else:
        stmt = stmt.order_by(sort_column.asc())

    offset = (query.page - 1) * query.limit
    stmt = stmt.offset(offset).limit(query.limit)

    result = await db.execute(stmt)
    items = result.scalars().unique().all()

    response_items = []
    for item in items:
        order_dict = {
            'id': item.id,
            'dispatch_no': item.dispatch_no,
            'contract_project_id': item.contract_project_id,
            'agency_doc_id': item.agency_doc_id,
            'company_doc_id': item.company_doc_id,
            'project_name': item.project_name,
            'work_type': item.work_type,
            'sub_case_name': item.sub_case_name,
            'deadline': item.deadline,
            'case_handler': item.case_handler,
            'survey_unit': item.survey_unit,
            'cloud_folder': item.cloud_folder,
            'project_folder': item.project_folder,
            'contact_note': item.contact_note,
            'created_at': item.created_at,
            'updated_at': item.updated_at,
            'agency_doc_number': item.agency_doc.doc_number if item.agency_doc else None,
            'company_doc_number': item.company_doc.doc_number if item.company_doc else None,
            'attachment_count': len(item.attachments) if item.attachments else 0,
            'linked_projects': [
                LinkedProjectItem.model_validate({
                    **TaoyuanProjectSchema.model_validate(link.project).model_dump(),
                    'link_id': link.id,
                    'project_id': link.taoyuan_project_id,
                }).model_dump()
                for link in item.project_links if link.project
            ] if item.project_links else [],
            'linked_documents': [
                {
                    'link_id': link.id,
                    'link_type': link.link_type,
                    'dispatch_order_id': link.dispatch_order_id,
                    'document_id': link.document_id,
                    'doc_number': link.document.doc_number if link.document else None,
                    'subject': link.document.subject if link.document else None,
                    'doc_date': link.document.doc_date.isoformat() if link.document and link.document.doc_date else None,
                    'created_at': link.created_at.isoformat() if link.created_at else None,
                }
                for link in item.document_links
            ] if item.document_links else []
        }
        response_items.append(DispatchOrderSchema(**order_dict))

    total_pages = (total + query.limit - 1) // query.limit

    return DispatchOrderListResponse(
        success=True,
        items=response_items,
        pagination=PaginationMeta(
            total=total,
            page=query.page,
            limit=query.limit,
            total_pages=total_pages,
            has_next=query.page < total_pages,
            has_prev=query.page > 1
        )
    )


@router.post("/dispatch/import-template", summary="下載派工紀錄匯入範本")
async def download_dispatch_import_template():
    """下載派工紀錄 Excel 匯入範本"""
    template_columns = [
        '派工單號', '機關函文號', '工程名稱/派工事項', '作業類別',
        '分案名稱/派工備註', '履約期限', '案件承辦', '查估單位',
        '乾坤函文號', '雲端資料夾', '專案資料夾', '聯絡備註'
    ]

    sample_data = [{
        '派工單號': 'D-2026-001',
        '機關函文號': '桃工養字第1140001234號',
        '工程名稱/派工事項': '○○路拓寬工程',
        '作業類別': '土地查估',
        '分案名稱/派工備註': '第一標段',
        '履約期限': '2026-06-30',
        '案件承辦': '王○○',
        '查估單位': '第一組',
        '乾坤函文號': '乾字第1140000001號',
        '雲端資料夾': 'https://drive.google.com/...',
        '專案資料夾': 'D:/Projects/2026/001',
        '聯絡備註': '範例資料，請刪除後填入實際資料'
    }]

    df = pd.DataFrame(sample_data, columns=template_columns)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='派工紀錄')
        worksheet = writer.sheets['派工紀錄']
        for idx, col in enumerate(template_columns):
            width = max(len(col) * 2.5, 15)
            col_letter = chr(65 + idx) if idx < 26 else f'A{chr(65 + idx - 26)}'
            worksheet.column_dimensions[col_letter].width = width

    output.seek(0)

    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=dispatch_orders_import_template.xlsx'}
    )


@router.post("/dispatch/import", response_model=ExcelImportResult, summary="匯入派工紀錄")
async def import_dispatch_orders(
    file: UploadFile = File(...),
    contract_project_id: int = Form(...),
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """從 Excel 匯入派工紀錄"""
    from app.extended.models import ContractProject

    contract_project = await db.execute(
        select(ContractProject).where(ContractProject.id == contract_project_id)
    )
    if not contract_project.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"承攬案件 ID={contract_project_id} 不存在")

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="僅支援 Excel 檔案格式")

    content = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(content), sheet_name=0, header=0)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"讀取 Excel 失敗: {str(e)}")

    column_mapping = {
        '派工單號': 'dispatch_no',
        '機關函文號': 'agency_doc_number_text',
        '工程名稱/派工事項': 'project_name',
        '作業類別': 'work_type',
        '分案名稱/派工備註': 'sub_case_name',
        '履約期限': 'deadline',
        '案件承辦': 'case_handler',
        '查估單位': 'survey_unit',
        '乾坤函文號': 'company_doc_number_text',
        '雲端資料夾': 'cloud_folder',
        '專案資料夾': 'project_folder',
        '聯絡備註': 'contact_note',
    }

    imported_count = 0
    skipped_count = 0
    linked_count = 0
    errors = []

    for idx, row in df.iterrows():
        row_num = idx + 2
        try:
            dispatch_no = row.get('派工單號')
            if pd.isna(dispatch_no) or not str(dispatch_no).strip():
                errors.append({'row': row_num, 'error': '派工單號不可為空'})
                skipped_count += 1
                continue

            dispatch_no = str(dispatch_no).strip()

            existing = await db.execute(
                select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.dispatch_no == dispatch_no)
            )
            if existing.scalar_one_or_none():
                errors.append({'row': row_num, 'error': f'派工單號 {dispatch_no} 已存在'})
                skipped_count += 1
                continue

            project_name = row.get('工程名稱/派工事項')
            if pd.isna(project_name) or not str(project_name).strip():
                errors.append({'row': row_num, 'error': '工程名稱/派工事項不可為空'})
                skipped_count += 1
                continue

            order_data = {
                'contract_project_id': contract_project_id,
                'dispatch_no': dispatch_no,
                'project_name': str(project_name).strip(),
            }

            agency_doc_number_text = None
            company_doc_number_text = None

            for excel_col, db_col in column_mapping.items():
                if excel_col in ['派工單號', '工程名稱/派工事項']:
                    continue

                if excel_col in row.index:
                    value = row[excel_col]
                    if pd.notna(value) and str(value).strip():
                        if db_col == 'deadline':
                            if hasattr(value, 'date'):
                                value = value.date()
                            elif isinstance(value, str):
                                try:
                                    value = datetime.strptime(value.strip(), '%Y-%m-%d').date()
                                except ValueError:
                                    value = None
                        elif db_col == 'agency_doc_number_text':
                            agency_doc_number_text = str(value).strip()
                            continue
                        elif db_col == 'company_doc_number_text':
                            company_doc_number_text = str(value).strip()
                            continue
                        else:
                            value = str(value).strip()

                        if value is not None:
                            order_data[db_col] = value

            if agency_doc_number_text:
                agency_doc_result = await db.execute(
                    select(Document).where(Document.doc_number == agency_doc_number_text)
                )
                agency_doc = agency_doc_result.scalar_one_or_none()
                if agency_doc:
                    order_data['agency_doc_id'] = agency_doc.id

            if company_doc_number_text:
                company_doc_result = await db.execute(
                    select(Document).where(Document.doc_number == company_doc_number_text)
                )
                company_doc = company_doc_result.scalar_one_or_none()
                if company_doc:
                    order_data['company_doc_id'] = company_doc.id

            order = TaoyuanDispatchOrder(**order_data)
            db.add(order)
            await db.flush()

            if order_data.get('agency_doc_id'):
                link = TaoyuanDispatchDocumentLink(
                    dispatch_order_id=order.id,
                    document_id=order_data['agency_doc_id'],
                    link_type='agency_incoming'
                )
                db.add(link)
                linked_count += 1

            if order_data.get('company_doc_id'):
                link = TaoyuanDispatchDocumentLink(
                    dispatch_order_id=order.id,
                    document_id=order_data['company_doc_id'],
                    link_type='company_outgoing'
                )
                db.add(link)
                linked_count += 1

            imported_count += 1

        except Exception as e:
            errors.append({'row': row_num, 'error': str(e)})

    await db.commit()

    linked_info = f"，自動建立 {linked_count} 筆公文關聯" if linked_count > 0 else ""

    return ExcelImportResult(
        success=True,
        message=f"匯入完成：成功 {imported_count} 筆，跳過 {skipped_count} 筆{linked_info}",
        total_rows=len(df),
        imported_count=imported_count,
        skipped_count=skipped_count,
        error_count=len(errors),
        errors=errors[:20]
    )


@router.post("/dispatch/next-dispatch-no", summary="取得下一個派工單號")
async def get_next_dispatch_no(
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """根據現有派工單號自動生成下一個單號"""
    current_year = datetime.now().year - 1911
    year_prefix = f"{current_year}年_派工單號"

    result = await db.execute(
        select(TaoyuanDispatchOrder.dispatch_no)
        .where(TaoyuanDispatchOrder.dispatch_no.like(f"{year_prefix}%"))
        .order_by(TaoyuanDispatchOrder.dispatch_no.desc())
    )
    existing_nos = [r[0] for r in result.fetchall()]

    max_seq = 0
    pattern = re.compile(rf"^{current_year}年_派工單號(\d+)$")
    for no in existing_nos:
        if no:
            match = pattern.match(no)
            if match:
                seq = int(match.group(1))
                if seq > max_seq:
                    max_seq = seq

    next_seq = max_seq + 1
    next_dispatch_no = f"{current_year}年_派工單號{next_seq:03d}"

    return {
        "success": True,
        "next_dispatch_no": next_dispatch_no,
        "current_year": current_year,
        "next_sequence": next_seq
    }


@router.post("/dispatch/create", response_model=DispatchOrderSchema, summary="建立派工紀錄")
async def create_dispatch_order(
    data: DispatchOrderCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """建立派工紀錄"""
    existing = await db.execute(
        select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.dispatch_no == data.dispatch_no)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="派工單號已存在")

    order_data = data.model_dump(exclude={'linked_project_ids'})
    order = TaoyuanDispatchOrder(**order_data)
    db.add(order)
    await db.flush()

    if data.linked_project_ids:
        for project_id in data.linked_project_ids:
            link = TaoyuanDispatchProjectLink(
                dispatch_order_id=order.id,
                taoyuan_project_id=project_id
            )
            db.add(link)

    await db.commit()
    await db.refresh(order)
    return DispatchOrderSchema.model_validate(order)


@router.post("/dispatch/{dispatch_id}/update", response_model=DispatchOrderSchema, summary="更新派工紀錄")
async def update_dispatch_order(
    dispatch_id: int,
    data: DispatchOrderUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """更新派工紀錄"""
    result = await db.execute(
        select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.id == dispatch_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="派工紀錄不存在")

    update_data = data.model_dump(exclude_unset=True, exclude_none=True, exclude={'linked_project_ids'})
    for key, value in update_data.items():
        setattr(order, key, value)

    if data.linked_project_ids is not None:
        await db.execute(
            TaoyuanDispatchProjectLink.__table__.delete().where(
                TaoyuanDispatchProjectLink.dispatch_order_id == dispatch_id
            )
        )
        for project_id in data.linked_project_ids:
            link = TaoyuanDispatchProjectLink(
                dispatch_order_id=dispatch_id,
                taoyuan_project_id=project_id
            )
            db.add(link)

    await db.commit()
    await db.refresh(order)
    return DispatchOrderSchema.model_validate(order)


@router.post("/dispatch/{dispatch_id}/detail", response_model=DispatchOrderSchema, summary="取得派工紀錄詳情")
async def get_dispatch_order_detail(
    dispatch_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """取得派工紀錄詳情"""
    stmt = select(TaoyuanDispatchOrder).options(
        selectinload(TaoyuanDispatchOrder.agency_doc),
        selectinload(TaoyuanDispatchOrder.company_doc),
        selectinload(TaoyuanDispatchOrder.project_links).selectinload(TaoyuanDispatchProjectLink.project),
        selectinload(TaoyuanDispatchOrder.document_links).selectinload(TaoyuanDispatchDocumentLink.document)
    ).where(TaoyuanDispatchOrder.id == dispatch_id)

    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="派工紀錄不存在")

    linked_documents = []
    for link in (order.document_links or []):
        if link.document:
            linked_documents.append({
                'link_id': link.id,
                'link_type': link.link_type,
                'dispatch_order_id': link.dispatch_order_id,
                'document_id': link.document.id,
                'doc_number': link.document.doc_number,
                'subject': link.document.subject,
                'doc_date': link.document.doc_date.isoformat() if link.document.doc_date else None,
                'created_at': link.created_at.isoformat() if link.created_at else None,
            })

    order_dict = {
        'id': order.id,
        'dispatch_no': order.dispatch_no,
        'contract_project_id': order.contract_project_id,
        'agency_doc_id': order.agency_doc_id,
        'company_doc_id': order.company_doc_id,
        'project_name': order.project_name,
        'work_type': order.work_type,
        'sub_case_name': order.sub_case_name,
        'deadline': order.deadline,
        'case_handler': order.case_handler,
        'survey_unit': order.survey_unit,
        'cloud_folder': order.cloud_folder,
        'project_folder': order.project_folder,
        'contact_note': order.contact_note,
        'created_at': order.created_at,
        'updated_at': order.updated_at,
        'agency_doc_number': order.agency_doc.doc_number if order.agency_doc else None,
        'company_doc_number': order.company_doc.doc_number if order.company_doc else None,
        'linked_projects': [
            LinkedProjectItem.model_validate({
                **TaoyuanProjectSchema.model_validate(link.project).model_dump(),
                'link_id': link.id,
                'project_id': link.taoyuan_project_id,
            }).model_dump()
            for link in order.project_links if link.project
        ] if order.project_links else [],
        'linked_documents': linked_documents,
    }

    return order_dict


@router.post("/dispatch/{dispatch_id}/delete", summary="刪除派工紀錄")
async def delete_dispatch_order(
    dispatch_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """刪除派工紀錄"""
    result = await db.execute(
        select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.id == dispatch_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="派工紀錄不存在")

    await db.delete(order)
    await db.commit()
    return {"success": True, "message": "刪除成功"}


@router.post("/dispatch/match-documents", summary="匹配公文歷程")
async def match_document_history(
    project_name: str,
    include_subject: bool = False,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """根據工程名稱自動匹配公文歷程"""
    if not project_name or not project_name.strip():
        return {
            "success": False,
            "message": "工程名稱不可為空",
            "agency_documents": [],
            "company_documents": []
        }

    search_pattern = f"%{project_name.strip()}%"

    agency_stmt = select(Document).where(
        and_(
            Document.type == '收文',
            Document.subject.ilike(search_pattern)
        )
    ).order_by(Document.doc_date.desc()).limit(50)

    agency_result = await db.execute(agency_stmt)
    agency_docs = agency_result.scalars().all()

    company_stmt = select(Document).where(
        and_(
            Document.type == '發文',
            Document.subject.ilike(search_pattern)
        )
    ).order_by(Document.doc_date.desc()).limit(50)

    company_result = await db.execute(company_stmt)
    company_docs = company_result.scalars().all()

    def format_doc(doc, match_type="project_name"):
        return {
            "id": doc.id,
            "doc_number": doc.doc_number,
            "doc_date": doc.doc_date,
            "subject": doc.subject,
            "sender": doc.sender,
            "receiver": doc.receiver,
            "doc_type": doc.type,
            "match_type": match_type
        }

    return {
        "success": True,
        "project_name": project_name,
        "agency_documents": [format_doc(d) for d in agency_docs],
        "company_documents": [format_doc(d) for d in company_docs],
        "total_agency_docs": len(agency_docs),
        "total_company_docs": len(company_docs)
    }


@router.post("/dispatch/{dispatch_id}/detail-with-history", summary="取得派工紀錄詳情 (含公文歷程)")
async def get_dispatch_order_detail_with_history(
    dispatch_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """取得派工紀錄詳情，並自動匹配公文歷程"""
    stmt = select(TaoyuanDispatchOrder).options(
        selectinload(TaoyuanDispatchOrder.agency_doc),
        selectinload(TaoyuanDispatchOrder.company_doc),
        selectinload(TaoyuanDispatchOrder.project_links).selectinload(TaoyuanDispatchProjectLink.project),
        selectinload(TaoyuanDispatchOrder.document_links).selectinload(TaoyuanDispatchDocumentLink.document)
    ).where(TaoyuanDispatchOrder.id == dispatch_id)

    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="派工紀錄不存在")

    order_dict = {
        'id': order.id,
        'dispatch_no': order.dispatch_no,
        'contract_project_id': order.contract_project_id,
        'agency_doc_id': order.agency_doc_id,
        'company_doc_id': order.company_doc_id,
        'project_name': order.project_name,
        'work_type': order.work_type,
        'sub_case_name': order.sub_case_name,
        'deadline': order.deadline,
        'case_handler': order.case_handler,
        'survey_unit': order.survey_unit,
        'cloud_folder': order.cloud_folder,
        'project_folder': order.project_folder,
        'contact_note': order.contact_note,
        'created_at': order.created_at,
        'updated_at': order.updated_at,
        'agency_doc_number': order.agency_doc.doc_number if order.agency_doc else None,
        'company_doc_number': order.company_doc.doc_number if order.company_doc else None,
        'linked_projects': [
            LinkedProjectItem.model_validate({
                **TaoyuanProjectSchema.model_validate(link.project).model_dump(),
                'link_id': link.id,
                'project_id': link.taoyuan_project_id,
            }).model_dump()
            for link in order.project_links if link.project
        ] if order.project_links else []
    }

    doc_history = {
        'agency_doc_history_by_name': [],
        'agency_doc_history_by_subject': [],
        'company_doc_history_by_name': [],
        'company_doc_history_by_subject': []
    }

    if order.project_name:
        search_pattern = f"%{order.project_name}%"

        agency_stmt = select(Document).where(
            and_(
                Document.type == '收文',
                Document.subject.ilike(search_pattern)
            )
        ).order_by(Document.doc_date.desc()).limit(20)
        agency_result = await db.execute(agency_stmt)
        agency_docs = agency_result.scalars().all()

        for doc in agency_docs:
            doc_info = {
                'id': doc.id,
                'doc_number': doc.doc_number,
                'doc_date': doc.doc_date,
                'subject': doc.subject,
                'sender': doc.sender,
                'receiver': doc.receiver,
                'doc_type': doc.type,
                'match_type': 'project_name'
            }
            doc_history['agency_doc_history_by_name'].append(doc_info)
            if order.project_name in (doc.subject or ''):
                doc_history['agency_doc_history_by_subject'].append(doc_info)

        company_stmt = select(Document).where(
            and_(
                Document.type == '發文',
                Document.subject.ilike(search_pattern)
            )
        ).order_by(Document.doc_date.desc()).limit(20)
        company_result = await db.execute(company_stmt)
        company_docs = company_result.scalars().all()

        for doc in company_docs:
            doc_info = {
                'id': doc.id,
                'doc_number': doc.doc_number,
                'doc_date': doc.doc_date,
                'subject': doc.subject,
                'sender': doc.sender,
                'receiver': doc.receiver,
                'doc_type': doc.type,
                'match_type': 'project_name'
            }
            doc_history['company_doc_history_by_name'].append(doc_info)
            if order.project_name in (doc.subject or ''):
                doc_history['company_doc_history_by_subject'].append(doc_info)

    order_dict.update(doc_history)

    return {
        "success": True,
        "data": order_dict
    }

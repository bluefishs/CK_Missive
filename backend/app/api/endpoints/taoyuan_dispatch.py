"""
桃園查估派工管理系統 API 端點
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
import pandas as pd
import io

from app.db.database import get_async_db
from app.core.dependencies import require_auth
from app.extended.models import (
    TaoyuanProject, TaoyuanDispatchOrder, TaoyuanDispatchProjectLink,
    TaoyuanDispatchDocumentLink, TaoyuanContractPayment, OfficialDocument as Document
)
from app.schemas.taoyuan_dispatch import (
    TaoyuanProjectCreate, TaoyuanProjectUpdate, TaoyuanProject as TaoyuanProjectSchema,
    TaoyuanProjectListQuery, TaoyuanProjectListResponse,
    DispatchOrderCreate, DispatchOrderUpdate, DispatchOrder as DispatchOrderSchema,
    DispatchOrderListQuery, DispatchOrderListResponse,
    DispatchDocumentLinkCreate, DispatchDocumentLink,
    ContractPaymentCreate, ContractPaymentUpdate, ContractPayment as ContractPaymentSchema,
    ContractPaymentListResponse,
    MasterControlQuery, MasterControlResponse, MasterControlItem,
    ExcelImportRequest, ExcelImportResult,
    WORK_TYPES
)
from app.schemas.common import PaginationMeta

router = APIRouter(prefix="/taoyuan-dispatch", tags=["桃園派工管理"])


# =============================================================================
# 轄管工程清單 API
# =============================================================================

@router.post("/projects/list", response_model=TaoyuanProjectListResponse, summary="轄管工程清單列表")
async def list_taoyuan_projects(
    query: TaoyuanProjectListQuery,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """查詢轄管工程清單"""
    # 建立基本查詢
    stmt = select(TaoyuanProject)

    # 篩選條件
    conditions = []
    if query.contract_project_id:
        conditions.append(TaoyuanProject.contract_project_id == query.contract_project_id)
    if query.district:
        conditions.append(TaoyuanProject.district == query.district)
    if query.review_year:
        conditions.append(TaoyuanProject.review_year == query.review_year)
    if query.search:
        search_pattern = f"%{query.search}%"
        conditions.append(or_(
            TaoyuanProject.project_name.ilike(search_pattern),
            TaoyuanProject.sub_case_name.ilike(search_pattern),
            TaoyuanProject.case_handler.ilike(search_pattern)
        ))

    if conditions:
        stmt = stmt.where(and_(*conditions))

    # 計算總數
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # 排序
    sort_column = getattr(TaoyuanProject, query.sort_by, TaoyuanProject.id)
    if query.sort_order == "desc":
        stmt = stmt.order_by(sort_column.desc())
    else:
        stmt = stmt.order_by(sort_column.asc())

    # 分頁
    offset = (query.page - 1) * query.limit
    stmt = stmt.offset(offset).limit(query.limit)

    result = await db.execute(stmt)
    items = result.scalars().all()

    total_pages = (total + query.limit - 1) // query.limit

    return TaoyuanProjectListResponse(
        success=True,
        items=[TaoyuanProjectSchema.model_validate(item) for item in items],
        pagination=PaginationMeta(
            total=total,
            page=query.page,
            limit=query.limit,
            total_pages=total_pages,
            has_next=query.page < total_pages,
            has_prev=query.page > 1
        )
    )


@router.post("/projects/create", response_model=TaoyuanProjectSchema, summary="建立轄管工程")
async def create_taoyuan_project(
    data: TaoyuanProjectCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """建立轄管工程"""
    project = TaoyuanProject(**data.model_dump(exclude_unset=True))
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return TaoyuanProjectSchema.model_validate(project)


@router.post("/projects/{project_id}/update", response_model=TaoyuanProjectSchema, summary="更新轄管工程")
async def update_taoyuan_project(
    project_id: int,
    data: TaoyuanProjectUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """更新轄管工程"""
    result = await db.execute(select(TaoyuanProject).where(TaoyuanProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="工程不存在")

    update_data = data.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    await db.commit()
    await db.refresh(project)
    return TaoyuanProjectSchema.model_validate(project)


@router.post("/projects/{project_id}/detail", response_model=TaoyuanProjectSchema, summary="取得轄管工程詳情")
async def get_taoyuan_project_detail(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """取得轄管工程詳情"""
    result = await db.execute(select(TaoyuanProject).where(TaoyuanProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="工程不存在")
    return TaoyuanProjectSchema.model_validate(project)


@router.post("/projects/{project_id}/delete", summary="刪除轄管工程")
async def delete_taoyuan_project(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """刪除轄管工程"""
    result = await db.execute(select(TaoyuanProject).where(TaoyuanProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="工程不存在")

    await db.delete(project)
    await db.commit()
    return {"success": True, "message": "刪除成功"}


@router.post("/projects/import", response_model=ExcelImportResult, summary="匯入轄管工程清單")
async def import_taoyuan_projects(
    contract_project_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """從 Excel 匯入轄管工程清單"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="僅支援 Excel 檔案格式")

    content = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(content), sheet_name=0, header=0)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"讀取 Excel 失敗: {str(e)}")

    # 欄位對應
    column_mapping = {
        '項次': 'sequence_no',
        '審議年度': 'review_year',
        '案件類型': 'case_type',
        '行政區': 'district',
        '工程名稱': 'project_name',
        '工程起點': 'start_point',
        '工程迄點': 'end_point',
        '道路長度(公尺)': 'road_length',
        '現況路寬(公尺)': 'current_width',
        '計畫路寬(公尺)': 'planned_width',
        '公有土地(筆)': 'public_land_count',
        '私有土地(筆)': 'private_land_count',
        'RC數量(棟)': 'rc_count',
        '鐵皮屋數量(棟)': 'iron_sheet_count',
        '工程費(元)': 'construction_cost',
        '用地費(元)': 'land_cost',
        '補償費(元)': 'compensation_cost',
        '總經費(元)': 'total_cost',
        '審議結果': 'review_result',
        '都市計畫': 'urban_plan',
        '完工日期': 'completion_date',
        '提案人': 'proposer',
        '備註': 'remark',
    }

    imported_count = 0
    skipped_count = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            # 跳過空行
            project_name = row.get('工程名稱')
            if pd.isna(project_name) or not str(project_name).strip():
                skipped_count += 1
                continue

            # 建立資料
            project_data = {'contract_project_id': contract_project_id}
            for excel_col, db_col in column_mapping.items():
                if excel_col in row.index:
                    value = row[excel_col]
                    if pd.notna(value):
                        # 處理日期
                        if db_col == 'completion_date' and not pd.isna(value):
                            if hasattr(value, 'date'):
                                value = value.date()
                        # 處理數字
                        elif db_col in ['sequence_no', 'review_year', 'public_land_count',
                                       'private_land_count', 'rc_count', 'iron_sheet_count']:
                            value = int(value) if pd.notna(value) else None
                        elif db_col in ['road_length', 'current_width', 'planned_width',
                                       'construction_cost', 'land_cost', 'compensation_cost', 'total_cost']:
                            value = float(value) if pd.notna(value) else None
                        project_data[db_col] = value

            project = TaoyuanProject(**project_data)
            db.add(project)
            imported_count += 1

        except Exception as e:
            errors.append({'row': idx + 2, 'error': str(e)})

    await db.commit()

    return ExcelImportResult(
        success=True,
        message=f"匯入完成：成功 {imported_count} 筆，跳過 {skipped_count} 筆",
        total_rows=len(df),
        imported_count=imported_count,
        skipped_count=skipped_count,
        error_count=len(errors),
        errors=errors
    )


# =============================================================================
# 派工紀錄 API
# =============================================================================

@router.post("/dispatch/list", response_model=DispatchOrderListResponse, summary="派工紀錄列表")
async def list_dispatch_orders(
    query: DispatchOrderListQuery,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """查詢派工紀錄列表"""
    stmt = select(TaoyuanDispatchOrder).options(
        selectinload(TaoyuanDispatchOrder.agency_doc),
        selectinload(TaoyuanDispatchOrder.company_doc),
        selectinload(TaoyuanDispatchOrder.project_links).selectinload(TaoyuanDispatchProjectLink.project)
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

    # 轉換為回應格式
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
            'created_at': item.created_at,
            'updated_at': item.updated_at,
            'agency_doc_number': item.agency_doc.doc_number if item.agency_doc else None,
            'company_doc_number': item.company_doc.doc_number if item.company_doc else None,
            'linked_projects': [
                TaoyuanProjectSchema.model_validate(link.project)
                for link in item.project_links
            ] if item.project_links else []
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


@router.post("/dispatch/create", response_model=DispatchOrderSchema, summary="建立派工紀錄")
async def create_dispatch_order(
    data: DispatchOrderCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """建立派工紀錄"""
    # 檢查派工單號是否重複
    existing = await db.execute(
        select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.dispatch_no == data.dispatch_no)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="派工單號已存在")

    order_data = data.model_dump(exclude={'linked_project_ids'})
    order = TaoyuanDispatchOrder(**order_data)
    db.add(order)
    await db.flush()

    # 建立工程關聯
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

    # 更新工程關聯
    if data.linked_project_ids is not None:
        # 刪除舊關聯
        await db.execute(
            TaoyuanDispatchProjectLink.__table__.delete().where(
                TaoyuanDispatchProjectLink.dispatch_order_id == dispatch_id
            )
        )
        # 建立新關聯
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
        selectinload(TaoyuanDispatchOrder.project_links).selectinload(TaoyuanDispatchProjectLink.project)
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
        'created_at': order.created_at,
        'updated_at': order.updated_at,
        'agency_doc_number': order.agency_doc.doc_number if order.agency_doc else None,
        'company_doc_number': order.company_doc.doc_number if order.company_doc else None,
        'linked_projects': [
            TaoyuanProjectSchema.model_validate(link.project)
            for link in order.project_links
        ] if order.project_links else []
    }
    return DispatchOrderSchema(**order_dict)


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


# =============================================================================
# 派工-公文關聯 API
# =============================================================================

@router.post("/dispatch/{dispatch_id}/link-document", summary="關聯公文到派工單")
async def link_document_to_dispatch(
    dispatch_id: int,
    data: DispatchDocumentLinkCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
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
    current_user = Depends(require_auth)
):
    """移除派工單的公文關聯"""
    result = await db.execute(
        select(TaoyuanDispatchDocumentLink).where(
            TaoyuanDispatchDocumentLink.id == link_id,
            TaoyuanDispatchDocumentLink.dispatch_order_id == dispatch_id
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="公文關聯不存在")

    await db.delete(link)
    await db.commit()
    return {"success": True, "message": "移除關聯成功"}


@router.post("/dispatch/{dispatch_id}/documents", summary="取得派工單關聯公文")
async def get_dispatch_documents(
    dispatch_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
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


# =============================================================================
# 契金管控 API
# =============================================================================

@router.post("/payments/list", response_model=ContractPaymentListResponse, summary="契金管控列表")
async def list_contract_payments(
    contract_project_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """查詢契金管控列表"""
    stmt = select(TaoyuanContractPayment).options(
        selectinload(TaoyuanContractPayment.dispatch_order)
    )

    if contract_project_id:
        stmt = stmt.join(TaoyuanDispatchOrder).where(
            TaoyuanDispatchOrder.contract_project_id == contract_project_id
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    items = result.scalars().all()

    response_items = []
    for item in items:
        payment_dict = {
            'id': item.id,
            'dispatch_order_id': item.dispatch_order_id,
            'work_01_date': item.work_01_date,
            'work_01_amount': item.work_01_amount,
            'work_02_date': item.work_02_date,
            'work_02_amount': item.work_02_amount,
            'work_03_date': item.work_03_date,
            'work_03_amount': item.work_03_amount,
            'work_04_date': item.work_04_date,
            'work_04_amount': item.work_04_amount,
            'work_05_date': item.work_05_date,
            'work_05_amount': item.work_05_amount,
            'work_06_date': item.work_06_date,
            'work_06_amount': item.work_06_amount,
            'work_07_date': item.work_07_date,
            'work_07_amount': item.work_07_amount,
            'current_amount': item.current_amount,
            'cumulative_amount': item.cumulative_amount,
            'remaining_amount': item.remaining_amount,
            'acceptance_date': item.acceptance_date,
            'created_at': item.created_at,
            'updated_at': item.updated_at,
            'dispatch_no': item.dispatch_order.dispatch_no if item.dispatch_order else None,
            'project_name': item.dispatch_order.project_name if item.dispatch_order else None
        }
        response_items.append(ContractPaymentSchema(**payment_dict))

    total_pages = (total + limit - 1) // limit

    return ContractPaymentListResponse(
        success=True,
        items=response_items,
        pagination=PaginationMeta(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    )


@router.post("/payments/create", response_model=ContractPaymentSchema, summary="建立契金管控")
async def create_contract_payment(
    data: ContractPaymentCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """建立契金管控記錄"""
    # 檢查派工單
    order = await db.execute(
        select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.id == data.dispatch_order_id)
    )
    if not order.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="派工紀錄不存在")

    payment = TaoyuanContractPayment(**data.model_dump())
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return ContractPaymentSchema.model_validate(payment)


@router.post("/payments/{payment_id}/update", response_model=ContractPaymentSchema, summary="更新契金管控")
async def update_contract_payment(
    payment_id: int,
    data: ContractPaymentUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """更新契金管控記錄"""
    result = await db.execute(
        select(TaoyuanContractPayment).where(TaoyuanContractPayment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="契金管控記錄不存在")

    update_data = data.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(payment, key, value)

    await db.commit()
    await db.refresh(payment)
    return ContractPaymentSchema.model_validate(payment)


# =============================================================================
# 總控表 API
# =============================================================================

@router.post("/master-control", response_model=MasterControlResponse, summary="總控表查詢")
async def get_master_control(
    query: MasterControlQuery,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """查詢總控表（整合工程、派工、公文、契金資訊）"""
    # 查詢轄管工程
    stmt = select(TaoyuanProject).options(
        selectinload(TaoyuanProject.dispatch_links)
        .selectinload(TaoyuanDispatchProjectLink.dispatch_order)
        .selectinload(TaoyuanDispatchOrder.document_links)
        .selectinload(TaoyuanDispatchDocumentLink.document)
    )

    conditions = []
    if query.contract_project_id:
        conditions.append(TaoyuanProject.contract_project_id == query.contract_project_id)
    if query.district:
        conditions.append(TaoyuanProject.district == query.district)
    if query.review_year:
        conditions.append(TaoyuanProject.review_year == query.review_year)
    if query.search:
        search_pattern = f"%{query.search}%"
        conditions.append(TaoyuanProject.project_name.ilike(search_pattern))

    if conditions:
        stmt = stmt.where(and_(*conditions))

    result = await db.execute(stmt)
    projects = result.scalars().unique().all()

    items = []
    for project in projects:
        # 取得關聯的派工單
        dispatch_orders = [link.dispatch_order for link in project.dispatch_links if link.dispatch_order]

        # 收集公文歷程
        agency_docs = []
        company_docs = []
        payment_info = None
        dispatch_no = None
        case_handler = project.case_handler
        survey_unit = project.survey_unit

        for order in dispatch_orders:
            if not dispatch_no:
                dispatch_no = order.dispatch_no
            if not case_handler:
                case_handler = order.case_handler
            if not survey_unit:
                survey_unit = order.survey_unit

            # 收集公文
            for doc_link in order.document_links:
                doc = doc_link.document
                doc_info = {
                    'doc_number': doc.doc_number,
                    'doc_date': str(doc.doc_date) if doc.doc_date else None,
                    'subject': doc.subject
                }
                if doc_link.link_type == 'agency_incoming':
                    agency_docs.append(doc_info)
                else:
                    company_docs.append(doc_info)

            # 取得契金資訊
            if order.payment and not payment_info:
                payment_info = ContractPaymentSchema.model_validate(order.payment)

        item = MasterControlItem(
            id=project.id,
            project_name=project.project_name,
            sub_case_name=project.sub_case_name,
            district=project.district,
            review_year=project.review_year,
            land_agreement_status=project.land_agreement_status,
            land_expropriation_status=project.land_expropriation_status,
            building_survey_status=project.building_survey_status,
            actual_entry_date=project.actual_entry_date,
            acceptance_status=project.acceptance_status,
            dispatch_no=dispatch_no,
            case_handler=case_handler,
            survey_unit=survey_unit,
            agency_documents=agency_docs,
            company_documents=company_docs,
            payment_info=payment_info
        )
        items.append(item)

    # 計算彙總統計
    summary = {
        'total_projects': len(items),
        'total_dispatches': len(set(item.dispatch_no for item in items if item.dispatch_no)),
        'total_agency_docs': sum(len(item.agency_documents or []) for item in items),
        'total_company_docs': sum(len(item.company_documents or []) for item in items)
    }

    return MasterControlResponse(
        success=True,
        items=items,
        summary=summary
    )


# =============================================================================
# 輔助 API
# =============================================================================

@router.get("/work-types", summary="取得作業類別清單")
async def get_work_types():
    """取得作業類別清單"""
    return {"success": True, "items": WORK_TYPES}


@router.get("/districts", summary="取得行政區清單")
async def get_districts(
    contract_project_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """取得行政區清單（從轄管工程中提取）"""
    stmt = select(TaoyuanProject.district).distinct()
    if contract_project_id:
        stmt = stmt.where(TaoyuanProject.contract_project_id == contract_project_id)
    stmt = stmt.where(TaoyuanProject.district.isnot(None))

    result = await db.execute(stmt)
    districts = [row[0] for row in result.fetchall() if row[0]]

    return {"success": True, "items": sorted(districts)}

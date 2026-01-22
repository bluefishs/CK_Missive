"""
桃園派工系統 - 契金管控 API

包含端點：
- /payments/list - 契金管控列表
- /payments/create - 建立契金管控
- /payments/{payment_id}/update - 更新契金管控
- /payments/control - 契金管控展示
"""
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from .common import (
    get_async_db, require_auth,
    TaoyuanDispatchOrder, TaoyuanDispatchDocumentLink, TaoyuanContractPayment,
    ContractPaymentCreate, ContractPaymentUpdate, ContractPaymentSchema,
    ContractPaymentListResponse, PaymentControlItem, PaymentControlResponse,
    PaginationMeta
)

router = APIRouter()


async def _calculate_cumulative_payment(
    db: AsyncSession,
    contract_project_id: int,
    current_dispatch_id: int
) -> tuple[float, float]:
    """
    計算累進派工金額和剩餘金額

    Args:
        db: 資料庫連線
        contract_project_id: 承攬案件 ID
        current_dispatch_id: 當前派工單 ID

    Returns:
        (cumulative_amount, remaining_amount)
    """
    from app.extended.models import ContractProject

    # 從承攬案件動態取得總預算
    budget_result = await db.execute(
        select(ContractProject.winning_amount, ContractProject.contract_amount)
        .where(ContractProject.id == contract_project_id)
    )
    budget_row = budget_result.first()
    total_budget = float(budget_row[0] or budget_row[1] or 0) if budget_row else 0

    # 查詢所有相同承攬案件的契金記錄
    stmt = (
        select(TaoyuanContractPayment)
        .join(TaoyuanDispatchOrder, TaoyuanContractPayment.dispatch_order_id == TaoyuanDispatchOrder.id)
        .where(TaoyuanDispatchOrder.contract_project_id == contract_project_id)
        .order_by(TaoyuanDispatchOrder.dispatch_no)
    )
    result = await db.execute(stmt)
    all_payments = result.scalars().all()

    # 計算累進金額
    cumulative = 0.0
    for payment in all_payments:
        cumulative += float(payment.current_amount or 0)
        if payment.dispatch_order_id == current_dispatch_id:
            break

    remaining = total_budget - cumulative
    return cumulative, remaining


@router.post("/payments/list", response_model=ContractPaymentListResponse, summary="契金管控列表")
async def list_contract_payments(
    dispatch_order_id: Optional[int] = Body(None),
    contract_project_id: Optional[int] = Body(None),
    page: int = Body(1),
    limit: int = Body(20),
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
):
    """查詢契金管控列表"""
    stmt = select(TaoyuanContractPayment).options(
        selectinload(TaoyuanContractPayment.dispatch_order)
    )

    if dispatch_order_id:
        stmt = stmt.where(TaoyuanContractPayment.dispatch_order_id == dispatch_order_id)
    elif contract_project_id:
        stmt = stmt.join(TaoyuanDispatchOrder).where(
            TaoyuanDispatchOrder.contract_project_id == contract_project_id
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    items = result.scalars().all()

    items_to_update = []

    response_items = []
    for item in items:
        cumulative = item.cumulative_amount
        remaining = item.remaining_amount

        if (cumulative is None or cumulative == 0) and item.dispatch_order:
            cumulative, remaining = await _calculate_cumulative_payment(
                db,
                item.dispatch_order.contract_project_id,
                item.dispatch_order_id
            )
            item.cumulative_amount = cumulative
            item.remaining_amount = remaining
            items_to_update.append(item)

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
            'cumulative_amount': cumulative,
            'remaining_amount': remaining,
            'acceptance_date': item.acceptance_date,
            'created_at': item.created_at,
            'updated_at': item.updated_at,
            'dispatch_no': item.dispatch_order.dispatch_no if item.dispatch_order else None,
            'project_name': item.dispatch_order.project_name if item.dispatch_order else None
        }
        response_items.append(ContractPaymentSchema(**payment_dict))

    if items_to_update:
        await db.commit()

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
    order_result = await db.execute(
        select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.id == data.dispatch_order_id)
    )
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="派工紀錄不存在")

    payment = TaoyuanContractPayment(**data.model_dump())
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    cumulative, remaining = await _calculate_cumulative_payment(
        db, order.contract_project_id, data.dispatch_order_id
    )
    payment.cumulative_amount = cumulative
    payment.remaining_amount = remaining
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
        select(TaoyuanContractPayment)
        .options(selectinload(TaoyuanContractPayment.dispatch_order))
        .where(TaoyuanContractPayment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="契金管控記錄不存在")

    update_data = data.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(payment, key, value)

    await db.commit()
    await db.refresh(payment)

    if payment.dispatch_order:
        cumulative, remaining = await _calculate_cumulative_payment(
            db, payment.dispatch_order.contract_project_id, payment.dispatch_order_id
        )
        payment.cumulative_amount = cumulative
        payment.remaining_amount = remaining
        await db.commit()
        await db.refresh(payment)

    return ContractPaymentSchema.model_validate(payment)


@router.post("/payments/control", response_model=PaymentControlResponse, summary="契金管控展示")
async def get_payment_control(
    contract_project_id: Optional[int] = Body(None),
    page: int = Body(1),
    limit: int = Body(100),
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
):
    """取得契金管控展示資料"""
    from app.extended.models import ContractProject

    stmt = select(TaoyuanDispatchOrder).options(
        selectinload(TaoyuanDispatchOrder.document_links)
        .selectinload(TaoyuanDispatchDocumentLink.document),
        selectinload(TaoyuanDispatchOrder.payment)
    )

    if contract_project_id:
        stmt = stmt.where(TaoyuanDispatchOrder.contract_project_id == contract_project_id)

    stmt = stmt.order_by(TaoyuanDispatchOrder.dispatch_no)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    orders = result.scalars().unique().all()

    total_budget = 0
    if contract_project_id:
        budget_result = await db.execute(
            select(ContractProject.winning_amount, ContractProject.contract_amount)
            .where(ContractProject.id == contract_project_id)
        )
        budget_row = budget_result.first()
        total_budget = float(budget_row[0] or budget_row[1] or 0) if budget_row else 0

    items = []
    running_total = 0

    for order in orders:
        dispatch_date = None
        agency_docs = [
            link for link in order.document_links
            if link.link_type == 'agency_incoming' and link.document
        ]
        company_docs = [
            link for link in order.document_links
            if link.link_type == 'company_outgoing' and link.document
        ]

        agency_doc_history = None
        if agency_docs:
            sorted_agency = sorted(
                agency_docs,
                key=lambda x: x.document.doc_date if x.document and x.document.doc_date else '9999-12-31'
            )
            if sorted_agency and sorted_agency[0].document and sorted_agency[0].document.doc_date:
                dispatch_date = sorted_agency[0].document.doc_date
            history_items = []
            for link in sorted_agency:
                if link.document:
                    doc_date_str = link.document.doc_date.strftime('%Y年%m月%d日') if link.document.doc_date else ''
                    doc_number = link.document.doc_number or ''
                    if doc_date_str or doc_number:
                        history_items.append(f"{doc_date_str}_{doc_number}")
            agency_doc_history = '\n'.join(history_items) if history_items else None

        company_doc_history = None
        if company_docs:
            sorted_company = sorted(
                company_docs,
                key=lambda x: x.document.doc_date if x.document and x.document.doc_date else '9999-12-31'
            )
            history_items = []
            for link in sorted_company:
                if link.document:
                    doc_date_str = link.document.doc_date.strftime('%Y年%m月%d日') if link.document.doc_date else ''
                    doc_number = link.document.doc_number or ''
                    if doc_date_str or doc_number:
                        history_items.append(f"{doc_date_str}_{doc_number}")
            company_doc_history = '\n'.join(history_items) if history_items else None

        payment = order.payment
        current_amount = 0
        payment_data = {}

        work_type_codes = set()
        if order.work_type:
            matches = re.findall(r'(\d{2})\.', order.work_type)
            work_type_codes = set(matches)

        if payment:
            current_amount = float(payment.current_amount or 0)
            payment_data = {
                'payment_id': payment.id,
                'work_01_date': payment.work_01_date or (dispatch_date if '01' in work_type_codes else None),
                'work_01_amount': payment.work_01_amount,
                'work_02_date': payment.work_02_date or (dispatch_date if '02' in work_type_codes else None),
                'work_02_amount': payment.work_02_amount,
                'work_03_date': payment.work_03_date or (dispatch_date if '03' in work_type_codes else None),
                'work_03_amount': payment.work_03_amount,
                'work_04_date': payment.work_04_date or (dispatch_date if '04' in work_type_codes else None),
                'work_04_amount': payment.work_04_amount,
                'work_05_date': payment.work_05_date or (dispatch_date if '05' in work_type_codes else None),
                'work_05_amount': payment.work_05_amount,
                'work_06_date': payment.work_06_date or (dispatch_date if '06' in work_type_codes else None),
                'work_06_amount': payment.work_06_amount,
                'work_07_date': payment.work_07_date or (dispatch_date if '07' in work_type_codes else None),
                'work_07_amount': payment.work_07_amount,
                'current_amount': payment.current_amount,
                'acceptance_date': payment.acceptance_date,
            }
        else:
            if work_type_codes and dispatch_date:
                payment_data = {}
                for code in work_type_codes:
                    payment_data[f'work_{code}_date'] = dispatch_date

        running_total += current_amount
        cumulative_amount = running_total
        remaining_amount = total_budget - running_total

        item = PaymentControlItem(
            dispatch_order_id=order.id,
            dispatch_no=order.dispatch_no,
            project_name=order.project_name,
            work_type=order.work_type,
            sub_case_name=order.sub_case_name,
            case_handler=order.case_handler,
            survey_unit=order.survey_unit,
            cloud_folder=order.cloud_folder,
            project_folder=order.project_folder,
            deadline=order.deadline,
            dispatch_date=dispatch_date,
            agency_doc_history=agency_doc_history,
            company_doc_history=company_doc_history,
            cumulative_amount=cumulative_amount,
            remaining_amount=remaining_amount,
            **payment_data
        )
        items.append(item)

    total_pages = (total + limit - 1) // limit
    total_dispatched = running_total
    total_remaining = total_budget - running_total

    return PaymentControlResponse(
        success=True,
        items=items,
        total_budget=total_budget,
        total_dispatched=total_dispatched,
        total_remaining=total_remaining,
        pagination=PaginationMeta(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    )

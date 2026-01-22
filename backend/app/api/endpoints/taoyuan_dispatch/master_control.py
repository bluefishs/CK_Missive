"""
桃園派工系統 - 總控表與輔助 API

包含端點：
- /master-control - 總控表查詢
- /work-types - 取得作業類別清單
- /districts - 取得行政區清單
"""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from .common import (
    get_async_db, require_auth,
    TaoyuanProject, TaoyuanDispatchOrder, TaoyuanDispatchProjectLink,
    TaoyuanDispatchDocumentLink,
    MasterControlQuery, MasterControlResponse, MasterControlItem,
    ContractPaymentSchema, WORK_TYPES
)

router = APIRouter()


@router.post("/master-control", response_model=MasterControlResponse, summary="總控表查詢")
async def get_master_control(
    query: MasterControlQuery,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """查詢總控表（整合工程、派工、公文、契金資訊）"""
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
        dispatch_orders = [link.dispatch_order for link in project.dispatch_links if link.dispatch_order]

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

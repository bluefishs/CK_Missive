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

@version 2.0.0 - 重構使用 Service Layer
@date 2026-01-28
"""
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .common import (
    get_async_db, require_auth,
    DispatchOrderCreate, DispatchOrderUpdate, DispatchOrderSchema,
    DispatchOrderListQuery, DispatchOrderListResponse,
    ExcelImportResult, PaginationMeta
)
from app.services.taoyuan import DispatchOrderService

router = APIRouter()


def get_dispatch_service(db: AsyncSession = Depends(get_async_db)) -> DispatchOrderService:
    """依賴注入：取得 DispatchOrderService"""
    return DispatchOrderService(db)


@router.post("/dispatch/list", response_model=DispatchOrderListResponse, summary="派工紀錄列表")
async def list_dispatch_orders(
    query: DispatchOrderListQuery,
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth)
):
    """查詢派工紀錄列表"""
    items, total = await service.list_dispatch_orders(query)

    total_pages = (total + query.limit - 1) // query.limit

    return DispatchOrderListResponse(
        success=True,
        items=[DispatchOrderSchema(**item) for item in items],
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
async def download_dispatch_import_template(
    service: DispatchOrderService = Depends(get_dispatch_service),
):
    """下載派工紀錄 Excel 匯入範本"""
    template_bytes = service.generate_import_template()

    return StreamingResponse(
        io.BytesIO(template_bytes),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=dispatch_orders_import_template.xlsx'}
    )


@router.post("/dispatch/import", response_model=ExcelImportResult, summary="匯入派工紀錄")
async def import_dispatch_orders(
    file: UploadFile = File(...),
    contract_project_id: int = Form(...),
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth)
):
    """從 Excel 匯入派工紀錄"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="僅支援 Excel 檔案格式")

    content = await file.read()
    result = await service.import_from_excel(content, contract_project_id)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['errors'][0] if result['errors'] else '匯入失敗')

    linked_info = ""  # 匯入功能已移至服務層

    return ExcelImportResult(
        success=True,
        message=f"匯入完成：成功 {result['success_count']} 筆，跳過 {result['error_count']} 筆",
        total_rows=result['total'],
        imported_count=result['success_count'],
        skipped_count=result['error_count'],
        error_count=len(result['errors']),
        errors=result['errors'][:20]
    )


@router.post("/dispatch/next-dispatch-no", summary="取得下一個派工單號")
async def get_next_dispatch_no(
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth)
):
    """根據現有派工單號自動生成下一個單號"""
    from datetime import datetime

    current_year = datetime.now().year - 1911
    next_dispatch_no = await service.get_next_dispatch_no()

    # 從派工單號解析序號
    import re
    match = re.search(r'(\d+)$', next_dispatch_no)
    next_seq = int(match.group(1)) if match else 1

    return {
        "success": True,
        "next_dispatch_no": next_dispatch_no,
        "current_year": current_year,
        "next_sequence": next_seq
    }


@router.post("/dispatch/create", response_model=DispatchOrderSchema, summary="建立派工紀錄")
async def create_dispatch_order(
    data: DispatchOrderCreate,
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth)
):
    """建立派工紀錄"""
    order = await service.create_dispatch_order(data, auto_generate_no=False)
    return DispatchOrderSchema.model_validate(order)


@router.post("/dispatch/{dispatch_id}/update", response_model=DispatchOrderSchema, summary="更新派工紀錄")
async def update_dispatch_order(
    dispatch_id: int,
    data: DispatchOrderUpdate,
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth)
):
    """更新派工紀錄"""
    order = await service.update_dispatch_order(dispatch_id, data)
    if not order:
        raise HTTPException(status_code=404, detail="派工紀錄不存在")
    return DispatchOrderSchema.model_validate(order)


@router.post("/dispatch/{dispatch_id}/detail", response_model=DispatchOrderSchema, summary="取得派工紀錄詳情")
async def get_dispatch_order_detail(
    dispatch_id: int,
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth)
):
    """取得派工紀錄詳情"""
    order = await service.get_dispatch_order(dispatch_id, with_relations=True)
    if not order:
        raise HTTPException(status_code=404, detail="派工紀錄不存在")

    return service._to_response_dict(order)


@router.post("/dispatch/{dispatch_id}/delete", summary="刪除派工紀錄")
async def delete_dispatch_order(
    dispatch_id: int,
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth)
):
    """刪除派工紀錄"""
    success = await service.delete_dispatch_order(dispatch_id)
    if not success:
        raise HTTPException(status_code=404, detail="派工紀錄不存在")
    return {"success": True, "message": "刪除成功"}


@router.post("/dispatch/match-documents", summary="匹配公文歷程")
async def match_document_history(
    project_name: str,
    include_subject: bool = False,
    service: DispatchOrderService = Depends(get_dispatch_service),
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

    documents = await service.match_documents(project_name=project_name)

    # 分類收發文
    agency_docs = [d for d in documents if d.get('doc_type') == '收文']
    company_docs = [d for d in documents if d.get('doc_type') == '發文']

    return {
        "success": True,
        "project_name": project_name,
        "agency_documents": agency_docs,
        "company_documents": company_docs,
        "total_agency_docs": len(agency_docs),
        "total_company_docs": len(company_docs)
    }


@router.post("/dispatch/{dispatch_id}/detail-with-history", summary="取得派工紀錄詳情 (含公文歷程)")
async def get_dispatch_order_detail_with_history(
    dispatch_id: int,
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth)
):
    """取得派工紀錄詳情，並自動匹配公文歷程"""
    result = await service.get_dispatch_with_history(dispatch_id)
    if not result:
        raise HTTPException(status_code=404, detail="派工紀錄不存在")

    return {
        "success": True,
        "data": result
    }

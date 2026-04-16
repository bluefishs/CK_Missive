"""
桃園派工系統 - 派工紀錄 CRUD API

包含端點：
- /dispatch/list - 派工紀錄列表
- /dispatch/import-template - 下載匯入範本
- /dispatch/import - 匯入派工紀錄
- /dispatch/batch-relink-documents - 批次重新關聯公文
- /dispatch/enrich-from-excel - 從主表 Excel 增強匯入（價金+公文）
- /dispatch/create-document-stubs - 從原始文號反建公文 Stub + 自動關聯
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
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from sqlalchemy import select

from .common import (
    get_async_db, require_auth,
    DispatchOrderCreate, DispatchOrderUpdate, DispatchOrderSchema,
    DispatchOrderListQuery, DispatchOrderListResponse,
    ExcelImportResult, PaginationMeta,
    ContractProject,
)
from app.schemas.taoyuan.dispatch import (
    BatchSetRequest, BatchSetResponse, BatchRelinkRequest, BatchRelinkResult,
    ContractProjectListResponse, NextDispatchNoResponse,
    EnrichFromExcelResponse, DocumentStubsResponse,
    DispatchSuccessResponse, AsyncExportResponse, ExportProgressResponse,
    DocumentHistoryResponse, DispatchDetailWithHistoryResponse,
)
from app.utils.doc_helpers import is_outgoing_doc_number
from app.services.taoyuan import DispatchOrderService, DispatchExportService, ExportTaskManager
from app.services.taoyuan.dispatch_response_formatter import dispatch_to_response_dict
from app.extended.models import User

router = APIRouter()


def get_dispatch_service(db: AsyncSession = Depends(get_async_db)) -> DispatchOrderService:
    """依賴注入：取得 DispatchOrderService"""
    return DispatchOrderService(db)


@router.post("/dispatch/contract-projects", response_model=ContractProjectListResponse, summary="桃園派工承攬案件列表")
async def list_contract_projects(
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user=Depends(require_auth()),
) -> ContractProjectListResponse:
    """取得與桃園派工相關的承攬案件列表（用於專案切換下拉選單）"""
    items = await service.get_contract_projects()
    return ContractProjectListResponse(success=True, items=items)


@router.post("/dispatch/list", response_model=DispatchOrderListResponse, summary="派工紀錄列表")
async def list_dispatch_orders(
    query: DispatchOrderListQuery,
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth())
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
    current_user=Depends(require_auth()),
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
    current_user = Depends(require_auth())
):
    """從 Excel 匯入派工紀錄"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="僅支援 Excel 檔案格式")

    content = await file.read()
    result = await service.import_from_excel(content, contract_project_id)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['errors'][0] if result['errors'] else '匯入失敗')

    # 組合公文關聯統計訊息
    link_stats = result.get('doc_link_stats') or {}
    linked_count = link_stats.get('linked', 0)
    not_found_count = len(link_stats.get('not_found', []))
    link_info = ""
    if linked_count or not_found_count:
        link_info = f"，關聯 {linked_count} 筆公文"
        if not_found_count:
            link_info += f"（{not_found_count} 筆文號未找到）"

    return ExcelImportResult(
        success=True,
        message=f"匯入完成：成功 {result['success_count']} 筆，跳過 {result['error_count']} 筆{link_info}",
        total_rows=result['total'],
        imported_count=result['success_count'],
        skipped_count=result['error_count'],
        error_count=len(result['errors']),
        errors=result['errors'][:20],
        doc_link_stats=link_stats if link_stats else None,
        warnings=result.get('warnings', []),
    )


@router.post("/dispatch/batch-relink-documents", summary="批次重新關聯公文")
async def batch_relink_documents(
    request: BatchRelinkRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_auth()),
):
    """
    批次重新關聯：掃描指定案件所有有原始文號的派工單，嘗試匹配公文。

    適用場景：派工單先匯入（文號已存），公文後建檔，需補建關聯。
    """
    from app.services.taoyuan.dispatch_import_service import DispatchImportService
    import_service = DispatchImportService(db)
    result = await import_service.batch_relink_by_project(request.contract_project_id)

    not_found_count = len(result.get('not_found', []))
    msg_parts = [f"掃描 {result['total_scanned']} 筆派工單"]
    if result['newly_linked']:
        msg_parts.append(f"新建 {result['newly_linked']} 筆關聯")
    if not_found_count:
        msg_parts.append(f"{not_found_count} 筆文號未找到")
    if not result['newly_linked'] and not not_found_count:
        msg_parts.append("無需更新")

    return BatchRelinkResult(
        success=True,
        total_scanned=result['total_scanned'],
        newly_linked=result['newly_linked'],
        already_linked=result.get('already_linked', 0),
        doc_map_size=result.get('doc_map_size', 0),
        not_found=result.get('not_found', [])[:100],
        message="，".join(msg_parts),
    )


@router.post("/dispatch/enrich-from-excel", response_model=EnrichFromExcelResponse, summary="從主表 Excel 增強匯入（價金+公文）")
async def enrich_from_excel(
    file: UploadFile = File(..., description="分派案件紀錄表 Excel"),
    dispatch_no_prefix: str = Form(default="112年_派工單號", description="派工單號前綴"),
    data_start_row: int = Form(default=4, description="資料起始行 (1-based)"),
    sheet_name: str = Form(default="派工單", description="Sheet 名稱"),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_auth()),
):
    """
    從「分派案件紀錄表」主表 Excel 增強匯入：

    - 以項次 (A 欄) 為索引對應現有派工單
    - 價金匯入：7 種作業類別的派工日期/金額 (C-P) + 彙總 (S/T/U) + 驗收日期 (R)
    - 公文原始值：機關來文 (Z 欄) + 公司發文 (AB 欄)，不過度解析
    """
    from app.services.taoyuan.dispatch_enrichment_service import DispatchEnrichmentService
    content = await file.read()
    service = DispatchEnrichmentService(db)
    result = await service.enrich_from_master_excel(
        file_content=content,
        dispatch_no_prefix=dispatch_no_prefix,
        data_start_row=data_start_row,
        sheet_name=sheet_name,
    )
    return EnrichFromExcelResponse(success=True, **result)


@router.post("/dispatch/create-document-stubs", response_model=DocumentStubsResponse, summary="從原始文號反建公文 Stub + 自動關聯")
async def create_document_stubs(
    request: BatchRelinkRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_auth()),
):
    """
    從派工單已存的原始文號 (agency_doc_number_raw / company_doc_number_raw)
    反向建立 OfficialDocument Stub 記錄，並自動建立 DispatchDocumentLink 關聯。

    **不需要額外匯入公文 Excel**，直接從 DB 現有資料產生公文矩陣。
    """
    from app.services.taoyuan.dispatch_enrichment_service import DispatchEnrichmentService
    service = DispatchEnrichmentService(db)
    result = await service.create_document_stubs(request.contract_project_id)
    return DocumentStubsResponse(success=True, **result)


@router.post("/dispatch/next-dispatch-no", response_model=NextDispatchNoResponse, summary="取得下一個派工單號")
async def get_next_dispatch_no(
    contract_project_id: Optional[int] = Body(None, embed=True),
    service: DispatchOrderService = Depends(get_dispatch_service),
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth()),
) -> NextDispatchNoResponse:
    """根據承攬案件年度自動生成下一個單號（格式: {民國年}年_派工單號{NNN}）"""
    import re as re_mod
    from datetime import datetime

    roc_year = datetime.now().year - 1911  # 預設當前民國年

    # 若指定承攬案件，從專案名稱解析民國年
    # 支援 "115年度..." → 115 以及 "112至113年度..." → 112（取起始年）
    if contract_project_id:
        result = await db.execute(
            select(ContractProject.project_name)
            .where(ContractProject.id == contract_project_id)
        )
        project_name = result.scalar_one_or_none()
        if project_name:
            year_match = re_mod.search(r'(\d{2,3})(?:[-~～至]\d{2,3})?年', project_name)
            if year_match:
                roc_year = int(year_match.group(1))

    next_dispatch_no = await service.get_next_dispatch_no(year=roc_year)

    # 從派工單號解析序號
    match = re_mod.search(r'(\d+)$', next_dispatch_no)
    next_seq = int(match.group(1)) if match else 1

    return NextDispatchNoResponse(
        success=True,
        next_dispatch_no=next_dispatch_no,
        current_year=roc_year,
        next_sequence=next_seq,
    )


@router.post("/dispatch/create", response_model=DispatchOrderSchema, summary="建立派工紀錄")
async def create_dispatch_order(
    data: DispatchOrderCreate,
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth())
):
    """建立派工紀錄"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        order = await service.create_dispatch_order(data, auto_generate_no=False)
        return DispatchOrderSchema.model_validate(order)
    except IntegrityError as e:
        # 處理重複派工單號錯誤
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        logger.warning(f"[dispatch/create] IntegrityError: {error_msg}")
        if 'dispatch_no' in error_msg.lower() or 'unique' in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail=f"派工單號 '{data.dispatch_no}' 已存在，請使用其他單號"
            )
        raise HTTPException(status_code=400, detail="資料驗證失敗，請檢查輸入資料")
    except Exception as e:
        # 捕獲其他異常並記錄詳細錯誤（不向客戶端暴露內部細節）
        logger.error(f"[dispatch/create] 未預期錯誤: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail="建立派工單失敗，請稍後再試或聯繫管理員"
        )


@router.post("/dispatch/work-type/update-deadline", summary="更新作業類別交付期限")
async def update_work_type_deadline(
    work_type_id: int,
    deadline: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """設定 dispatch_work_types.deadline（per-type 交付期限）"""
    from sqlalchemy import select, update
    from app.extended.models import TaoyuanDispatchWorkType
    from datetime import date as _date

    wt = await db.execute(
        select(TaoyuanDispatchWorkType).where(TaoyuanDispatchWorkType.id == work_type_id)
    )
    wt = wt.scalar_one_or_none()
    if not wt:
        raise HTTPException(status_code=404, detail="作業類別不存在")

    wt.deadline = _date.fromisoformat(deadline) if deadline else None
    await db.commit()
    return {"success": True, "id": work_type_id, "deadline": str(wt.deadline) if wt.deadline else None}


@router.post("/dispatch/{dispatch_id}/update", response_model=DispatchOrderSchema, summary="更新派工紀錄")
async def update_dispatch_order(
    dispatch_id: int,
    data: DispatchOrderUpdate,
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth())
):
    """更新派工紀錄"""
    order = await service.update_dispatch_order(dispatch_id, data)
    if not order:
        raise HTTPException(status_code=404, detail="派工紀錄不存在")
    return DispatchOrderSchema.model_validate(order)


@router.post("/dispatch/{dispatch_id}/detail", summary="取得派工紀錄詳情")
async def get_dispatch_order_detail(
    dispatch_id: int,
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth())
):
    """取得派工紀錄詳情"""
    order = await service.get_dispatch_order(dispatch_id, with_relations=True)
    if not order:
        raise HTTPException(status_code=404, detail="派工紀錄不存在")

    # 批次查詢每筆公文被幾個派工單引用（供前端顯示跨派工單重疊）
    doc_ids = [link.document_id for link in (order.document_links or []) if link.document_id]
    doc_dispatch_counts = await service.repository.get_doc_dispatch_counts(doc_ids) if doc_ids else None
    # 查詢每筆公文在哪些派工單的作業紀錄中被引用（跨派工單未指派判定）
    doc_record_dispatches = await service.repository.get_doc_work_record_dispatches(doc_ids) if doc_ids else None

    result = dispatch_to_response_dict(order, doc_dispatch_counts=doc_dispatch_counts, doc_record_dispatches=doc_record_dispatches)
    import json as _json
    from fastapi.responses import Response
    return Response(
        content=_json.dumps(result, default=str, ensure_ascii=False),
        media_type="application/json",
    )


@router.post("/dispatch/batch-set-batch", response_model=BatchSetResponse, summary="批量設定結案批次")
async def batch_set_batch(
    data: BatchSetRequest,
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth())
):
    """批量設定多筆派工單的結案批次"""
    updated = 0
    for did in data.dispatch_ids:
        update_data = DispatchOrderUpdate(
            batch_no=data.batch_no,
            batch_label=data.batch_label,
        )
        result = await service.update_dispatch_order(did, update_data)
        if result:
            updated += 1
    return BatchSetResponse(
        success=True,
        updated_count=updated,
        message=f"已更新 {updated} 筆派工單的結案批次",
    )


@router.post("/dispatch/{dispatch_id}/delete", response_model=DispatchSuccessResponse, summary="刪除派工紀錄")
async def delete_dispatch_order(
    dispatch_id: int,
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth())
) -> DispatchSuccessResponse:
    """刪除派工紀錄"""
    success = await service.delete_dispatch_order(dispatch_id)
    if not success:
        raise HTTPException(status_code=404, detail="派工紀錄不存在")
    return DispatchSuccessResponse(success=True, message="刪除成功")


@router.post(
    "/dispatch/export/excel",
    summary="匯出派工總表 Excel",
    response_class=StreamingResponse,
)
async def export_dispatch_master_excel(
    contract_project_id: Optional[int] = Body(None, embed=True),
    work_type: Optional[str] = Body(None, embed=True),
    search: Optional[str] = Body(None, embed=True),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_auth()),
) -> StreamingResponse:
    """
    匯出所有派工單的 5 工作表 Excel 總表

    - 派工總表: 每張派工單一列摘要
    - 作業紀錄明細: 跨派工單所有作業歷程
    - 公文對照矩陣: 來文/覆文配對
    - 契金摘要: 各派工單 7 項作業金額
    - 統計摘要: 匯出範圍統計
    """
    import logging as _logging
    _logger = _logging.getLogger(__name__)

    try:
        export_service = DispatchExportService(db)
        excel_output = await export_service.export_master_matrix(
            contract_project_id=contract_project_id,
            work_type=work_type,
            search=search,
        )
    except ValueError as e:
        _logger.error(f"派工總表 Excel 匯出驗證失敗: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="匯出條件驗證失敗，請檢查篩選條件")
    except Exception:
        _logger.exception("派工總表 Excel 匯出失敗")
        raise HTTPException(status_code=500, detail="匯出失敗，請稍後再試")

    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f'dispatch_master_{timestamp}.xlsx'

    return StreamingResponse(
        excel_output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.post("/dispatch/export/excel/async", response_model=AsyncExportResponse, summary="提交非同步匯出任務")
async def submit_async_export(
    contract_project_id: Optional[int] = Body(None, embed=True),
    work_type: Optional[str] = Body(None, embed=True),
    search: Optional[str] = Body(None, embed=True),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(require_auth()),
) -> AsyncExportResponse:
    """提交非同步匯出任務，回傳 task_id 供前端輪詢進度"""
    task_id = await ExportTaskManager.submit_export(
        db=db,
        contract_project_id=contract_project_id,
        work_type=work_type,
        search=search,
    )
    return AsyncExportResponse(success=True, task_id=task_id)


@router.post("/dispatch/export/excel/progress", response_model=ExportProgressResponse, summary="查詢匯出進度")
async def get_export_progress(
    task_id: str = Body(..., embed=True),
    current_user=Depends(require_auth()),
) -> ExportProgressResponse:
    """輪詢匯出任務進度 (status/progress/total/message)"""
    progress = await ExportTaskManager.get_progress(task_id)
    if not progress:
        raise HTTPException(status_code=404, detail="任務不存在或已過期")
    return ExportProgressResponse(success=True, **progress)


@router.post(
    "/dispatch/export/excel/download",
    summary="下載非同步匯出結果",
    response_class=StreamingResponse,
)
async def download_async_export(
    task_id: str = Body(..., embed=True),
    current_user=Depends(require_auth()),
) -> StreamingResponse:
    """下載已完成的非同步匯出結果 (取後即刪)"""
    # 先檢查任務狀態
    progress = await ExportTaskManager.get_progress(task_id)
    if not progress:
        raise HTTPException(status_code=404, detail="任務不存在或已過期")
    if progress["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"任務尚未完成: {progress['status']}")

    result = await ExportTaskManager.get_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="匯出結果已過期，請重新匯出")

    filename = progress.get("filename", "dispatch_master.xlsx")

    return StreamingResponse(
        result,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.post("/dispatch/match-documents", response_model=DocumentHistoryResponse, summary="匹配公文歷程")
async def match_document_history(
    project_name: str = Body(..., embed=True),
    dispatch_id: Optional[int] = Body(None, embed=True),
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth())
) -> DocumentHistoryResponse:
    """根據工程名稱自動匹配公文歷程（含多策略關鍵字搜尋）"""
    if not project_name or not project_name.strip():
        raise HTTPException(status_code=400, detail="工程名稱不可為空")

    documents = await service.match_documents(
        project_name=project_name,
        dispatch_id=dispatch_id,
    )

    # 分類收發文（用 doc_number 前綴判斷，與 searchLinkableDocuments 一致）
    agency_docs = [d for d in documents if not is_outgoing_doc_number(d.get('doc_number'))]
    company_docs = [d for d in documents if is_outgoing_doc_number(d.get('doc_number'))]

    return DocumentHistoryResponse(
        success=True,
        project_name=project_name,
        agency_documents=agency_docs,
        company_documents=company_docs,
        total_agency_docs=len(agency_docs),
        total_company_docs=len(company_docs),
    )


@router.post("/dispatch/{dispatch_id}/detail-with-history", response_model=DispatchDetailWithHistoryResponse, summary="取得派工紀錄詳情 (含公文歷程)")
async def get_dispatch_order_detail_with_history(
    dispatch_id: int,
    service: DispatchOrderService = Depends(get_dispatch_service),
    current_user = Depends(require_auth())
) -> DispatchDetailWithHistoryResponse:
    """取得派工紀錄詳情，並自動匹配公文歷程"""
    result = await service.get_dispatch_with_history(dispatch_id)
    if not result:
        raise HTTPException(status_code=404, detail="派工紀錄不存在")

    return DispatchDetailWithHistoryResponse(success=True, data=result)

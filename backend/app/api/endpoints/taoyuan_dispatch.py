"""
桃園查估派工管理系統 API 端點
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
import pandas as pd
import io

from app.db.database import get_async_db
from app.core.dependencies import require_auth
from app.extended.models import (
    TaoyuanProject, TaoyuanDispatchOrder, TaoyuanDispatchProjectLink,
    TaoyuanDispatchDocumentLink, TaoyuanDocumentProjectLink, TaoyuanContractPayment,
    OfficialDocument as Document
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
    WORK_TYPES,
    # 統計資料
    ProjectStatistics, DispatchStatistics, PaymentStatistics, TaoyuanStatisticsResponse,
)
from app.schemas.common import PaginationMeta
import re

router = APIRouter(prefix="/taoyuan-dispatch", tags=["桃園派工管理"])


# =============================================================================
# 輔助函數：安全的數值轉換
# =============================================================================

def _safe_int(value) -> Optional[int]:
    """
    安全轉換為整數，支援特殊格式

    支援格式：
    - 純數字: 123 -> 123
    - 帶文字: '電桿3' -> 3, '3棟' -> 3
    - 加法: '3+1' -> 4
    - 範圍: '3~5' -> 4 (取平均)
    - 無法解析: None
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    try:
        # 已經是數字
        if isinstance(value, (int, float)):
            return int(value)

        value_str = str(value).strip()
        if not value_str:
            return None

        # 處理加法格式 (3+1)
        if '+' in value_str:
            parts = value_str.split('+')
            total = 0
            for part in parts:
                nums = re.findall(r'\d+', part)
                if nums:
                    total += int(nums[0])
            return total if total > 0 else None

        # 處理範圍格式 (3~5, 3-5)
        range_match = re.match(r'(\d+)\s*[~\-]\s*(\d+)', value_str)
        if range_match:
            low, high = int(range_match.group(1)), int(range_match.group(2))
            return (low + high) // 2

        # 提取第一個數字
        nums = re.findall(r'\d+', value_str)
        if nums:
            return int(nums[0])

        return None
    except (ValueError, TypeError):
        return None


def _safe_float(value) -> Optional[float]:
    """
    安全轉換為浮點數，支援特殊格式

    支援格式：
    - 純數字: 123.5 -> 123.5
    - 範圍: '9~13' -> 11.0 (取平均)
    - 帶文字: '約100' -> 100.0
    - 無法解析: None
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    try:
        # 已經是數字
        if isinstance(value, (int, float)):
            return float(value)

        value_str = str(value).strip()
        if not value_str:
            return None

        # 處理範圍格式 (9~13, 9-13)
        range_match = re.match(r'([\d.]+)\s*[~\-]\s*([\d.]+)', value_str)
        if range_match:
            low, high = float(range_match.group(1)), float(range_match.group(2))
            return (low + high) / 2

        # 提取數字（包含小數點）
        nums = re.findall(r'[\d.]+', value_str)
        if nums:
            return float(nums[0])

        return None
    except (ValueError, TypeError):
        return None


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


@router.post("/projects/import-template", summary="下載轄管工程匯入範本")
async def download_import_template():
    """
    下載 Excel 匯入範本

    範本包含所有支援的欄位及範例資料
    """
    # 定義範本欄位（與匯入時的 column_mapping 一致）
    template_columns = [
        '項次', '審議年度', '案件類型', '行政區', '工程名稱',
        '工程起點', '工程迄點', '道路長度(公尺)', '現況路寬(公尺)', '計畫路寬(公尺)',
        '公有土地(筆)', '私有土地(筆)', 'RC數量(棟)', '鐵皮屋數量(棟)',
        '工程費(元)', '用地費(元)', '補償費(元)', '總經費(元)',
        '審議結果', '都市計畫', '完工日期', '提案人', '備註'
    ]

    # 範例資料
    sample_data = [{
        '項次': 1,
        '審議年度': 114,
        '案件類型': '新建',
        '行政區': '桃園區',
        '工程名稱': '○○路拓寬工程',
        '工程起點': '中山路口',
        '工程迄點': '民生路口',
        '道路長度(公尺)': 500,
        '現況路寬(公尺)': 8,
        '計畫路寬(公尺)': 12,
        '公有土地(筆)': 5,
        '私有土地(筆)': 10,
        'RC數量(棟)': 2,
        '鐵皮屋數量(棟)': 3,
        '工程費(元)': 5000000,
        '用地費(元)': 3000000,
        '補償費(元)': 2000000,
        '總經費(元)': 10000000,
        '審議結果': '通過',
        '都市計畫': '住宅區',
        '完工日期': '2025-12-31',
        '提案人': '王○○',
        '備註': '範例資料，請刪除後填入實際資料'
    }]

    # 建立 DataFrame
    df = pd.DataFrame(sample_data, columns=template_columns)

    # 寫入 Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='轄管工程清單')

        # 調整欄寬
        worksheet = writer.sheets['轄管工程清單']
        for idx, col in enumerate(template_columns):
            # 根據欄位名稱長度設定欄寬
            width = max(len(col) * 2, 12)
            col_letter = chr(65 + idx) if idx < 26 else f'A{chr(65 + idx - 26)}'
            worksheet.column_dimensions[col_letter].width = width

    output.seek(0)

    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': 'attachment; filename=taoyuan_projects_import_template.xlsx'
        }
    )


@router.post("/projects/import", response_model=ExcelImportResult, summary="匯入轄管工程清單")
async def import_taoyuan_projects(
    file: UploadFile = File(...),
    contract_project_id: int = Form(...),
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """從 Excel 匯入轄管工程清單"""
    # 驗證承攬案件是否存在
    from app.extended.models import ContractProject
    contract_project = await db.execute(
        select(ContractProject).where(ContractProject.id == contract_project_id)
    )
    contract_project = contract_project.scalar_one_or_none()
    if not contract_project:
        raise HTTPException(
            status_code=400,
            detail=f"承攬案件 ID={contract_project_id} 不存在，請選擇有效的承攬案件"
        )

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
                        # 處理整數（支援特殊格式如 '3+1', '電桿3' 等）
                        elif db_col in ['sequence_no', 'review_year', 'public_land_count',
                                       'private_land_count', 'rc_count', 'iron_sheet_count']:
                            value = _safe_int(value)
                        # 處理浮點數（支援範圍格式如 '9~13' 取平均值）
                        elif db_col in ['road_length', 'current_width', 'planned_width',
                                       'construction_cost', 'land_cost', 'compensation_cost', 'total_cost']:
                            value = _safe_float(value)
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
        selectinload(TaoyuanDispatchOrder.project_links).selectinload(TaoyuanDispatchProjectLink.project),
        selectinload(TaoyuanDispatchOrder.document_links).selectinload(TaoyuanDispatchDocumentLink.document)
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
            'contact_note': item.contact_note,
            'created_at': item.created_at,
            'updated_at': item.updated_at,
            'agency_doc_number': item.agency_doc.doc_number if item.agency_doc else None,
            'company_doc_number': item.company_doc.doc_number if item.company_doc else None,
            'linked_projects': [
                {
                    'link_id': link.id,
                    'project_id': link.project_id,
                    **TaoyuanProjectSchema.model_validate(link.project).model_dump()
                }
                for link in item.project_links if link.project
            ] if item.project_links else [],
            'linked_documents': [
                {
                    'link_id': link.id,
                    'link_type': link.link_type,
                    'document_id': link.document_id,
                    'doc_number': link.document.doc_number if link.document else None,
                    'subject': link.document.subject if link.document else None,
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


# =============================================================================
# 派工紀錄匯入 API
# =============================================================================

@router.post("/dispatch/import-template", summary="下載派工紀錄匯入範本")
async def download_dispatch_import_template():
    """
    下載派工紀錄 Excel 匯入範本

    範本包含對應原始需求的 12 個欄位：
    - 派工單號 (必填)
    - 機關函文號
    - 工程名稱/派工事項 (必填)
    - 作業類別
    - 分案名稱/派工備註
    - 履約期限
    - 案件承辦
    - 查估單位
    - 乾坤函文號
    - 雲端資料夾
    - 專案資料夾
    - 聯絡備註
    """
    # 定義範本欄位
    template_columns = [
        '派工單號', '機關函文號', '工程名稱/派工事項', '作業類別',
        '分案名稱/派工備註', '履約期限', '案件承辦', '查估單位',
        '乾坤函文號', '雲端資料夾', '專案資料夾', '聯絡備註'
    ]

    # 範例資料
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

    # 建立 DataFrame
    df = pd.DataFrame(sample_data, columns=template_columns)

    # 寫入 Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='派工紀錄')

        # 調整欄寬
        worksheet = writer.sheets['派工紀錄']
        for idx, col in enumerate(template_columns):
            width = max(len(col) * 2.5, 15)
            col_letter = chr(65 + idx) if idx < 26 else f'A{chr(65 + idx - 26)}'
            worksheet.column_dimensions[col_letter].width = width

    output.seek(0)

    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': 'attachment; filename=dispatch_orders_import_template.xlsx'
        }
    )


@router.post("/dispatch/import", response_model=ExcelImportResult, summary="匯入派工紀錄")
async def import_dispatch_orders(
    file: UploadFile = File(...),
    contract_project_id: int = Form(...),
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """
    從 Excel 匯入派工紀錄

    支援欄位對應原始需求的 12 個欄位：
    - 派工單號 (必填，需唯一)
    - 機關函文號
    - 工程名稱/派工事項 (必填)
    - 作業類別
    - 分案名稱/派工備註
    - 履約期限 (日期格式)
    - 案件承辦
    - 查估單位
    - 乾坤函文號
    - 雲端資料夾
    - 專案資料夾
    - 聯絡備註
    """
    # 驗證承攬案件是否存在
    from app.extended.models import ContractProject
    contract_project = await db.execute(
        select(ContractProject).where(ContractProject.id == contract_project_id)
    )
    contract_project = contract_project.scalar_one_or_none()
    if not contract_project:
        raise HTTPException(
            status_code=400,
            detail=f"承攬案件 ID={contract_project_id} 不存在，請選擇有效的承攬案件"
        )

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="僅支援 Excel 檔案格式")

    content = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(content), sheet_name=0, header=0)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"讀取 Excel 失敗: {str(e)}")

    # 欄位對應 (Excel 欄位 -> 資料庫欄位)
    column_mapping = {
        '派工單號': 'dispatch_no',
        '機關函文號': 'agency_doc_number_text',  # 暫存文字，稍後處理
        '工程名稱/派工事項': 'project_name',
        '作業類別': 'work_type',
        '分案名稱/派工備註': 'sub_case_name',
        '履約期限': 'deadline',
        '案件承辦': 'case_handler',
        '查估單位': 'survey_unit',
        '乾坤函文號': 'company_doc_number_text',  # 暫存文字，稍後處理
        '雲端資料夾': 'cloud_folder',
        '專案資料夾': 'project_folder',
        '聯絡備註': 'contact_note',
    }

    imported_count = 0
    skipped_count = 0
    linked_count = 0  # 公文關聯數量
    errors = []

    for idx, row in df.iterrows():
        row_num = idx + 2  # Excel 行號 (從 2 開始，因為第 1 行是標題)
        try:
            # 取得派工單號
            dispatch_no = row.get('派工單號')
            if pd.isna(dispatch_no) or not str(dispatch_no).strip():
                errors.append({'row': row_num, 'error': '派工單號不可為空'})
                skipped_count += 1
                continue

            dispatch_no = str(dispatch_no).strip()

            # 檢查派工單號是否已存在
            existing = await db.execute(
                select(TaoyuanDispatchOrder).where(
                    TaoyuanDispatchOrder.dispatch_no == dispatch_no
                )
            )
            if existing.scalar_one_or_none():
                errors.append({'row': row_num, 'error': f'派工單號 {dispatch_no} 已存在'})
                skipped_count += 1
                continue

            # 取得工程名稱
            project_name = row.get('工程名稱/派工事項')
            if pd.isna(project_name) or not str(project_name).strip():
                errors.append({'row': row_num, 'error': '工程名稱/派工事項不可為空'})
                skipped_count += 1
                continue

            # 建立派工紀錄資料
            order_data = {
                'contract_project_id': contract_project_id,
                'dispatch_no': dispatch_no,
                'project_name': str(project_name).strip(),
            }

            # 暫存公文號資訊，稍後用於建立關聯
            agency_doc_number_text = None
            company_doc_number_text = None

            # 處理其他欄位
            for excel_col, db_col in column_mapping.items():
                if excel_col in ['派工單號', '工程名稱/派工事項']:
                    continue  # 已處理

                if excel_col in row.index:
                    value = row[excel_col]
                    if pd.notna(value) and str(value).strip():
                        # 處理日期欄位
                        if db_col == 'deadline':
                            if hasattr(value, 'date'):
                                value = value.date()
                            elif isinstance(value, str):
                                try:
                                    from datetime import datetime
                                    value = datetime.strptime(value.strip(), '%Y-%m-%d').date()
                                except ValueError:
                                    value = None
                        # 保存公文號文字，稍後處理關聯
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

            # 根據公文號查找公文 ID
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

            # 建立派工紀錄
            order = TaoyuanDispatchOrder(**order_data)
            db.add(order)
            await db.flush()  # 取得 order.id

            # 建立公文關聯記錄
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

    # 建立關聯資訊
    linked_info = f"，自動建立 {linked_count} 筆公文關聯" if linked_count > 0 else ""

    return ExcelImportResult(
        success=True,
        message=f"匯入完成：成功 {imported_count} 筆，跳過 {skipped_count} 筆{linked_info}",
        total_rows=len(df),
        imported_count=imported_count,
        skipped_count=skipped_count,
        error_count=len(errors),
        errors=errors[:20]  # 只回傳前 20 個錯誤
    )


@router.post("/dispatch/next-dispatch-no", summary="取得下一個派工單號")
async def get_next_dispatch_no(
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """
    根據現有派工單號自動生成下一個單號
    格式: 115年_派工單號001, 115年_派工單號002, ...
    """
    import re
    from datetime import datetime

    # 取得當前民國年
    current_year = datetime.now().year - 1911  # 西元轉民國

    # 查詢當年度所有派工單號
    year_prefix = f"{current_year}年_派工單號"
    result = await db.execute(
        select(TaoyuanDispatchOrder.dispatch_no)
        .where(TaoyuanDispatchOrder.dispatch_no.like(f"{year_prefix}%"))
        .order_by(TaoyuanDispatchOrder.dispatch_no.desc())
    )
    existing_nos = [r[0] for r in result.fetchall()]

    # 找出最大序號
    max_seq = 0
    pattern = re.compile(rf"^{current_year}年_派工單號(\d+)$")
    for no in existing_nos:
        if no:
            match = pattern.match(no)
            if match:
                seq = int(match.group(1))
                if seq > max_seq:
                    max_seq = seq

    # 生成下一個單號
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
        selectinload(TaoyuanDispatchOrder.project_links).selectinload(TaoyuanDispatchProjectLink.project),
        selectinload(TaoyuanDispatchOrder.document_links).selectinload(TaoyuanDispatchDocumentLink.document)
    ).where(TaoyuanDispatchOrder.id == dispatch_id)

    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="派工紀錄不存在")

    # 處理關聯公文列表
    linked_documents = []
    for link in (order.document_links or []):
        if link.document:
            linked_documents.append({
                'link_id': link.id,
                'link_type': link.link_type,
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
            {
                'link_id': link.id,
                'project_id': link.project_id,
                **TaoyuanProjectSchema.model_validate(link.project).model_dump()
            }
            for link in order.project_links if link.project
        ] if order.project_links else [],
        'linked_documents': linked_documents,
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
# 公文關聯查詢 API (以公文為主體)
# =============================================================================

@router.post("/document/{document_id}/dispatch-links", summary="查詢公文關聯的派工單")
async def get_document_dispatch_links(
    document_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
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
            # 取得關聯的機關/乾坤函文文號
            agency_doc_number = None
            company_doc_number = None
            if order.agency_doc_id:
                agency_doc = await db.execute(
                    select(Document.doc_number).where(Document.id == order.agency_doc_id)
                )
                agency_doc_number = agency_doc.scalar_one_or_none()
            if order.company_doc_id:
                company_doc = await db.execute(
                    select(Document.doc_number).where(Document.id == order.company_doc_id)
                )
                company_doc_number = company_doc.scalar_one_or_none()

            dispatch_orders.append({
                'link_id': link.id,
                'link_type': link.link_type,
                'dispatch_order_id': order.id,
                'dispatch_no': order.dispatch_no,
                'project_name': order.project_name,
                'work_type': order.work_type,
                # 完整派工資訊欄位
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
    link_type: str = 'agency_incoming',  # agency_incoming 或 company_outgoing
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
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
    current_user = Depends(require_auth)
):
    """移除公文與派工的關聯"""
    result = await db.execute(
        select(TaoyuanDispatchDocumentLink).where(
            TaoyuanDispatchDocumentLink.id == link_id,
            TaoyuanDispatchDocumentLink.document_id == document_id
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="關聯不存在")

    await db.delete(link)
    await db.commit()
    return {"success": True, "message": "移除關聯成功"}


@router.post("/documents/batch-dispatch-links", summary="批次查詢多筆公文的派工關聯")
async def get_batch_document_dispatch_links(
    document_ids: List[int],
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
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


# =============================================================================
# 以工程為主體的關聯 API
# =============================================================================

@router.post("/project/{project_id}/dispatch-links", summary="查詢工程關聯的派工單")
async def get_project_dispatch_links(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """
    以工程為主體，查詢該工程關聯的所有派工單
    用於「工程資訊」Tab 顯示已關聯的派工
    """
    result = await db.execute(
        select(TaoyuanDispatchProjectLink)
        .options(selectinload(TaoyuanDispatchProjectLink.dispatch_order))
        .where(TaoyuanDispatchProjectLink.taoyuan_project_id == project_id)
    )
    links = result.scalars().all()

    dispatch_orders = []
    for link in links:
        if link.dispatch_order:
            dispatch_orders.append({
                'link_id': link.id,
                'dispatch_order_id': link.dispatch_order.id,
                'dispatch_no': link.dispatch_order.dispatch_no,
                'project_name': link.dispatch_order.project_name,
                'work_type': link.dispatch_order.work_type,
            })

    return {
        "success": True,
        "project_id": project_id,
        "dispatch_orders": dispatch_orders,
        "total": len(dispatch_orders)
    }


@router.post("/project/{project_id}/link-dispatch", summary="將工程關聯到派工單")
async def link_dispatch_to_project(
    project_id: int,
    dispatch_order_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """
    以工程為主體，將工程關聯到指定的派工單
    """
    # 檢查工程是否存在
    proj = await db.execute(select(TaoyuanProject).where(TaoyuanProject.id == project_id))
    if not proj.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="工程不存在")

    # 檢查派工單是否存在
    order = await db.execute(
        select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.id == dispatch_order_id)
    )
    if not order.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="派工單不存在")

    # 檢查是否已存在關聯
    existing = await db.execute(
        select(TaoyuanDispatchProjectLink).where(
            TaoyuanDispatchProjectLink.taoyuan_project_id == project_id,
            TaoyuanDispatchProjectLink.dispatch_order_id == dispatch_order_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="此關聯已存在")

    # 建立關聯
    link = TaoyuanDispatchProjectLink(
        dispatch_order_id=dispatch_order_id,
        taoyuan_project_id=project_id
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)

    return {
        "success": True,
        "message": "關聯成功",
        "link_id": link.id
    }


@router.post("/project/{project_id}/unlink-dispatch/{link_id}", summary="移除工程與派工的關聯")
async def unlink_dispatch_from_project(
    project_id: int,
    link_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """移除工程與派工的關聯"""
    result = await db.execute(
        select(TaoyuanDispatchProjectLink).where(
            TaoyuanDispatchProjectLink.id == link_id,
            TaoyuanDispatchProjectLink.taoyuan_project_id == project_id
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="關聯不存在")

    await db.delete(link)
    await db.commit()
    return {"success": True, "message": "移除關聯成功"}


@router.post("/projects/batch-dispatch-links", summary="批次查詢多筆工程的派工關聯")
async def get_batch_project_dispatch_links(
    project_ids: List[int],
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """
    批次查詢多筆工程的派工關聯
    用於「工程資訊」Tab 一次載入所有工程的關聯狀態
    """
    result = await db.execute(
        select(TaoyuanDispatchProjectLink)
        .options(selectinload(TaoyuanDispatchProjectLink.dispatch_order))
        .where(TaoyuanDispatchProjectLink.taoyuan_project_id.in_(project_ids))
    )
    links = result.scalars().all()

    # 按工程 ID 分組
    links_by_project = {}
    for link in links:
        proj_id = link.taoyuan_project_id
        if proj_id not in links_by_project:
            links_by_project[proj_id] = []
        if link.dispatch_order:
            links_by_project[proj_id].append({
                'link_id': link.id,
                'dispatch_order_id': link.dispatch_order.id,
                'dispatch_no': link.dispatch_order.dispatch_no,
                'project_name': link.dispatch_order.project_name,
            })

    return {
        "success": True,
        "links": links_by_project
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


# =============================================================================
# 公文歷程匹配 API (對應原始需求欄位 14-17)
# =============================================================================

@router.post("/dispatch/match-documents", summary="匹配公文歷程")
async def match_document_history(
    project_name: str,
    include_subject: bool = False,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """
    根據工程名稱自動匹配公文歷程

    - 機關函文：doc_type = '收文' 且 subject 包含工程名稱
    - 乾坤函文：doc_type = '發文' 且 subject 包含工程名稱

    對應原始需求欄位：
    - 14. 機關函文歷程(對應工程名稱)
    - 15. 機關函文歷程(對應工程名稱+主旨)
    - 16. 乾坤函文紀錄(對應工程名稱)
    - 17. 乾坤函文歷程(對應工程名稱+主旨)
    """
    if not project_name or not project_name.strip():
        return {
            "success": False,
            "message": "工程名稱不可為空",
            "agency_documents": [],
            "company_documents": []
        }

    search_pattern = f"%{project_name.strip()}%"

    # 查詢機關函文 (收文)
    agency_stmt = select(Document).where(
        and_(
            Document.type == '收文',
            Document.subject.ilike(search_pattern)
        )
    ).order_by(Document.doc_date.desc()).limit(50)

    agency_result = await db.execute(agency_stmt)
    agency_docs = agency_result.scalars().all()

    # 查詢乾坤函文 (發文)
    company_stmt = select(Document).where(
        and_(
            Document.type == '發文',
            Document.subject.ilike(search_pattern)
        )
    ).order_by(Document.doc_date.desc()).limit(50)

    company_result = await db.execute(company_stmt)
    company_docs = company_result.scalars().all()

    # 格式化回應
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
    """
    取得派工紀錄詳情，並自動匹配公文歷程

    回應包含原始需求的 17 個欄位:
    1. 序 (id)
    2. 派工單號
    3. 機關函文號 (來自 agency_doc)
    4. 工程名稱/派工事項
    5. 作業類別
    6. 分案名稱/派工備註
    7. 履約期限
    8. 案件承辦
    9. 查估單位
    10. 乾坤函文號 (來自 company_doc)
    11. 雲端資料夾
    12. 專案資料夾
    13. 聯絡備註
    14-17. 公文歷程 (自動匹配)
    """
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

    # 基本資訊
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
            {
                'link_id': link.id,
                'project_id': link.project_id,
                **TaoyuanProjectSchema.model_validate(link.project).model_dump()
            }
            for link in order.project_links if link.project
        ] if order.project_links else []
    }

    # 自動匹配公文歷程 (如果有工程名稱)
    doc_history = {
        'agency_doc_history_by_name': [],
        'agency_doc_history_by_subject': [],
        'company_doc_history_by_name': [],
        'company_doc_history_by_subject': []
    }

    if order.project_name:
        search_pattern = f"%{order.project_name}%"

        # 機關函文歷程 (收文)
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

        # 乾坤函文歷程 (發文)
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

    # 合併回應
    order_dict.update(doc_history)

    return {
        "success": True,
        "data": order_dict
    }


# =============================================================================
# 公文-工程關聯 API (直接關聯，不經過派工單)
# =============================================================================

@router.post("/document/{document_id}/project-links", summary="查詢公文關聯的工程")
async def get_document_project_links(
    document_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """
    以公文為主體，查詢該公文直接關聯的所有工程
    用於「工程關聯」Tab 顯示已關聯的工程
    """
    result = await db.execute(
        select(TaoyuanDocumentProjectLink)
        .options(selectinload(TaoyuanDocumentProjectLink.project))
        .where(TaoyuanDocumentProjectLink.document_id == document_id)
    )
    links = result.scalars().all()

    projects = []
    for link in links:
        if link.project:
            proj = link.project
            projects.append({
                'link_id': link.id,
                'link_type': link.link_type,
                'notes': link.notes,
                'project_id': proj.id,
                'project_name': proj.project_name,
                'district': proj.district,
                'review_year': proj.review_year,
                'case_type': proj.case_type,
                'sub_case_name': proj.sub_case_name,
                'case_handler': proj.case_handler,
                'survey_unit': proj.survey_unit,
                'start_point': proj.start_point,
                'end_point': proj.end_point,
                'road_length': float(proj.road_length) if proj.road_length else None,
                'current_width': float(proj.current_width) if proj.current_width else None,
                'planned_width': float(proj.planned_width) if proj.planned_width else None,
                'review_result': proj.review_result,
                'created_at': link.created_at.isoformat() if link.created_at else None,
            })

    return {
        "success": True,
        "document_id": document_id,
        "projects": projects,
        "total": len(projects)
    }


@router.post("/document/{document_id}/link-project", summary="將公文關聯到工程")
async def link_project_to_document(
    document_id: int,
    project_id: int,
    link_type: str = 'agency_incoming',  # agency_incoming 或 company_outgoing
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """
    以公文為主體，將公文直接關聯到指定的工程

    link_type:
    - agency_incoming: 機關來函（機關發文）
    - company_outgoing: 乾坤發文
    """
    # 檢查公文是否存在
    doc = await db.execute(select(Document).where(Document.id == document_id))
    if not doc.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="公文不存在")

    # 檢查工程是否存在
    project = await db.execute(
        select(TaoyuanProject).where(TaoyuanProject.id == project_id)
    )
    if not project.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="工程不存在")

    # 檢查是否已存在關聯
    existing = await db.execute(
        select(TaoyuanDocumentProjectLink).where(
            TaoyuanDocumentProjectLink.document_id == document_id,
            TaoyuanDocumentProjectLink.taoyuan_project_id == project_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="此關聯已存在")

    # 建立關聯
    link = TaoyuanDocumentProjectLink(
        document_id=document_id,
        taoyuan_project_id=project_id,
        link_type=link_type,
        notes=notes
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)

    return {
        "success": True,
        "message": "關聯成功",
        "link_id": link.id
    }


@router.post("/document/{document_id}/unlink-project/{link_id}", summary="移除公文與工程的關聯")
async def unlink_project_from_document(
    document_id: int,
    link_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """移除公文與工程的直接關聯"""
    result = await db.execute(
        select(TaoyuanDocumentProjectLink).where(
            TaoyuanDocumentProjectLink.id == link_id,
            TaoyuanDocumentProjectLink.document_id == document_id
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="關聯不存在")

    await db.delete(link)
    await db.commit()
    return {"success": True, "message": "移除關聯成功"}


@router.post("/documents/batch-project-links", summary="批次查詢多筆公文的工程關聯")
async def get_batch_document_project_links(
    document_ids: List[int],
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """
    批次查詢多筆公文的工程關聯
    用於「工程關聯」Tab 一次載入所有公文的關聯狀態
    """
    result = await db.execute(
        select(TaoyuanDocumentProjectLink)
        .options(selectinload(TaoyuanDocumentProjectLink.project))
        .where(TaoyuanDocumentProjectLink.document_id.in_(document_ids))
    )
    links = result.scalars().all()

    # 按 document_id 分組
    grouped = {}
    for link in links:
        doc_id = link.document_id
        if doc_id not in grouped:
            grouped[doc_id] = []
        if link.project:
            proj = link.project
            grouped[doc_id].append({
                'link_id': link.id,
                'link_type': link.link_type,
                'notes': link.notes,
                'project_id': proj.id,
                'project_name': proj.project_name,
                'district': proj.district,
                'review_year': proj.review_year,
            })

    return {
        "success": True,
        "data": grouped,
        "total": len(links)
    }


# =============================================================================
# 統計 API
# =============================================================================
@router.post("/statistics", response_model=TaoyuanStatisticsResponse, summary="桃園查估派工統計資料")
async def get_statistics(
    contract_project_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """
    取得桃園查估派工統計資料

    包含：
    - 工程統計：總數、已派工、已完成、完成率
    - 派工統計：總數、有機關函文、有乾坤函文、作業類別數
    - 契金統計：本次派工金額、累進金額、剩餘金額、紀錄數
    """
    # 查詢工程統計
    project_query = select(TaoyuanProject).filter(
        TaoyuanProject.contract_project_id == contract_project_id
    )
    project_result = await db.execute(project_query)
    projects = project_result.scalars().all()

    total_projects = len(projects)
    dispatched_count = sum(1 for p in projects if p.land_agreement_status or p.building_survey_status)
    completed_count = sum(1 for p in projects if p.acceptance_status == '已驗收')
    completion_rate = round((completed_count / total_projects * 100) if total_projects > 0 else 0, 1)

    # 查詢派工統計
    dispatch_query = select(TaoyuanDispatchOrder).filter(
        TaoyuanDispatchOrder.contract_project_id == contract_project_id
    )
    dispatch_result = await db.execute(dispatch_query)
    dispatches = dispatch_result.scalars().all()

    total_dispatches = len(dispatches)
    with_agency_doc = sum(1 for d in dispatches if d.agency_doc_id is not None)
    with_company_doc = sum(1 for d in dispatches if d.company_doc_id is not None)
    work_types = set(d.work_type for d in dispatches if d.work_type)
    work_type_count = len(work_types)

    # 查詢契金統計
    # 先取得該專案所有派工單 ID
    dispatch_ids = [d.id for d in dispatches]

    if dispatch_ids:
        payment_query = select(TaoyuanContractPayment).filter(
            TaoyuanContractPayment.dispatch_order_id.in_(dispatch_ids)
        )
        payment_result = await db.execute(payment_query)
        payments = payment_result.scalars().all()
    else:
        payments = []

    total_current = sum(float(p.current_amount or 0) for p in payments)
    total_cumulative = sum(float(p.cumulative_amount or 0) for p in payments)
    total_remaining = sum(float(p.remaining_amount or 0) for p in payments)
    payment_count = len(payments)

    return TaoyuanStatisticsResponse(
        success=True,
        projects=ProjectStatistics(
            total_count=total_projects,
            dispatched_count=dispatched_count,
            completed_count=completed_count,
            completion_rate=completion_rate,
        ),
        dispatches=DispatchStatistics(
            total_count=total_dispatches,
            with_agency_doc_count=with_agency_doc,
            with_company_doc_count=with_company_doc,
            work_type_count=work_type_count,
        ),
        payments=PaymentStatistics(
            total_current_amount=total_current,
            total_cumulative_amount=total_cumulative,
            total_remaining_amount=total_remaining,
            payment_count=payment_count,
        ),
    )

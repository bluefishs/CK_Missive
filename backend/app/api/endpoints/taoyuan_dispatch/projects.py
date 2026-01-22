"""
桃園派工管理 - 轄管工程 API

@version 1.0.0
@date 2026-01-22
"""
from .common import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Body,
    StreamingResponse,
    AsyncSession,
    select,
    func,
    and_,
    or_,
    selectinload,
    pd,
    io,
    get_async_db,
    require_auth,
    TaoyuanProject,
    TaoyuanDispatchProjectLink,
    TaoyuanDocumentProjectLink,
    ContractProject,
    TaoyuanProjectCreate,
    TaoyuanProjectUpdate,
    TaoyuanProjectSchema,
    TaoyuanProjectListQuery,
    TaoyuanProjectListResponse,
    TaoyuanProjectWithLinks,
    ProjectDispatchLink,
    ProjectDocumentLink,
    ExcelImportResult,
    PaginationMeta,
    _safe_int,
    _safe_float,
)

router = APIRouter()


@router.post("/projects/list", response_model=TaoyuanProjectListResponse, summary="轄管工程清單列表")
async def list_taoyuan_projects(
    query: TaoyuanProjectListQuery,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """查詢轄管工程清單（包含派工關聯和公文關聯）"""
    stmt = select(TaoyuanProject).options(
        selectinload(TaoyuanProject.dispatch_links).selectinload(TaoyuanDispatchProjectLink.dispatch_order),
        selectinload(TaoyuanProject.document_links).selectinload(TaoyuanDocumentProjectLink.document)
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
        conditions.append(or_(
            TaoyuanProject.project_name.ilike(search_pattern),
            TaoyuanProject.sub_case_name.ilike(search_pattern),
            TaoyuanProject.case_handler.ilike(search_pattern)
        ))

    if conditions:
        stmt = stmt.where(and_(*conditions))

    count_stmt = select(func.count(TaoyuanProject.id))
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total = (await db.execute(count_stmt)).scalar() or 0

    sort_column = getattr(TaoyuanProject, query.sort_by, TaoyuanProject.id)
    if query.sort_order == "desc":
        stmt = stmt.order_by(sort_column.desc())
    else:
        stmt = stmt.order_by(sort_column.asc())

    offset = (query.page - 1) * query.limit
    stmt = stmt.offset(offset).limit(query.limit)

    result = await db.execute(stmt)
    items = result.scalars().all()

    total_pages = (total + query.limit - 1) // query.limit

    project_items = []
    for item in items:
        linked_dispatches = []
        for link in (item.dispatch_links or []):
            if link.dispatch_order:
                linked_dispatches.append(ProjectDispatchLink(
                    link_id=link.id,
                    dispatch_order_id=link.dispatch_order_id,
                    dispatch_no=link.dispatch_order.dispatch_no,
                    work_type=link.dispatch_order.work_type
                ))

        linked_documents = []
        for link in (item.document_links or []):
            if link.document:
                linked_documents.append(ProjectDocumentLink(
                    link_id=link.id,
                    document_id=link.document_id,
                    doc_number=link.document.doc_number,
                    link_type=link.link_type or 'agency_incoming'
                ))

        project_data = TaoyuanProjectSchema.model_validate(item).model_dump()
        project_data['linked_dispatches'] = linked_dispatches
        project_data['linked_documents'] = linked_documents
        project_items.append(TaoyuanProjectWithLinks(**project_data))

    return TaoyuanProjectListResponse(
        success=True,
        items=project_items,
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
    """下載 Excel 匯入範本"""
    template_columns = [
        '項次', '審議年度', '案件類型', '行政區', '工程名稱',
        '工程起點', '工程迄點', '道路長度(公尺)', '現況路寬(公尺)', '計畫路寬(公尺)',
        '公有土地(筆)', '私有土地(筆)', 'RC數量(棟)', '鐵皮屋數量(棟)',
        '工程費(元)', '用地費(元)', '補償費(元)', '總經費(元)',
        '審議結果', '都市計畫', '完工日期', '提案人', '備註'
    ]

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

    df = pd.DataFrame(sample_data, columns=template_columns)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='轄管工程清單')
        worksheet = writer.sheets['轄管工程清單']
        for idx, col in enumerate(template_columns):
            width = max(len(col) * 2, 12)
            col_letter = chr(65 + idx) if idx < 26 else f'A{chr(65 + idx - 26)}'
            worksheet.column_dimensions[col_letter].width = width

    output.seek(0)

    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=taoyuan_projects_import_template.xlsx'}
    )


@router.post("/projects/import", response_model=ExcelImportResult, summary="匯入轄管工程清單")
async def import_taoyuan_projects(
    file: UploadFile = File(...),
    contract_project_id: int = Form(...),
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth)
):
    """從 Excel 匯入轄管工程清單"""
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
            project_name = row.get('工程名稱')
            if pd.isna(project_name) or not str(project_name).strip():
                skipped_count += 1
                continue

            project_data = {'contract_project_id': contract_project_id}
            for excel_col, db_col in column_mapping.items():
                if excel_col in row.index:
                    value = row[excel_col]
                    if pd.notna(value):
                        if db_col == 'completion_date' and not pd.isna(value):
                            if hasattr(value, 'date'):
                                value = value.date()
                        elif db_col in ['sequence_no', 'review_year', 'public_land_count',
                                       'private_land_count', 'rc_count', 'iron_sheet_count']:
                            value = _safe_int(value)
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

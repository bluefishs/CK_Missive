"""
Phase 1: 工程歷程 (WorkRecord) 後端整合 - Claude CLI 自動執行腳本
==================================================================
日期: 2026-02-12
目標: 完成 TaoyuanWorkRecord 的後端整合（模型匯出、Schema、API、Migration）

執行方式:
  cd C:\GeminiCli\CK_Missive
  python claude_plant/project_dispatch_workflow/phase1_execute_backend.py

步驟:
  1. 更新 extended/models/__init__.py 匯出 TaoyuanWorkRecord
  2. 新增 schemas/taoyuan/workflow.py
  3. 更新 schemas/taoyuan/__init__.py
  4. 新增 api/endpoints/taoyuan_dispatch/workflow.py
  5. 更新 api/endpoints/taoyuan_dispatch/__init__.py
  6. 建立 Alembic migration（直接 SQL）
  7. 驗證啟動
"""
import os
import sys
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"C:\GeminiCli\CK_Missive")
BACKEND = BASE_DIR / "backend"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ============================================================
# Step 1: 更新 models/__init__.py 匯出 TaoyuanWorkRecord
# ============================================================
def step1_update_models_init():
    log("Step 1: 更新 models/__init__.py")
    init_path = BACKEND / "app" / "extended" / "models" / "__init__.py"
    content = init_path.read_text(encoding="utf-8")

    if "TaoyuanWorkRecord" in content:
        log("  → TaoyuanWorkRecord 已存在於 __init__.py，跳過")
        return

    # 在 taoyuan import 區塊加入 TaoyuanWorkRecord
    content = content.replace(
        "    TaoyuanDispatchAttachment,\n)",
        "    TaoyuanDispatchAttachment,\n    TaoyuanWorkRecord,\n)"
    )

    # 在 __all__ 的桃園派工區塊加入
    content = content.replace(
        '    "TaoyuanDispatchAttachment",\n]',
        '    "TaoyuanDispatchAttachment",\n    "TaoyuanWorkRecord",\n]'
    )

    init_path.write_text(content, encoding="utf-8")
    log("  ✅ TaoyuanWorkRecord 已加入 __init__.py")

# ============================================================
# Step 2: 新增 schemas/taoyuan/workflow.py
# ============================================================
def step2_create_workflow_schema():
    log("Step 2: 建立 workflow schema")
    schema_path = BACKEND / "app" / "schemas" / "taoyuan" / "workflow.py"

    if schema_path.exists():
        log("  → workflow.py 已存在，跳過")
        return

    schema_content = '''"""
桃園派工 - 作業歷程 Schema
對應 TaoyuanWorkRecord 模型

里程碑流程: 派工 → 會勘 → 送件 → 修正 → 審查 → 協議 → 定稿 → 結案

@version 1.0.0
@date 2026-02-12
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


# === 里程碑類型枚舉 ===
class MilestoneType(str, Enum):
    DISPATCH = "dispatch"
    SURVEY = "survey"
    SITE_INSPECTION = "site_inspection"
    SUBMIT_RESULT = "submit_result"
    REVISION = "revision"
    REVIEW_MEETING = "review_meeting"
    NEGOTIATION = "negotiation"
    FINAL_APPROVAL = "final_approval"
    BOUNDARY_SURVEY = "boundary_survey"
    CLOSED = "closed"
    OTHER = "other"


class WorkRecordStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


# === 里程碑常數 ===
MILESTONE_TYPES = [
    {"value": "dispatch", "label": "派工", "color": "green", "order": 1},
    {"value": "survey", "label": "會勘", "color": "blue", "order": 2},
    {"value": "site_inspection", "label": "查估檢視", "color": "cyan", "order": 3},
    {"value": "submit_result", "label": "送件/檢送成果", "color": "gold", "order": 4},
    {"value": "revision", "label": "修正成果", "color": "orange", "order": 5},
    {"value": "review_meeting", "label": "審查/價審會議", "color": "purple", "order": 6},
    {"value": "negotiation", "label": "協議價購", "color": "magenta", "order": 7},
    {"value": "final_approval", "label": "定稿核定", "color": "lime", "order": 8},
    {"value": "boundary_survey", "label": "土地鑑界", "color": "geekblue", "order": 9},
    {"value": "closed", "label": "結案", "color": "red", "order": 99},
    {"value": "other", "label": "其他", "color": "default", "order": 50},
]

SUBMISSION_TYPES = [
    "檢送成果(紙本+電子檔)",
    "檢送修正後成果(紙本+電子檔)",
    "檢修正後成果(協議市價-電子檔)",
    "檢送成果(電子檔)",
    "檢修正後成果",
    "檢送成果定稿版(繳送)",
    "檢修正後成果(協議市價)",
]

BATCH_CLOSE_COLORS = {
    1: "#52c41a",
    2: "#1890ff",
    3: "#faad14",
    4: "#eb2f96",
    5: "#722ed1",
}


# === 關聯公文摘要 ===
class DocBrief(BaseModel):
    """公文簡要資訊"""
    id: int
    doc_number: Optional[str] = None
    doc_date: Optional[str] = None
    subject: Optional[str] = None

    class Config:
        from_attributes = True


# === WorkRecord CRUD Schemas ===
class WorkRecordBase(BaseModel):
    """作業歷程基礎欄位"""
    dispatch_order_id: int = Field(..., description="關聯派工單 ID")
    taoyuan_project_id: Optional[int] = Field(None, description="關聯工程項次 ID")
    incoming_doc_id: Optional[int] = Field(None, description="機關來文 ID")
    outgoing_doc_id: Optional[int] = Field(None, description="公司發文 ID")
    milestone_type: MilestoneType = Field(..., description="里程碑類型")
    description: Optional[str] = Field(None, max_length=500, description="事項描述")
    submission_type: Optional[str] = Field(None, max_length=200, description="發文類別")
    record_date: date = Field(..., description="紀錄日期")
    deadline_date: Optional[date] = Field(None, description="期限日期")
    completed_date: Optional[date] = Field(None, description="完成日期")
    status: WorkRecordStatus = Field(default=WorkRecordStatus.PENDING)
    sort_order: int = Field(default=0)
    notes: Optional[str] = None


class WorkRecordCreate(WorkRecordBase):
    """新增作業歷程"""
    pass


class WorkRecordUpdate(BaseModel):
    """更新作業歷程 (部分更新)"""
    taoyuan_project_id: Optional[int] = None
    incoming_doc_id: Optional[int] = None
    outgoing_doc_id: Optional[int] = None
    milestone_type: Optional[MilestoneType] = None
    description: Optional[str] = None
    submission_type: Optional[str] = None
    record_date: Optional[date] = None
    deadline_date: Optional[date] = None
    completed_date: Optional[date] = None
    status: Optional[WorkRecordStatus] = None
    sort_order: Optional[int] = None
    notes: Optional[str] = None


class WorkRecord(WorkRecordBase):
    """作業歷程回應"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 關聯摘要
    incoming_doc: Optional[DocBrief] = None
    outgoing_doc: Optional[DocBrief] = None

    class Config:
        from_attributes = True


class WorkRecordListQuery(BaseModel):
    """作業歷程查詢參數"""
    dispatch_order_id: Optional[int] = None
    taoyuan_project_id: Optional[int] = None
    milestone_type: Optional[MilestoneType] = None
    status: Optional[WorkRecordStatus] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class WorkRecordListResponse(BaseModel):
    """作業歷程列表回應"""
    items: List[WorkRecord]
    total: int
    page: int
    page_size: int


# === 工程歷程總覽 ===
class ProjectWorkflowSummary(BaseModel):
    """工程歷程總覽"""
    project_id: int
    sequence_no: Optional[int] = None
    project_name: str
    sub_case_name: Optional[str] = None
    batch_close_no: Optional[int] = None
    case_handler: Optional[str] = None
    total_incoming_docs: int = 0
    total_outgoing_docs: int = 0
    milestones_completed: int = 0
    current_stage: Optional[str] = None
    work_records: List[WorkRecord] = []


class WorkflowSummaryResponse(BaseModel):
    """工程歷程總覽回應"""
    items: List[ProjectWorkflowSummary]
    total: int


# === 常數端點回應 ===
class WorkflowConstantsResponse(BaseModel):
    """作業歷程常數"""
    milestone_types: list = MILESTONE_TYPES
    submission_types: list = SUBMISSION_TYPES
    batch_close_colors: dict = BATCH_CLOSE_COLORS
'''
    schema_path.write_text(schema_content, encoding="utf-8")
    log("  ✅ workflow.py schema 已建立")

# ============================================================
# Step 3: 更新 schemas/taoyuan/__init__.py
# ============================================================
def step3_update_schema_init():
    log("Step 3: 更新 schemas/taoyuan/__init__.py")
    init_path = BACKEND / "app" / "schemas" / "taoyuan" / "__init__.py"
    content = init_path.read_text(encoding="utf-8")

    if "WorkRecord" in content:
        log("  → WorkRecord schemas 已存在，跳過")
        return

    # 在 Statistics import 之前加入 Workflow import
    workflow_import = """
# Workflow schemas (作業歷程)
from app.schemas.taoyuan.workflow import (
    MilestoneType,
    WorkRecordStatus,
    WorkRecordBase,
    WorkRecordCreate,
    WorkRecordUpdate,
    WorkRecord,
    WorkRecordListQuery,
    WorkRecordListResponse,
    ProjectWorkflowSummary,
    WorkflowSummaryResponse,
    WorkflowConstantsResponse,
    DocBrief,
    MILESTONE_TYPES,
    SUBMISSION_TYPES,
    BATCH_CLOSE_COLORS,
)

"""
    content = content.replace(
        "# Statistics schemas",
        workflow_import + "# Statistics schemas"
    )

    # 在 __all__ 中加入
    workflow_all = """    # Workflow (作業歷程)
    "MilestoneType",
    "WorkRecordStatus",
    "WorkRecordBase",
    "WorkRecordCreate",
    "WorkRecordUpdate",
    "WorkRecord",
    "WorkRecordListQuery",
    "WorkRecordListResponse",
    "ProjectWorkflowSummary",
    "WorkflowSummaryResponse",
    "WorkflowConstantsResponse",
    "DocBrief",
    "MILESTONE_TYPES",
    "SUBMISSION_TYPES",
    "BATCH_CLOSE_COLORS",
"""
    content = content.replace(
        '    # Statistics\n',
        workflow_all + '    # Statistics\n'
    )

    init_path.write_text(content, encoding="utf-8")
    log("  ✅ schemas/__init__.py 已更新")

# ============================================================
# Step 4: 建立 API endpoint workflow.py
# ============================================================
def step4_create_workflow_api():
    log("Step 4: 建立 workflow API endpoint")
    api_path = BACKEND / "app" / "api" / "endpoints" / "taoyuan_dispatch" / "workflow.py"

    if api_path.exists():
        log("  → workflow.py API 已存在，跳過")
        return

    api_content = '''"""
桃園派工 - 作業歷程 API
========================
工程歷程 CRUD + 總覽 + 常數 + 匯出

@version 1.0.0
@date 2026-02-12
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from typing import Optional
from datetime import date

from app.db.database import get_db
from app.extended.models import (
    TaoyuanWorkRecord,
    TaoyuanDispatchOrder,
    TaoyuanProject,
    OfficialDocument,
)
from app.schemas.taoyuan.workflow import (
    WorkRecordCreate,
    WorkRecordUpdate,
    WorkRecord as WorkRecordSchema,
    WorkRecordListQuery,
    WorkRecordListResponse,
    ProjectWorkflowSummary,
    WorkflowSummaryResponse,
    WorkflowConstantsResponse,
    DocBrief,
    MILESTONE_TYPES,
    SUBMISSION_TYPES,
    BATCH_CLOSE_COLORS,
)

router = APIRouter()


def _build_doc_brief(doc) -> Optional[DocBrief]:
    """將 OfficialDocument 轉為 DocBrief"""
    if not doc:
        return None
    return DocBrief(
        id=doc.id,
        doc_number=getattr(doc, 'doc_number', None) or getattr(doc, 'document_number', None),
        doc_date=str(getattr(doc, 'doc_date', None) or getattr(doc, 'document_date', '')),
        subject=getattr(doc, 'subject', None),
    )


def _record_to_schema(record: TaoyuanWorkRecord) -> WorkRecordSchema:
    """將 ORM 物件轉換為 Schema"""
    data = {
        "id": record.id,
        "dispatch_order_id": record.dispatch_order_id,
        "taoyuan_project_id": record.taoyuan_project_id,
        "incoming_doc_id": record.incoming_doc_id,
        "outgoing_doc_id": record.outgoing_doc_id,
        "milestone_type": record.milestone_type,
        "description": record.description,
        "submission_type": record.submission_type,
        "record_date": record.record_date,
        "deadline_date": record.deadline_date,
        "completed_date": record.completed_date,
        "status": record.status or "pending",
        "sort_order": record.sort_order or 0,
        "notes": record.notes,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "incoming_doc": _build_doc_brief(record.incoming_doc) if hasattr(record, 'incoming_doc') and record.incoming_doc else None,
        "outgoing_doc": _build_doc_brief(record.outgoing_doc) if hasattr(record, 'outgoing_doc') and record.outgoing_doc else None,
    }
    return WorkRecordSchema(**data)


# ─── 常數端點 ──────────────────────────────────────────────
@router.get("/workflow/constants", response_model=WorkflowConstantsResponse,
            summary="取得作業歷程常數")
def get_workflow_constants():
    """回傳里程碑類型、發文類別、批次色彩等常數"""
    return WorkflowConstantsResponse(
        milestone_types=MILESTONE_TYPES,
        submission_types=SUBMISSION_TYPES,
        batch_close_colors=BATCH_CLOSE_COLORS,
    )


# ─── CRUD ──────────────────────────────────────────────────
@router.get("/workflow/records", response_model=WorkRecordListResponse,
            summary="查詢作業歷程")
def list_work_records(
    dispatch_order_id: Optional[int] = Query(None),
    taoyuan_project_id: Optional[int] = Query(None),
    milestone_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(TaoyuanWorkRecord).options(
        joinedload(TaoyuanWorkRecord.incoming_doc),
        joinedload(TaoyuanWorkRecord.outgoing_doc),
    )

    if dispatch_order_id:
        query = query.filter(TaoyuanWorkRecord.dispatch_order_id == dispatch_order_id)
    if taoyuan_project_id:
        query = query.filter(TaoyuanWorkRecord.taoyuan_project_id == taoyuan_project_id)
    if milestone_type:
        query = query.filter(TaoyuanWorkRecord.milestone_type == milestone_type)
    if status:
        query = query.filter(TaoyuanWorkRecord.status == status)
    if date_from:
        query = query.filter(TaoyuanWorkRecord.record_date >= date_from)
    if date_to:
        query = query.filter(TaoyuanWorkRecord.record_date <= date_to)

    total = query.count()
    records = query.order_by(
        TaoyuanWorkRecord.record_date.asc(),
        TaoyuanWorkRecord.sort_order.asc(),
    ).offset((page - 1) * page_size).limit(page_size).all()

    return WorkRecordListResponse(
        items=[_record_to_schema(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/workflow/records", response_model=WorkRecordSchema,
             summary="新增作業歷程", status_code=201)
def create_work_record(
    data: WorkRecordCreate,
    db: Session = Depends(get_db),
):
    # 驗證派工單存在
    dispatch = db.query(TaoyuanDispatchOrder).get(data.dispatch_order_id)
    if not dispatch:
        raise HTTPException(404, f"派工單 ID {data.dispatch_order_id} 不存在")

    record = TaoyuanWorkRecord(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)

    # 重新載入關聯
    db.refresh(record, ["incoming_doc", "outgoing_doc"])
    return _record_to_schema(record)


@router.get("/workflow/records/{record_id}", response_model=WorkRecordSchema,
            summary="取得單筆作業歷程")
def get_work_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(TaoyuanWorkRecord).options(
        joinedload(TaoyuanWorkRecord.incoming_doc),
        joinedload(TaoyuanWorkRecord.outgoing_doc),
    ).filter(TaoyuanWorkRecord.id == record_id).first()

    if not record:
        raise HTTPException(404, f"作業歷程 ID {record_id} 不存在")
    return _record_to_schema(record)


@router.put("/workflow/records/{record_id}", response_model=WorkRecordSchema,
            summary="更新作業歷程")
def update_work_record(
    record_id: int,
    data: WorkRecordUpdate,
    db: Session = Depends(get_db),
):
    record = db.query(TaoyuanWorkRecord).get(record_id)
    if not record:
        raise HTTPException(404, f"作業歷程 ID {record_id} 不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(record, key, val)

    db.commit()
    db.refresh(record, ["incoming_doc", "outgoing_doc"])
    return _record_to_schema(record)


@router.delete("/workflow/records/{record_id}",
               summary="刪除作業歷程")
def delete_work_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(TaoyuanWorkRecord).get(record_id)
    if not record:
        raise HTTPException(404, f"作業歷程 ID {record_id} 不存在")

    db.delete(record)
    db.commit()
    return {"message": f"作業歷程 ID {record_id} 已刪除"}


# ─── 工程歷程總覽 ───────────────────────────────────────────
@router.get("/workflow/project-summary", response_model=WorkflowSummaryResponse,
            summary="工程歷程總覽")
def get_project_workflow_summary(
    contract_project_id: Optional[int] = Query(None),
    batch_close_no: Optional[int] = Query(None),
    district: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """取得所有工程的歷程摘要，含里程碑統計"""
    query = db.query(TaoyuanProject)

    if contract_project_id:
        query = query.filter(TaoyuanProject.contract_project_id == contract_project_id)
    if batch_close_no:
        query = query.filter(TaoyuanProject.batch_close_no == batch_close_no)
    if district:
        query = query.filter(TaoyuanProject.district == district)
    if keyword:
        query = query.filter(TaoyuanProject.project_name.contains(keyword))

    projects = query.order_by(TaoyuanProject.sequence_no.asc()).all()
    items = []

    for proj in projects:
        # 統計該工程下所有派工單的作業歷程
        records = db.query(TaoyuanWorkRecord).join(
            TaoyuanDispatchOrder
        ).filter(
            TaoyuanWorkRecord.taoyuan_project_id == proj.id
        ).options(
            joinedload(TaoyuanWorkRecord.incoming_doc),
            joinedload(TaoyuanWorkRecord.outgoing_doc),
        ).order_by(
            TaoyuanWorkRecord.record_date.asc(),
            TaoyuanWorkRecord.sort_order.asc(),
        ).all()

        incoming_count = sum(1 for r in records if r.incoming_doc_id)
        outgoing_count = sum(1 for r in records if r.outgoing_doc_id)
        completed = sum(1 for r in records if r.status == "completed")
        current = records[-1].milestone_type if records else None

        items.append(ProjectWorkflowSummary(
            project_id=proj.id,
            sequence_no=proj.sequence_no,
            project_name=proj.project_name,
            sub_case_name=proj.sub_case_name,
            batch_close_no=getattr(proj, 'batch_close_no', None),
            case_handler=proj.case_handler,
            total_incoming_docs=incoming_count,
            total_outgoing_docs=outgoing_count,
            milestones_completed=completed,
            current_stage=current,
            work_records=[_record_to_schema(r) for r in records],
        ))

    return WorkflowSummaryResponse(items=items, total=len(items))


# ─── 單一工程歷程 ──────────────────────────────────────────
@router.get("/workflow/projects/{project_id}", response_model=ProjectWorkflowSummary,
            summary="取得單一工程歷程")
def get_project_workflow(project_id: int, db: Session = Depends(get_db)):
    proj = db.query(TaoyuanProject).get(project_id)
    if not proj:
        raise HTTPException(404, f"工程 ID {project_id} 不存在")

    records = db.query(TaoyuanWorkRecord).filter(
        TaoyuanWorkRecord.taoyuan_project_id == project_id
    ).options(
        joinedload(TaoyuanWorkRecord.incoming_doc),
        joinedload(TaoyuanWorkRecord.outgoing_doc),
    ).order_by(
        TaoyuanWorkRecord.record_date.asc(),
        TaoyuanWorkRecord.sort_order.asc(),
    ).all()

    incoming_count = sum(1 for r in records if r.incoming_doc_id)
    outgoing_count = sum(1 for r in records if r.outgoing_doc_id)
    completed = sum(1 for r in records if r.status == "completed")
    current = records[-1].milestone_type if records else None

    return ProjectWorkflowSummary(
        project_id=proj.id,
        sequence_no=proj.sequence_no,
        project_name=proj.project_name,
        sub_case_name=proj.sub_case_name,
        batch_close_no=getattr(proj, 'batch_close_no', None),
        case_handler=proj.case_handler,
        total_incoming_docs=incoming_count,
        total_outgoing_docs=outgoing_count,
        milestones_completed=completed,
        current_stage=current,
        work_records=[_record_to_schema(r) for r in records],
    )
'''
    api_path.write_text(api_content, encoding="utf-8")
    log("  ✅ workflow.py API endpoint 已建立")

# ============================================================
# Step 5: 更新 taoyuan_dispatch/__init__.py 加入 workflow router
# ============================================================
def step5_update_dispatch_init():
    log("Step 5: 更新 taoyuan_dispatch/__init__.py")
    init_path = BACKEND / "app" / "api" / "endpoints" / "taoyuan_dispatch" / "__init__.py"
    content = init_path.read_text(encoding="utf-8")

    if "workflow" in content:
        log("  → workflow router 已存在，跳過")
        return

    # 加入 import
    content = content.replace(
        "from .attachments import router as attachments_router",
        "from .attachments import router as attachments_router\nfrom .workflow import router as workflow_router"
    )

    # 加入 include_router
    content = content.replace(
        'router.include_router(attachments_router)',
        'router.include_router(attachments_router)\n\n# 5. 作業歷程\nrouter.include_router(workflow_router)'
    )

    init_path.write_text(content, encoding="utf-8")
    log("  ✅ taoyuan_dispatch/__init__.py 已更新")

# ============================================================
# Step 6: 建立 Migration SQL (直接執行)
# ============================================================
def step6_run_migration():
    log("Step 6: 執行資料庫 Migration")

    # 找到 SQLite 資料庫
    import sqlite3
    db_candidates = [
        BACKEND / "documents.db",
        BACKEND / "app" / "documents.db",
    ]
    db_path = None
    for p in db_candidates:
        if p.exists():
            db_path = p
            break

    if not db_path:
        log("  ⚠️ 找不到 SQLite 資料庫，跳過 migration")
        log("  → 請手動執行 migration SQL")
        return

    log(f"  → 資料庫路徑: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 檢查 taoyuan_work_records 是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='taoyuan_work_records'")
    if cursor.fetchone():
        log("  → taoyuan_work_records 表已存在")
    else:
        cursor.execute("""
            CREATE TABLE taoyuan_work_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dispatch_order_id INTEGER NOT NULL,
                taoyuan_project_id INTEGER,
                incoming_doc_id INTEGER,
                outgoing_doc_id INTEGER,
                milestone_type VARCHAR(50) NOT NULL,
                description VARCHAR(500),
                submission_type VARCHAR(200),
                record_date DATE NOT NULL,
                deadline_date DATE,
                completed_date DATE,
                status VARCHAR(30) DEFAULT 'pending',
                sort_order INTEGER DEFAULT 0,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dispatch_order_id) REFERENCES taoyuan_dispatch_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (taoyuan_project_id) REFERENCES taoyuan_projects(id) ON DELETE CASCADE,
                FOREIGN KEY (incoming_doc_id) REFERENCES documents(id) ON DELETE SET NULL,
                FOREIGN KEY (outgoing_doc_id) REFERENCES documents(id) ON DELETE SET NULL
            )
        """)
        log("  ✅ taoyuan_work_records 表已建立")

    # 建立索引
    indexes = [
        ("ix_work_records_dispatch", "taoyuan_work_records", "dispatch_order_id"),
        ("ix_work_records_project", "taoyuan_work_records", "taoyuan_project_id"),
        ("ix_work_records_milestone", "taoyuan_work_records", "milestone_type"),
        ("ix_work_records_date", "taoyuan_work_records", "record_date"),
        ("ix_work_records_status", "taoyuan_work_records", "status"),
    ]
    for idx_name, table, col in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({col})")
        except Exception as e:
            log(f"  ⚠️ 索引 {idx_name}: {e}")

    # 擴充 taoyuan_projects 欄位
    cursor.execute("PRAGMA table_info(taoyuan_projects)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    new_cols = [
        ("batch_close_no", "INTEGER"),
        ("batch_close_date", "DATE"),
        ("company_submit_info", "VARCHAR(500)"),
    ]
    for col_name, col_type in new_cols:
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE taoyuan_projects ADD COLUMN {col_name} {col_type}")
                log(f"  ✅ 新增欄位 taoyuan_projects.{col_name}")
            except Exception as e:
                log(f"  ⚠️ 欄位 {col_name}: {e}")
        else:
            log(f"  → 欄位 {col_name} 已存在")

    conn.commit()
    conn.close()
    log("  ✅ Migration 完成")


# ============================================================
# Step 7: 驗證
# ============================================================
def step7_verify():
    log("Step 7: 驗證整合結果")

    checks = [
        (BACKEND / "app" / "extended" / "models" / "__init__.py", "TaoyuanWorkRecord"),
        (BACKEND / "app" / "schemas" / "taoyuan" / "workflow.py", "WorkRecordCreate"),
        (BACKEND / "app" / "api" / "endpoints" / "taoyuan_dispatch" / "workflow.py", "list_work_records"),
        (BACKEND / "app" / "api" / "endpoints" / "taoyuan_dispatch" / "__init__.py", "workflow_router"),
    ]

    all_ok = True
    for filepath, keyword in checks:
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            if keyword in content:
                log(f"  ✅ {filepath.name} → 包含 '{keyword}'")
            else:
                log(f"  ❌ {filepath.name} → 缺少 '{keyword}'")
                all_ok = False
        else:
            log(f"  ❌ {filepath.name} → 檔案不存在")
            all_ok = False

    if all_ok:
        log("=" * 50)
        log("🎉 Phase 1 後端整合完成！")
        log("=" * 50)
        log("")
        log("新增 API 端點：")
        log("  GET    /taoyuan-dispatch/workflow/constants")
        log("  GET    /taoyuan-dispatch/workflow/records")
        log("  POST   /taoyuan-dispatch/workflow/records")
        log("  GET    /taoyuan-dispatch/workflow/records/{id}")
        log("  PUT    /taoyuan-dispatch/workflow/records/{id}")
        log("  DELETE /taoyuan-dispatch/workflow/records/{id}")
        log("  GET    /taoyuan-dispatch/workflow/project-summary")
        log("  GET    /taoyuan-dispatch/workflow/projects/{id}")
        log("")
        log("下一步: 執行 phase2_execute_frontend.py 完成前端整合")
    else:
        log("⚠️ 部分驗證失敗，請檢查上方錯誤訊息")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    log("=" * 50)
    log("Phase 1: 工程歷程 後端整合")
    log("=" * 50)

    step1_update_models_init()
    step2_create_workflow_schema()
    step3_update_schema_init()
    step4_create_workflow_api()
    step5_update_dispatch_init()
    step6_run_migration()
    step7_verify()

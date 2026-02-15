"""
桃園派工 - 作業歷程 Schema

v2: 新增 WorkCategory enum + 鏈式欄位 + on_hold 狀態

@version 2.0.0
@date 2026-02-13
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union
from datetime import date, datetime
from enum import Enum


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


class WorkCategory(str, Enum):
    DISPATCH_NOTICE = "dispatch_notice"
    WORK_RESULT = "work_result"
    MEETING_NOTICE = "meeting_notice"
    MEETING_RECORD = "meeting_record"
    SURVEY_NOTICE = "survey_notice"
    SURVEY_RECORD = "survey_record"
    OTHER = "other"


class WorkRecordStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    ON_HOLD = "on_hold"


# === 關聯公文摘要 ===
class DocBrief(BaseModel):
    id: int
    doc_number: Optional[str] = None
    doc_date: Optional[Union[str, date]] = None
    subject: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_validator("doc_date", mode="before")
    @classmethod
    def coerce_doc_date(cls, v):
        if isinstance(v, date):
            return v.isoformat()
        return v


# === WorkRecord CRUD Schemas ===
class WorkRecordBase(BaseModel):
    dispatch_order_id: int = Field(..., description="關聯派工單 ID")
    taoyuan_project_id: Optional[int] = Field(None, description="關聯工程項次 ID")
    incoming_doc_id: Optional[int] = Field(None, description="機關來文 ID (舊格式)")
    outgoing_doc_id: Optional[int] = Field(None, description="公司發文 ID (舊格式)")
    document_id: Optional[int] = Field(None, description="關聯公文 ID (新格式)")
    parent_record_id: Optional[int] = Field(None, description="前序紀錄 ID (鏈式)")
    work_category: Optional[WorkCategory] = Field(None, description="作業類別 (新格式)")
    batch_no: Optional[int] = Field(None, description="批次序號 (第幾批結案)")
    batch_label: Optional[str] = Field(None, max_length=50, description="批次標籤")
    milestone_type: MilestoneType = Field(default=MilestoneType.OTHER, description="里程碑類型")
    description: Optional[str] = Field(None, max_length=500, description="事項描述")
    submission_type: Optional[str] = Field(None, max_length=200, description="發文類別")
    record_date: Optional[date] = Field(None, description="紀錄日期 (有 document_id 時後端自動填)")
    deadline_date: Optional[date] = Field(None, description="期限日期")
    completed_date: Optional[date] = Field(None, description="完成日期")
    status: WorkRecordStatus = Field(default=WorkRecordStatus.IN_PROGRESS)
    sort_order: int = Field(default=0)
    notes: Optional[str] = None


class WorkRecordCreate(WorkRecordBase):
    pass


class WorkRecordUpdate(BaseModel):
    taoyuan_project_id: Optional[int] = None
    incoming_doc_id: Optional[int] = None
    outgoing_doc_id: Optional[int] = None
    document_id: Optional[int] = None
    parent_record_id: Optional[int] = None
    work_category: Optional[WorkCategory] = None
    batch_no: Optional[int] = None
    batch_label: Optional[str] = None
    milestone_type: Optional[MilestoneType] = None
    description: Optional[str] = None
    submission_type: Optional[str] = None
    record_date: Optional[date] = None
    deadline_date: Optional[date] = None
    completed_date: Optional[date] = None
    status: Optional[WorkRecordStatus] = None
    sort_order: Optional[int] = None
    notes: Optional[str] = None


class WorkRecordResponse(WorkRecordBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    incoming_doc: Optional[DocBrief] = None
    outgoing_doc: Optional[DocBrief] = None
    document: Optional[DocBrief] = None
    dispatch_subject: Optional[str] = Field(None, description="派工事項（by-project 查詢時填入）")

    model_config = {"from_attributes": True}


class WorkRecordBrief(BaseModel):
    """輕量版紀錄（防止鏈式序列化無限遞迴）"""
    id: int
    doc_number: Optional[str] = None
    work_category: Optional[str] = None
    record_date: Optional[date] = None
    status: Optional[str] = None


class BatchUpdateRequest(BaseModel):
    """批量更新批次歸屬"""
    record_ids: List[int] = Field(..., description="要更新的紀錄 ID 列表", min_length=1)
    batch_no: Optional[int] = Field(None, description="批次序號（null 表示清除批次）")
    batch_label: Optional[str] = Field(None, max_length=50, description="批次標籤")


class BatchUpdateResponse(BaseModel):
    updated_count: int
    batch_no: Optional[int] = None
    batch_label: Optional[str] = None


class WorkRecordListResponse(BaseModel):
    items: List[WorkRecordResponse]
    total: int
    page: int
    page_size: int


# === 工程歷程總覽 ===
class ProjectWorkflowSummary(BaseModel):
    project_id: int
    sequence_no: Optional[int] = None
    project_name: str
    sub_case_name: Optional[str] = None
    case_handler: Optional[str] = None
    total_incoming_docs: int = 0
    total_outgoing_docs: int = 0
    milestones_completed: int = 0
    current_stage: Optional[str] = None
    work_records: List[WorkRecordResponse] = []


class WorkflowSummaryResponse(BaseModel):
    items: List[ProjectWorkflowSummary]
    total: int

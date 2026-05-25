# Phase 2: 後端 API 服務規劃
# 檔案清單與實作要點 - 供 Claude CLI 執行

> 日期: 2026-02-12

---

## 需新增/修改的檔案清單

### 2.1 Schema (Pydantic 驗證模型)
**新增: `backend/app/schemas/taoyuan/work_record.py`**

```python
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List

class WorkRecordBase(BaseModel):
    dispatch_order_id: int
    taoyuan_project_id: Optional[int] = None
    incoming_doc_id: Optional[int] = None
    outgoing_doc_id: Optional[int] = None
    milestone_type: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    submission_type: Optional[str] = Field(None, max_length=200)
    record_date: date
    deadline_date: Optional[date] = None
    completed_date: Optional[date] = None
    status: str = Field(default="pending", max_length=30)
    sort_order: int = 0
    notes: Optional[str] = None

class WorkRecordCreate(WorkRecordBase):
    pass

class WorkRecordUpdate(BaseModel):
    milestone_type: Optional[str] = None
    description: Optional[str] = None
    submission_type: Optional[str] = None
    record_date: Optional[date] = None
    deadline_date: Optional[date] = None
    completed_date: Optional[date] = None
    status: Optional[str] = None
    incoming_doc_id: Optional[int] = None
    outgoing_doc_id: Optional[int] = None
    notes: Optional[str] = None

class WorkRecordResponse(WorkRecordBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # 嵌套的簡要公文資訊
    incoming_doc_number: Optional[str] = None
    incoming_doc_date: Optional[str] = None
    outgoing_doc_number: Optional[str] = None
    outgoing_doc_date: Optional[str] = None
    
    class Config:
        from_attributes = True

class ProjectWorkflowResponse(BaseModel):
    """工程完整歷程回應"""
    project_id: int
    sequence_no: int
    project_name: str
    sub_case_name: Optional[str] = None
    batch_close_no: Optional[int] = None
    total_incoming_docs: int = 0
    total_outgoing_docs: int = 0
    milestones: List[WorkRecordResponse] = []
    current_stage: Optional[str] = None
```

### 2.2 Repository
**新增: `backend/app/repositories/taoyuan/work_record_repository.py`**

主要方法:
- `get_by_dispatch(dispatch_order_id)` - 取得派工單下所有歷程
- `get_by_project(taoyuan_project_id)` - 取得工程下所有歷程
- `get_workflow_summary(project_id)` - 工程歷程摘要含公文統計
- `create(data)` / `update(id, data)` / `delete(id)`
- `bulk_create(records)` - 批次匯入

### 2.3 Service
**新增: `backend/app/services/taoyuan/work_record_service.py`**

主要方法:
- `get_project_workflow(project_id)` - 組裝完整歷程含公文詳情
- `get_workflow_list(filters)` - 篩選查詢
- `create_record(data)` - 新增並自動排序
- `import_from_excel(file)` - Excel 匯入解析
- `export_workflow(project_ids)` - 匯出 XLSX

### 2.4 API Endpoint
**新增: `backend/app/api/endpoints/taoyuan_workflow.py`**

```python
router = APIRouter(prefix="/taoyuan/workflow", tags=["桃園作業歷程"])

@router.get("/projects/{project_id}")
async def get_project_workflow(project_id: int):
    """取得工程完整歷程"""

@router.get("/records")
async def list_work_records(
    dispatch_order_id: Optional[int] = None,
    project_id: Optional[int] = None,
    milestone_type: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """查詢作業歷程紀錄"""

@router.post("/records")
async def create_work_record(data: WorkRecordCreate):
    """新增作業歷程紀錄"""

@router.put("/records/{record_id}")
async def update_work_record(record_id: int, data: WorkRecordUpdate):
    """更新作業歷程"""

@router.delete("/records/{record_id}")
async def delete_work_record(record_id: int):
    """刪除作業歷程"""

@router.get("/summary")
async def get_workflow_summary(
    contract_project_id: Optional[int] = None,
    batch_close_no: Optional[int] = None,
):
    """工程歷程總覽（含統計）"""

@router.post("/import")
async def import_workflow(file: UploadFile):
    """從 Excel 匯入歷程"""

@router.get("/export")
async def export_workflow(project_ids: str = Query(...)):
    """匯出歷程報表 XLSX"""
```

### 2.5 路由註冊
**修改: `backend/app/api/routes.py`**
加入 `from app.api.endpoints.taoyuan_workflow import router as workflow_router`

---

## 檔案影響範圍

| 操作 | 檔案路徑 | 變更類型 |
|------|---------|---------|
| 新增 | `app/schemas/taoyuan/work_record.py` | 新檔案 |
| 修改 | `app/schemas/taoyuan/__init__.py` | 加入 export |
| 新增 | `app/repositories/taoyuan/work_record_repository.py` | 新檔案 |
| 新增 | `app/services/taoyuan/work_record_service.py` | 新檔案 |
| 新增 | `app/api/endpoints/taoyuan_workflow.py` | 新檔案 |
| 修改 | `app/api/routes.py` | 註冊路由 |
| 修改 | `app/extended/models/taoyuan.py` | 加入模型 |
| 修改 | `app/extended/models/__init__.py` | 加入 export |

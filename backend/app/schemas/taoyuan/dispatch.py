"""
桃園查估派工 - 派工紀錄 Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime

from app.schemas.common import PaginationMeta
from app.schemas.taoyuan.project import TaoyuanProject, LinkedProjectItem
from app.schemas.taoyuan.links import DispatchDocumentLink


class DispatchOrderBase(BaseModel):
    """派工紀錄基礎欄位"""
    dispatch_no: str = Field(..., max_length=50, description="派工單號")
    project_name: Optional[str] = Field(None, max_length=500, description="工程名稱/派工事項")
    work_type: Optional[str] = Field(None, max_length=50, description="作業類別")
    sub_case_name: Optional[str] = Field(None, max_length=200, description="分案名稱/派工備註")
    deadline: Optional[str] = Field(None, max_length=200, description="履約期限")
    case_handler: Optional[str] = Field(None, max_length=50, description="案件承辦")
    survey_unit: Optional[str] = Field(None, max_length=100, description="查估單位")
    cloud_folder: Optional[str] = Field(None, max_length=500, description="雲端資料夾")
    project_folder: Optional[str] = Field(None, max_length=500, description="專案資料夾")
    contact_note: Optional[str] = Field(None, max_length=500, description="聯絡備註")

    model_config = ConfigDict(from_attributes=True)


class DispatchOrderCreate(DispatchOrderBase):
    """建立派工紀錄"""
    contract_project_id: Optional[int] = Field(None, description="關聯承攬案件ID")
    agency_doc_id: Optional[int] = Field(None, description="關聯機關公文ID")
    company_doc_id: Optional[int] = Field(None, description="關聯乾坤公文ID")
    linked_project_ids: Optional[List[int]] = Field(None, description="關聯工程ID列表")


class DispatchOrderUpdate(BaseModel):
    """更新派工紀錄"""
    dispatch_no: Optional[str] = None
    contract_project_id: Optional[int] = None
    agency_doc_id: Optional[int] = None
    company_doc_id: Optional[int] = None
    project_name: Optional[str] = None
    work_type: Optional[str] = None
    sub_case_name: Optional[str] = None
    deadline: Optional[str] = None
    case_handler: Optional[str] = None
    survey_unit: Optional[str] = None
    cloud_folder: Optional[str] = None
    project_folder: Optional[str] = None
    contact_note: Optional[str] = None
    linked_project_ids: Optional[List[int]] = None


class DispatchOrder(DispatchOrderBase):
    """派工紀錄完整資訊"""
    id: int
    contract_project_id: Optional[int] = None
    agency_doc_id: Optional[int] = None
    company_doc_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 關聯資訊（用於列表顯示）
    agency_doc_number: Optional[str] = Field(None, description="機關函文號")
    company_doc_number: Optional[str] = Field(None, description="乾坤函文號")
    attachment_count: int = Field(0, description="附件數量")
    linked_projects: Optional[List[LinkedProjectItem]] = Field(None, description="關聯工程 (含 link_id, project_id)")
    linked_documents: Optional[List[DispatchDocumentLink]] = Field(None, description="關聯公文")


class DispatchOrderListQuery(BaseModel):
    """派工紀錄列表查詢參數"""
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=1000, description="每頁筆數")
    contract_project_id: Optional[int] = Field(None, description="關聯承攬案件ID")
    work_type: Optional[str] = Field(None, description="作業類別")
    search: Optional[str] = Field(None, description="搜尋關鍵字")
    sort_by: str = Field(default="id", description="排序欄位")
    sort_order: str = Field(default="desc", description="排序方向")


class DispatchOrderListResponse(BaseModel):
    """派工紀錄列表回應"""
    success: bool = True
    items: List[DispatchOrder] = []
    pagination: PaginationMeta

    model_config = ConfigDict(from_attributes=True)


# 公文歷程匹配 Schemas
class DocumentHistoryItem(BaseModel):
    """公文歷程項目"""
    id: int = Field(..., description="公文ID")
    doc_number: Optional[str] = Field(None, description="文號")
    doc_date: Optional[date] = Field(None, description="日期")
    subject: Optional[str] = Field(None, description="主旨")
    sender: Optional[str] = Field(None, description="發文單位")
    receiver: Optional[str] = Field(None, description="收文單位")
    doc_type: Optional[str] = Field(None, description="公文類型 (收文/發文)")
    match_type: Optional[str] = Field(None, description="匹配方式 (project_name/subject)")

    model_config = ConfigDict(from_attributes=True)


class DocumentHistoryMatchRequest(BaseModel):
    """公文歷程匹配請求"""
    project_name: str = Field(..., description="工程名稱 (用於匹配)")
    include_subject: bool = Field(default=False, description="是否包含主旨匹配")


class DocumentHistoryResponse(BaseModel):
    """公文歷程匹配回應"""
    success: bool = True
    project_name: str = Field(..., description="查詢的工程名稱")
    agency_documents: List[DocumentHistoryItem] = Field(default_factory=list, description="機關函文歷程 (收文)")
    company_documents: List[DocumentHistoryItem] = Field(default_factory=list, description="乾坤函文歷程 (發文)")
    total_agency_docs: int = Field(0, description="機關函文總數")
    total_company_docs: int = Field(0, description="乾坤函文總數")

    model_config = ConfigDict(from_attributes=True)


class DispatchOrderWithHistory(DispatchOrder):
    """派工紀錄 (含公文歷程)"""
    agency_doc_history_by_name: Optional[List[DocumentHistoryItem]] = Field(
        None, description="機關函文歷程(對應工程名稱)"
    )
    agency_doc_history_by_subject: Optional[List[DocumentHistoryItem]] = Field(
        None, description="機關函文歷程(對應工程名稱+主旨)"
    )
    company_doc_history_by_name: Optional[List[DocumentHistoryItem]] = Field(
        None, description="乾坤函文紀錄(對應工程名稱)"
    )
    company_doc_history_by_subject: Optional[List[DocumentHistoryItem]] = Field(
        None, description="乾坤函文歷程(對應工程名稱+主旨)"
    )


# 派工單附件 Schemas
class DispatchAttachmentBase(BaseModel):
    """派工單附件基礎欄位"""
    file_name: str = Field(..., description="儲存檔案名稱")
    original_name: Optional[str] = Field(None, description="原始檔案名稱")
    file_size: int = Field(..., description="檔案大小(bytes)")
    mime_type: Optional[str] = Field(None, description="MIME類型")
    storage_type: Optional[str] = Field(default='local', description="儲存類型: local/network/s3")
    checksum: Optional[str] = Field(None, description="SHA256校驗碼")

    model_config = ConfigDict(from_attributes=True)


class DispatchAttachment(DispatchAttachmentBase):
    """派工單附件完整資訊"""
    id: int
    dispatch_order_id: int
    file_path: Optional[str] = Field(None, description="檔案路徑")
    uploaded_by: Optional[int] = Field(None, description="上傳者ID")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 相容前端欄位名稱
    @property
    def filename(self) -> str:
        return self.file_name

    @property
    def original_filename(self) -> Optional[str]:
        return self.original_name

    @property
    def content_type(self) -> Optional[str]:
        return self.mime_type


class DispatchAttachmentListResponse(BaseModel):
    """派工單附件列表回應"""
    success: bool = True
    dispatch_order_id: int
    total: int
    attachments: List[DispatchAttachment]

    model_config = ConfigDict(from_attributes=True)


class DispatchAttachmentUploadResult(BaseModel):
    """派工單附件上傳結果"""
    success: bool
    message: str
    files: List[dict] = Field(default_factory=list, description="上傳成功的檔案列表")
    errors: List[str] = Field(default_factory=list, description="上傳失敗的錯誤訊息")

    model_config = ConfigDict(from_attributes=True)


class DispatchAttachmentDeleteResult(BaseModel):
    """派工單附件刪除結果"""
    success: bool
    message: str

    model_config = ConfigDict(from_attributes=True)


class DispatchAttachmentVerifyResult(BaseModel):
    """派工單附件驗證結果"""
    success: bool
    message: str
    valid: bool = Field(..., description="檔案完整性是否有效")
    expected_checksum: Optional[str] = Field(None, description="預期的校驗碼")
    actual_checksum: Optional[str] = Field(None, description="實際的校驗碼")

    model_config = ConfigDict(from_attributes=True)

"""
收發文功能 Pydantic 資料結構 (優化後)
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

class DocumentCategory(str, Enum):
    """公文分類 (用於篩選)"""
    ADMIN = "行政"
    BUSINESS = "業務"
    # 根據實際業務需求添加更多分類

class DocumentStatus(str, Enum):
    """公文狀態"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"
    PENDING = "待處理" # 新增狀態
    
class DocumentType(str, Enum):
    """公文類型 - 與資料庫實際值對齊"""
    LETTER = "函"
    SEND = "發文"
    RECEIVE = "收文"
    MEETING_NOTICE = "開會通知單"
    SURVEY_NOTICE = "會勘通知單"

class DocumentBase(BaseModel):
    """公文基礎資料結構 - 與 OfficialDocument 模型對齊"""
    doc_number: str = Field(..., description="公文文號")
    doc_type: DocumentType = Field(..., description="公文類型 (收文/發文)") # 修正: 使用 Enum
    subject: str = Field(..., description="主旨")
    sender: Optional[str] = Field(None, description="發文機關")
    receiver: Optional[str] = Field(None, description="收文機關")
    doc_date: Optional[date] = Field(None, description="公文日期")
    receive_date: Optional[date] = Field(None, description="收文日期") # 修正: 類型
    send_date: Optional[date] = Field(None, description="發文日期") # 修正: 類型
    status: str = Field(default="待處理", description="處理狀態") # 修正: 預設值
    
    # 新增欄位以匹配 OfficialDocument 模型
    category: Optional[DocumentCategory] = Field(None, description="公文分類") # 修正: 使用 Enum
    contract_case: Optional[str] = Field(None, description="承攬案件名稱或編號")
    doc_word: Optional[str] = Field(None, description="公文字 (例如：府、院、部)")
    doc_class: Optional[str] = Field(None, description="公文類別 (例如：函、令、公告)")
    assignee: Optional[str] = Field(None, description="承辦人")
    user_confirm: Optional[bool] = Field(False, description="使用者確認狀態")
    auto_serial: Optional[int] = Field(None, description="自動生成流水號 (用於 CSV 匯入)")
    creator: Optional[str] = Field(None, description="建立者")
    is_deleted: Optional[bool] = Field(False, description="是否已軟刪除")
    notes: Optional[str] = Field(None, description="備註")
    priority_level: Optional[str] = Field("普通", description="速別 (例如：普通, 速件, 最速件)") # 修正: 預設值
    content: Optional[str] = Field(None, description="公文內容摘要") # 修正: 欄位名稱

class DocumentCreate(DocumentBase):
    """建立公文資料結構"""
    pass

class DocumentUpdate(BaseModel):
    """更新公文資料結構 - 僅包含可更新的欄位"""
    doc_number: Optional[str] = None
    doc_type: Optional[DocumentType] = None # 修正: 使用 Enum
    subject: Optional[str] = None
    sender: Optional[str] = None # 修正: 欄位名稱
    receiver: Optional[str] = None # 修正: 欄位名稱
    doc_date: Optional[date] = None
    receive_date: Optional[date] = None # 修正: 類型
    send_date: Optional[date] = None # 修正: 類型
    status: Optional[str] = None
    category: Optional[DocumentCategory] = None # 修正: 使用 Enum
    contract_case: Optional[str] = None
    doc_word: Optional[str] = None
    doc_class: Optional[str] = None
    assignee: Optional[str] = None
    user_confirm: Optional[bool] = None
    auto_serial: Optional[int] = None
    creator: Optional[str] = None
    is_deleted: Optional[bool] = None
    notes: Optional[str] = None
    priority_level: Optional[str] = None
    content: Optional[str] = None

class DocumentResponse(DocumentBase):
    """公文回應資料結構 - 包含資料庫自動生成欄位"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentFilter(BaseModel):
    """公文篩選條件 - 與 OfficialDocument 模型對齊"""
    doc_type: Optional[DocumentType] = Field(None, description="公文類型篩選") # 修正: 欄位名稱和類型
    year: Optional[int] = Field(None, description="年度篩選")
    doc_word: Optional[str] = Field(None, description="公文字篩選") # 修正: 欄位名稱
    sender: Optional[str] = Field(None, description="發文機關篩選")
    receiver: Optional[str] = Field(None, description="收文機關篩選")
    contract_case: Optional[str] = Field(None, description="承攬案件篩選") # 修正: 欄位名稱
    category: Optional[str] = Field(None, description="公文分類篩選 (send/receive)") # 新增
    keyword: Optional[str] = Field(None, description="關鍵字搜尋 (主旨或文號)")
    date_from: Optional[date] = Field(None, description="公文日期從")
    date_to: Optional[date] = Field(None, description="公文日期到")
    status: Optional[str] = Field(None, description="處理狀態篩選")
    assignee: Optional[str] = Field(None, description="承辦人篩選")
    creator: Optional[str] = Field(None, description="建立者篩選")
    is_deleted: Optional[bool] = Field(None, description="是否已刪除篩選")

    sort_by: Optional[str] = Field("id", description="排序欄位") # 修正: 預設值
    sort_order: Optional[str] = Field("desc", description="排序順序 (asc/desc)") # 修正: 預設值

class DocumentImportData(BaseModel):
    """匯入公文資料 - 與 OfficialDocument 模型對齊"""
    doc_number: str = Field(..., min_length=1, description="公文文號（必填）")
    doc_type: DocumentType = Field(..., description="公文類型（必填）") # 修正: 使用 Enum
    subject: str = Field(..., min_length=1, description="主旨（必填）")
    sender: Optional[str] = Field(None, description="發文機關")
    receiver: Optional[str] = Field(None, description="收文機關")
    doc_date: Optional[date] = Field(None, description="公文日期") # 修正: 類型
    receive_date: Optional[date] = Field(None, description="收文日期") # 修正: 類型
    send_date: Optional[date] = Field(None, description="發文日期") # 修正: 類型
    status: Optional[str] = Field(None, description="處理狀態")
    category: Optional[DocumentCategory] = Field(None, description="公文分類") # 修正: 使用 Enum
    contract_case: Optional[str] = Field(None, description="承攬案件")
    doc_word: Optional[str] = Field(None, description="字")
    doc_class: Optional[str] = Field(None, description="類別")
    assignee: Optional[str] = Field(None, description="承辦人")
    user_confirm: Optional[bool] = Field(None, description="使用者確認")
    auto_serial: Optional[int] = Field(None, description="自動流水號")
    creator: Optional[str] = Field(None, description="建立者")
    is_deleted: Optional[bool] = Field(None, description="是否刪除")
    notes: Optional[str] = Field(None, description="備註")
    priority_level: Optional[str] = Field(None, description="速別")
    content: Optional[str] = Field(None, description="公文內容摘要")
    
    # 移除 @field_validator('category', mode='before')，因為現在使用 DocumentType Enum
    # 移除 @field_validator('doc_number', 'doc_type', 'subject', mode='before')，因為 Pydantic 內建驗證更強大

class DocumentImportResult(BaseModel):
    """匯入結果"""
    total_rows: int = Field(..., description="總行數")
    success_count: int = Field(..., description="成功匯入數量")
    skipped_count: int = Field(default=0, description="跳過數量")
    error_count: int = Field(..., description="錯誤數量")
    errors: List[str] = Field(default=[], description="錯誤訊息")
    processing_time: float = Field(..., description="處理時間(秒)")

class DocumentListResponse(BaseModel):
    """公文列表回應"""
    documents: List[DocumentResponse]
    total: int
    page: int
    per_page: int
    pages: int
    
class DocumentStats(BaseModel):
    """公文統計"""
    total_documents: int
    receive_count: int
    send_count: int
    current_year_count: int
    last_auto_serial: Optional[int] = None
    last_serial_number: Optional[int] = None

class ExportRequest(BaseModel):
    """匯出請求"""
    filters: Optional[DocumentFilter] = None
    format: str = Field(default="xlsx", description="匯出格式")
    filename: Optional[str] = None

class DocumentSearchRequest(BaseModel):
    """
    公文複雜查詢請求體
    用於支援多條件、更靈活的組合查詢
    """
    doc_numbers: Optional[List[str]] = Field(None, description="公文文號列表")
    doc_types: Optional[List[DocumentType]] = Field(None, description="公文類型列表 (收文/發文)")
    subjects: Optional[List[str]] = Field(None, description="主旨關鍵字列表")
    senders: Optional[List[str]] = Field(None, description="發文機關列表")
    receivers: Optional[List[str]] = Field(None, description="收文機關列表")
    doc_date_from: Optional[date] = Field(None, description="公文日期從")
    doc_date_to: Optional[date] = Field(None, description="公文日期到")
    receive_date_from: Optional[date] = Field(None, description="收文日期從")
    receive_date_to: Optional[date] = Field(None, description="收文日期到")
    send_date_from: Optional[date] = Field(None, description="發文日期從")
    send_date_to: Optional[date] = Field(None, description="發文日期到")
    statuses: Optional[List[str]] = Field(None, description="處理狀態列表")
    assignees: Optional[List[str]] = Field(None, description="承辦人列表")
    creators: Optional[List[str]] = Field(None, description="建立者列表")
    is_deleted: Optional[bool] = Field(None, description="是否已軟刪除")
    
    # 模糊搜尋關鍵字 (可同時搜尋多個欄位)
    keyword: Optional[str] = Field(None, description="模糊搜尋關鍵字 (主旨、文號、內容、備註)")

    # 分頁和排序
    skip: int = Field(0, ge=0, description="跳過筆數")
    limit: int = Field(50, ge=1, le=2000, description="取得筆數")
    sort_by: Optional[str] = Field("id", description="排序欄位")
    sort_order: Optional[str] = Field("desc", description="排序順序 (asc/desc)")
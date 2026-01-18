"""
收發文功能 Pydantic 資料結構 (優化後)

使用統一回應格式
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

from app.schemas.common import PaginatedResponse, PaginationMeta, SortOrder

class DocumentCategory(str, Enum):
    """公文分類 (用於篩選) - 與資料庫實際值對齊"""
    RECEIVE = "收文"
    SEND = "發文"

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
    auto_serial: Optional[str] = Field(None, description="自動生成流水號 (R0001=收文, S0001=發文)")
    creator: Optional[str] = Field(None, description="建立者")
    is_deleted: Optional[bool] = Field(False, description="是否已軟刪除")
    notes: Optional[str] = Field(None, description="備註")
    ck_note: Optional[str] = Field(None, description="簡要說明(乾坤備註)")
    priority_level: Optional[str] = Field("普通", description="速別 (例如：普通, 速件, 最速件)") # 修正: 預設值
    content: Optional[str] = Field(None, description="公文內容摘要") # 修正: 欄位名稱

    # 新增：發文形式與附件欄位
    delivery_method: Optional[str] = Field("電子交換", description="發文形式 (電子交換/紙本郵寄/電子+紙本)")
    has_attachment: Optional[bool] = Field(False, description="是否含附件")

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
    auto_serial: Optional[str] = None
    creator: Optional[str] = None
    is_deleted: Optional[bool] = None
    notes: Optional[str] = None
    ck_note: Optional[str] = None
    priority_level: Optional[str] = None
    content: Optional[str] = None
    delivery_method: Optional[str] = None
    has_attachment: Optional[bool] = None

class StaffInfo(BaseModel):
    """業務同仁資訊"""
    user_id: int
    name: str
    role: str

class DocumentResponse(BaseModel):
    """
    公文回應資料結構 - 與 OfficialDocument 模型欄位完全對齊

    注意：此 Schema 只包含 OfficialDocument 模型實際存在的欄位
    """
    # 基本欄位
    id: int
    auto_serial: Optional[str] = Field(None, description="流水序號")
    doc_number: str = Field(..., description="公文文號")
    doc_type: str = Field(..., description="公文類型")
    subject: str = Field(..., description="主旨")
    sender: Optional[str] = Field(None, description="發文單位")
    receiver: Optional[str] = Field(None, description="受文單位")
    doc_date: Optional[date] = Field(None, description="公文日期")
    receive_date: Optional[date] = Field(None, description="收文日期")
    send_date: Optional[date] = Field(None, description="發文日期")
    status: Optional[str] = Field(None, description="處理狀態")
    category: Optional[str] = Field(None, description="公文分類")

    # 發文形式與附件欄位
    delivery_method: Optional[str] = Field("電子交換", description="發文形式")
    has_attachment: Optional[bool] = Field(False, description="是否含附件")

    # 關聯欄位
    contract_project_id: Optional[int] = Field(None, description="承攬案件 ID")
    sender_agency_id: Optional[int] = Field(None, description="發文機關 ID")
    receiver_agency_id: Optional[int] = Field(None, description="受文機關 ID")

    # 其他欄位
    title: Optional[str] = Field(None, description="標題")
    content: Optional[str] = Field(None, description="說明")
    notes: Optional[str] = Field(None, description="備註")
    ck_note: Optional[str] = Field(None, description="簡要說明(乾坤備註)")
    cloud_file_link: Optional[str] = Field(None, description="雲端檔案連結")
    dispatch_format: Optional[str] = Field(None, description="發文形式")
    assignee: Optional[str] = Field(None, description="承辦人")

    # 時間戳
    created_at: datetime
    updated_at: datetime

    # 擴充欄位（由 API 端點額外填入）
    contract_project_name: Optional[str] = Field(None, description="承攬案件名稱")
    assigned_staff: Optional[List[StaffInfo]] = Field(default=[], description="負責業務同仁")
    attachment_count: int = Field(default=0, description="附件數量")

    # 機關名稱虛擬欄位 (2026-01-08 新增)
    sender_agency_name: Optional[str] = Field(None, description="發文機關名稱")
    receiver_agency_name: Optional[str] = Field(None, description="受文機關名稱")

    model_config = ConfigDict(from_attributes=True)

class DocumentFilter(BaseModel):
    """
    公文篩選條件 - 統一篩選參數格式

    支援前端多種命名慣例：
    - 日期：date_from/date_to 或 doc_date_from/doc_date_to
    - 搜尋：keyword 或 search
    - 公文字號：doc_number（僅搜尋 doc_number 欄位）
    - 分類：category (send/receive) 自動轉換為資料庫值 (發文/收文)

    注意：所有日期欄位使用字串格式 'YYYY-MM-DD'，由服務層轉換
    """
    # 關鍵字搜尋
    keyword: Optional[str] = Field(None, description="關鍵字搜尋 (主旨、說明、備註)")
    search: Optional[str] = Field(None, description="搜尋 (別名，與 keyword 等效)")
    doc_number: Optional[str] = Field(None, description="公文字號搜尋（僅搜尋 doc_number 欄位）")

    # 類型與狀態篩選
    doc_type: Optional[str] = Field(None, description="公文類型 (函/開會通知單/會勘通知單)")
    year: Optional[int] = Field(None, description="年度篩選")
    status: Optional[str] = Field(None, description="處理狀態篩選")
    category: Optional[str] = Field(None, description="收發文分類 (send=發文, receive=收文)")

    # 單位與案件篩選
    doc_word: Optional[str] = Field(None, description="公文字篩選")
    sender: Optional[str] = Field(None, description="發文單位篩選 (模糊匹配)")
    receiver: Optional[str] = Field(None, description="受文單位篩選 (模糊匹配)")
    contract_case: Optional[str] = Field(None, description="承攬案件篩選 (名稱或編號)")

    # 發文形式篩選 (僅支援：電子交換、紙本郵寄)
    delivery_method: Optional[str] = Field(None, description="發文形式 (電子交換/紙本郵寄)")

    # 日期篩選 (支援兩種命名格式)
    date_from: Optional[str] = Field(None, description="公文日期起 (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="公文日期迄 (YYYY-MM-DD)")
    doc_date_from: Optional[str] = Field(None, description="公文日期起 (別名)")
    doc_date_to: Optional[str] = Field(None, description="公文日期迄 (別名)")

    # 其他篩選
    assignee: Optional[str] = Field(None, description="承辦人篩選")
    creator: Optional[str] = Field(None, description="建立者篩選")
    is_deleted: Optional[bool] = Field(None, description="是否已刪除篩選")

    # 排序
    sort_by: Optional[str] = Field("updated_at", description="排序欄位")
    sort_order: Optional[str] = Field("desc", description="排序順序 (asc/desc)")

    def get_effective_keyword(self) -> Optional[str]:
        """取得有效的關鍵字值 (keyword 或 search)"""
        return self.keyword or self.search

    def get_effective_date_from(self) -> Optional[str]:
        """取得有效的起始日期 (date_from 或 doc_date_from)"""
        return self.date_from or self.doc_date_from

    def get_effective_date_to(self) -> Optional[str]:
        """取得有效的結束日期 (date_to 或 doc_date_to)"""
        return self.date_to or self.doc_date_to


class DocumentListQuery(BaseModel):
    """公文列表查詢參數（統一格式）"""
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=1000, description="每頁筆數")
    # 基本篩選
    keyword: Optional[str] = Field(None, description="關鍵字搜尋（主旨、說明、備註）")
    doc_number: Optional[str] = Field(None, description="公文字號搜尋（僅搜尋公文字號欄位）")
    doc_type: Optional[str] = Field(None, description="公文類型")
    year: Optional[int] = Field(None, description="年度")
    status: Optional[str] = Field(None, description="狀態")
    category: Optional[str] = Field(None, description="收發文分類 (send=發文, receive=收文)")
    # 進階篩選
    contract_case: Optional[str] = Field(None, description="承攬案件")
    sender: Optional[str] = Field(None, description="發文單位")
    receiver: Optional[str] = Field(None, description="受文單位")
    doc_date_from: Optional[str] = Field(None, description="公文日期起")
    doc_date_to: Optional[str] = Field(None, description="公文日期迄")
    delivery_method: Optional[str] = Field(None, description="發文形式 (電子交換/紙本郵寄/電子+紙本)")
    # 排序
    sort_by: str = Field(default="updated_at", description="排序欄位")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="排序方向")

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
    auto_serial: Optional[str] = Field(None, description="流水序號 (R0001=收文, S0001=發文)")
    creator: Optional[str] = Field(None, description="建立者")
    is_deleted: Optional[bool] = Field(None, description="是否刪除")
    notes: Optional[str] = Field(None, description="備註")
    ck_note: Optional[str] = Field(None, description="簡要說明(乾坤備註)")
    priority_level: Optional[str] = Field(None, description="速別")
    content: Optional[str] = Field(None, description="公文內容摘要")
    delivery_method: Optional[str] = Field("電子交換", description="發文形式 (電子交換/紙本郵寄/電子+紙本)")
    has_attachment: Optional[bool] = Field(False, description="是否含附件")

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

class DocumentListResponse(PaginatedResponse):
    """
    公文列表回應 Schema（統一分頁格式）

    回應格式：
    {
        "success": true,
        "items": [...],
        "pagination": { "total": 100, "page": 1, "limit": 20, ... }
    }
    """
    items: List[DocumentResponse] = Field(default=[], description="公文列表")


# 保留舊版格式供向後相容（已棄用）
class DocumentListResponseLegacy(BaseModel):
    """公文列表回應（舊版格式，已棄用）"""
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

# =============================================================================
# API 請求專用 Schema（日期使用字串格式，由 endpoint 轉換）
# =============================================================================

# doc_type 白名單 - 統一定義，供所有 endpoints 使用
# 注意：「發文」和「收文」是 category（類別），不是 doc_type（公文類型）
VALID_DOC_TYPES = {"函", "開會通知單", "會勘通知單", "書函", "公告", "令", "通知"}


class DocumentCreateRequest(BaseModel):
    """
    公文建立請求 (API 專用)

    注意：日期欄位使用字串格式 'YYYY-MM-DD'，由 endpoint 轉換為 date 物件
    此 Schema 統一由 API endpoints 使用，避免重複定義
    """
    doc_number: str = Field(..., description="公文編號")
    doc_type: str = Field(..., description="公文類型")
    subject: str = Field(..., description="主旨")
    sender: Optional[str] = Field(None, description="發文單位")
    receiver: Optional[str] = Field(None, description="受文單位")
    doc_date: Optional[str] = Field(None, description="公文日期 (YYYY-MM-DD)")
    receive_date: Optional[str] = Field(None, description="收文日期 (YYYY-MM-DD)")
    send_date: Optional[str] = Field(None, description="發文日期 (YYYY-MM-DD)")
    status: Optional[str] = Field(None, description="狀態")
    category: Optional[str] = Field(None, description="收發文類別")
    contract_case: Optional[str] = Field(None, description="承攬案件名稱")
    contract_project_id: Optional[int] = Field(None, description="承攬案件 ID")
    doc_word: Optional[str] = Field(None, description="發文字")
    doc_class: Optional[str] = Field(None, description="文別")
    assignee: Optional[str] = Field(None, description="承辦人")
    notes: Optional[str] = Field(None, description="備註")
    ck_note: Optional[str] = Field(None, description="簡要說明(乾坤備註)")
    priority_level: Optional[str] = Field(None, description="優先級")
    content: Optional[str] = Field(None, description="內容")
    delivery_method: Optional[str] = Field("電子交換", description="發文形式 (電子交換/紙本郵寄/電子+紙本)")
    has_attachment: Optional[bool] = Field(False, description="是否含附件")

    @field_validator('doc_type')
    @classmethod
    def validate_doc_type(cls, v: str) -> str:
        """驗證 doc_type 是否在白名單中"""
        if v and v not in VALID_DOC_TYPES:
            raise ValueError(
                f"無效的公文類型 '{v}'。有效值: {', '.join(sorted(VALID_DOC_TYPES))}"
            )
        return v


class DocumentUpdateRequest(BaseModel):
    """
    公文更新請求 (API 專用)

    注意：日期欄位使用字串格式 'YYYY-MM-DD'，由 endpoint 轉換為 date 物件
    此 Schema 統一由 API endpoints 使用，避免重複定義
    """
    doc_number: Optional[str] = Field(None, description="公文編號")
    doc_type: Optional[str] = Field(None, description="公文類型")
    subject: Optional[str] = Field(None, description="主旨")
    sender: Optional[str] = Field(None, description="發文單位")
    receiver: Optional[str] = Field(None, description="受文單位")
    doc_date: Optional[str] = Field(None, description="公文日期 (YYYY-MM-DD)")
    receive_date: Optional[str] = Field(None, description="收文日期 (YYYY-MM-DD)")
    send_date: Optional[str] = Field(None, description="發文日期 (YYYY-MM-DD)")
    status: Optional[str] = Field(None, description="狀態")
    category: Optional[str] = Field(None, description="收發文類別")
    contract_case: Optional[str] = Field(None, description="承攬案件名稱")
    contract_project_id: Optional[int] = Field(None, description="承攬案件 ID")
    sender_agency_id: Optional[int] = Field(None, description="發文機關 ID")
    receiver_agency_id: Optional[int] = Field(None, description="受文機關 ID")
    doc_word: Optional[str] = Field(None, description="發文字")
    doc_class: Optional[str] = Field(None, description="文別")
    assignee: Optional[str] = Field(None, description="承辦人")
    notes: Optional[str] = Field(None, description="備註")
    ck_note: Optional[str] = Field(None, description="簡要說明(乾坤備註)")
    priority_level: Optional[str] = Field(None, description="優先級")
    content: Optional[str] = Field(None, description="內容")
    delivery_method: Optional[str] = Field(None, description="發文形式 (電子交換/紙本郵寄/電子+紙本)")
    has_attachment: Optional[bool] = Field(None, description="是否含附件")
    title: Optional[str] = Field(None, description="標題")
    cloud_file_link: Optional[str] = Field(None, description="雲端檔案連結")
    dispatch_format: Optional[str] = Field(None, description="發文形式")
    auto_serial: Optional[str] = Field(None, description="流水序號")

    @field_validator('doc_type')
    @classmethod
    def validate_doc_type(cls, v: Optional[str]) -> Optional[str]:
        """驗證 doc_type 是否在白名單中"""
        if v and v not in VALID_DOC_TYPES:
            raise ValueError(
                f"無效的公文類型 '{v}'。有效值: {', '.join(sorted(VALID_DOC_TYPES))}"
            )
        return v


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
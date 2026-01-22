"""
桃園查估派工管理系統 - Pydantic Schemas
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from decimal import Decimal

from app.schemas.common import PaginationMeta


# =============================================================================
# 關聯類型常數 (SSOT)
# =============================================================================

# 關聯類型：機關來函 / 乾坤發文
LinkTypeEnum = Literal['agency_incoming', 'company_outgoing']


# =============================================================================
# 作業類別常數
# =============================================================================
WORK_TYPES = [
    "#0.專案行政作業",
    "00.專案會議",
    "01.地上物查估作業",
    "02.土地協議市價查估作業",
    "03.土地徵收市價查估作業",
    "04.相關計畫書製作",
    "05.測量作業",
    "06.樁位測釘作業",
    "07.辦理教育訓練",
    "08.作業提繳事項",
]


# =============================================================================
# 轄管工程清單 Schemas
# =============================================================================
class TaoyuanProjectBase(BaseModel):
    """轄管工程清單基礎欄位"""
    sequence_no: Optional[int] = Field(None, description="項次")
    review_year: Optional[int] = Field(None, description="審議年度")
    case_type: Optional[str] = Field(None, max_length=50, description="案件類型")
    district: Optional[str] = Field(None, max_length=50, description="行政區")
    project_name: str = Field(..., max_length=500, description="工程名稱")
    start_point: Optional[str] = Field(None, max_length=200, description="工程起點")
    start_coordinate: Optional[str] = Field(None, max_length=100, description="起點坐標(經緯度)")
    end_point: Optional[str] = Field(None, max_length=200, description="工程迄點")
    end_coordinate: Optional[str] = Field(None, max_length=100, description="迄點坐標(經緯度)")
    road_length: Optional[Decimal] = Field(None, description="道路長度(公尺)")
    current_width: Optional[Decimal] = Field(None, description="現況路寬")
    planned_width: Optional[Decimal] = Field(None, description="計畫路寬")
    public_land_count: Optional[int] = Field(None, description="公有土地筆數")
    private_land_count: Optional[int] = Field(None, description="私有土地筆數")
    rc_count: Optional[int] = Field(None, description="RC數量")
    iron_sheet_count: Optional[int] = Field(None, description="鐵皮屋數量")
    construction_cost: Optional[Decimal] = Field(None, description="工程費")
    land_cost: Optional[Decimal] = Field(None, description="用地費")
    compensation_cost: Optional[Decimal] = Field(None, description="補償費")
    total_cost: Optional[Decimal] = Field(None, description="總經費")
    review_result: Optional[str] = Field(None, max_length=100, description="審議結果")
    urban_plan: Optional[str] = Field(None, max_length=200, description="都市計畫")
    completion_date: Optional[date] = Field(None, description="完工日期")
    proposer: Optional[str] = Field(None, max_length=100, description="提案人")
    remark: Optional[str] = Field(None, description="備註")

    # 派工關聯欄位
    sub_case_name: Optional[str] = Field(None, max_length=200, description="分案名稱")
    case_handler: Optional[str] = Field(None, max_length=50, description="案件承辦")
    survey_unit: Optional[str] = Field(None, max_length=100, description="查估單位")

    # 進度追蹤欄位
    land_agreement_status: Optional[str] = Field(None, max_length=100, description="土地協議進度")
    land_expropriation_status: Optional[str] = Field(None, max_length=100, description="土地徵收進度")
    building_survey_status: Optional[str] = Field(None, max_length=100, description="地上物查估進度")
    actual_entry_date: Optional[date] = Field(None, description="實際進場日期")
    acceptance_status: Optional[str] = Field(None, max_length=100, description="驗收狀態")

    model_config = ConfigDict(from_attributes=True)


class TaoyuanProjectCreate(TaoyuanProjectBase):
    """建立轄管工程"""
    contract_project_id: Optional[int] = Field(None, description="關聯承攬案件ID")


class TaoyuanProjectUpdate(BaseModel):
    """更新轄管工程（所有欄位可選）"""
    contract_project_id: Optional[int] = None
    sequence_no: Optional[int] = None
    review_year: Optional[int] = None
    case_type: Optional[str] = None
    district: Optional[str] = None
    project_name: Optional[str] = None
    start_point: Optional[str] = None
    start_coordinate: Optional[str] = None
    end_point: Optional[str] = None
    end_coordinate: Optional[str] = None
    road_length: Optional[Decimal] = None
    current_width: Optional[Decimal] = None
    planned_width: Optional[Decimal] = None
    public_land_count: Optional[int] = None
    private_land_count: Optional[int] = None
    rc_count: Optional[int] = None
    iron_sheet_count: Optional[int] = None
    construction_cost: Optional[Decimal] = None
    land_cost: Optional[Decimal] = None
    compensation_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    review_result: Optional[str] = None
    urban_plan: Optional[str] = None
    completion_date: Optional[date] = None
    proposer: Optional[str] = None
    remark: Optional[str] = None
    sub_case_name: Optional[str] = None
    case_handler: Optional[str] = None
    survey_unit: Optional[str] = None
    land_agreement_status: Optional[str] = None
    land_expropriation_status: Optional[str] = None
    building_survey_status: Optional[str] = None
    actual_entry_date: Optional[date] = None
    acceptance_status: Optional[str] = None


class TaoyuanProject(TaoyuanProjectBase):
    """轄管工程完整資訊"""
    id: int
    contract_project_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProjectDispatchLink(BaseModel):
    """工程關聯的派工單簡要資訊"""
    link_id: int = Field(..., description="關聯記錄 ID")
    dispatch_order_id: int = Field(..., description="派工單 ID")
    dispatch_no: Optional[str] = Field(None, description="派工單號")
    work_type: Optional[str] = Field(None, description="作業類別")

    model_config = ConfigDict(from_attributes=True)


class ProjectDocumentLink(BaseModel):
    """工程關聯的公文簡要資訊"""
    link_id: int = Field(..., description="關聯記錄 ID")
    document_id: int = Field(..., description="公文 ID")
    doc_number: Optional[str] = Field(None, description="公文字號")
    link_type: str = Field(..., description="關聯類型 (agency_incoming/company_outgoing)")

    model_config = ConfigDict(from_attributes=True)


class TaoyuanProjectWithLinks(TaoyuanProject):
    """轄管工程完整資訊（包含關聯）"""
    linked_dispatches: List[ProjectDispatchLink] = Field(default_factory=list, description="關聯派工單")
    linked_documents: List[ProjectDocumentLink] = Field(default_factory=list, description="關聯公文")

    model_config = ConfigDict(from_attributes=True)


class LinkedProjectItem(TaoyuanProject):
    """派工單關聯的工程項目 (包含關聯資訊)"""
    link_id: int = Field(..., description="關聯記錄 ID (用於刪除操作)")
    project_id: int = Field(..., description="工程 ID")

    model_config = ConfigDict(from_attributes=True)


class TaoyuanProjectListQuery(BaseModel):
    """轄管工程列表查詢參數"""
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=1000, description="每頁筆數")
    contract_project_id: Optional[int] = Field(None, description="關聯承攬案件ID")
    district: Optional[str] = Field(None, description="行政區")
    review_year: Optional[int] = Field(None, description="審議年度")
    search: Optional[str] = Field(None, description="搜尋關鍵字")
    sort_by: str = Field(default="id", description="排序欄位")
    sort_order: str = Field(default="asc", description="排序方向")


class TaoyuanProjectListResponse(BaseModel):
    """轄管工程列表回應（包含關聯資訊）"""
    success: bool = True
    items: List[TaoyuanProjectWithLinks] = []
    pagination: PaginationMeta

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# 派工紀錄 Schemas
# =============================================================================
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
    linked_documents: Optional[List[dict]] = Field(None, description="關聯公文")


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


# =============================================================================
# 派工-公文關聯 Schemas
# =============================================================================
class DispatchDocumentLink(BaseModel):
    """派工-公文關聯"""
    id: int
    dispatch_order_id: int
    document_id: int
    link_type: LinkTypeEnum = Field(..., description="關聯類型：agency_incoming(機關來函) / company_outgoing(乾坤發文)")
    created_at: Optional[datetime] = None

    # 公文資訊
    doc_number: Optional[str] = None
    doc_date: Optional[date] = None
    subject: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DispatchDocumentLinkCreate(BaseModel):
    """建立派工-公文關聯"""
    dispatch_order_id: int
    document_id: int
    link_type: LinkTypeEnum = Field(..., description="關聯類型：agency_incoming(機關來函) / company_outgoing(乾坤發文)")


# =============================================================================
# 統一關聯回應 Schemas (SSOT)
# =============================================================================

class BaseLinkResponse(BaseModel):
    """基礎關聯回應 (所有關聯類型共用)"""
    link_id: int = Field(..., description="關聯記錄 ID")
    link_type: Optional[LinkTypeEnum] = Field(None, description="關聯類型")
    created_at: Optional[datetime] = Field(None, description="建立時間")


class DispatchLinkResponse(BaseLinkResponse):
    """派工單關聯回應"""
    dispatch_order_id: int = Field(..., description="派工單 ID")
    dispatch_no: str = Field(..., description="派工單號")
    project_name: Optional[str] = Field(None, description="工程名稱")
    work_type: Optional[str] = Field(None, description="作業類別")


class ProjectLinkResponse(BaseLinkResponse):
    """工程關聯回應"""
    project_id: int = Field(..., description="工程 ID")
    project_name: str = Field(..., description="工程名稱")


class DocumentDispatchLinkResponse(DispatchLinkResponse):
    """公文關聯的派工單回應 (完整版)"""
    link_type: LinkTypeEnum = Field(..., description="關聯類型")
    sub_case_name: Optional[str] = Field(None, description="分案名稱")
    deadline: Optional[str] = Field(None, description="工作期限")
    case_handler: Optional[str] = Field(None, description="案件承辦")
    survey_unit: Optional[str] = Field(None, description="查估單位")
    contact_note: Optional[str] = Field(None, description="聯繫備註")
    cloud_folder: Optional[str] = Field(None, description="雲端資料夾")
    project_folder: Optional[str] = Field(None, description="專案資料夾")
    agency_doc_number: Optional[str] = Field(None, description="機關函文文號")
    company_doc_number: Optional[str] = Field(None, description="乾坤函文文號")

    model_config = ConfigDict(from_attributes=True)


class DocumentProjectLinkResponse(ProjectLinkResponse):
    """公文關聯的工程回應 (完整版)"""
    notes: Optional[str] = Field(None, description="備註")
    district: Optional[str] = Field(None, description="行政區")
    review_year: Optional[int] = Field(None, description="審議年度")
    case_type: Optional[str] = Field(None, description="案件類型")
    sub_case_name: Optional[str] = Field(None, description="分案名稱")
    case_handler: Optional[str] = Field(None, description="案件承辦")
    survey_unit: Optional[str] = Field(None, description="查估單位")

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# 契金管控 Schemas
# =============================================================================
class WorkPayment(BaseModel):
    """單一作業類別的派工日期/金額"""
    date: Optional[date] = None
    amount: Optional[Decimal] = None


class ContractPaymentBase(BaseModel):
    """契金管控基礎欄位"""
    work_01: Optional[WorkPayment] = Field(None, description="01.地上物查估作業")
    work_02: Optional[WorkPayment] = Field(None, description="02.土地協議市價查估作業")
    work_03: Optional[WorkPayment] = Field(None, description="03.土地徵收市價查估作業")
    work_04: Optional[WorkPayment] = Field(None, description="04.相關計畫書製作")
    work_05: Optional[WorkPayment] = Field(None, description="05.測量作業")
    work_06: Optional[WorkPayment] = Field(None, description="06.樁位測釘作業")
    work_07: Optional[WorkPayment] = Field(None, description="07.辦理教育訓練")

    current_amount: Optional[Decimal] = Field(None, description="本次派工金額")
    cumulative_amount: Optional[Decimal] = Field(None, description="累進派工金額")
    remaining_amount: Optional[Decimal] = Field(None, description="剩餘金額")
    acceptance_date: Optional[date] = Field(None, description="完成驗收日期")

    model_config = ConfigDict(from_attributes=True)


class ContractPaymentCreate(BaseModel):
    """建立契金管控記錄"""
    dispatch_order_id: int
    work_01_date: Optional[date] = None
    work_01_amount: Optional[Decimal] = None
    work_02_date: Optional[date] = None
    work_02_amount: Optional[Decimal] = None
    work_03_date: Optional[date] = None
    work_03_amount: Optional[Decimal] = None
    work_04_date: Optional[date] = None
    work_04_amount: Optional[Decimal] = None
    work_05_date: Optional[date] = None
    work_05_amount: Optional[Decimal] = None
    work_06_date: Optional[date] = None
    work_06_amount: Optional[Decimal] = None
    work_07_date: Optional[date] = None
    work_07_amount: Optional[Decimal] = None
    current_amount: Optional[Decimal] = None
    cumulative_amount: Optional[Decimal] = None
    remaining_amount: Optional[Decimal] = None
    acceptance_date: Optional[date] = None


class ContractPaymentUpdate(BaseModel):
    """更新契金管控記錄"""
    work_01_date: Optional[date] = None
    work_01_amount: Optional[Decimal] = None
    work_02_date: Optional[date] = None
    work_02_amount: Optional[Decimal] = None
    work_03_date: Optional[date] = None
    work_03_amount: Optional[Decimal] = None
    work_04_date: Optional[date] = None
    work_04_amount: Optional[Decimal] = None
    work_05_date: Optional[date] = None
    work_05_amount: Optional[Decimal] = None
    work_06_date: Optional[date] = None
    work_06_amount: Optional[Decimal] = None
    work_07_date: Optional[date] = None
    work_07_amount: Optional[Decimal] = None
    current_amount: Optional[Decimal] = None
    cumulative_amount: Optional[Decimal] = None
    remaining_amount: Optional[Decimal] = None
    acceptance_date: Optional[date] = None


class ContractPayment(BaseModel):
    """契金管控完整資訊"""
    id: int
    dispatch_order_id: int

    work_01_date: Optional[date] = None
    work_01_amount: Optional[Decimal] = None
    work_02_date: Optional[date] = None
    work_02_amount: Optional[Decimal] = None
    work_03_date: Optional[date] = None
    work_03_amount: Optional[Decimal] = None
    work_04_date: Optional[date] = None
    work_04_amount: Optional[Decimal] = None
    work_05_date: Optional[date] = None
    work_05_amount: Optional[Decimal] = None
    work_06_date: Optional[date] = None
    work_06_amount: Optional[Decimal] = None
    work_07_date: Optional[date] = None
    work_07_amount: Optional[Decimal] = None

    current_amount: Optional[Decimal] = None
    cumulative_amount: Optional[Decimal] = None
    remaining_amount: Optional[Decimal] = None
    acceptance_date: Optional[date] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 派工單資訊
    dispatch_no: Optional[str] = None
    project_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ContractPaymentListResponse(BaseModel):
    """契金管控列表回應"""
    success: bool = True
    items: List[ContractPayment] = []
    pagination: PaginationMeta

    model_config = ConfigDict(from_attributes=True)


class PaymentControlItem(BaseModel):
    """契金管控展示項目（派工單為主）"""
    # 派工單基本資訊
    dispatch_order_id: int
    dispatch_no: str
    project_name: Optional[str] = None
    work_type: Optional[str] = None
    sub_case_name: Optional[str] = Field(None, description="分案名稱/派工備註")
    case_handler: Optional[str] = None
    survey_unit: Optional[str] = None
    cloud_folder: Optional[str] = Field(None, description="雲端資料夾")
    project_folder: Optional[str] = Field(None, description="專案資料夾")
    deadline: Optional[str] = Field(None, description="履約期限")

    # 派工日期（取第一筆機關來函日期）
    dispatch_date: Optional[date] = Field(None, description="派工日期（第一筆機關來函日期）")

    # 公文歷程
    agency_doc_history: Optional[str] = Field(None, description="機關函文歷程")
    company_doc_history: Optional[str] = Field(None, description="乾坤函文歷程")

    # 契金資訊
    payment_id: Optional[int] = None
    work_01_date: Optional[date] = None
    work_01_amount: Optional[Decimal] = None
    work_02_date: Optional[date] = None
    work_02_amount: Optional[Decimal] = None
    work_03_date: Optional[date] = None
    work_03_amount: Optional[Decimal] = None
    work_04_date: Optional[date] = None
    work_04_amount: Optional[Decimal] = None
    work_05_date: Optional[date] = None
    work_05_amount: Optional[Decimal] = None
    work_06_date: Optional[date] = None
    work_06_amount: Optional[Decimal] = None
    work_07_date: Optional[date] = None
    work_07_amount: Optional[Decimal] = None
    current_amount: Optional[Decimal] = None
    cumulative_amount: Optional[Decimal] = None
    remaining_amount: Optional[Decimal] = None
    acceptance_date: Optional[date] = None
    remark: Optional[str] = Field(None, description="備註")

    model_config = ConfigDict(from_attributes=True)


class PaymentControlResponse(BaseModel):
    """契金管控展示回應"""
    success: bool = True
    items: List[PaymentControlItem] = []
    total_budget: Optional[Decimal] = Field(None, description="總預算金額")
    total_dispatched: Optional[Decimal] = Field(None, description="累計派工金額")
    total_remaining: Optional[Decimal] = Field(None, description="剩餘金額")
    pagination: PaginationMeta

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# 總控表 Schemas
# =============================================================================
class MasterControlItem(BaseModel):
    """總控表單項資料"""
    # 工程基本資訊
    id: int
    project_name: str
    sub_case_name: Optional[str] = None
    district: Optional[str] = None
    review_year: Optional[int] = None

    # 進度追蹤
    land_agreement_status: Optional[str] = None
    land_expropriation_status: Optional[str] = None
    building_survey_status: Optional[str] = None
    actual_entry_date: Optional[date] = None
    acceptance_status: Optional[str] = None

    # 派工資訊
    dispatch_no: Optional[str] = None
    case_handler: Optional[str] = None
    survey_unit: Optional[str] = None

    # 公文歷程
    agency_documents: Optional[List[dict]] = Field(None, description="機關來文歷程")
    company_documents: Optional[List[dict]] = Field(None, description="公司發文歷程")

    # 契金資訊
    payment_info: Optional[ContractPayment] = None

    model_config = ConfigDict(from_attributes=True)


class MasterControlQuery(BaseModel):
    """總控表查詢參數"""
    contract_project_id: Optional[int] = Field(None, description="關聯承攬案件ID")
    district: Optional[str] = Field(None, description="行政區")
    review_year: Optional[int] = Field(None, description="審議年度")
    search: Optional[str] = Field(None, description="搜尋關鍵字")


class MasterControlResponse(BaseModel):
    """總控表回應"""
    success: bool = True
    items: List[MasterControlItem] = []
    summary: dict = Field(default_factory=dict, description="彙總統計")

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Excel 匯入 Schemas
# =============================================================================
class ExcelImportRequest(BaseModel):
    """Excel 匯入請求"""
    contract_project_id: int = Field(..., description="關聯承攬案件ID")
    sheet_name: Optional[str] = Field(None, description="工作表名稱")
    skip_rows: int = Field(default=0, description="跳過列數")


class ExcelImportResult(BaseModel):
    """Excel 匯入結果"""
    success: bool
    message: str
    total_rows: int = 0
    imported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: List[dict] = []


# =============================================================================
# 公文歷程匹配 Schemas
# =============================================================================
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
    # 公文歷程欄位 (對應原始需求欄位 14-17)
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


# =============================================================================
# 統計資料 Schemas
# =============================================================================
class ProjectStatistics(BaseModel):
    """工程統計資料"""
    total_count: int = Field(..., description="總工程數")
    dispatched_count: int = Field(..., description="已派工數")
    completed_count: int = Field(..., description="已完成數")
    completion_rate: float = Field(..., description="完成率 (%)")

    model_config = ConfigDict(from_attributes=True)


class DispatchStatistics(BaseModel):
    """派工統計資料"""
    total_count: int = Field(..., description="總派工單數")
    with_agency_doc_count: int = Field(..., description="有機關函文數")
    with_company_doc_count: int = Field(..., description="有乾坤函文數")
    work_type_count: int = Field(..., description="作業類別數")

    model_config = ConfigDict(from_attributes=True)


class PaymentStatistics(BaseModel):
    """契金統計資料"""
    total_current_amount: float = Field(..., description="本次派工金額總計")
    total_cumulative_amount: float = Field(..., description="累進派工金額總計")
    total_remaining_amount: float = Field(..., description="剩餘金額總計")
    payment_count: int = Field(..., description="契金紀錄數")

    model_config = ConfigDict(from_attributes=True)


class TaoyuanStatisticsResponse(BaseModel):
    """桃園查估派工統計資料回應"""
    success: bool = True
    projects: ProjectStatistics = Field(..., description="工程統計")
    dispatches: DispatchStatistics = Field(..., description="派工統計")
    payments: PaymentStatistics = Field(..., description="契金統計")

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# 派工單附件 Schemas
# =============================================================================
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

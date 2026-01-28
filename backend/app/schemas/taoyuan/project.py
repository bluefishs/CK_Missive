"""
桃園查估派工 - 轄管工程 Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from decimal import Decimal

from app.schemas.common import PaginationMeta


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
    items: List["TaoyuanProjectWithLinks"] = []
    pagination: PaginationMeta

    model_config = ConfigDict(from_attributes=True)


class LinkedProjectItem(TaoyuanProject):
    """派工單關聯的工程項目 (包含關聯資訊)"""
    link_id: int = Field(..., description="關聯記錄 ID (用於刪除操作)")
    project_id: int = Field(..., description="工程 ID")

    model_config = ConfigDict(from_attributes=True)


# Excel 匯入 Schemas
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

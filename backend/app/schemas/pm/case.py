"""PM 案件主檔 Schemas"""
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.schemas.common import BaseQueryParams


def _validate_date_ordering(
    start: Optional[date], end: Optional[date], actual_end: Optional[date] = None,
) -> None:
    """共用日期順序驗證"""
    if start and end and end < start:
        raise ValueError(
            f"結束日期 ({end}) 不得早於開始日期 ({start})"
        )
    if actual_end and start and actual_end < start:
        raise ValueError(
            f"實際結束日期 ({actual_end}) 不得早於開始日期 ({start})"
        )


class PMCaseCreate(BaseModel):
    """建立案件"""
    case_code: Optional[str] = Field(None, max_length=50, description="建案案號 (未提供時自動產生)")
    project_code: Optional[str] = Field(None, max_length=100, description="成案專案編號 (成案後由系統產生)")
    case_name: str = Field(..., max_length=500, description="案名")
    client_vendor_id: Optional[int] = Field(None, description="委託單位 ID (partner_vendors)")
    year: Optional[int] = Field(None, description="年度 (民國)")
    category: Optional[str] = Field(None, max_length=50, description="計畫類別: 01委辦招標, 02承攬報價")
    case_nature: Optional[str] = Field(None, max_length=50, description="作業性質: 01地面測量~11其他類別")
    client_name: Optional[str] = Field(None, max_length=200, description="業主")
    client_contact: Optional[str] = Field(None, max_length=100)
    client_phone: Optional[str] = Field(None, max_length=50)
    contract_amount: Optional[Decimal] = Field(None, description="合約金額")
    status: str = Field("planning", description="狀態")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    location: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "PMCaseCreate":
        """日期交叉驗證 — end_date 不得早於 start_date"""
        _validate_date_ordering(self.start_date, self.end_date)
        return self


class PMCaseUpdate(BaseModel):
    """更新案件"""
    case_code: Optional[str] = Field(None, max_length=50)
    project_code: Optional[str] = Field(None, max_length=100)
    case_name: Optional[str] = Field(None, max_length=500)
    year: Optional[int] = None
    category: Optional[str] = Field(None, max_length=50)
    case_nature: Optional[str] = Field(None, max_length=50)
    client_name: Optional[str] = Field(None, max_length=200)
    client_contact: Optional[str] = Field(None, max_length=100)
    client_phone: Optional[str] = Field(None, max_length=50)
    contract_amount: Optional[Decimal] = None
    status: Optional[str] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    location: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "PMCaseUpdate":
        """日期交叉驗證 — end_date/actual_end_date 不得早於 start_date"""
        _validate_date_ordering(self.start_date, self.end_date, self.actual_end_date)
        return self


class PMCaseResponse(BaseModel):
    """案件完整資訊"""
    id: int
    case_code: str
    project_code: Optional[str] = None
    case_name: str
    year: Optional[int] = None
    category: Optional[str] = None
    case_nature: Optional[str] = None
    client_name: Optional[str] = None
    client_vendor_id: Optional[int] = None
    client_contact: Optional[str] = None
    client_phone: Optional[str] = None
    contract_amount: Optional[float] = None
    status: str
    progress: int = 0
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    location: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 聚合欄位 (由 Service 層填充)
    milestone_count: int = 0
    staff_count: int = 0

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: float},
    )


class PMCaseListRequest(BaseQueryParams):
    """案件列表查詢"""
    year: Optional[int] = Field(None, description="年度篩選")
    status: Optional[str] = Field(None, description="狀態篩選")
    category: Optional[str] = Field(None, description="類別篩選")
    client_name: Optional[str] = Field(None, description="業主篩選")


class PMCaseSummary(BaseModel):
    """案件統計摘要"""
    total_cases: int = 0
    by_status: dict = Field(default_factory=dict)
    by_year: dict = Field(default_factory=dict)
    total_contract_amount: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


class PMYearlyTrendItem(BaseModel):
    """多年度案件趨勢項目"""
    year: int
    case_count: int = 0
    total_contract: Decimal = Decimal("0")
    closed_count: int = 0
    in_progress_count: int = 0
    avg_progress: int = 0

    model_config = ConfigDict(from_attributes=True)

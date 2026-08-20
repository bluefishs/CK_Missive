"""PM 案件主檔 Schemas"""
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator

from app.schemas.common import BaseQueryParams
from app.schemas._text_utils import normalize_cjk_compat


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
    year: Optional[int] = Field(None, description="年度（西元）")
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

    # 2026-08-16：只正規化「看不見卻會壞比對」的相容字，**不動全形標點**。
    #
    # 實測 documents.subject 有 1560/2009（78%）帶 CJK 相容漢字
    # （年 U+F98E vs 標準 U+5E74）—— 字形一模一樣、長度一樣、md5 不同，
    # 於是所有以名稱比對的管控靜默失效（含承攬案件防重）。
    #
    # 刻意**不**套完整的 normalize_name：那會把全形括號（）轉半形()，
    # 而公文主旨常用全形括號 —— 那是**看得見的改變**，不該由正規化順手做掉。
    @field_validator('case_name', mode='before')
    @classmethod
    def _normalize_cjk(cls, v):
        return normalize_cjk_compat(v) if isinstance(v, str) else v

    @field_validator("year", mode="before")
    @classmethod
    def _normalize_year(cls, v):
        """民國年一律轉西元（規範：統一西元年為主，見 schemas/_year.py）。"""
        from app.schemas._year import normalize_year
        return normalize_year(v)

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

    @field_validator("year", mode="before")
    @classmethod
    def _normalize_year(cls, v):
        """民國年一律轉西元（規範：統一西元年為主，見 schemas/_year.py）。"""
        from app.schemas._year import normalize_year
        return normalize_year(v)

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

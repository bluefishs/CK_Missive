"""
桃園查估派工 - 契金管控 Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from decimal import Decimal

from app.schemas.common import PaginationMeta


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


# 總控表 Schemas
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

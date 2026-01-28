"""
桃園查估派工 - 統計資料 Schemas
"""
from pydantic import BaseModel, Field, ConfigDict


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

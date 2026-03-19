"""PM 里程碑 Schemas"""
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict


class PMMilestoneCreate(BaseModel):
    """建立里程碑"""
    pm_case_id: int
    milestone_name: str = Field(..., max_length=200, description="里程碑名稱")
    milestone_type: Optional[str] = Field(None, max_length=50)
    planned_date: Optional[date] = None
    actual_date: Optional[date] = None
    status: str = Field("pending", description="狀態")
    sort_order: int = Field(0, description="排序")
    notes: Optional[str] = None


class PMMilestoneUpdate(BaseModel):
    """更新里程碑"""
    milestone_name: Optional[str] = Field(None, max_length=200)
    milestone_type: Optional[str] = Field(None, max_length=50)
    planned_date: Optional[date] = None
    actual_date: Optional[date] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None
    notes: Optional[str] = None


class PMMilestoneResponse(BaseModel):
    """里程碑完整資訊"""
    id: int
    pm_case_id: int
    milestone_name: str
    milestone_type: Optional[str] = None
    planned_date: Optional[date] = None
    actual_date: Optional[date] = None
    status: str = "pending"
    sort_order: int = 0
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

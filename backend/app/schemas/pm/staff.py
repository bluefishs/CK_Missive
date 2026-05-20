"""PM 案件人員 Schemas"""
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator

# v6.10.1 (2026-05-20): 日期防呆 SSOT helper
from app.schemas.common import validate_date_ordering


class PMCaseStaffCreate(BaseModel):
    """建立案件人員"""
    pm_case_id: int
    user_id: Optional[int] = Field(None, description="系統使用者 ID")
    staff_name: str = Field(..., max_length=100, description="人員姓名")
    role: str = Field(..., max_length=50, description="角色")
    is_primary: bool = Field(False, description="是否主要負責人")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=300)

    @model_validator(mode="after")
    def _check_date_order(self):
        validate_date_ordering(self.start_date, self.end_date)
        return self


class PMCaseStaffUpdate(BaseModel):
    """更新案件人員"""
    user_id: Optional[int] = None
    staff_name: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, max_length=50)
    is_primary: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=300)

    @model_validator(mode="after")
    def _check_date_order(self):
        validate_date_ordering(self.start_date, self.end_date)
        return self


class PMCaseStaffResponse(BaseModel):
    """案件人員完整資訊"""
    id: int
    pm_case_id: int
    user_id: Optional[int] = None
    staff_name: str
    role: str
    is_primary: bool = False
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

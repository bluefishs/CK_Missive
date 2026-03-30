"""作業性質代碼 Schema"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class CaseNatureCodeCreate(BaseModel):
    code: str = Field(..., max_length=10, description="代碼 (如 01, 12)")
    label: str = Field(..., max_length=100, description="標籤 (如 地面測量)")
    description: Optional[str] = Field(None, max_length=500, description="說明")
    sort_order: int = Field(0, description="排序")


class CaseNatureCodeUpdate(BaseModel):
    label: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class CaseNatureCodeResponse(BaseModel):
    id: int
    code: str
    label: str
    description: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class CaseNatureOption(BaseModel):
    """下拉選項 (僅啟用)"""
    value: str  # code
    label: str  # "{code}{label}" e.g. "01地面測量"

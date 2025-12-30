"""
Pydantic schemas for Government Agencies
"""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class AgencyBase(BaseModel):
    """所有 Agency schema 的基礎模型，定義通用欄位"""
    agency_name: str = Field(..., max_length=200)
    agency_code: Optional[str] = Field(None, max_length=50)
    agency_type: Optional[str] = Field(None, max_length=50)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=300)
    email: Optional[str] = Field(None, max_length=100)

    model_config = ConfigDict(from_attributes=True)

class AgencyCreate(AgencyBase):
    """用於新增機關單位的 schema"""
    pass # 直接繼承 AgencyBase 的所有欄位

class AgencyUpdate(BaseModel):
    """用於更新機關單位的 schema，所有欄位皆為可選"""
    agency_name: Optional[str] = Field(None, max_length=200)
    agency_code: Optional[str] = Field(None, max_length=50)
    agency_type: Optional[str] = Field(None, max_length=50)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=300)
    email: Optional[str] = Field(None, max_length=100)

class Agency(AgencyBase):
    """用於 API 回應的 schema，包含資料庫生成的欄位"""
    id: int
    created_at: datetime
    updated_at: datetime

class AgencyWithStats(AgencyBase):
    """包含統計資訊的機關 schema"""
    id: int
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    sent_count: int = 0
    received_count: int = 0
    last_activity: Optional[datetime] = None
    primary_type: str = "unknown"  # 'sender', 'receiver', 'both', 'unknown'
    category: str = "政府機關"  # 機關分類
    original_names: Optional[List[str]] = None

class CategoryStat(BaseModel):
    """分類統計 schema"""
    category: str
    count: int
    percentage: float

class AgencyStatistics(BaseModel):
    """機關統計資訊 schema"""
    total_agencies: int
    categories: List[CategoryStat]

class AgenciesResponse(BaseModel):
    """機關列表回應 schema"""
    agencies: List[AgencyWithStats]
    total: int
    returned: int
    search: Optional[str] = None

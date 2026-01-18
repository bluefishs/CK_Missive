"""
Pydantic schemas for Partner Vendors

使用統一回應格式，支援舊資料相容性
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime

# 營業項目選項 (與前端 BUSINESS_TYPE_OPTIONS 一致)
# 注意：建立/更新時建議使用這些值，但讀取舊資料時允許其他值
ALLOWED_BUSINESS_TYPES = ['測量業務', '資訊系統', '系統業務', '查估業務', '不動產估價', '大地工程', '其他類別']


class VendorBase(BaseModel):
    """
    廠商基礎 Schema

    不包含驗證，用於讀取資料（相容舊資料）
    """
    vendor_name: str = Field(..., max_length=200, description="廠商名稱")
    vendor_code: Optional[str] = Field(None, max_length=50, description="統一編號")
    contact_person: Optional[str] = Field(None, max_length=100, description="聯絡人")
    phone: Optional[str] = Field(None, max_length=50, description="電話")
    address: Optional[str] = Field(None, max_length=300, description="地址")
    email: Optional[str] = Field(None, max_length=100, description="電子郵件")
    business_type: Optional[str] = Field(None, max_length=100, description="營業項目")
    rating: Optional[int] = Field(None, ge=1, le=5, description="合作評價 (1-5)")

    model_config = ConfigDict(from_attributes=True)

class VendorCreate(VendorBase):
    pass

class VendorUpdate(BaseModel):
    vendor_name: Optional[str] = Field(None, max_length=200)
    vendor_code: Optional[str] = Field(None, max_length=50)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=300)
    email: Optional[str] = Field(None, max_length=100)
    business_type: Optional[str] = Field(None, max_length=100, description="營業項目")
    rating: Optional[int] = Field(None, ge=1, le=5, description="合作評價 (1-5)")

    @field_validator('business_type')
    @classmethod
    def validate_business_type(cls, v):
        if v and v not in ALLOWED_BUSINESS_TYPES:
            raise ValueError(f'營業項目必須是以下之一: {ALLOWED_BUSINESS_TYPES}')
        return v

    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError('評價必須在 1-5 之間')
        return v

class Vendor(VendorBase):
    id: int
    created_at: datetime
    updated_at: datetime


# ============================================================================
# 查詢參數與回應 Schema
# ============================================================================

class VendorListQuery(BaseModel):
    """廠商列表查詢參數"""
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=100, description="每頁筆數")
    search: Optional[str] = Field(None, description="搜尋關鍵字")
    business_type: Optional[str] = Field(None, description="業務類型篩選")
    sort_by: str = Field(default="id", description="排序欄位")
    sort_order: str = Field(default="desc", description="排序方向 (asc/desc)")


class VendorStatisticsResponse(BaseModel):
    """廠商統計回應"""
    success: bool = True
    data: dict = Field(..., description="統計資料")

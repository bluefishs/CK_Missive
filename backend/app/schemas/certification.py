"""
證照紀錄 Pydantic Schema

用於承辦同仁證照管理
"""
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.common import PaginatedResponse


# 證照類型選項
CERT_TYPES = ['核發證照', '評量證書', '訓練證明']

# 證照狀態選項
CERT_STATUS = ['有效', '已過期', '已撤銷']


class CertificationBase(BaseModel):
    """證照基礎 Schema"""
    cert_type: str = Field(..., description="證照類型: 核發證照/評量證書/訓練證明")
    cert_name: str = Field(..., max_length=200, description="證照名稱")
    issuing_authority: Optional[str] = Field(None, max_length=200, description="核發機關")
    cert_number: Optional[str] = Field(None, max_length=100, description="證照編號")
    issue_date: Optional[date] = Field(None, description="核發日期")
    expiry_date: Optional[date] = Field(None, description="有效期限（可為空表示永久有效）")
    status: str = Field("有效", description="狀態: 有效/已過期/已撤銷")
    notes: Optional[str] = Field(None, description="備註")


class CertificationCreate(CertificationBase):
    """建立證照 Schema"""
    user_id: int = Field(..., description="關聯的使用者ID")


class CertificationUpdate(BaseModel):
    """更新證照 Schema"""
    cert_type: Optional[str] = Field(None, description="證照類型")
    cert_name: Optional[str] = Field(None, max_length=200, description="證照名稱")
    issuing_authority: Optional[str] = Field(None, max_length=200, description="核發機關")
    cert_number: Optional[str] = Field(None, max_length=100, description="證照編號")
    issue_date: Optional[date] = Field(None, description="核發日期")
    expiry_date: Optional[date] = Field(None, description="有效期限")
    status: Optional[str] = Field(None, description="狀態")
    notes: Optional[str] = Field(None, description="備註")


class CertificationResponse(BaseModel):
    """證照回應 Schema"""
    id: int
    user_id: int
    cert_type: str
    cert_name: str
    issuing_authority: Optional[str] = None
    cert_number: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: str = "有效"
    notes: Optional[str] = None
    attachment_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CertificationListResponse(PaginatedResponse):
    """
    證照列表回應 Schema（統一分頁格式）
    """
    items: List[CertificationResponse] = Field(default=[], description="證照列表")


class CertificationListParams(BaseModel):
    """證照列表查詢參數"""
    page: int = Field(1, ge=1, description="頁碼")
    page_size: int = Field(20, ge=1, le=100, description="每頁筆數")
    cert_type: Optional[str] = Field(None, description="證照類型篩選")
    status: Optional[str] = Field(None, description="狀態篩選")
    keyword: Optional[str] = Field(None, description="關鍵字搜尋")

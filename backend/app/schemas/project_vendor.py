#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案件與廠商關聯相關的Pydantic Schema定義
"""

from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict, field_validator # 新增 ConfigDict, field_validator

class ProjectVendorBase(BaseModel):
    """案件與廠商關聯基礎Schema"""
    project_id: int = Field(..., description="案件ID")
    vendor_id: int = Field(..., description="廠商ID")
    role: Optional[str] = Field(None, max_length=50, description="廠商角色")
    contract_amount: Optional[float] = Field(None, ge=0, description="合約金額")
    start_date: Optional[date] = Field(None, description="合作開始日期")
    end_date: Optional[date] = Field(None, description="合作結束日期")
    status: Optional[str] = Field("active", max_length=20, description="合作狀態")

    @field_validator('end_date') # 使用 field_validator
    @classmethod
    def validate_end_date(cls, v, info): # info 替代 values
        if v and 'start_date' in info.data and info.data['start_date']:
            if v < info.data['start_date']:
                raise ValueError('結束日期不能早於開始日期')
        return v

    @field_validator('contract_amount') # 使用 field_validator
    @classmethod
    def validate_contract_amount(cls, v):
        if v is not None and v < 0:
            raise ValueError('合約金額不能為負數')
        return v

    @field_validator('status') # 使用 field_validator
    @classmethod
    def validate_status(cls, v):
        allowed_statuses = ['active', 'inactive', 'completed', 'cancelled']
        if v and v not in allowed_statuses:
            raise ValueError(f'狀態必須是以下之一: {allowed_statuses}')
        return v

    @field_validator('role') # 使用 field_validator
    @classmethod
    def validate_role(cls, v):
        if v:
            # 更新為新的業務類別選項
            allowed_roles = ['測量業務', '系統業務', '查估業務', '其他類別']
            if v not in allowed_roles:
                raise ValueError(f'業務類別必須是以下之一: {allowed_roles}')
        return v

class ProjectVendorCreate(ProjectVendorBase):
    """建立案件與廠商關聯Schema"""
    pass

class ProjectVendorUpdate(BaseModel):
    """更新案件與廠商關聯Schema"""
    role: Optional[str] = Field(None, max_length=50, description="廠商角色")
    contract_amount: Optional[float] = Field(None, ge=0, description="合約金額")
    start_date: Optional[date] = Field(None, description="合作開始日期")
    end_date: Optional[date] = Field(None, description="合作結束日期")
    status: Optional[str] = Field(None, max_length=20, description="合作狀態")

    @field_validator('end_date') # 使用 field_validator
    @classmethod
    def validate_end_date(cls, v, info):
        if v and 'start_date' in info.data and info.data['start_date']:
            if v < info.data['start_date']:
                raise ValueError('結束日期不能早於開始日期')
        return v

    @field_validator('contract_amount') # 使用 field_validator
    @classmethod
    def validate_contract_amount(cls, v):
        if v is not None and v < 0:
            raise ValueError('合約金額不能為負數')
        return v

    @field_validator('status') # 使用 field_validator
    @classmethod
    def validate_status(cls, v):
        if v:
            allowed_statuses = ['active', 'inactive', 'completed', 'cancelled']
            if v not in allowed_statuses:
                raise ValueError(f'狀態必須是以下之一: {allowed_statuses}')
        return v

    @field_validator('role') # 使用 field_validator
    @classmethod
    def validate_role(cls, v):
        if v:
            # 更新為新的業務類別選項
            allowed_roles = ['測量業務', '系統業務', '查估業務', '其他類別']
            if v not in allowed_roles:
                raise ValueError(f'業務類別必須是以下之一: {allowed_roles}')
        return v

class ProjectVendorResponse(BaseModel):
    """案件與廠商關聯回應Schema"""
    project_id: int
    vendor_id: int
    vendor_name: str
    vendor_code: Optional[str] = None
    vendor_contact_person: Optional[str] = None
    vendor_phone: Optional[str] = None
    vendor_business_type: Optional[str] = None
    role: Optional[str] = None
    contract_amount: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True) # 使用 model_config

class ProjectVendorListResponse(BaseModel):
    """案件廠商關聯列表回應Schema"""
    project_id: int
    project_name: str
    associations: List[ProjectVendorResponse]
    total: int = Field(..., description="總關聯數")

class VendorProjectResponse(BaseModel):
    """廠商案件關聯回應Schema"""
    vendor_id: int
    vendor_name: str
    project_id: int
    project_name: str
    project_code: Optional[str] = None
    project_year: Optional[int] = None
    project_category: Optional[str] = None
    project_status: Optional[str] = None
    role: Optional[str] = None
    contract_amount: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    association_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True) # 使用 model_config

class VendorProjectListResponse(BaseModel):
    """廠商案件關聯列表回應Schema"""
    vendor_id: int
    vendor_name: str
    associations: List[VendorProjectResponse]
    total: int = Field(..., description="總關聯數")


# ============================================================================
# 查詢參數 Schema
# ============================================================================

class VendorAssociationListQuery(BaseModel):
    """廠商關聯列表查詢參數"""
    skip: int = Field(default=0, ge=0, description="跳過筆數")
    limit: int = Field(default=100, ge=1, le=1000, description="限制筆數")
    project_id: Optional[int] = Field(None, description="案件 ID 篩選")
    vendor_id: Optional[int] = Field(None, description="廠商 ID 篩選")
    status: Optional[str] = Field(None, description="狀態篩選")
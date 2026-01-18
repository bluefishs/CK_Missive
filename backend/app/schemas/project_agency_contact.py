#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
專案機關承辦相關的Pydantic Schema定義
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, EmailStr


class ProjectAgencyContactBase(BaseModel):
    """機關承辦基礎Schema"""
    contact_name: str = Field(..., min_length=1, max_length=100, description="承辦人姓名")
    position: Optional[str] = Field(None, max_length=100, description="職稱")
    department: Optional[str] = Field(None, max_length=200, description="單位/科室")
    phone: Optional[str] = Field(None, max_length=50, description="電話")
    mobile: Optional[str] = Field(None, max_length=50, description="手機")
    email: Optional[str] = Field(None, max_length=100, description="電子郵件")
    is_primary: Optional[bool] = Field(False, description="是否為主要承辦人")
    notes: Optional[str] = Field(None, description="備註")


class ProjectAgencyContactCreate(ProjectAgencyContactBase):
    """建立機關承辦Schema"""
    project_id: int = Field(..., description="專案ID")


class ProjectAgencyContactUpdate(BaseModel):
    """更新機關承辦Schema"""
    contact_name: Optional[str] = Field(None, min_length=1, max_length=100, description="承辦人姓名")
    position: Optional[str] = Field(None, max_length=100, description="職稱")
    department: Optional[str] = Field(None, max_length=200, description="單位/科室")
    phone: Optional[str] = Field(None, max_length=50, description="電話")
    mobile: Optional[str] = Field(None, max_length=50, description="手機")
    email: Optional[str] = Field(None, max_length=100, description="電子郵件")
    is_primary: Optional[bool] = Field(None, description="是否為主要承辦人")
    notes: Optional[str] = Field(None, description="備註")


class ProjectAgencyContactResponse(ProjectAgencyContactBase):
    """機關承辦回應Schema"""
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectAgencyContactListResponse(BaseModel):
    """機關承辦列表回應Schema"""
    items: List[ProjectAgencyContactResponse] = Field(default=[], description="機關承辦列表")
    total: int = Field(..., description="總筆數")


# ============================================================================
# 更新請求 Schema
# ============================================================================

class UpdateContactRequest(BaseModel):
    """更新機關承辦請求"""
    contact_id: int = Field(..., description="承辦人 ID")
    contact_name: Optional[str] = Field(None, min_length=1, max_length=100, description="承辦人姓名")
    position: Optional[str] = Field(None, max_length=100, description="職稱")
    department: Optional[str] = Field(None, max_length=200, description="單位/科室")
    phone: Optional[str] = Field(None, max_length=50, description="電話")
    mobile: Optional[str] = Field(None, max_length=50, description="手機")
    email: Optional[str] = Field(None, max_length=100, description="電子郵件")
    is_primary: Optional[bool] = Field(None, description="是否為主要承辦人")
    notes: Optional[str] = Field(None, description="備註")

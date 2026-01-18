#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案件與承辦同仁關聯相關的Pydantic Schema定義
"""

from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ProjectStaffBase(BaseModel):
    """案件與承辦同仁關聯基礎Schema"""
    project_id: int = Field(..., description="案件ID")
    user_id: int = Field(..., description="使用者ID")
    role: Optional[str] = Field("member", max_length=50, description="角色 (主辦/協辦/支援)")
    is_primary: bool = Field(False, description="是否為主要負責人")
    start_date: Optional[date] = Field(None, description="開始日期")
    end_date: Optional[date] = Field(None, description="結束日期")
    status: Optional[str] = Field("active", max_length=50, description="狀態")
    notes: Optional[str] = Field(None, description="備註")

    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v, info):
        if v and 'start_date' in info.data and info.data['start_date']:
            if v < info.data['start_date']:
                raise ValueError('結束日期不能早於開始日期')
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed_statuses = ['active', 'inactive', 'completed']
        if v and v not in allowed_statuses:
            raise ValueError(f'狀態必須是以下之一: {allowed_statuses}')
        return v

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v:
            # 專案角色選項 (與前端 STAFF_ROLE_OPTIONS 一致)
            allowed_roles = [
                '主辦', '協辦', '支援', 'member',
                '計畫主持', '計畫協同', '專案PM', '職安主管'
            ]
            if v not in allowed_roles:
                raise ValueError(f'專案角色必須是以下之一: {allowed_roles}')
        return v


class ProjectStaffCreate(ProjectStaffBase):
    """建立案件與承辦同仁關聯Schema"""
    pass


class ProjectStaffUpdate(BaseModel):
    """更新案件與承辦同仁關聯Schema"""
    role: Optional[str] = Field(None, max_length=50, description="角色")
    is_primary: Optional[bool] = Field(None, description="是否為主要負責人")
    start_date: Optional[date] = Field(None, description="開始日期")
    end_date: Optional[date] = Field(None, description="結束日期")
    status: Optional[str] = Field(None, max_length=50, description="狀態")
    notes: Optional[str] = Field(None, description="備註")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v:
            allowed_statuses = ['active', 'inactive', 'completed']
            if v not in allowed_statuses:
                raise ValueError(f'狀態必須是以下之一: {allowed_statuses}')
        return v

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v:
            # 專案角色選項 (與前端 STAFF_ROLE_OPTIONS 一致)
            allowed_roles = [
                '主辦', '協辦', '支援', 'member',
                '計畫主持', '計畫協同', '專案PM', '職安主管'
            ]
            if v not in allowed_roles:
                raise ValueError(f'專案角色必須是以下之一: {allowed_roles}')
        return v


class ProjectStaffResponse(BaseModel):
    """案件與承辦同仁關聯回應Schema"""
    id: int
    project_id: int
    user_id: int
    user_name: str
    user_email: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_primary: bool = False
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectStaffListResponse(BaseModel):
    """案件承辦同仁列表回應Schema"""
    project_id: int
    project_name: str
    staff: List[ProjectStaffResponse]
    total: int = Field(..., description="總人數")


# ============================================================================
# 查詢參數 Schema
# ============================================================================

class StaffListQuery(BaseModel):
    """承辦同仁列表查詢參數"""
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=100, description="每頁筆數")
    project_id: Optional[int] = Field(None, description="案件 ID 篩選")
    user_id: Optional[int] = Field(None, description="使用者 ID 篩選")
    status: Optional[str] = Field(None, description="狀態篩選")

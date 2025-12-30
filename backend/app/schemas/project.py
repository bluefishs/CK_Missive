#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
承攬案件相關的Pydantic Schema定義
"""

from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict, field_validator # 新增 ConfigDict, field_validator

class ProjectBase(BaseModel):
    """承攬案件基礎Schema"""
    project_name: str = Field(..., min_length=1, max_length=500, description="專案名稱")
    project_code: Optional[str] = Field(None, max_length=50, description="專案編號")
    year: Optional[int] = Field(None, ge=1990, le=2050, description="年度")
    category: Optional[str] = Field(None, max_length=50, description="案件類別")
    status: Optional[str] = Field(None, max_length=50, description="案件狀態")
    client_agency: Optional[str] = Field(None, max_length=200, description="委託單位")
    contract_amount: Optional[float] = Field(None, ge=0, description="合約金額")
    start_date: Optional[date] = Field(None, description="起始日期")
    end_date: Optional[date] = Field(None, description="結束日期")
    description: Optional[str] = Field(None, description="專案描述")

    @field_validator('end_date') # 使用 field_validator
    @classmethod
    def validate_end_date(cls, v, info): # info 替代 values
        if v and 'start_date' in info.data and info.data['start_date']:
            if v < info.data['start_date']:
                raise ValueError('結束日期不能早於起始日期')
        return v

    @field_validator('contract_amount') # 使用 field_validator
    @classmethod
    def validate_contract_amount(cls, v):
        if v is not None and v < 0:
            raise ValueError('合約金額不能為負數')
        return v

class ProjectCreate(ProjectBase):
    """建立承攬案件Schema"""
    pass

class ProjectUpdate(BaseModel):
    """更新承攬案件Schema"""
    project_name: Optional[str] = Field(None, min_length=1, max_length=500, description="專案名稱")
    project_code: Optional[str] = Field(None, max_length=50, description="專案編號")
    year: Optional[int] = Field(None, ge=1990, le=2050, description="年度")
    category: Optional[str] = Field(None, max_length=50, description="案件類別")
    status: Optional[str] = Field(None, max_length=50, description="案件狀態")
    client_agency: Optional[str] = Field(None, max_length=200, description="委託單位")
    contract_amount: Optional[float] = Field(None, ge=0, description="合約金額")
    start_date: Optional[date] = Field(None, description="起始日期")
    end_date: Optional[date] = Field(None, description="結束日期")
    description: Optional[str] = Field(None, description="專案描述")

    @field_validator('end_date') # 使用 field_validator
    @classmethod
    def validate_end_date(cls, v, info): # info 替代 values
        if v and 'start_date' in info.data and info.data['start_date']:
            if v < info.data['start_date']:
                raise ValueError('結束日期不能早於起始日期')
        return v

    @field_validator('contract_amount') # 使用 field_validator
    @classmethod
    def validate_contract_amount(cls, v):
        if v is not None and v < 0:
            raise ValueError('合約金額不能為負數')
        return v

class ProjectResponse(ProjectBase):
    """承攬案件回應Schema"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True) # 使用 model_config

class ProjectListResponse(BaseModel):
    """承攬案件列表回應Schema"""
    projects: List[ProjectResponse]
    total: int = Field(..., description="總筆數")
    skip: int = Field(..., description="跳過筆數")
    limit: int = Field(..., description="限制筆數")

class ProjectOption(BaseModel):
    """承攬案件選項Schema (用於下拉選單)"""
    id: int
    project_name: str
    project_code: Optional[str] = None
    year: Optional[int] = None

    model_config = ConfigDict(from_attributes=True) # 使用 model_config
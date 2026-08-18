#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
專案機關承辦相關的Pydantic Schema定義
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator


class ProjectAgencyContactBase(BaseModel):
    """機關承辦基礎Schema"""
    contact_name: str = Field(..., min_length=1, max_length=100, description="承辦人姓名")
    position: Optional[str] = Field(None, max_length=100, description="職稱")
    department: Optional[str] = Field(None, max_length=200, description="單位/科室")
    phone: Optional[str] = Field(None, max_length=50, description="電話")
    mobile: Optional[str] = Field(None, max_length=50, description="手機")
    email: Optional[EmailStr] = Field(None, max_length=100, description="電子郵件")
    is_primary: Optional[bool] = Field(False, description="是否為主要承辦人")
    notes: Optional[str] = Field(None, description="備註")


# ---------------------------------------------------------------------------
# 2026-08-18：表單清空欄位時送的是 `""`，而 `Optional[EmailStr]` 與
# `min_length=1` 都只接受 `None` —— 於是**清空 email 或姓名再儲存就 422**，
# 而錯誤訊息說「不是有效的電子郵件」，使用者看不懂自己做錯什麼
# （他做的是「把這一欄清掉」，那是完全正常的操作）。
#
# owner 2026-08-18 實際踩到：`POST /api/project-agency-contacts/update` 422。
#
# 修在 schema 而不是前端：**每個表單都要記得把空字串轉成 null** 是行不通的
# ——漏一個就是一個 422，而它只在「使用者剛好清空那一欄」時發生。
# 語意上 `""` 與 `None` 對選填欄位本來就是同一件事：都是「沒有值」。
#
# 只用於**更新**類 schema；建立時的必填欄位仍應拒絕空字串。
def _blank_to_none(v):
    return None if isinstance(v, str) and not v.strip() else v


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
    email: Optional[EmailStr] = Field(None, max_length=100, description="電子郵件")
    is_primary: Optional[bool] = Field(None, description="是否為主要承辦人")
    notes: Optional[str] = Field(None, description="備註")

    # 空字串 → None（見檔頭 `_blank_to_none` 說明）
    _blank = field_validator(
        "contact_name", "position", "department", "phone", "mobile", "email", "notes",
        mode="before",
    )(classmethod(lambda cls, v: _blank_to_none(v)))


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
    email: Optional[EmailStr] = Field(None, max_length=100, description="電子郵件")
    is_primary: Optional[bool] = Field(None, description="是否為主要承辦人")
    notes: Optional[str] = Field(None, description="備註")

    # 空字串 → None（見檔頭 `_blank_to_none` 說明）
    _blank = field_validator(
        "contact_name", "position", "department", "phone", "mobile", "email", "notes",
        mode="before",
    )(classmethod(lambda cls, v: _blank_to_none(v)))

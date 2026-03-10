"""Prompt 版本管理 Schema"""
from typing import List, Optional

from pydantic import BaseModel, Field


class PromptVersionItem(BaseModel):
    """Prompt 版本項目"""
    id: int
    feature: str
    version: int
    system_prompt: str
    user_template: Optional[str] = None
    is_active: bool
    description: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None


class PromptListRequest(BaseModel):
    """列出 prompt 版本請求"""
    feature: Optional[str] = Field(None, description="按功能名稱篩選")


class PromptListResponse(BaseModel):
    """列出 prompt 版本回應"""
    items: List[PromptVersionItem]
    total: int
    features: List[str] = Field(description="所有可用的功能名稱")


class PromptCreateRequest(BaseModel):
    """新增 prompt 版本請求"""
    feature: str = Field(..., description="功能名稱")
    system_prompt: str = Field(..., min_length=1, description="系統提示詞")
    user_template: Optional[str] = Field(None, description="使用者提示詞模板")
    description: Optional[str] = Field(None, description="版本說明")
    activate: bool = Field(False, description="是否立即啟用")


class PromptCreateResponse(BaseModel):
    """新增 prompt 版本回應"""
    success: bool
    item: PromptVersionItem
    message: str


class PromptActivateRequest(BaseModel):
    """啟用 prompt 版本請求"""
    id: int = Field(..., description="要啟用的版本 ID")


class PromptActivateResponse(BaseModel):
    """啟用 prompt 版本回應"""
    success: bool
    message: str
    activated: PromptVersionItem


class PromptCompareRequest(BaseModel):
    """比較 prompt 版本請求"""
    id_a: int = Field(..., description="版本 A 的 ID")
    id_b: int = Field(..., description="版本 B 的 ID")


class PromptDiff(BaseModel):
    """版本差異"""
    field: str
    value_a: Optional[str] = None
    value_b: Optional[str] = None
    changed: bool


class PromptCompareResponse(BaseModel):
    """比較 prompt 版本回應"""
    version_a: PromptVersionItem
    version_b: PromptVersionItem
    diffs: List[PromptDiff]

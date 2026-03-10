"""同義詞管理 Schema"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class AISynonymBase(BaseModel):
    """同義詞群組基礎 Schema"""
    category: str = Field(..., min_length=1, max_length=100, description="分類")
    words: str = Field(..., min_length=1, description="同義詞列表，逗號分隔")
    is_active: bool = Field(default=True, description="是否啟用")


class AISynonymCreate(AISynonymBase):
    """建立同義詞群組請求"""
    pass


class AISynonymUpdate(BaseModel):
    """更新同義詞群組請求"""
    id: int = Field(..., description="同義詞群組 ID")
    category: Optional[str] = Field(None, min_length=1, max_length=100, description="分類")
    words: Optional[str] = Field(None, min_length=1, description="同義詞列表，逗號分隔")
    is_active: Optional[bool] = Field(None, description="是否啟用")


class AISynonymResponse(AISynonymBase):
    """同義詞群組回應"""
    id: int = Field(..., description="同義詞群組 ID")
    created_at: Optional[datetime] = Field(None, description="建立時間")
    updated_at: Optional[datetime] = Field(None, description="更新時間")

    model_config = ConfigDict(from_attributes=True)


class AISynonymListRequest(BaseModel):
    """同義詞列表查詢請求"""
    category: Optional[str] = Field(None, description="分類篩選")
    is_active: Optional[bool] = Field(None, description="啟用狀態篩選")


class AISynonymListResponse(BaseModel):
    """同義詞列表回應"""
    items: List[AISynonymResponse] = Field(default=[], description="同義詞群組列表")
    total: int = Field(default=0, description="總筆數")
    categories: List[str] = Field(default=[], description="所有分類列表")


class AISynonymDeleteRequest(BaseModel):
    """刪除同義詞群組請求"""
    id: int = Field(..., description="同義詞群組 ID")


class AISynonymReloadResponse(BaseModel):
    """重新載入同義詞回應"""
    success: bool = Field(default=True, description="是否成功")
    total_groups: int = Field(default=0, description="載入的同義詞群組數")
    total_words: int = Field(default=0, description="載入的詞彙總數")
    message: str = Field(default="", description="訊息")

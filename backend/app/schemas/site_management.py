"""
網站管理相關的 Pydantic Schema 定義
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# === 導覽列項目相關 Schema ===

class NavigationItemBase(BaseModel):
    """導覽項目基礎 Schema"""
    title: str = Field(..., description="導覽項目標題", max_length=100)
    key: str = Field(..., description="唯一識別碼", max_length=100)
    path: Optional[str] = Field(None, description="路由路徑", max_length=200)
    icon: Optional[str] = Field(None, description="圖示名稱", max_length=50)
    parent_id: Optional[int] = Field(None, description="父級項目ID")
    sort_order: int = Field(0, description="排序順序")
    is_visible: bool = Field(True, description="是否顯示")
    is_enabled: bool = Field(True, description="是否啟用")
    level: int = Field(1, description="層級深度", ge=1, le=5)
    description: Optional[str] = Field(None, description="項目描述", max_length=300)
    target: str = Field("_self", description="連結開啟方式")
    permission_required: Optional[str] = Field(None, description="所需權限", max_length=100)

class NavigationItemCreate(NavigationItemBase):
    """創建導覽項目 Schema"""
    pass

class NavigationItemUpdate(BaseModel):
    """更新導覽項目 Schema"""
    title: Optional[str] = Field(None, description="導覽項目標題", max_length=100)
    path: Optional[str] = Field(None, description="路由路徑", max_length=200)
    icon: Optional[str] = Field(None, description="圖示名稱", max_length=50)
    parent_id: Optional[int] = Field(None, description="父級項目ID")
    sort_order: Optional[int] = Field(None, description="排序順序")
    is_visible: Optional[bool] = Field(None, description="是否顯示")
    is_enabled: Optional[bool] = Field(None, description="是否啟用")
    level: Optional[int] = Field(None, description="層級深度", ge=1, le=5)
    description: Optional[str] = Field(None, description="項目描述", max_length=300)
    target: Optional[str] = Field(None, description="連結開啟方式")
    permission_required: Optional[str] = Field(None, description="所需權限", max_length=100)

class NavigationItemResponse(NavigationItemBase):
    """導覽項目回應 Schema"""
    id: int
    created_at: datetime
    updated_at: datetime
    children: Optional[List['NavigationItemResponse']] = Field(default_factory=list, description="子項目列表")
    
    class Config:
        from_attributes = True

class NavigationTreeResponse(BaseModel):
    """導覽樹狀結構回應 Schema"""
    items: List[NavigationItemResponse]
    total: int
    
class NavigationItemListResponse(BaseModel):
    """導覽項目列表回應 Schema"""
    items: List[NavigationItemResponse]
    total: int
    skip: int
    limit: int

# === 排序相關 Schema ===

class NavigationSortItem(BaseModel):
    """導覽項目排序 Schema"""
    id: int
    sort_order: int

class NavigationSortRequest(BaseModel):
    """導覽項目排序請求 Schema"""
    items: List[NavigationSortItem]

# === 網站配置相關 Schema ===

class SiteConfigBase(BaseModel):
    """網站配置基礎 Schema"""
    key: str = Field(..., description="配置項鍵值", max_length=100)
    value: Optional[str] = Field(None, description="配置項值")
    description: Optional[str] = Field(None, description="配置說明", max_length=300)
    category: str = Field("general", description="配置分類", max_length=50)
    is_active: bool = Field(True, description="是否啟用")

class SiteConfigCreate(SiteConfigBase):
    """創建網站配置 Schema"""
    pass

class SiteConfigUpdate(BaseModel):
    """更新網站配置 Schema"""
    value: Optional[str] = Field(None, description="配置項值")
    description: Optional[str] = Field(None, description="配置說明", max_length=300)
    category: Optional[str] = Field(None, description="配置分類", max_length=50)
    is_active: Optional[bool] = Field(None, description="是否啟用")

class SiteConfigResponse(SiteConfigBase):
    """網站配置回應 Schema"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class SiteConfigListResponse(BaseModel):
    """網站配置列表回應 Schema"""
    configs: List[SiteConfigResponse]
    total: int
    skip: int
    limit: int

# === 批量操作相關 Schema ===

class BulkOperationRequest(BaseModel):
    """批量操作請求 Schema"""
    ids: List[int] = Field(..., description="要操作的項目ID列表")
    action: str = Field(..., description="操作類型", pattern="^(delete|enable|disable|show|hide)$")

class BulkOperationResponse(BaseModel):
    """批量操作回應 Schema"""
    success_count: int
    failed_count: int
    failed_ids: List[int] = Field(default_factory=list)
    message: str

# === 導覽列預設數據 Schema ===

class DefaultNavigationData(BaseModel):
    """預設導覽列數據 Schema"""
    navigation_items: List[NavigationItemCreate]

# 解決 forward reference 問題
NavigationItemResponse.model_rebuild()
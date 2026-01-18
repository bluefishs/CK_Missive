"""
Pydantic schemas for Reminder Management
提醒管理相關的統一 Schema 定義

包含：
- 提醒模板配置
- 提醒操作請求
- 提醒狀態回應
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# =============================================================================
# 提醒模板 Schema
# =============================================================================

class ReminderTemplateConfig(BaseModel):
    """提醒模板配置"""
    minutes: int = Field(..., description="提前分鐘數")
    type: str = Field(default="email", description="提醒類型 (email/system)")
    priority: int = Field(default=3, description="優先級 (1-5)")
    title: Optional[str] = Field(None, description="自訂標題")


class CustomReminderTemplate(BaseModel):
    """自訂提醒模板"""
    event_id: int = Field(..., description="事件 ID")
    template: List[ReminderTemplateConfig] = Field(..., description="提醒配置列表")


# =============================================================================
# 提醒操作 Schema
# =============================================================================

class ReminderActionRequest(BaseModel):
    """提醒操作請求 (新增/刪除)"""
    action: str = Field(..., description="操作類型 ('add' or 'delete')")
    reminder_type: Optional[str] = Field(default="system", description="提醒類型")
    reminder_minutes: Optional[int] = Field(default=60, description="提前分鐘數")
    reminder_time: Optional[str] = Field(None, description="指定提醒時間")
    reminder_id: Optional[int] = Field(None, description="提醒 ID (刪除時使用)")


# =============================================================================
# 提醒回應 Schema
# =============================================================================

class ReminderStatusResponse(BaseModel):
    """提醒狀態回應"""
    total: int = Field(..., description="總提醒數")
    by_status: Dict[str, int] = Field(default={}, description="各狀態數量統計")
    reminders: List[Dict[str, Any]] = Field(default=[], description="提醒列表")


class BatchProcessResponse(BaseModel):
    """批量處理回應"""
    total: int = Field(..., description="處理總數")
    sent: int = Field(default=0, description="已發送數")
    failed: int = Field(default=0, description="失敗數")
    retries: int = Field(default=0, description="重試數")


# =============================================================================
# 提醒配置 Schema
# =============================================================================

class ReminderConfig(BaseModel):
    """提醒配置"""
    minutes_before: int = Field(..., description="提前分鐘數")
    reminder_type: str = Field(default="system", description="提醒類型")
    enabled: bool = Field(default=True, description="是否啟用")

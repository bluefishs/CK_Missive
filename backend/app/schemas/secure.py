"""
Pydantic schemas for Secure Site Management
安全站點管理相關的統一 Schema 定義
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# 安全請求/回應 Schema
# =============================================================================

class SecureRequest(BaseModel):
    """安全請求基礎模型"""
    action: str = Field(..., description="操作類型")
    csrf_token: Optional[str] = Field(None, description="CSRF 防護令牌 (開發模式下可選)")
    data: Optional[Dict[str, Any]] = Field(None, description="請求數據")

    model_config = ConfigDict(extra="forbid")


class SecureResponse(BaseModel):
    """安全回應基礎模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作訊息")
    data: Optional[Dict[str, Any]] = Field(None, description="回應數據")
    csrf_token: Optional[str] = Field(None, description="新的 CSRF 令牌")

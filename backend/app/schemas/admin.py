"""
管理後台相關的 Pydantic Schema 定義
"""
from pydantic import BaseModel, Field
from typing import Optional


class AdminQueryRequest(BaseModel):
    """管理後台 SQL 查詢請求"""
    query: str = Field(..., min_length=1, max_length=5000, description="SQL SELECT 查詢語句")


class AdminLineBindRequest(BaseModel):
    """管理員手動綁定 LINE 帳號"""
    line_user_id: str = Field(..., min_length=10, max_length=64, description="LINE User ID (U 開頭)")
    line_display_name: Optional[str] = Field(None, max_length=100, description="LINE 顯示名稱")

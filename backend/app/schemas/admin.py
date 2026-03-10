"""
管理後台相關的 Pydantic Schema 定義
"""
from pydantic import BaseModel, Field


class AdminQueryRequest(BaseModel):
    """管理後台 SQL 查詢請求"""
    query: str = Field(..., min_length=1, max_length=5000, description="SQL SELECT 查詢語句")

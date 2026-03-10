"""搜尋歷史 + 建議 Schema"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class SearchHistoryItem(BaseModel):
    """搜尋歷史項目"""
    id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    query: str
    parsed_intent: Optional[Dict[str, Any]] = None
    results_count: int = 0
    search_strategy: Optional[str] = None
    source: Optional[str] = None
    synonym_expanded: bool = False
    related_entity: Optional[str] = None
    latency_ms: Optional[int] = None
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SearchFeedbackRequest(BaseModel):
    """搜尋回饋請求"""
    history_id: int = Field(..., description="搜尋歷史 ID")
    score: int = Field(..., ge=-1, le=1, description="回饋分數 (1=有用, -1=無用)")


class SearchFeedbackResponse(BaseModel):
    """搜尋回饋回應"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="", description="訊息")


class SearchHistoryListRequest(BaseModel):
    """搜尋歷史列表請求"""
    page: int = Field(default=1, ge=1, description="頁碼")
    page_size: int = Field(default=20, ge=1, le=100, description="每頁筆數")
    date_from: Optional[str] = Field(None, description="起始日期 YYYY-MM-DD")
    date_to: Optional[str] = Field(None, description="結束日期 YYYY-MM-DD")
    search_strategy: Optional[str] = Field(None, description="搜尋策略篩選")
    source: Optional[str] = Field(None, description="來源篩選")
    keyword: Optional[str] = Field(None, max_length=200, description="查詢關鍵字篩選")


class SearchHistoryListResponse(BaseModel):
    """搜尋歷史列表回應"""
    items: List[SearchHistoryItem] = []
    total: int = 0
    page: int = 1
    page_size: int = 20


class DailyTrend(BaseModel):
    """日趨勢項目"""
    date: str
    count: int


class TopQuery(BaseModel):
    """熱門查詢項目"""
    query: str
    count: int
    avg_results: float


class ClearSearchHistoryRequest(BaseModel):
    """清除搜尋歷史請求"""
    before_date: Optional[str] = Field(
        None, description="清除此日期（含）之前的記錄，格式 YYYY-MM-DD。未指定則清除全部。"
    )


class ClearSearchHistoryResponse(BaseModel):
    """清除搜尋歷史回應"""
    success: bool = Field(default=True, description="是否成功")
    deleted_count: int = Field(default=0, description="刪除的記錄數")
    error: Optional[str] = Field(None, description="錯誤訊息")


class SearchStatsResponse(BaseModel):
    """搜尋統計回應"""
    total_searches: int = 0
    today_searches: int = 0
    rule_engine_hit_rate: float = 0.0
    avg_latency_ms: float = 0.0
    avg_confidence: float = 0.0
    daily_trend: List[DailyTrend] = []
    top_queries: List[TopQuery] = []
    strategy_distribution: Dict[str, int] = {}
    source_distribution: Dict[str, int] = {}
    entity_distribution: Dict[str, int] = {}


class QuerySuggestionRequest(BaseModel):
    """搜尋建議請求"""
    prefix: str = Field("", max_length=200, description="查詢前綴 (空字串=僅回傳熱門)")
    limit: int = Field(default=8, ge=1, le=20, description="建議數量上限")


class QuerySuggestionItem(BaseModel):
    """單筆搜尋建議"""
    query: str = Field(..., description="建議的查詢文字")
    type: str = Field(..., description="建議類型: popular / history / related")
    count: int = Field(default=0, description="歷史搜尋次數")
    avg_results: float = Field(default=0.0, description="平均結果數")


class QuerySuggestionResponse(BaseModel):
    """搜尋建議回應"""
    suggestions: List[QuerySuggestionItem] = []

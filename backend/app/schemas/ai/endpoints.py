"""AI 端點 Request/Response Schema"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SummaryRequest(BaseModel):
    """摘要生成請求"""
    subject: str = Field(..., description="公文主旨")
    content: Optional[str] = Field(None, description="公文內容")
    sender: Optional[str] = Field(None, description="發文機關")
    max_length: int = Field(100, ge=20, le=500, description="摘要最大長度")


class SummaryResponse(BaseModel):
    """摘要生成回應"""
    summary: str
    confidence: float
    source: str


class ClassifyRequest(BaseModel):
    """分類建議請求"""
    subject: str = Field(..., description="公文主旨")
    content: Optional[str] = Field(None, description="公文內容")
    sender: Optional[str] = Field(None, description="發文機關")


class ClassifyResponse(BaseModel):
    """分類建議回應"""
    doc_type: str
    category: str
    doc_type_confidence: float
    category_confidence: float
    reasoning: Optional[str] = None
    source: str


class KeywordsRequest(BaseModel):
    """關鍵字提取請求"""
    subject: str = Field(..., description="公文主旨")
    content: Optional[str] = Field(None, description="公文內容")
    max_keywords: int = Field(5, ge=1, le=10, description="最大關鍵字數量")


class KeywordsExtractResponse(BaseModel):
    """關鍵字提取回應"""
    keywords: List[str]
    confidence: float
    source: str


class AgencyCandidate(BaseModel):
    """機關候選項"""
    id: int
    name: str
    short_name: Optional[str] = None


class AgencyMatchRequest(BaseModel):
    """機關匹配請求"""
    agency_name: str = Field(..., description="輸入的機關名稱")
    candidates: Optional[List[AgencyCandidate]] = Field(
        None, description="候選機關列表"
    )


class AgencyMatchResult(BaseModel):
    """匹配結果"""
    id: int
    name: str
    score: float


class AgencyMatchResponse(BaseModel):
    """機關匹配回應"""
    best_match: Optional[AgencyMatchResult] = None
    alternatives: List[AgencyMatchResult] = []
    is_new: bool
    reasoning: Optional[str] = None
    source: str


class RateLimitStatus(BaseModel):
    """速率限制狀態"""
    can_proceed: bool = Field(description="是否可繼續請求")
    current_requests: int = Field(description="目前窗口內請求數")
    max_requests: int = Field(description="最大請求數")
    window_seconds: int = Field(description="窗口時間（秒）")


class HealthResponse(BaseModel):
    """健康檢查回應"""
    groq: Dict[str, Any]
    ollama: Dict[str, Any]
    rate_limit: Optional[RateLimitStatus] = Field(None, description="速率限制狀態")


class AIConfigResponse(BaseModel):
    """AI 配置回應"""
    enabled: bool = Field(description="AI 功能是否啟用")
    providers: Dict[str, Any] = Field(description="可用的 AI 提供者")
    rate_limit: Dict[str, int] = Field(description="速率限制設定")
    cache: Dict[str, Any] = Field(description="快取設定")
    features: Dict[str, Dict[str, Any]] = Field(description="各功能的配置")

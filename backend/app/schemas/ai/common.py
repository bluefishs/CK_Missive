"""通用回應 + AI 統計 Schema"""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict


class SuccessResponse(BaseModel):
    """通用成功回應"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="", description="訊息")


class OkResponse(BaseModel):
    """簡易 OK 回應"""
    ok: bool = Field(default=True, description="操作結果")


class AIFeatureStatsDetail(BaseModel):
    """AI 功能統計明細"""
    count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    total_latency_ms: float = 0
    avg_latency_ms: float = 0

    model_config = ConfigDict(extra="allow")


class AIStatsResponse(BaseModel):
    """AI 統計回應"""
    total_requests: int = 0
    by_feature: Dict[str, AIFeatureStatsDetail] = Field(default_factory=dict)
    rate_limit_hits: int = 0
    groq_requests: int = 0
    ollama_requests: int = 0
    fallback_requests: int = 0
    start_time: Optional[str] = None
    source: Optional[str] = None

    model_config = ConfigDict(extra="allow")

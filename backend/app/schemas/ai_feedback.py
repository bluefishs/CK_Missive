# -*- coding: utf-8 -*-
"""
AI 對話回饋 Schema

v1.0.0 - 2026-02-27
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class AIFeedbackSubmitRequest(BaseModel):
    """提交 AI 回答回饋"""
    conversation_id: str = Field(..., min_length=1, max_length=64)
    message_index: int = Field(default=0, ge=0)
    feature_type: str = Field(..., pattern=r"^(agent|rag)$")
    score: int = Field(..., ge=-1, le=1, description="1=有用, -1=無用")
    question: Optional[str] = Field(default=None, max_length=500)
    answer_preview: Optional[str] = Field(default=None, max_length=200)
    feedback_text: Optional[str] = Field(default=None, max_length=500)
    latency_ms: Optional[int] = Field(default=None, ge=0)
    model: Optional[str] = Field(default=None, max_length=50)


class AIFeedbackSubmitResponse(BaseModel):
    """回饋提交回應"""
    success: bool
    message: str = ""


class AIFeedbackItem(BaseModel):
    """回饋記錄項目"""
    id: int
    conversation_id: str
    message_index: int
    feature_type: str
    score: int
    question: Optional[str] = None
    answer_preview: Optional[str] = None
    feedback_text: Optional[str] = None
    latency_ms: Optional[int] = None
    model: Optional[str] = None
    user_id: Optional[int] = None
    created_at: Optional[datetime] = None


class AIFeedbackStatsResponse(BaseModel):
    """回饋統計回應"""
    success: bool
    total_feedback: int = 0
    positive_count: int = 0
    negative_count: int = 0
    positive_rate: float = 0.0
    by_feature: dict = Field(default_factory=dict)
    recent_negative: List[AIFeedbackItem] = Field(default_factory=list)


class AIAnalyticsOverviewResponse(BaseModel):
    """系統使用分析總覽"""
    success: bool
    # AI 功能使用量 (from AIStatsManager)
    ai_feature_usage: dict = Field(default_factory=dict)
    # 回饋摘要
    feedback_summary: dict = Field(default_factory=dict)
    # 搜尋統計
    search_stats: dict = Field(default_factory=dict)
    # 零使用功能
    unused_features: List[str] = Field(default_factory=list)

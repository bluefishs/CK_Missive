"""AI 分析持久化 Schema"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class DocumentAIAnalysisResponse(BaseModel):
    """公文 AI 分析結果回應"""
    id: int
    document_id: int

    # 摘要
    summary: Optional[str] = None
    summary_confidence: Optional[float] = None

    # 分類
    suggested_doc_type: Optional[str] = None
    doc_type_confidence: Optional[float] = None
    suggested_category: Optional[str] = None
    category_confidence: Optional[float] = None
    classification_reasoning: Optional[str] = None

    # 關鍵字
    keywords: Optional[List[str]] = None
    keywords_confidence: Optional[float] = None

    # NER 統計（從 document_entities 聚合）
    entities_count: int = 0
    relations_count: int = 0

    # 元資料
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    processing_ms: int = 0
    status: str = "completed"
    is_stale: bool = False
    analyzed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentAIBriefResponse(BaseModel):
    """公文列表用 AI 簡要（輕量）"""
    document_id: int
    summary: Optional[str] = None
    keywords: Optional[List[str]] = None
    is_stale: bool = False
    has_analysis: bool = False


class DocumentAIAnalysisBatchRequest(BaseModel):
    """批次分析請求"""
    limit: int = Field(default=50, ge=1, le=200, description="批次數量")
    force: bool = Field(default=False, description="強制重新分析")


class DocumentAIAnalysisBatchResponse(BaseModel):
    """批次分析回應"""
    success: bool = True
    processed: int = 0
    success_count: int = 0
    error_count: int = 0
    skip_count: int = 0
    message: str = ""


class DocumentAIAnalysisStatsResponse(BaseModel):
    """分析覆蓋率統計"""
    total_documents: int = 0
    analyzed_documents: int = 0
    stale_documents: int = 0
    without_analysis: int = 0
    coverage_percent: float = 0.0
    avg_processing_ms: float = 0.0

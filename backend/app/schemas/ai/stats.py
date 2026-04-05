"""
AI 統計相關 Schemas

Version: 1.0.0
Created: 2026-03-16

所有 AI 統計 API 端點的 Pydantic model 定義 (SSOT)。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolSuccessRateItem(BaseModel):
    """工具成功率項目"""
    tool_name: str
    total_calls: int
    success_count: int
    success_rate: float
    avg_latency_ms: float
    avg_result_count: float


class ToolSuccessRatesResponse(BaseModel):
    """工具成功率回應"""
    tools: List[ToolSuccessRateItem] = []
    degraded_tools: List[str] = []
    source: str = "db"


class DailyTrendItem(BaseModel):
    """每日趨勢項目"""
    date: str
    query_count: int
    avg_latency_ms: float
    avg_results: float
    avg_feedback: Optional[float] = None


class DailyTrendResponse(BaseModel):
    """每日趨勢回應"""
    trend: List[DailyTrendItem] = []
    days: int = 14


class AgentTraceQuery(BaseModel):
    """Agent 追蹤記錄查詢"""
    context: Optional[str] = None
    feedback_only: bool = False
    limit: int = Field(default=50, le=200)


class AgentTracesResponse(BaseModel):
    """Agent 追蹤記錄回應"""
    traces: List[Dict[str, Any]] = []
    total_count: int = 0
    route_distribution: Dict[str, int] = {}


class TraceToolCallItem(BaseModel):
    """Trace 內的單筆工具呼叫 (V-1.2 Timeline)"""
    tool_name: str
    call_order: int = 0
    duration_ms: int = 0
    success: bool = True
    result_count: int = 0
    error_message: Optional[str] = None
    created_at: Optional[str] = None


class TraceDetailResponse(BaseModel):
    """單筆 Trace 詳情 (V-1.2 Timeline)"""
    id: int
    query_id: str
    question: str
    context: Optional[str] = None
    route_type: str = "llm"
    total_ms: int = 0
    iterations: int = 0
    total_results: int = 0
    correction_triggered: bool = False
    react_triggered: bool = False
    plan_tool_count: int = 0
    model_used: Optional[str] = None
    tools_used: Optional[List[str]] = None
    answer_preview: Optional[str] = None
    feedback_score: Optional[int] = None
    created_at: Optional[str] = None
    tool_calls: List[TraceToolCallItem] = []


class PatternItem(BaseModel):
    """學習模式項目"""
    pattern_key: str
    template: str
    tool_sequence: List[str]
    hit_count: int
    success_rate: float
    avg_latency_ms: float
    score: float


class PatternsResponse(BaseModel):
    """學習模式回應"""
    patterns: List[PatternItem] = []
    total_count: int = 0


class LearningsResponse(BaseModel):
    """持久化學習回應"""
    learnings: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {}


class ProactiveAlertsResponse(BaseModel):
    """主動觸發警報回應"""
    total_alerts: int = 0
    by_severity: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    alerts: List[Dict[str, Any]] = []


class ToolRegistryItem(BaseModel):
    """工具註冊清單項目"""
    name: str
    description: str = ""
    category: str = "other"
    priority: int = 0
    contexts: List[str] = []
    is_degraded: bool = False
    total_calls: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0


class ToolRegistryResponse(BaseModel):
    """工具註冊清單回應"""
    tools: List[ToolRegistryItem] = []
    total_count: int = 0
    degraded_count: int = 0


class RecommendationMatchItem(BaseModel):
    """推薦匹配項目"""
    interest: str = ""
    entity: str = ""
    weight: int = 0


class RecommendationItem(BaseModel):
    """單筆推薦"""
    document_id: int
    subject: str = ""
    doc_type: str = ""
    doc_number: str = ""
    matched_entities: List[RecommendationMatchItem] = []
    score: int = 0
    user_id: Optional[str] = None


class RecommendationsQuery(BaseModel):
    """推薦查詢參數"""
    user_id: Optional[str] = None
    limit: int = Field(default=10, le=50)
    hours: int = Field(default=24, le=168)


class RecommendationsResponse(BaseModel):
    """推薦回應"""
    recommendations: List[RecommendationItem] = []
    total_count: int = 0
    user_count: int = 0


# ── Link Integrity ──


class LinkIntegrityIssue(BaseModel):
    """單筆連結完整性問題"""
    dispatch_id: int
    dispatch_no: str = ""
    document_id: Optional[int] = None
    issue_type: str = ""
    detail: str = ""


class LinkIntegrityStats(BaseModel):
    """連結完整性統計"""
    total_links: int = 0
    total_dispatches: int = 0
    orphan_links: int = 0
    duplicate_links: int = 0
    missing_ck_note_dispatches: int = 0


class LinkIntegrityResponse(BaseModel):
    """連結完整性檢查回應"""
    passed: bool = True
    issues: List[LinkIntegrityIssue] = []
    stats: LinkIntegrityStats = LinkIntegrityStats()


# ── Search Benchmark ──


class BenchmarkRequest(BaseModel):
    """搜尋品質基準測試請求"""
    mode: str = Field(
        default="v1",
        description="Reranker mode: v1 (rule-based), v2 (Gemma4), both (A/B)",
        pattern="^(v1|v2|both)$",
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Top-K for P@K / nDCG@K")
    categories: Optional[List[str]] = Field(
        default=None,
        description="Filter by categories (agency_search, keyword_search, etc.)",
    )


class BenchmarkCategoryMetrics(BaseModel):
    """單一類別的基準指標"""
    avg_precision_at_k: float = 0.0
    avg_mrr: float = 0.0
    avg_latency_ms: float = 0.0
    count: int = 0


class BenchmarkModeSummary(BaseModel):
    """單一模式的彙總指標"""
    avg_precision_at_k: float = 0.0
    avg_mrr: float = 0.0
    avg_ndcg_at_k: float = 0.0
    avg_latency_ms: float = 0.0
    avg_hit_rate: float = 0.0
    meets_minimum_pct: float = 0.0
    total_queries: int = 0
    by_category: Dict[str, BenchmarkCategoryMetrics] = {}


class BenchmarkComparison(BaseModel):
    """A/B 比較結果"""
    precision_delta: float = 0.0
    mrr_delta: float = 0.0
    latency_delta_ms: float = 0.0
    hit_rate_delta: float = 0.0
    v2_better_precision: bool = False
    v2_faster: bool = False


class BenchmarkQueryResult(BaseModel):
    """單筆查詢的基準結果"""
    id: str = ""
    query: str
    category: str
    mode: str
    latency_ms: float = 0.0
    result_count: int = 0
    precision_at_k: float = 0.0
    mrr: float = 0.0
    ndcg_at_k: float = 0.0
    keyword_hit_rate: float = 0.0
    meets_minimum: bool = True


class BenchmarkResponse(BaseModel):
    """搜尋品質基準測試回應"""
    v1: List[BenchmarkQueryResult] = []
    v2: List[BenchmarkQueryResult] = []
    summary: Dict[str, Any] = {}
    meta: Dict[str, Any] = {}

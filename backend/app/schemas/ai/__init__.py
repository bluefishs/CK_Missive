"""
AI 服務相關 Pydantic Schema

拆分為功能子模組，此 __init__.py 統一匯出確保向後相容。

Version: 2.0.0
Created: 2026-02-05
Updated: 2026-03-10 - 拆分為 10 個子模組
"""

# === 搜尋 ===
from app.schemas.ai.search import (
    ParsedSearchIntent,
    ParseIntentRequest,
    ParseIntentResponse,
    NaturalSearchRequest,
    AttachmentInfo,
    DocumentSearchResult,
    ClassificationResponse,
    KeywordsValidationResponse,
    MatchedEntity,
    NaturalSearchResponse,
)

# === AI 端點 ===
from app.schemas.ai.endpoints import (
    SummaryRequest,
    SummaryResponse,
    ClassifyRequest,
    ClassifyResponse,
    KeywordsRequest,
    KeywordsExtractResponse,
    AgencyCandidate,
    AgencyMatchRequest,
    AgencyMatchResult,
    AgencyMatchResponse,
    RateLimitStatus,
    HealthResponse,
    AIConfigResponse,
)

# === 同義詞 ===
from app.schemas.ai.synonyms import (
    AISynonymBase,
    AISynonymCreate,
    AISynonymUpdate,
    AISynonymResponse,
    AISynonymListRequest,
    AISynonymListResponse,
    AISynonymDeleteRequest,
    AISynonymReloadResponse,
)

# === 通用 ===
from app.schemas.ai.common import (
    SuccessResponse,
    OkResponse,
    AIFeatureStatsDetail,
    AIStatsResponse,
)

# === 搜尋歷史 ===
from app.schemas.ai.search_history import (
    SearchHistoryItem,
    SearchFeedbackRequest,
    SearchFeedbackResponse,
    SearchHistoryListRequest,
    SearchHistoryListResponse,
    DailyTrend,
    TopQuery,
    ClearSearchHistoryRequest,
    ClearSearchHistoryResponse,
    SearchStatsResponse,
    QuerySuggestionRequest,
    QuerySuggestionItem,
    QuerySuggestionResponse,
)

# === 知識圖譜 ===
from app.schemas.ai.graph import (
    GraphNode,
    GraphEdge,
    SemanticSimilarRequest,
    SemanticSimilarItem,
    SemanticSimilarResponse,
    EmbeddingStatsResponse,
    EmbeddingBatchRequest,
    EmbeddingBatchResponse,
    RelationGraphRequest,
    RelationGraphResponse,
)

# === Prompt ===
from app.schemas.ai.prompts import (
    PromptVersionItem,
    PromptListRequest,
    PromptListResponse,
    PromptCreateRequest,
    PromptCreateResponse,
    PromptActivateRequest,
    PromptActivateResponse,
    PromptCompareRequest,
    PromptDiff,
    PromptCompareResponse,
)

# === 實體提取 ===
from app.schemas.ai.entity import (
    EntityItem,
    EntityRelationItem,
    EntityExtractRequest,
    EntityExtractResponse,
    EntityBatchRequest,
    EntityBatchResponse,
    EntityStatsResponse,
)

# === Ollama ===
from app.schemas.ai.ollama import (
    OllamaGpuLoadedModel,
    OllamaGpuInfo,
    OllamaStatusResponse,
    OllamaEnsureModelsResponse,
    OllamaWarmupResponse,
)

# === RAG ===
from app.schemas.ai.rag import (
    AgentQueryRequest,
    AgentSyncResponse,
    RAGQueryRequest,
    RAGStreamRequest,
    RAGSourceItem,
    RAGQueryResponse,
)

# === 分析 ===
from app.schemas.ai.analysis import (
    DocumentAIAnalysisResponse,
    DocumentAIBriefResponse,
    DocumentAIAnalysisBatchRequest,
    DocumentAIAnalysisBatchResponse,
    DocumentAIAnalysisStatsResponse,
)

__all__ = [
    # search
    "ParsedSearchIntent", "ParseIntentRequest", "ParseIntentResponse",
    "NaturalSearchRequest", "AttachmentInfo", "DocumentSearchResult",
    "ClassificationResponse", "KeywordsValidationResponse",
    "MatchedEntity", "NaturalSearchResponse",
    # endpoints
    "SummaryRequest", "SummaryResponse", "ClassifyRequest", "ClassifyResponse",
    "KeywordsRequest", "KeywordsExtractResponse",
    "AgencyCandidate", "AgencyMatchRequest", "AgencyMatchResult", "AgencyMatchResponse",
    "RateLimitStatus", "HealthResponse", "AIConfigResponse",
    # synonyms
    "AISynonymBase", "AISynonymCreate", "AISynonymUpdate", "AISynonymResponse",
    "AISynonymListRequest", "AISynonymListResponse",
    "AISynonymDeleteRequest", "AISynonymReloadResponse",
    # common
    "SuccessResponse", "OkResponse", "AIFeatureStatsDetail", "AIStatsResponse",
    # search_history
    "SearchHistoryItem", "SearchFeedbackRequest", "SearchFeedbackResponse",
    "SearchHistoryListRequest", "SearchHistoryListResponse",
    "DailyTrend", "TopQuery",
    "ClearSearchHistoryRequest", "ClearSearchHistoryResponse",
    "SearchStatsResponse",
    "QuerySuggestionRequest", "QuerySuggestionItem", "QuerySuggestionResponse",
    # graph
    "GraphNode", "GraphEdge",
    "SemanticSimilarRequest", "SemanticSimilarItem", "SemanticSimilarResponse",
    "EmbeddingStatsResponse", "EmbeddingBatchRequest", "EmbeddingBatchResponse",
    "RelationGraphRequest", "RelationGraphResponse",
    # prompts
    "PromptVersionItem", "PromptListRequest", "PromptListResponse",
    "PromptCreateRequest", "PromptCreateResponse",
    "PromptActivateRequest", "PromptActivateResponse",
    "PromptCompareRequest", "PromptDiff", "PromptCompareResponse",
    # entity
    "EntityItem", "EntityRelationItem",
    "EntityExtractRequest", "EntityExtractResponse",
    "EntityBatchRequest", "EntityBatchResponse", "EntityStatsResponse",
    # ollama
    "OllamaGpuLoadedModel", "OllamaGpuInfo",
    "OllamaStatusResponse", "OllamaEnsureModelsResponse", "OllamaWarmupResponse",
    # rag
    "AgentQueryRequest", "AgentSyncResponse",
    "RAGQueryRequest", "RAGStreamRequest", "RAGSourceItem", "RAGQueryResponse",
    # analysis
    "DocumentAIAnalysisResponse", "DocumentAIBriefResponse",
    "DocumentAIAnalysisBatchRequest", "DocumentAIAnalysisBatchResponse",
    "DocumentAIAnalysisStatsResponse",
]

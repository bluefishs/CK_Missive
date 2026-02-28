/**
 * AI 服務型別定義 — 相容性 re-export
 *
 * ⚠️ DEPRECATED: 型別定義已遷移至 types/ai.ts (SSOT)
 * 此檔案僅保留 re-export 以維持向後相容。
 * 新程式碼請直接從 '../../types/ai' 匯入。
 *
 * @deprecated 請改用 import type { ... } from '../../types/ai'
 * @migrated-to /frontend/src/types/ai.ts
 * @date 2026-02-24
 */

export type {
  // 摘要
  SummaryRequest,
  SummaryResponse,
  // 分類
  ClassifyRequest,
  ClassifyResponse,
  // 關鍵字
  KeywordsRequest,
  KeywordsResponse,
  // 機關匹配
  AgencyCandidate,
  AgencyMatchRequest,
  AgencyMatchResult,
  AgencyMatchResponse,
  // 健康檢查
  AIHealthStatus,
  AIConfigResponse,
  // 自然語言搜尋
  ParsedSearchIntent,
  ParseIntentRequest,
  ParseIntentResponse,
  NaturalSearchRequest,
  AttachmentInfo,
  DocumentSearchResult,
  MatchedEntity,
  NaturalSearchResponse,
  SearchFeedbackRequest,
  SearchFeedbackResponse,
  // 搜尋建議
  QuerySuggestionRequest,
  QuerySuggestionItem,
  QuerySuggestionResponse,
  // 知識圖譜
  GraphNode,
  GraphEdge,
  RelationGraphRequest,
  RelationGraphResponse,
  // 語意相似
  SemanticSimilarRequest,
  SemanticSimilarItem,
  SemanticSimilarResponse,
  // Embedding
  EmbeddingStatsResponse,
  EmbeddingBatchRequest,
  EmbeddingBatchResponse,
  // 同義詞
  AISynonymItem,
  AISynonymListRequest,
  AISynonymListResponse,
  AISynonymCreateRequest,
  AISynonymUpdateRequest,
  AISynonymDeleteRequest,
  AISynonymReloadResponse,
  // Prompt
  PromptVersionItem,
  PromptListRequest,
  PromptListResponse,
  PromptCreateRequest,
  PromptCreateResponse,
  PromptActivateRequest,
  PromptActivateResponse,
  PromptDiff,
  PromptCompareRequest,
  PromptCompareResponse,
  // 搜尋歷史
  SearchHistoryItem,
  SearchHistoryListRequest,
  SearchHistoryListResponse,
  DailyTrend,
  TopQuery,
  SearchStatsResponse,
  // 實體提取
  EntityExtractRequest,
  EntityExtractResponse,
  EntityBatchRequest,
  EntityBatchResponse,
  EntityStatsResponse,
  // 知識圖譜 Phase 2
  KGEntitySearchRequest,
  KGEntityItem,
  KGEntitySearchResponse,
  KGNeighborsRequest,
  KGGraphNode,
  KGGraphEdge,
  KGNeighborsResponse,
  KGShortestPathRequest,
  KGPathNode,
  KGShortestPathResponse,
  KGEntityDetailRequest,
  KGEntityDocument,
  KGEntityRelationship,
  KGEntityDetailResponse,
  KGTimelineRequest,
  KGTimelineItem,
  KGTimelineResponse,
  KGTopEntitiesRequest,
  KGTopEntitiesResponse,
  KGGraphStatsResponse,
  KGIngestRequest,
  KGIngestResponse,
  KGMergeEntitiesRequest,
  KGMergeEntitiesResponse,
  // Ollama 管理
  OllamaGpuLoadedModel,
  OllamaGpuInfo,
  OllamaStatusResponse,
  OllamaEnsureModelsResponse,
  OllamaWarmupResponse,
  // RAG 問答
  RAGQueryRequest,
  RAGSourceItem,
  RAGQueryResponse,
  RAGStreamRequest,
  // re-export from types/api
  AIStatsResponse,
  // AI 分析持久化
  DocumentAIAnalysisResponse,
  DocumentAIAnalysisStatsResponse,
  DocumentAIAnalysisBatchResponse,
} from '../../types/ai';

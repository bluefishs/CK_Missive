/**
 * AI API 模組統一匯出
 *
 * 將拆分後的子模組重新組合為 `aiApi` 物件，
 * 保持與原始 aiApi.ts 完全相同的外部介面。
 *
 * @version 2.0.0
 * @created 2026-02-11
 */

// Re-export all types
export type {
  SummaryRequest,
  SummaryResponse,
  ClassifyRequest,
  ClassifyResponse,
  KeywordsRequest,
  KeywordsResponse,
  AgencyCandidate,
  AgencyMatchRequest,
  AgencyMatchResult,
  AgencyMatchResponse,
  AIHealthStatus,
  AIConfigResponse,
  ParsedSearchIntent,
  ParseIntentRequest,
  ParseIntentResponse,
  NaturalSearchRequest,
  AttachmentInfo,
  DocumentSearchResult,
  NaturalSearchResponse,
  AISynonymItem,
  AISynonymListRequest,
  AISynonymListResponse,
  AISynonymCreateRequest,
  AISynonymUpdateRequest,
  AISynonymDeleteRequest,
  AISynonymReloadResponse,
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
  SearchHistoryItem,
  SearchHistoryListRequest,
  SearchHistoryListResponse,
  DailyTrend,
  TopQuery,
  SearchStatsResponse,
  AIStatsResponse,
  SearchFeedbackRequest,
  SearchFeedbackResponse,
  QuerySuggestionRequest,
  QuerySuggestionItem,
  QuerySuggestionResponse,
  GraphNode,
  GraphEdge,
  RelationGraphRequest,
  RelationGraphResponse,
  SemanticSimilarRequest,
  SemanticSimilarItem,
  SemanticSimilarResponse,
  EmbeddingStatsResponse,
  EmbeddingBatchRequest,
  EmbeddingBatchResponse,
  EntityExtractRequest,
  EntityExtractResponse,
  EntityBatchRequest,
  EntityBatchResponse,
  EntityStatsResponse,
  // Knowledge Graph Phase 2
  KGEntitySearchRequest,
  KGEntitySearchResponse,
  KGEntityItem,
  KGNeighborsRequest,
  KGNeighborsResponse,
  KGGraphNode,
  KGGraphEdge,
  KGShortestPathRequest,
  KGPathNode,
  KGShortestPathResponse,
  KGEntityDetailRequest,
  KGEntityDetailResponse,
  KGEntityDocument,
  KGEntityRelationship,
  KGTimelineRequest,
  KGTimelineResponse,
  KGTimelineItem,
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
  // AI 分析持久化
  DocumentAIAnalysisResponse,
  DocumentAIAnalysisStatsResponse,
  DocumentAIAnalysisBatchResponse,
  // Code Wiki 代碼圖譜
  CodeWikiRequest,
  CodeWikiResponse,
  // Knowledge Graph API
  CodeGraphIngestRequest,
  CodeGraphIngestResponse,
  CycleDetectionResponse,
  ArchitectureAnalysisResponse,
  JsonImportRequest,
  JsonImportResponse,
  ModuleOverviewResponse,
  // SSE Callbacks
  SSEErrorCode,
  RAGStreamCallbacks,
  AgentStreamCallbacks,
  // Proactive Alerts
  ProactiveAlertItem,
  ProactiveAlertsResponse,
  // Tool Registry
  ToolRegistryItem,
  ToolRegistryResponse,
} from './types';

// Re-export abortNaturalSearch (standalone function)
export { abortNaturalSearch } from './naturalSearch';

// Import standalone functions from sub-modules
import {
  generateSummary,
  streamSummary,
  suggestClassification,
  extractKeywords,
  matchAgency,
  checkHealth,
  getConfig,
  analyzeDocument,
  getStats,
  resetStats,
  parseSearchIntent,
} from './coreFeatures';

import { naturalSearch } from './naturalSearch';

import {
  listSynonyms,
  createSynonym,
  updateSynonym,
  deleteSynonym,
  reloadSynonyms,
  listPrompts,
  createPrompt,
  activatePrompt,
  comparePrompts,
  listSearchHistory,
  getSearchStats,
  clearSearchHistory,
  submitSearchFeedback,
  getQuerySuggestions,
  getRelationGraph,
  getSemanticSimilar,
  getEmbeddingStats,
  runEmbeddingBatch,
  extractEntities,
  runEntityBatch,
  getEntityStats,
  getOllamaStatus,
  ensureOllamaModels,
  warmupOllamaModels,
  ragQuery,
  streamRAGQuery,
  streamAgentQuery,
  getDocumentAnalysis,
  triggerDocumentAnalysis,
  batchAnalyze,
  getAnalysisStats,
  // Phase 3A stats
  getToolSuccessRates,
  getAgentTraces,
  getLearnedPatterns,
  getPersistentLearnings,
  // Proactive alerts
  getProactiveAlerts,
  // Daily trend
  getDailyTrend,
  // Tool registry
  getToolRegistry,
} from './adminManagement';

import {
  searchGraphEntities,
  getEntityNeighbors,
  findShortestPath,
  getEntityDetail,
  getEntityTimeline,
  getTopEntities,
  getGraphStats,
  triggerGraphIngest,
  mergeGraphEntities,
  getCodeWikiGraph,
  getEntityGraph,
  triggerCodeGraphIngest,
  detectImportCycles,
  analyzeArchitecture,
  importJsonGraph,
  getModuleOverview,
  getDbSchemaGraph,
  getDbSchema,
  getModuleMappings,
  getSkillsMap,
} from './knowledgeGraph';

export type { DbSchemaGraphResponse, DbSchemaResponse, DbTableInfo, DbColumnInfo, ModuleMappingsResponse } from './knowledgeGraph';

// Compose the aiApi object (backward-compatible with original aiApi.ts)
export const aiApi = {
  // Core features
  generateSummary,
  streamSummary,
  suggestClassification,
  extractKeywords,
  matchAgency,
  checkHealth,
  getConfig,
  analyzeDocument,
  getStats,
  resetStats,
  parseSearchIntent,

  // Natural search
  naturalSearch,

  // Synonym management
  listSynonyms,
  createSynonym,
  updateSynonym,
  deleteSynonym,
  reloadSynonyms,

  // Prompt management
  listPrompts,
  createPrompt,
  activatePrompt,
  comparePrompts,

  // Search history & feedback
  listSearchHistory,
  getSearchStats,
  clearSearchHistory,
  submitSearchFeedback,
  getQuerySuggestions,
  getRelationGraph,
  getSemanticSimilar,
  getEmbeddingStats,
  runEmbeddingBatch,

  // Entity extraction
  extractEntities,
  runEntityBatch,
  getEntityStats,

  // Knowledge Graph Phase 2
  searchGraphEntities,
  getEntityNeighbors,
  findShortestPath,
  getEntityDetail,
  getEntityTimeline,
  getTopEntities,
  getGraphStats,
  triggerGraphIngest,
  mergeGraphEntities,

  // Code Wiki 代碼圖譜
  getCodeWikiGraph,
  triggerCodeGraphIngest,
  detectImportCycles,
  analyzeArchitecture,
  importJsonGraph,
  getModuleOverview,

  // DB Schema 圖譜
  getDbSchemaGraph,
  getDbSchema,

  // 動態模組映射
  getModuleMappings,

  // Entity-centric graph
  getEntityGraph,

  // Skills capability map
  getSkillsMap,

  // Ollama management
  getOllamaStatus,
  ensureOllamaModels,
  warmupOllamaModels,

  // RAG 問答
  ragQuery,
  streamRAGQuery,

  // Agentic 問答
  streamAgentQuery,

  // AI 分析持久化
  getDocumentAnalysis,
  triggerDocumentAnalysis,
  batchAnalyze,
  getAnalysisStats,

  // Phase 3A Agent 統計
  getToolSuccessRates,
  getAgentTraces,
  getLearnedPatterns,
  getPersistentLearnings,

  // Proactive Alerts
  getProactiveAlerts,

  // Daily Trend
  getDailyTrend,

  // Tool Registry
  getToolRegistry,
};

export default aiApi;

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
} from './adminManagement';

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
};

export default aiApi;

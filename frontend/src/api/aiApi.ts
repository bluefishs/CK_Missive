/**
 * AI 服務 API - Facade
 *
 * 原始 1055 行模組已拆分至 api/ai/ 子目錄：
 * - ai/types.ts         — 型別定義 (~340 行)
 * - ai/coreFeatures.ts  — 核心功能 (~200 行)
 * - ai/naturalSearch.ts — 自然語言搜尋 (~90 行)
 * - ai/adminManagement.ts — 管理 API (~150 行)
 * - ai/index.ts         — 統一匯出 + aiApi 物件組合
 *
 * 此檔案為向後相容 facade，所有匯入路徑仍可使用。
 *
 * @version 2.0.0
 * @created 2026-02-04
 * @refactored 2026-02-11 — 拆分至 api/ai/ 子模組
 */

export {
  aiApi,
  abortNaturalSearch,
} from './ai';

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
} from './ai';

export { aiApi as default } from './ai';

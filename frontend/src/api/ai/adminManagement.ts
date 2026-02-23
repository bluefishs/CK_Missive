/**
 * AI 管理功能 API
 *
 * 同義詞管理、Prompt 版本管理、搜尋歷史管理
 *
 * @version 1.0.0
 * @created 2026-02-11
 */

import { apiClient } from '../client';
import { AI_ENDPOINTS } from '../endpoints';
import { logger } from '../../services/logger';
import type {
  AISynonymListRequest,
  AISynonymListResponse,
  AISynonymCreateRequest,
  AISynonymItem,
  AISynonymUpdateRequest,
  AISynonymReloadResponse,
  PromptListResponse,
  PromptCreateRequest,
  PromptCreateResponse,
  PromptActivateResponse,
  PromptCompareResponse,
  SearchHistoryListRequest,
  SearchHistoryListResponse,
  SearchStatsResponse,
  SearchFeedbackRequest,
  SearchFeedbackResponse,
  QuerySuggestionRequest,
  QuerySuggestionResponse,
  RelationGraphRequest,
  RelationGraphResponse,
  SemanticSimilarRequest,
  SemanticSimilarResponse,
  EmbeddingStatsResponse,
  EmbeddingBatchRequest,
  EmbeddingBatchResponse,
} from './types';

// ============================================================================
// 同義詞管理
// ============================================================================

export async function listSynonyms(request: AISynonymListRequest = {}): Promise<AISynonymListResponse> {
  try {
    logger.log('取得同義詞列表');
    return await apiClient.post<AISynonymListResponse>(AI_ENDPOINTS.SYNONYMS_LIST, request);
  } catch (error) {
    logger.error('取得同義詞列表失敗:', error);
    return { items: [], total: 0, categories: [] };
  }
}

export async function createSynonym(request: AISynonymCreateRequest): Promise<AISynonymItem | null> {
  try {
    logger.log('新增同義詞群組:', request.category);
    return await apiClient.post<AISynonymItem>(AI_ENDPOINTS.SYNONYMS_CREATE, request);
  } catch (error) {
    logger.error('新增同義詞群組失敗:', error);
    throw error;
  }
}

export async function updateSynonym(request: AISynonymUpdateRequest): Promise<AISynonymItem | null> {
  try {
    logger.log('更新同義詞群組:', request.id);
    return await apiClient.post<AISynonymItem>(AI_ENDPOINTS.SYNONYMS_UPDATE, request);
  } catch (error) {
    logger.error('更新同義詞群組失敗:', error);
    throw error;
  }
}

export async function deleteSynonym(id: number): Promise<boolean> {
  try {
    logger.log('刪除同義詞群組:', id);
    await apiClient.post(AI_ENDPOINTS.SYNONYMS_DELETE, { id });
    return true;
  } catch (error) {
    logger.error('刪除同義詞群組失敗:', error);
    throw error;
  }
}

export async function reloadSynonyms(): Promise<AISynonymReloadResponse> {
  try {
    logger.log('重新載入同義詞');
    return await apiClient.post<AISynonymReloadResponse>(AI_ENDPOINTS.SYNONYMS_RELOAD, {});
  } catch (error) {
    logger.error('重新載入同義詞失敗:', error);
    return { success: false, total_groups: 0, total_words: 0, message: error instanceof Error ? error.message : '重新載入失敗' };
  }
}

// ============================================================================
// Prompt 版本管理
// ============================================================================

export async function listPrompts(feature?: string): Promise<PromptListResponse> {
  try {
    logger.log('列出 Prompt 版本', feature ? `feature=${feature}` : '全部');
    return await apiClient.post<PromptListResponse>(AI_ENDPOINTS.PROMPTS_LIST, { feature: feature || null });
  } catch (error) {
    logger.error('列出 Prompt 版本失敗:', error);
    throw error;
  }
}

export async function createPrompt(request: PromptCreateRequest): Promise<PromptCreateResponse> {
  try {
    logger.log('新增 Prompt 版本:', request.feature);
    return await apiClient.post<PromptCreateResponse>(AI_ENDPOINTS.PROMPTS_CREATE, request);
  } catch (error) {
    logger.error('新增 Prompt 版本失敗:', error);
    throw error;
  }
}

export async function activatePrompt(id: number): Promise<PromptActivateResponse> {
  try {
    logger.log('啟用 Prompt 版本:', id);
    return await apiClient.post<PromptActivateResponse>(AI_ENDPOINTS.PROMPTS_ACTIVATE, { id });
  } catch (error) {
    logger.error('啟用 Prompt 版本失敗:', error);
    throw error;
  }
}

export async function comparePrompts(idA: number, idB: number): Promise<PromptCompareResponse> {
  try {
    logger.log('比較 Prompt 版本:', idA, 'vs', idB);
    return await apiClient.post<PromptCompareResponse>(AI_ENDPOINTS.PROMPTS_COMPARE, { id_a: idA, id_b: idB });
  } catch (error) {
    logger.error('比較 Prompt 版本失敗:', error);
    throw error;
  }
}

// ============================================================================
// 搜尋歷史
// ============================================================================

export async function listSearchHistory(params: SearchHistoryListRequest = {}): Promise<SearchHistoryListResponse | null> {
  try {
    logger.log('取得搜尋歷史列表');
    return await apiClient.post<SearchHistoryListResponse>(AI_ENDPOINTS.SEARCH_HISTORY_LIST, params);
  } catch (error) {
    logger.error('搜尋歷史列表失敗:', error);
    return null;
  }
}

export async function getSearchStats(): Promise<SearchStatsResponse | null> {
  try {
    logger.log('取得搜尋統計');
    return await apiClient.post<SearchStatsResponse>(AI_ENDPOINTS.SEARCH_HISTORY_STATS, {});
  } catch (error) {
    logger.error('搜尋統計失敗:', error);
    return null;
  }
}

export async function clearSearchHistory(beforeDate?: string): Promise<boolean> {
  try {
    logger.log('清除搜尋歷史');
    const params = beforeDate ? { before_date: beforeDate } : {};
    await apiClient.post(AI_ENDPOINTS.SEARCH_HISTORY_CLEAR, params);
    return true;
  } catch (error) {
    logger.error('清除搜尋歷史失敗:', error);
    return false;
  }
}

export async function getQuerySuggestions(
  request: QuerySuggestionRequest,
): Promise<QuerySuggestionResponse | null> {
  try {
    return await apiClient.post<QuerySuggestionResponse>(
      AI_ENDPOINTS.SEARCH_HISTORY_SUGGESTIONS,
      request,
    );
  } catch (error) {
    logger.error('取得搜尋建議失敗:', error);
    return null;
  }
}

export async function getRelationGraph(
  request: RelationGraphRequest,
): Promise<RelationGraphResponse | null> {
  try {
    return await apiClient.post<RelationGraphResponse>(
      AI_ENDPOINTS.RELATION_GRAPH,
      request,
    );
  } catch (error) {
    logger.error('取得關聯圖譜失敗:', error);
    return null;
  }
}

export async function getSemanticSimilar(
  request: SemanticSimilarRequest,
): Promise<SemanticSimilarResponse | null> {
  try {
    return await apiClient.post<SemanticSimilarResponse>(
      AI_ENDPOINTS.SEMANTIC_SIMILAR,
      request,
    );
  } catch (error) {
    logger.error('取得語意相似推薦失敗:', error);
    return null;
  }
}

export async function getEmbeddingStats(): Promise<EmbeddingStatsResponse | null> {
  try {
    return await apiClient.post<EmbeddingStatsResponse>(AI_ENDPOINTS.EMBEDDING_STATS, {});
  } catch (error) {
    logger.error('取得 Embedding 統計失敗:', error);
    return null;
  }
}

export async function runEmbeddingBatch(
  request: EmbeddingBatchRequest = {},
): Promise<EmbeddingBatchResponse | null> {
  try {
    return await apiClient.post<EmbeddingBatchResponse>(AI_ENDPOINTS.EMBEDDING_BATCH, request);
  } catch (error) {
    logger.error('Embedding 批次管線失敗:', error);
    return null;
  }
}

export async function submitSearchFeedback(
  request: SearchFeedbackRequest,
): Promise<SearchFeedbackResponse | null> {
  try {
    return await apiClient.post<SearchFeedbackResponse>(
      AI_ENDPOINTS.SEARCH_HISTORY_FEEDBACK,
      request,
    );
  } catch (error) {
    logger.error('搜尋回饋提交失敗:', error);
    return null;
  }
}

/**
 * AI 管理功能 API
 *
 * 同義詞管理、Prompt 版本管理、搜尋歷史管理
 *
 * @version 1.0.0
 * @created 2026-02-11
 */

import { apiClient, API_BASE_URL } from '../client';
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
  EntityExtractRequest,
  EntityExtractResponse,
  EntityBatchRequest,
  EntityBatchResponse,
  EntityStatsResponse,
  OllamaStatusResponse,
  OllamaEnsureModelsResponse,
  OllamaWarmupResponse,
  RAGQueryRequest,
  RAGQueryResponse,
  RAGStreamRequest,
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

// ============================================================================
// 實體提取管理
// ============================================================================

export async function extractEntities(
  request: EntityExtractRequest,
): Promise<EntityExtractResponse | null> {
  try {
    return await apiClient.post<EntityExtractResponse>(AI_ENDPOINTS.ENTITY_EXTRACT, request);
  } catch (error) {
    logger.error('實體提取失敗:', error);
    return null;
  }
}

export async function runEntityBatch(
  request: EntityBatchRequest = {},
): Promise<EntityBatchResponse | null> {
  try {
    return await apiClient.post<EntityBatchResponse>(AI_ENDPOINTS.ENTITY_BATCH, request);
  } catch (error) {
    logger.error('實體批次提取失敗:', error);
    return null;
  }
}

export async function getEntityStats(): Promise<EntityStatsResponse | null> {
  try {
    return await apiClient.post<EntityStatsResponse>(AI_ENDPOINTS.ENTITY_STATS, {});
  } catch (error) {
    logger.error('取得實體統計失敗:', error);
    return null;
  }
}

// ============================================================================
// Ollama 管理
// ============================================================================

export async function getOllamaStatus(): Promise<OllamaStatusResponse> {
  logger.log('取得 Ollama 狀態');
  return await apiClient.post<OllamaStatusResponse>(AI_ENDPOINTS.OLLAMA_STATUS, {});
}

export async function ensureOllamaModels(): Promise<OllamaEnsureModelsResponse> {
  logger.log('檢查並拉取 Ollama 模型');
  return await apiClient.post<OllamaEnsureModelsResponse>(AI_ENDPOINTS.OLLAMA_ENSURE_MODELS, {});
}

export async function warmupOllamaModels(): Promise<OllamaWarmupResponse> {
  logger.log('預熱 Ollama 模型');
  return await apiClient.post<OllamaWarmupResponse>(AI_ENDPOINTS.OLLAMA_WARMUP, {});
}

// ============================================================================
// RAG 問答
// ============================================================================

export async function ragQuery(request: RAGQueryRequest): Promise<RAGQueryResponse> {
  logger.log('RAG 問答:', request.question.substring(0, 50));
  return await apiClient.post<RAGQueryResponse>(AI_ENDPOINTS.RAG_QUERY, request);
}

/** RAG SSE 事件回調 */
export interface RAGStreamCallbacks {
  onSources: (sources: RAGQueryResponse['sources'], count: number) => void;
  onToken: (token: string) => void;
  onDone: (latencyMs: number, model: string) => void;
  onError?: (error: string) => void;
}

/**
 * RAG 串流問答（SSE）
 *
 * 傳回 AbortController 供取消使用。
 */
export function streamRAGQuery(
  params: RAGStreamRequest,
  callbacks: RAGStreamCallbacks,
): AbortController {
  const controller = new AbortController();
  const RAG_TIMEOUT_MS = 30000; // 30s for RAG mode
  const timeoutId = setTimeout(() => controller.abort(), RAG_TIMEOUT_MS);
  const url = `${API_BASE_URL}${AI_ENDPOINTS.RAG_QUERY_STREAM}`;
  const accessToken = localStorage.getItem('access_token');

  (async () => {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify(params),
        signal: controller.signal,
        credentials: 'include',
      });

      if (!response.ok) {
        clearTimeout(timeoutId);
        const text = await response.text();
        callbacks.onError?.(text || `HTTP ${response.status}`);
        callbacks.onDone(0, 'error');
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        clearTimeout(timeoutId);
        callbacks.onError?.('ReadableStream not supported');
        callbacks.onDone(0, 'error');
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith('data: ')) continue;

          try {
            const data = JSON.parse(line.slice(6));
            switch (data.type) {
              case 'sources':
                callbacks.onSources(data.sources || [], data.retrieval_count || 0);
                break;
              case 'token':
                if (data.token) callbacks.onToken(data.token);
                break;
              case 'done':
                clearTimeout(timeoutId);
                callbacks.onDone(data.latency_ms || 0, data.model || '');
                return;
              case 'error':
                callbacks.onError?.(data.error || 'Unknown error');
                break;
            }
          } catch {
            logger.warn('RAG SSE parse error:', line);
          }
        }
      }

      // Process remaining buffer after stream ends
      if (buffer.trim()) {
        const line = buffer.trim();
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            switch (data.type) {
              case 'sources':
                callbacks.onSources(data.sources || [], data.retrieval_count || 0);
                break;
              case 'token':
                if (data.token) callbacks.onToken(data.token);
                break;
              case 'done':
                clearTimeout(timeoutId);
                callbacks.onDone(data.latency_ms || 0, data.model || '');
                return;
              case 'error':
                callbacks.onError?.(data.error || 'Unknown error');
                break;
            }
          } catch {
            logger.warn('RAG SSE parse error (remaining buffer):', line);
          }
        }
      }

      clearTimeout(timeoutId);
      callbacks.onDone(0, 'unknown');
    } catch (err) {
      clearTimeout(timeoutId);
      if (err instanceof DOMException && err.name === 'AbortError') return;
      const msg = err instanceof Error ? err.message : 'RAG 串流連線失敗';
      logger.error('RAG SSE error:', msg);
      callbacks.onError?.(msg);
      callbacks.onDone(0, 'error');
    }
  })();

  return controller;
}

// ============================================================================
// Agentic 問答
// ============================================================================

/** Agent 推理步驟 */
export interface AgentStep {
  type: 'thinking' | 'tool_call' | 'tool_result';
  step_index: number;
  // thinking
  step?: string;
  // tool_call
  tool?: string;
  params?: Record<string, unknown>;
  // tool_result
  summary?: string;
  count?: number;
}

/** Agent SSE 事件回調 */
export interface AgentStreamCallbacks {
  onThinking: (step: string, stepIndex: number) => void;
  onToolCall: (tool: string, params: Record<string, unknown>, stepIndex: number) => void;
  onToolResult: (tool: string, summary: string, count: number, stepIndex: number) => void;
  onSources: (sources: RAGQueryResponse['sources'], count: number) => void;
  onToken: (token: string) => void;
  onDone: (latencyMs: number, model: string, toolsUsed: string[], iterations: number) => void;
  onError?: (error: string) => void;
}

/**
 * Agentic 串流問答（SSE）
 *
 * 傳回 AbortController 供取消使用。
 */
export function streamAgentQuery(
  params: { question: string; history?: Array<{ role: string; content: string }> },
  callbacks: AgentStreamCallbacks,
): AbortController {
  const controller = new AbortController();
  const AGENT_TIMEOUT_MS = 60000; // 60s for agent mode
  const timeoutId = setTimeout(() => controller.abort(), AGENT_TIMEOUT_MS);
  const url = `${API_BASE_URL}${AI_ENDPOINTS.AGENT_QUERY_STREAM}`;
  const accessToken = localStorage.getItem('access_token');

  (async () => {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify(params),
        signal: controller.signal,
        credentials: 'include',
      });

      if (!response.ok) {
        clearTimeout(timeoutId);
        const text = await response.text();
        callbacks.onError?.(text || `HTTP ${response.status}`);
        callbacks.onDone(0, 'error', [], 0);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        clearTimeout(timeoutId);
        callbacks.onError?.('ReadableStream not supported');
        callbacks.onDone(0, 'error', [], 0);
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith('data: ')) continue;

          try {
            const data = JSON.parse(line.slice(6));
            switch (data.type) {
              case 'thinking':
                callbacks.onThinking(data.step || '', data.step_index || 0);
                break;
              case 'tool_call':
                callbacks.onToolCall(data.tool || '', data.params || {}, data.step_index || 0);
                break;
              case 'tool_result':
                callbacks.onToolResult(data.tool || '', data.summary || '', data.count || 0, data.step_index || 0);
                break;
              case 'sources':
                callbacks.onSources(data.sources || [], data.retrieval_count || 0);
                break;
              case 'token':
                if (data.token) callbacks.onToken(data.token);
                break;
              case 'done':
                clearTimeout(timeoutId);
                callbacks.onDone(
                  data.latency_ms || 0,
                  data.model || '',
                  data.tools_used || [],
                  data.iterations || 0,
                );
                return;
              case 'error':
                callbacks.onError?.(data.error || 'Unknown error');
                break;
            }
          } catch {
            logger.warn('Agent SSE parse error:', line);
          }
        }
      }

      // Process remaining buffer after stream ends
      if (buffer.trim()) {
        const line = buffer.trim();
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            switch (data.type) {
              case 'thinking':
                callbacks.onThinking(data.step || '', data.step_index || 0);
                break;
              case 'tool_call':
                callbacks.onToolCall(data.tool || '', data.params || {}, data.step_index || 0);
                break;
              case 'tool_result':
                callbacks.onToolResult(data.tool || '', data.summary || '', data.count || 0, data.step_index || 0);
                break;
              case 'sources':
                callbacks.onSources(data.sources || [], data.retrieval_count || 0);
                break;
              case 'token':
                if (data.token) callbacks.onToken(data.token);
                break;
              case 'done':
                clearTimeout(timeoutId);
                callbacks.onDone(
                  data.latency_ms || 0,
                  data.model || '',
                  data.tools_used || [],
                  data.iterations || 0,
                );
                return;
              case 'error':
                callbacks.onError?.(data.error || 'Unknown error');
                break;
            }
          } catch {
            logger.warn('Agent SSE parse error (remaining buffer):', line);
          }
        }
      }

      clearTimeout(timeoutId);
      callbacks.onDone(0, 'unknown', [], 0);
    } catch (err) {
      clearTimeout(timeoutId);
      if (err instanceof DOMException && err.name === 'AbortError') return;
      const msg = err instanceof Error ? err.message : 'Agent 串流連線失敗';
      logger.error('Agent SSE error:', msg);
      callbacks.onError?.(msg);
      callbacks.onDone(0, 'error', [], 0);
    }
  })();

  return controller;
}

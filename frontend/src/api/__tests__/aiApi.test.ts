/**
 * AI API 單元測試
 * AI API Unit Tests
 *
 * 測試 AI 核心功能、管理功能、自然語言搜尋 API
 *
 * 執行方式:
 *   cd frontend && npx vitest run src/api/__tests__/aiApi.test.ts
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock apiClient
vi.mock('../client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
  API_BASE_URL: 'http://localhost:8001',
}));

// Mock logger (services/logger)
vi.mock('../../services/logger', () => ({
  logger: {
    log: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
    info: vi.fn(),
  },
}));

// Mock endpoints
vi.mock('../endpoints', () => ({
  AI_ENDPOINTS: {
    SUMMARY: '/ai/document/summary',
    SUMMARY_STREAM: '/ai/document/summary/stream',
    CLASSIFY: '/ai/document/classify',
    KEYWORDS: '/ai/document/keywords',
    AGENCY_MATCH: '/ai/agency/match',
    HEALTH: '/ai/health',
    CONFIG: '/ai/config',
    STATS: '/ai/stats',
    STATS_RESET: '/ai/stats/reset',
    PARSE_INTENT: '/ai/document/parse-intent',
    NATURAL_SEARCH: '/ai/document/natural-search',
    SYNONYMS_LIST: '/ai/synonyms/list',
    SYNONYMS_CREATE: '/ai/synonyms/create',
    SYNONYMS_UPDATE: '/ai/synonyms/update',
    SYNONYMS_DELETE: '/ai/synonyms/delete',
    SYNONYMS_RELOAD: '/ai/synonyms/reload',
    PROMPTS_LIST: '/ai/prompts/list',
    PROMPTS_CREATE: '/ai/prompts/create',
    PROMPTS_ACTIVATE: '/ai/prompts/activate',
    PROMPTS_COMPARE: '/ai/prompts/compare',
    SEARCH_HISTORY_LIST: '/ai/search-history/list',
    SEARCH_HISTORY_STATS: '/ai/search-history/stats',
    SEARCH_HISTORY_CLEAR: '/ai/search-history/clear',
    SEARCH_HISTORY_FEEDBACK: '/ai/search-history/feedback',
    SEARCH_HISTORY_SUGGESTIONS: '/ai/search-history/suggestions',
    RELATION_GRAPH: '/ai/document/relation-graph',
    EMBEDDING_STATS: '/ai/embedding/stats',
    EMBEDDING_BATCH: '/ai/embedding/batch',
    SEMANTIC_SIMILAR: '/ai/document/semantic-similar',
    ENTITY_EXTRACT: '/ai/entity/extract',
    ENTITY_BATCH: '/ai/entity/batch',
    ENTITY_STATS: '/ai/entity/stats',
    OLLAMA_STATUS: '/ai/ollama/status',
    OLLAMA_ENSURE_MODELS: '/ai/ollama/ensure-models',
    OLLAMA_WARMUP: '/ai/ollama/warmup',
    RAG_QUERY: '/ai/rag/query',
    RAG_QUERY_STREAM: '/ai/rag/query/stream',
    AGENT_QUERY_STREAM: '/ai/agent/query/stream',
  },
}));

// Mock axios (used in naturalSearch for isCancel)
vi.mock('axios', () => ({
  default: {
    isCancel: vi.fn(() => false),
  },
  isCancel: vi.fn(() => false),
}));

import { apiClient } from '../client';
import {
  generateSummary,
  suggestClassification,
  extractKeywords,
  matchAgency,
  checkHealth,
  getConfig,
  analyzeDocument,
  getStats,
  resetStats,
  parseSearchIntent,
} from '../ai/coreFeatures';
import { naturalSearch, abortNaturalSearch } from '../ai/naturalSearch';
import {
  listSynonyms,
  createSynonym,
  deleteSynonym,
  reloadSynonyms,
  listPrompts,
  activatePrompt,
  comparePrompts,
  listSearchHistory,
  getSearchStats,
  clearSearchHistory,
  getRelationGraph,
  getSemanticSimilar,
  getEmbeddingStats,
  extractEntities,
  getEntityStats,
  getOllamaStatus,
  ragQuery,
} from '../ai/adminManagement';

// ============================================================================
// generateSummary 測試
// ============================================================================

describe('generateSummary - AI 摘要生成', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功生成摘要應回傳正確結構', async () => {
    const mockResponse = {
      summary: '這是一份關於工程查估的公文摘要',
      confidence: 0.92,
      source: 'groq',
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await generateSummary({
      subject: '桃園市政府工程查估報告',
      content: '有關 114 年度工程查估案...',
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/ai/document/summary',
      expect.objectContaining({ subject: '桃園市政府工程查估報告' })
    );
    expect(result.summary).toBe('這是一份關於工程查估的公文摘要');
    expect(result.confidence).toBe(0.92);
  });

  it('API 錯誤時應回傳 fallback 摘要', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Service Unavailable'));

    const result = await generateSummary({
      subject: '桃園市政府工程查估報告',
    });

    expect(result.source).toBe('fallback');
    expect(result.confidence).toBe(0);
    expect(result.error).toBe('Service Unavailable');
    // fallback summary should be a substring of the subject
    expect(result.summary).toBe('桃園市政府工程查估報告');
  });
});

// ============================================================================
// suggestClassification 測試
// ============================================================================

describe('suggestClassification - AI 分類建議', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功分類應回傳 doc_type 和 category', async () => {
    const mockResponse = {
      doc_type: '函',
      category: '收文',
      doc_type_confidence: 0.95,
      category_confidence: 0.88,
      source: 'groq',
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await suggestClassification({
      subject: '有關工程查估案',
      content: '依據...',
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/ai/document/classify',
      expect.objectContaining({ subject: '有關工程查估案' })
    );
    expect(result.doc_type).toBe('函');
    expect(result.category).toBe('收文');
  });

  it('API 錯誤時應回傳 fallback 分類', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('timeout'));

    const result = await suggestClassification({ subject: '測試' });

    expect(result.doc_type).toBe('函');
    expect(result.category).toBe('收文');
    expect(result.source).toBe('fallback');
    expect(result.doc_type_confidence).toBe(0);
  });
});

// ============================================================================
// extractKeywords 測試
// ============================================================================

describe('extractKeywords - AI 關鍵字提取', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功提取關鍵字', async () => {
    const mockResponse = {
      keywords: ['工程查估', '桃園市', '橋梁'],
      confidence: 0.85,
      source: 'groq',
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await extractKeywords({ subject: '桃園市橋梁工程查估報告' });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/ai/document/keywords',
      expect.objectContaining({ subject: '桃園市橋梁工程查估報告' })
    );
    expect(result.keywords).toHaveLength(3);
    expect(result.keywords).toContain('工程查估');
  });

  it('API 錯誤時應回傳空關鍵字陣列', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await extractKeywords({ subject: '測試' });

    expect(result.keywords).toEqual([]);
    expect(result.source).toBe('fallback');
  });
});

// ============================================================================
// matchAgency 測試
// ============================================================================

describe('matchAgency - AI 機關匹配', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功匹配機關', async () => {
    const mockResponse = {
      best_match: { id: 1, name: '桃園市政府', similarity: 0.98 },
      alternatives: [],
      is_new: false,
      source: 'groq',
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await matchAgency({ agency_name: '桃園市政府' });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/ai/agency/match',
      { agency_name: '桃園市政府' }
    );
    expect(result.best_match).toBeTruthy();
    expect(result.is_new).toBe(false);
  });

  it('API 錯誤時應回傳 is_new: true 的 fallback', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await matchAgency({ agency_name: '未知機關' });

    expect(result.best_match).toBeNull();
    expect(result.is_new).toBe(true);
    expect(result.source).toBe('fallback');
  });
});

// ============================================================================
// checkHealth 測試
// ============================================================================

describe('checkHealth - AI 健康檢查', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功回傳 AI 服務健康狀態', async () => {
    const mockResponse = {
      groq: { available: true, message: '正常' },
      ollama: { available: true, message: '正常' },
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await checkHealth();

    expect(apiClient.post).toHaveBeenCalledWith('/ai/health', {});
    expect(result.groq.available).toBe(true);
    expect(result.ollama.available).toBe(true);
  });

  it('API 錯誤時應回傳全部不可用', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await checkHealth();

    expect(result.groq.available).toBe(false);
    expect(result.ollama.available).toBe(false);
  });
});

// ============================================================================
// getConfig 測試
// ============================================================================

describe('getConfig - AI 配置取得', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功回傳配置', async () => {
    const mockConfig = { groq_model: 'llama3-70b', ollama_model: 'qwen3:4b' };
    vi.mocked(apiClient.post).mockResolvedValue(mockConfig);

    const result = await getConfig();

    expect(apiClient.post).toHaveBeenCalledWith('/ai/config', {});
    expect(result).toEqual(mockConfig);
  });

  it('API 錯誤時應回傳 null', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await getConfig();

    expect(result).toBeNull();
  });
});

// ============================================================================
// analyzeDocument 測試
// ============================================================================

describe('analyzeDocument - 公文綜合分析', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應同時呼叫摘要和分類 API', async () => {
    const mockSummary = { summary: '摘要', confidence: 0.9, source: 'groq' };
    const mockClassify = { doc_type: '函', category: '收文', doc_type_confidence: 0.9, category_confidence: 0.9, source: 'groq' };

    vi.mocked(apiClient.post)
      .mockResolvedValueOnce(mockSummary)
      .mockResolvedValueOnce(mockClassify);

    const result = await analyzeDocument('測試主旨', '內容', '來文機關');

    expect(apiClient.post).toHaveBeenCalledTimes(2);
    expect(result.summary).toEqual(mockSummary);
    expect(result.classification).toEqual(mockClassify);
  });
});

// ============================================================================
// getStats / resetStats 測試
// ============================================================================

describe('getStats - AI 統計', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功取得統計', async () => {
    const mockStats = { total_requests: 100, success_rate: 0.95 };
    vi.mocked(apiClient.post).mockResolvedValue(mockStats);

    const result = await getStats();

    expect(apiClient.post).toHaveBeenCalledWith('/ai/stats', {});
    expect(result).toEqual(mockStats);
  });

  it('API 錯誤時應回傳 null', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await getStats();

    expect(result).toBeNull();
  });
});

describe('resetStats - 重設 AI 統計', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功重設應回傳 true', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true });

    const result = await resetStats();

    expect(apiClient.post).toHaveBeenCalledWith('/ai/stats/reset', {});
    expect(result).toBe(true);
  });

  it('失敗應回傳 false', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await resetStats();

    expect(result).toBe(false);
  });
});

// ============================================================================
// parseSearchIntent 測試
// ============================================================================

describe('parseSearchIntent - 意圖解析', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功解析搜尋意圖', async () => {
    const mockResponse = {
      success: true,
      query: '找橋梁公文',
      parsed_intent: { keywords: ['橋梁', '公文'], confidence: 0.88 },
      source: 'groq',
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await parseSearchIntent('找橋梁公文');

    expect(apiClient.post).toHaveBeenCalledWith(
      '/ai/document/parse-intent',
      { query: '找橋梁公文' }
    );
    expect(result.success).toBe(true);
  });

  it('API 錯誤時應回傳 fallback 意圖', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await parseSearchIntent('測試查詢');

    expect(result.success).toBe(false);
    expect(result.source).toBe('error');
    expect(result.parsed_intent.keywords).toEqual(['測試查詢']);
  });
});

// ============================================================================
// naturalSearch 測試
// ============================================================================

describe('naturalSearch - 自然語言搜尋', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功搜尋應回傳結果', async () => {
    const mockResponse = {
      success: true,
      query: '橋梁查估',
      parsed_intent: { keywords: ['橋梁', '查估'], confidence: 0.9 },
      results: [{ id: 1, subject: '橋梁查估報告' }],
      total: 1,
      source: 'groq',
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await naturalSearch('橋梁查估', 20, true, 0);

    expect(apiClient.post).toHaveBeenCalledWith(
      '/ai/document/natural-search',
      { query: '橋梁查估', max_results: 20, include_attachments: true, offset: 0 },
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(result.success).toBe(true);
    expect(result.results).toHaveLength(1);
  });

  it('API 錯誤時應回傳空結果', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Network Error'));

    const result = await naturalSearch('測試');

    expect(result.success).toBe(false);
    expect(result.results).toEqual([]);
    expect(result.total).toBe(0);
    expect(result.error).toBe('Network Error');
  });

  it('abortNaturalSearch 不應拋出錯誤', () => {
    expect(() => abortNaturalSearch()).not.toThrow();
  });
});

// ============================================================================
// listSynonyms 測試
// ============================================================================

describe('listSynonyms - 同義詞列表', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功取得同義詞列表', async () => {
    const mockResponse = {
      items: [{ id: 1, category: '機關', words: ['市政府', '市府'] }],
      total: 1,
      categories: ['機關'],
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await listSynonyms();

    expect(apiClient.post).toHaveBeenCalledWith('/ai/synonyms/list', {});
    expect(result.items).toHaveLength(1);
    expect(result.total).toBe(1);
  });

  it('API 錯誤時應回傳空列表', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await listSynonyms();

    expect(result.items).toEqual([]);
    expect(result.total).toBe(0);
  });
});

// ============================================================================
// createSynonym / deleteSynonym / reloadSynonyms 測試
// ============================================================================

describe('createSynonym - 新增同義詞', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功新增同義詞群組', async () => {
    const mockItem = { id: 1, category: '機關', words: ['市政府', '市府'] };
    vi.mocked(apiClient.post).mockResolvedValue(mockItem);

    const result = await createSynonym({
      category: '機關',
      words: '市政府,市府',
    });

    expect(result).toEqual(mockItem);
  });

  it('API 錯誤時應拋出錯誤', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Conflict'));

    await expect(createSynonym({
      category: '機關',
      words: '重複詞',
    })).rejects.toThrow('Conflict');
  });
});

describe('deleteSynonym - 刪除同義詞', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功刪除應回傳 true', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true });

    const result = await deleteSynonym(1);

    expect(apiClient.post).toHaveBeenCalledWith('/ai/synonyms/delete', { id: 1 });
    expect(result).toBe(true);
  });

  it('API 錯誤時應拋出錯誤', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Not Found'));

    await expect(deleteSynonym(999)).rejects.toThrow('Not Found');
  });
});

describe('reloadSynonyms - 重新載入同義詞', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功重新載入', async () => {
    const mockResponse = { success: true, total_groups: 10, total_words: 50, message: '完成' };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await reloadSynonyms();

    expect(result.success).toBe(true);
    expect(result.total_groups).toBe(10);
  });

  it('API 錯誤時應回傳 fallback', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await reloadSynonyms();

    expect(result.success).toBe(false);
  });
});

// ============================================================================
// Prompt 管理測試
// ============================================================================

describe('listPrompts - Prompt 列表', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功取得 Prompt 列表', async () => {
    const mockResponse = { items: [{ id: 1, feature: 'summary', version: 1 }], total: 1 };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await listPrompts('summary');

    expect(apiClient.post).toHaveBeenCalledWith('/ai/prompts/list', { feature: 'summary' });
    expect(result.items).toHaveLength(1);
  });

  it('API 錯誤時應拋出錯誤', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    await expect(listPrompts()).rejects.toThrow();
  });
});

describe('activatePrompt - 啟用 Prompt', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功啟用 Prompt 版本', async () => {
    const mockResponse = { success: true, message: '已啟用' };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await activatePrompt(5);

    expect(apiClient.post).toHaveBeenCalledWith('/ai/prompts/activate', { id: 5 });
    expect(result.success).toBe(true);
  });
});

describe('comparePrompts - 比較 Prompt 版本', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功比較兩個版本', async () => {
    const mockResponse = { diffs: [{ field: 'content', old_value: 'v1', new_value: 'v2' }] };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await comparePrompts(1, 2);

    expect(apiClient.post).toHaveBeenCalledWith('/ai/prompts/compare', { id_a: 1, id_b: 2 });
    expect(result.diffs).toHaveLength(1);
  });
});

// ============================================================================
// 搜尋歷史測試
// ============================================================================

describe('listSearchHistory - 搜尋歷史列表', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功取得搜尋歷史', async () => {
    const mockResponse = { items: [{ id: 1, query: '橋梁' }], total: 1 };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await listSearchHistory({ page: 1, page_size: 10 });

    expect(result).toEqual(mockResponse);
  });

  it('API 錯誤時應回傳 null', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await listSearchHistory();

    expect(result).toBeNull();
  });
});

describe('getSearchStats - 搜尋統計', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('API 錯誤時應回傳 null', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await getSearchStats();

    expect(result).toBeNull();
  });
});

describe('clearSearchHistory - 清除搜尋歷史', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功清除應回傳 true', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true });

    const result = await clearSearchHistory();

    expect(apiClient.post).toHaveBeenCalledWith('/ai/search-history/clear', {});
    expect(result).toBe(true);
  });

  it('帶日期參數清除', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true });

    await clearSearchHistory('2026-01-01');

    expect(apiClient.post).toHaveBeenCalledWith(
      '/ai/search-history/clear',
      { before_date: '2026-01-01' }
    );
  });

  it('失敗應回傳 false', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await clearSearchHistory();

    expect(result).toBe(false);
  });
});

// ============================================================================
// getRelationGraph / getSemanticSimilar / getEmbeddingStats 測試
// ============================================================================

describe('getRelationGraph - 關聯圖譜', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功取得關聯圖譜', async () => {
    const mockResponse = { nodes: [{ id: '1', label: '公文A' }], edges: [] };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await getRelationGraph({ document_ids: [1] });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/ai/document/relation-graph',
      { document_ids: [1] }
    );
    expect(result).toEqual(mockResponse);
  });

  it('API 錯誤時應回傳 null', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await getRelationGraph({ document_ids: [1] });

    expect(result).toBeNull();
  });
});

describe('getSemanticSimilar - 語意相似推薦', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('API 錯誤時應回傳 null', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await getSemanticSimilar({ document_id: 1 });

    expect(result).toBeNull();
  });
});

describe('getEmbeddingStats - Embedding 統計', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('API 錯誤時應回傳 null', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await getEmbeddingStats();

    expect(result).toBeNull();
  });
});

// ============================================================================
// 實體提取測試
// ============================================================================

describe('extractEntities - 實體提取', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功提取實體', async () => {
    const mockResponse = { entities: [{ name: '桃園市', type: 'ORG' }], document_id: 1 };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await extractEntities({ document_id: 1 });

    expect(apiClient.post).toHaveBeenCalledWith('/ai/entity/extract', { document_id: 1 });
    expect(result).toEqual(mockResponse);
  });

  it('API 錯誤時應回傳 null', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await extractEntities({ document_id: 1 });

    expect(result).toBeNull();
  });
});

describe('getEntityStats - 實體統計', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('API 錯誤時應回傳 null', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('error'));

    const result = await getEntityStats();

    expect(result).toBeNull();
  });
});

// ============================================================================
// Ollama 管理測試
// ============================================================================

describe('getOllamaStatus - Ollama 狀態', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功取得 Ollama 狀態', async () => {
    const mockResponse = { running: true, models: ['qwen3:4b'] };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await getOllamaStatus();

    expect(apiClient.post).toHaveBeenCalledWith('/ai/ollama/status', {});
    expect((result as any).running).toBe(true);
  });

  it('API 錯誤時應向上拋出', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Connection refused'));

    await expect(getOllamaStatus()).rejects.toThrow('Connection refused');
  });
});

// ============================================================================
// RAG 問答測試
// ============================================================================

describe('ragQuery - RAG 問答', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功執行 RAG 問答', async () => {
    const mockResponse = {
      answer: '根據公文記載...',
      sources: [{ id: 1, subject: '相關公文' }],
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await ragQuery({ question: '查估進度如何' });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/ai/rag/query',
      { question: '查估進度如何' }
    );
    expect(result.answer).toBe('根據公文記載...');
  });

  it('API 錯誤時應向上拋出', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('LLM Error'));

    await expect(ragQuery({ question: '測試' })).rejects.toThrow('LLM Error');
  });
});

/**
 * useNaturalSearch - AI 自然語言公文搜尋 Hook
 *
 * 從 NaturalSearchPanel.tsx 提取的狀態管理、API 呼叫、搜尋邏輯、
 * 歷史管理與快取管理。
 *
 * @version 1.0.0
 * @created 2026-02-19
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { App } from 'antd';
import { aiApi, abortNaturalSearch } from '../../../api/aiApi';
import type {
  DocumentSearchResult,
  ParsedSearchIntent,
  AttachmentInfo,
  NaturalSearchResponse,
  QuerySuggestionItem,
  MatchedEntity,
} from '../../../types/ai';
import { filesApi } from '../../../api/filesApi';

// ============================================================================
// 常數
// ============================================================================

/** 搜尋歷史 localStorage 鍵 */
const AI_SEARCH_HISTORY_KEY = 'ai_search_history';

/** 搜尋歷史最大筆數 */
const MAX_HISTORY = 10;

/** 快取 TTL: 5 分鐘 (毫秒) */
const CACHE_TTL_MS = 300000;

// ============================================================================
// 搜尋結果快取 (module-level)
// ============================================================================

interface CacheEntry {
  results: DocumentSearchResult[];
  parsedIntent: ParsedSearchIntent;
  total: number;
  source: NaturalSearchResponse['source'];
  timestamp: number;
}

/** 模組層級快取 Map，跨元件實例共享 */
const searchCache = new Map<string, CacheEntry>();

/**
 * 取得快取鍵 (trim + lowercase)
 */
function getCacheKey(query: string): string {
  return query.trim().toLowerCase();
}

/**
 * 檢查快取是否命中且未過期
 */
function getCachedResult(query: string): CacheEntry | null {
  const key = getCacheKey(query);
  const entry = searchCache.get(key);
  if (!entry) return null;

  if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
    searchCache.delete(key);
    return null;
  }

  return entry;
}

/**
 * 儲存搜尋結果到快取
 */
function setCachedResult(
  query: string,
  results: DocumentSearchResult[],
  parsedIntent: ParsedSearchIntent,
  total: number,
  source: NaturalSearchResponse['source'],
): void {
  const key = getCacheKey(query);
  searchCache.set(key, {
    results,
    parsedIntent,
    total,
    source,
    timestamp: Date.now(),
  });
}

// ============================================================================
// 搜尋歷史工具函數
// ============================================================================

/**
 * 從 localStorage 讀取搜尋歷史
 */
function loadSearchHistory(): string[] {
  try {
    const raw = localStorage.getItem(AI_SEARCH_HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item: unknown) => typeof item === 'string').slice(0, MAX_HISTORY);
  } catch {
    return [];
  }
}

/**
 * 儲存搜尋歷史到 localStorage
 */
function saveSearchHistory(history: string[]): void {
  try {
    localStorage.setItem(AI_SEARCH_HISTORY_KEY, JSON.stringify(history.slice(0, MAX_HISTORY)));
  } catch {
    // localStorage 可能已滿或不可用，靜默忽略
  }
}

/**
 * 新增查詢到搜尋歷史 (去重，最新在前)
 */
function addToHistory(history: string[], query: string): string[] {
  const trimmed = query.trim();
  if (!trimmed) return history;

  // 去重：移除已存在的相同查詢
  const filtered = history.filter((item) => item !== trimmed);
  // 最新在前
  const updated = [trimmed, ...filtered].slice(0, MAX_HISTORY);
  return updated;
}

// ============================================================================
// Hook 型別定義
// ============================================================================

export interface UseNaturalSearchOptions {
  /** 搜尋完成後的回調 */
  onSearchComplete?: (total: number) => void;
}

export interface UseNaturalSearchReturn {
  // 搜尋狀態
  query: string;
  setQuery: (value: string) => void;
  loading: boolean;
  loadingMore: boolean;
  results: DocumentSearchResult[];
  parsedIntent: ParsedSearchIntent | null;
  total: number;
  offset: number;
  searched: boolean;
  error: string | null;
  fromCache: boolean;
  searchSource: NaturalSearchResponse['source'] | null;
  matchedEntities: MatchedEntity[];

  // 展開/收合
  expandedId: number | null;
  setExpandedId: (id: number | null) => void;
  showIntentDetails: boolean;
  setShowIntentDetails: (show: boolean) => void;

  // 搜尋歷史 & 建議
  searchHistory: string[];
  autoCompleteOpen: boolean;
  setAutoCompleteOpen: (open: boolean) => void;
  serverSuggestions: QuerySuggestionItem[];
  fetchSuggestions: (prefix: string) => void;

  // 搜尋回饋
  historyId: number | null;
  feedbackScore: number | null;
  handleFeedback: (score: 1 | -1) => Promise<void>;

  // 操作
  handleSearch: (searchQuery: string, searchOffset?: number) => Promise<void>;
  handleDocumentClick: (docId: number) => void;
  handleDownloadAttachment: (attachment: AttachmentInfo) => Promise<void>;
  handlePreviewAttachment: (attachment: AttachmentInfo) => Promise<void>;
  handleAutoCompleteSelect: (value: string) => void;
  handleLoadMore: () => void;
  removeHistoryItem: (item: string, e: React.MouseEvent) => void;
  clearAllHistory: (e: React.SyntheticEvent) => void;
}

// ============================================================================
// Hook
// ============================================================================

/**
 * AI 自然語言公文搜尋 Hook
 *
 * 管理搜尋狀態、API 呼叫、快取、歷史記錄等所有邏輯。
 */
export function useNaturalSearch(options: UseNaturalSearchOptions = {}): UseNaturalSearchReturn {
  const { onSearchComplete } = options;
  const navigate = useNavigate();
  const { message } = App.useApp();

  // 狀態
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [results, setResults] = useState<DocumentSearchResult[]>([]);
  const [parsedIntent, setParsedIntent] = useState<ParsedSearchIntent | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fromCache, setFromCache] = useState(false);
  const [searchSource, setSearchSource] = useState<NaturalSearchResponse['source'] | null>(null);
  const [matchedEntities, setMatchedEntities] = useState<MatchedEntity[]>([]);

  // 搜尋回饋
  const [historyId, setHistoryId] = useState<number | null>(null);
  const [feedbackScore, setFeedbackScore] = useState<number | null>(null);

  // 壓縮結果 + 手風琴展開
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showIntentDetails, setShowIntentDetails] = useState(false);

  // 搜尋歷史 & 伺服器建議
  const [searchHistory, setSearchHistory] = useState<string[]>(() => loadSearchHistory());
  const [autoCompleteOpen, setAutoCompleteOpen] = useState(false);
  const [serverSuggestions, setServerSuggestions] = useState<QuerySuggestionItem[]>([]);
  const suggestTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ref 用於追蹤最新的 loading 狀態 (避免 useCallback 閉包問題)
  const loadingRef = useRef(false);
  const loadingMoreRef = useRef(false);
  loadingRef.current = loading;
  loadingMoreRef.current = loadingMore;

  // 元件卸載時取消進行中的搜尋
  useEffect(() => {
    return () => {
      abortNaturalSearch();
    };
  }, []);

  // 更新搜尋歷史並持久化
  const updateHistory = useCallback((newHistory: string[]) => {
    setSearchHistory(newHistory);
    saveSearchHistory(newHistory);
  }, []);

  // 刪除單筆歷史記錄
  const removeHistoryItem = useCallback((item: string, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    const updated = searchHistory.filter((h) => h !== item);
    updateHistory(updated);
  }, [searchHistory, updateHistory]);

  // 清除全部歷史
  const clearAllHistory = useCallback((e: React.SyntheticEvent) => {
    e.stopPropagation();
    e.preventDefault();
    updateHistory([]);
    setAutoCompleteOpen(false);
  }, [updateHistory]);

  // 取得伺服器端搜尋建議（debounce 300ms）
  const fetchSuggestions = useCallback((prefix: string) => {
    if (suggestTimerRef.current) {
      clearTimeout(suggestTimerRef.current);
    }
    suggestTimerRef.current = setTimeout(async () => {
      const result = await aiApi.getQuerySuggestions({ prefix, limit: 8 });
      if (result?.suggestions) {
        setServerSuggestions(result.suggestions);
      }
    }, 500);
  }, []);

  // 元件卸載時清除 debounce timer
  useEffect(() => {
    return () => {
      if (suggestTimerRef.current) {
        clearTimeout(suggestTimerRef.current);
      }
    };
  }, []);

  // 執行搜尋（防止重複提交，支援分頁載入更多）
  const handleSearch = useCallback(async (searchQuery: string, searchOffset: number = 0) => {
    if (!searchQuery.trim()) {
      message.warning('請輸入搜尋內容');
      return;
    }

    // 防止重複提交
    if (loadingRef.current || loadingMoreRef.current) return;

    // 關閉 AutoComplete 下拉
    setAutoCompleteOpen(false);

    const isLoadMore = searchOffset > 0;

    // 快取檢查（僅針對首次搜尋，不包含載入更多）
    if (!isLoadMore) {
      const cached = getCachedResult(searchQuery);
      if (cached) {
        setResults(cached.results);
        setParsedIntent(cached.parsedIntent);
        setTotal(cached.total);
        setSearchSource(cached.source);
        setSearched(true);
        setFromCache(true);
        setError(null);
        setOffset(0);
        onSearchComplete?.(cached.total);

        // 即使從快取取得，也記錄歷史
        const updatedHistory = addToHistory(searchHistory, searchQuery);
        updateHistory(updatedHistory);

        if (cached.total === 0) {
          message.info('未找到符合條件的公文');
        }
        return;
      }
    }

    if (isLoadMore) {
      setLoadingMore(true);
      setOffset(searchOffset);
    } else {
      setLoading(true);
      setOffset(0);
      setFromCache(false);
    }
    setError(null);

    try {
      const response = await aiApi.naturalSearch(searchQuery, 20, true, searchOffset);

      if (response.success) {
        if (isLoadMore) {
          // 載入更多：追加結果
          setResults((prev) => [...prev, ...response.results]);
        } else {
          // 新搜尋：替換結果
          setResults(response.results);
          setSearchSource(response.source);
          setMatchedEntities(response.matched_entities ?? []);
          setHistoryId(response.history_id ?? null);
          setFeedbackScore(null);

          // 快取結果（僅首次搜尋）
          setCachedResult(searchQuery, response.results, response.parsed_intent, response.total, response.source);

          // 記錄搜尋歷史
          const updatedHistory = addToHistory(searchHistory, searchQuery);
          updateHistory(updatedHistory);
        }
        setParsedIntent(response.parsed_intent);
        setTotal(response.total);
        setSearched(true);
        onSearchComplete?.(response.total);

        if (response.total === 0 && !isLoadMore) {
          message.info('未找到符合條件的公文');
        }
      } else {
        // 區分錯誤類型提供更有用的訊息
        const errorMsg = response.error || '搜尋失敗';
        const isAiUnavailable = errorMsg.includes('AI 服務') || errorMsg.includes('ConnectError');
        const isTimeout = errorMsg.includes('超時') || errorMsg.includes('timeout');
        const isRateLimit = errorMsg.includes('速率') || errorMsg.includes('rate');

        let userMessage: string;
        if (isTimeout) {
          userMessage = '搜尋查詢超時，請縮小搜尋範圍或使用更具體的關鍵字';
        } else if (isAiUnavailable) {
          userMessage = '目前 AI 服務暫時無法使用，系統已自動使用關鍵字搜尋';
        } else if (isRateLimit) {
          userMessage = 'AI 服務請求過於頻繁，請稍後再試';
        } else {
          userMessage = errorMsg;
        }

        setError(userMessage);
        // 超時和 AI 不可用用 warning（非嚴重錯誤），其餘用 error
        if (isTimeout || isAiUnavailable) {
          message.warning(userMessage);
        } else {
          message.error(userMessage);
        }
      }
    } catch (err) {
      const rawMsg = err instanceof Error ? err.message : '搜尋發生錯誤';
      const isCancelled = rawMsg.includes('取消') || rawMsg.includes('abort') || rawMsg.includes('cancel');
      if (isCancelled) {
        setError('搜尋已取消');
      } else {
        setError(rawMsg);
        message.error(rawMsg);
      }
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [message, onSearchComplete, searchHistory, updateHistory]);

  // 點擊公文查看詳情
  const handleDocumentClick = useCallback((docId: number) => {
    navigate(`/documents/${docId}`);
  }, [navigate]);

  // 下載附件
  const handleDownloadAttachment = useCallback(async (attachment: AttachmentInfo) => {
    try {
      await filesApi.downloadAttachment(
        attachment.id,
        attachment.original_name || attachment.file_name
      );
      message.success(`已開始下載: ${attachment.original_name || attachment.file_name}`);
    } catch {
      message.error('下載失敗');
    }
  }, [message]);

  // 預覽附件 (取得 Blob 並開啟新視窗)
  const handlePreviewAttachment = useCallback(async (attachment: AttachmentInfo) => {
    try {
      const blob = await filesApi.getAttachmentBlob(attachment.id);
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
      // 延遲釋放 URL，確保瀏覽器有時間開啟
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch {
      message.error('預覽失敗');
    }
  }, [message]);

  // AutoComplete 選擇事件
  const handleAutoCompleteSelect = useCallback((value: string) => {
    // 忽略清除歷史的特殊選項
    if (value === '__clear_history__') return;
    setQuery(value);
    handleSearch(value);
  }, [handleSearch]);

  // 搜尋回饋
  const handleFeedback = useCallback(async (score: 1 | -1) => {
    if (!historyId) return;
    const result = await aiApi.submitSearchFeedback({ history_id: historyId, score });
    if (result?.success) {
      setFeedbackScore(score);
      message.success(result.message);
    } else {
      message.error('回饋提交失敗');
    }
  }, [historyId, message]);

  // 載入更多結果
  const handleLoadMore = useCallback(() => {
    const newOffset = offset + 20;
    handleSearch(query, newOffset);
  }, [offset, query, handleSearch]);

  return {
    // 搜尋狀態
    query,
    setQuery,
    loading,
    loadingMore,
    results,
    parsedIntent,
    total,
    offset,
    searched,
    error,
    fromCache,
    searchSource,
    matchedEntities,

    // 展開/收合
    expandedId,
    setExpandedId,
    showIntentDetails,
    setShowIntentDetails,

    // 搜尋歷史 & 建議
    searchHistory,
    autoCompleteOpen,
    setAutoCompleteOpen,
    serverSuggestions,
    fetchSuggestions,

    // 搜尋回饋
    historyId,
    feedbackScore,
    handleFeedback,

    // 操作
    handleSearch,
    handleDocumentClick,
    handleDownloadAttachment,
    handlePreviewAttachment,
    handleAutoCompleteSelect,
    handleLoadMore,
    removeHistoryItem,
    clearAllHistory,
  };
}

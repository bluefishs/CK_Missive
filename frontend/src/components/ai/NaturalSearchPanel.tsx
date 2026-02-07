/**
 * AI 自然語言公文搜尋面板
 *
 * 支援自然語言輸入搜尋公文，顯示結果列表與附件
 * - 搜尋歷史 (localStorage 持久化，最多 10 筆)
 * - 結果快取 (記憶體，5 分鐘 TTL)
 *
 * @version 1.1.0
 * @created 2026-02-05
 * @updated 2026-02-07 - 新增搜尋歷史與結果快取
 */

import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import {
  AutoComplete,
  Button as AntButton,
  List,
  Space,
  Tag,
  Button,
  Empty,
  Spin,
  Typography,
  Collapse,
  Tooltip,
  App,
} from 'antd';
import {
  SearchOutlined,
  FileOutlined,
  PaperClipOutlined,
  DownloadOutlined,
  EyeOutlined,
  CalendarOutlined,
  UserOutlined,
  InfoCircleOutlined,
  CloseOutlined,
  DeleteOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { aiApi, abortNaturalSearch, DocumentSearchResult, ParsedSearchIntent, AttachmentInfo } from '../../api/aiApi';
import { filesApi } from '../../api/filesApi';

const { Text, Paragraph } = Typography;

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
): void {
  const key = getCacheKey(query);
  searchCache.set(key, {
    results,
    parsedIntent,
    total,
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
// 元件
// ============================================================================

interface NaturalSearchPanelProps {
  /** 面板高度 */
  height?: number | string;
  /** 搜尋完成後的回調 */
  onSearchComplete?: (total: number) => void;
}

/**
 * AI 自然語言公文搜尋面板
 */
export const NaturalSearchPanel: React.FC<NaturalSearchPanelProps> = ({
  height,
  onSearchComplete,
}) => {
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

  // 搜尋歷史
  const [searchHistory, setSearchHistory] = useState<string[]>(() => loadSearchHistory());
  const [autoCompleteOpen, setAutoCompleteOpen] = useState(false);

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
  const clearAllHistory = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    updateHistory([]);
    setAutoCompleteOpen(false);
  }, [updateHistory]);

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

          // 快取結果（僅首次搜尋）
          setCachedResult(searchQuery, response.results, response.parsed_intent, response.total);

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
        setError(isAiUnavailable ? '目前 AI 服務暫時無法使用，請稍後再試' : errorMsg);
        message.error(isAiUnavailable ? 'AI 服務暫時無法使用' : errorMsg);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '搜尋發生錯誤';
      setError(errorMsg);
      message.error(errorMsg);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [onSearchComplete, searchHistory, updateHistory]);

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
  }, []);

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
  }, []);

  // 渲染搜尋意圖標籤（useMemo 優化，僅在 parsedIntent 變化時重新計算）
  const intentTagsNode = useMemo(() => {
    if (!parsedIntent || parsedIntent.confidence === 0) return null;

    const tags: React.ReactNode[] = [];

    if (parsedIntent.keywords?.length) {
      tags.push(
        <Tag key="keywords" color="blue">
          關鍵字: {parsedIntent.keywords.join(', ')}
        </Tag>
      );
    }
    if (parsedIntent.category) {
      tags.push(<Tag key="category" color="green">{parsedIntent.category}</Tag>);
    }
    if (parsedIntent.sender) {
      tags.push(<Tag key="sender" color="orange">發文: {parsedIntent.sender}</Tag>);
    }
    if (parsedIntent.date_from || parsedIntent.date_to) {
      const dateRange = [parsedIntent.date_from, parsedIntent.date_to].filter(Boolean).join(' ~ ');
      tags.push(<Tag key="date" color="purple">日期: {dateRange}</Tag>);
    }
    if (parsedIntent.status) {
      tags.push(<Tag key="status" color="cyan">{parsedIntent.status}</Tag>);
    }

    if (tags.length === 0) return null;

    return (
      <div style={{ marginBottom: 8 }}>
        <Text type="secondary" style={{ fontSize: 11 }}>
          <InfoCircleOutlined style={{ marginRight: 4 }} />
          AI 解析結果 (信心度: {Math.round(parsedIntent.confidence * 100)}%):
        </Text>
        <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {tags}
        </div>
      </div>
    );
  }, [parsedIntent]);

  // AutoComplete 選項：搜尋歷史下拉選單
  const autoCompleteOptions = useMemo(() => {
    // 只在查詢為空且有歷史時顯示
    if (query.trim() || searchHistory.length === 0) return [];

    const historyItems = searchHistory.map((item) => ({
      value: item,
      label: (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Space size="small" style={{ flex: 1, overflow: 'hidden' }}>
            <ClockCircleOutlined style={{ color: '#999', fontSize: 12 }} />
            <Text ellipsis style={{ fontSize: 13, maxWidth: 200 }}>
              {item}
            </Text>
          </Space>
          <AntButton
            type="text"
            size="small"
            icon={<CloseOutlined style={{ fontSize: 10, color: '#999' }} />}
            onClick={(e) => removeHistoryItem(item, e)}
            style={{ minWidth: 20, padding: '0 4px' }}
          />
        </div>
      ),
    }));

    // 底部加入「清除搜尋歷史」按鈕
    historyItems.push({
      value: '__clear_history__',
      label: (
        <div
          style={{
            textAlign: 'center',
            borderTop: '1px solid #f0f0f0',
            paddingTop: 4,
          }}
          onClick={clearAllHistory}
        >
          <AntButton
            type="text"
            size="small"
            icon={<DeleteOutlined style={{ fontSize: 11 }} />}
            style={{ color: '#999', fontSize: 12 }}
          >
            清除搜尋歷史
          </AntButton>
        </div>
      ),
    });

    return historyItems;
  }, [query, searchHistory, removeHistoryItem, clearAllHistory]);

  // AutoComplete 選擇事件
  const handleAutoCompleteSelect = useCallback((value: string) => {
    // 忽略清除歷史的特殊選項
    if (value === '__clear_history__') return;
    setQuery(value);
    handleSearch(value);
  }, [handleSearch]);

  // 渲染附件列表
  const renderAttachments = (attachments: AttachmentInfo[]) => {
    if (!attachments.length) return null;

    return (
      <Collapse
        size="small"
        ghost
        items={[
          {
            key: 'attachments',
            label: (
              <Space size="small">
                <PaperClipOutlined />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  附件 ({attachments.length})
                </Text>
              </Space>
            ),
            children: (
              <List
                size="small"
                dataSource={attachments}
                renderItem={(att) => (
                  <List.Item
                    actions={[
                      <Tooltip key="preview" title="預覽">
                        <Button
                          type="text"
                          size="small"
                          icon={<EyeOutlined />}
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePreviewAttachment(att);
                          }}
                        />
                      </Tooltip>,
                      <Tooltip key="download" title="下載">
                        <Button
                          type="text"
                          size="small"
                          icon={<DownloadOutlined />}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDownloadAttachment(att);
                          }}
                        />
                      </Tooltip>,
                    ]}
                    style={{ padding: '4px 0' }}
                  >
                    <Space size="small">
                      <FileOutlined style={{ color: '#1890ff' }} />
                      <Text
                        ellipsis
                        style={{ fontSize: 12, maxWidth: 150 }}
                        title={att.original_name || att.file_name}
                      >
                        {att.original_name || att.file_name}
                      </Text>
                    </Space>
                  </List.Item>
                )}
              />
            ),
          },
        ]}
      />
    );
  };

  // 渲染搜尋結果項目
  const renderResultItem = (item: DocumentSearchResult) => (
    <List.Item
      key={item.id}
      onClick={() => handleDocumentClick(item.id)}
      style={{
        cursor: 'pointer',
        padding: '8px 12px',
        borderRadius: 8,
        marginBottom: 4,
        background: '#fafafa',
        border: '1px solid #f0f0f0',
        transition: 'all 0.2s',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = '#e6f7ff';
        e.currentTarget.style.borderColor = '#91d5ff';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = '#fafafa';
        e.currentTarget.style.borderColor = '#f0f0f0';
      }}
    >
      <div style={{ width: '100%' }}>
        {/* 第一行: 公文字號 + 類型 + 附件數 */}
        <Space size="small" style={{ marginBottom: 4 }}>
          <Tag color={item.category === '收文' ? 'blue' : 'green'}>
            {item.category || '公文'}
          </Tag>
          <Text strong style={{ fontSize: 13 }}>
            {item.doc_number}
          </Text>
          {item.attachment_count > 0 && (
            <Tag icon={<PaperClipOutlined />} style={{ fontSize: 11 }}>
              {item.attachment_count}
            </Tag>
          )}
        </Space>

        {/* 第二行: 主旨 */}
        <Paragraph
          ellipsis={{ rows: 2 }}
          style={{ fontSize: 12, margin: 0, color: '#333' }}
        >
          {item.subject}
        </Paragraph>

        {/* 第三行: 日期 + 發文單位 */}
        <Space size="middle" style={{ marginTop: 4 }}>
          {item.doc_date && (
            <Text type="secondary" style={{ fontSize: 11 }}>
              <CalendarOutlined style={{ marginRight: 4 }} />
              {item.doc_date}
            </Text>
          )}
          {item.sender && (
            <Text type="secondary" style={{ fontSize: 11 }}>
              <UserOutlined style={{ marginRight: 4 }} />
              {item.sender}
            </Text>
          )}
        </Space>

        {/* 附件列表 (可展開) */}
        {item.attachments.length > 0 && (
          <div style={{ marginTop: 8 }} onClick={(e) => e.stopPropagation()}>
            {renderAttachments(item.attachments)}
          </div>
        )}
      </div>
    </List.Item>
  );

  return (
    <div style={{ flex: 1, minHeight: 200, display: 'flex', flexDirection: 'column', ...(height != null ? { height } : {}) }}>
      {/* 搜尋框: AutoComplete + 搜尋按鈕 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <AutoComplete
          style={{ flex: 1 }}
          options={autoCompleteOptions}
          value={query}
          onChange={(value) => setQuery(value)}
          onSelect={handleAutoCompleteSelect}
          open={autoCompleteOpen}
          onFocus={() => {
            if (!query.trim() && searchHistory.length > 0) {
              setAutoCompleteOpen(true);
            }
          }}
          onBlur={() => {
            // 延遲關閉以允許點擊選項
            setTimeout(() => setAutoCompleteOpen(false), 200);
          }}
          onSearch={(value) => {
            // 輸入文字時關閉歷史下拉
            if (value.trim()) {
              setAutoCompleteOpen(false);
            } else if (searchHistory.length > 0) {
              setAutoCompleteOpen(true);
            }
          }}
          placeholder="輸入自然語言搜尋，例如：找桃園市政府上個月的公文"
        >
          <input
            style={{
              width: '100%',
              padding: '4px 11px',
              border: '1px solid #d9d9d9',
              borderRadius: 6,
              outline: 'none',
              fontSize: 14,
              lineHeight: '22px',
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                setAutoCompleteOpen(false);
                handleSearch(query);
              }
            }}
          />
        </AutoComplete>
        <Button
          type="primary"
          icon={<SearchOutlined />}
          loading={loading}
          onClick={() => handleSearch(query)}
        >
          搜尋
        </Button>
      </div>

      {/* 快取命中提示 */}
      {searched && fromCache && (
        <div style={{ marginBottom: 8 }}>
          <Tag color="blue">快取結果</Tag>
        </div>
      )}

      {/* 搜尋意圖顯示 */}
      {searched && intentTagsNode}

      {/* 搜尋結果區 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin tip="AI 正在搜尋中...">
              <div style={{ padding: '30px 50px' }} />
            </Spin>
          </div>
        ) : error ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Text type="danger">{error}</Text>
            }
          />
        ) : !searched ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <div>
                <Text type="secondary">輸入自然語言搜尋公文</Text>
                <div style={{ marginTop: 12 }}>
                  <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>
                    試試看：
                  </Text>
                  <Space size={[4, 8]} wrap>
                    {[
                      '找桃園市政府上個月的公文',
                      '有截止日的待處理收文',
                      '今年度的會勘通知',
                      '乾坤測字 1140 開頭的公文',
                    ].map((suggestion) => (
                      <Tag
                        key={suggestion}
                        color="blue"
                        style={{ cursor: 'pointer', fontSize: 12 }}
                        onClick={() => {
                          setQuery(suggestion);
                          handleSearch(suggestion);
                        }}
                      >
                        {suggestion}
                      </Tag>
                    ))}
                  </Space>
                </div>
              </div>
            }
          />
        ) : results.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="未找到符合條件的公文"
          />
        ) : (
          <>
            <div style={{ marginBottom: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                找到 {total} 筆公文，已顯示 {results.length} 筆
              </Text>
            </div>
            <List
              size="small"
              dataSource={results}
              renderItem={renderResultItem}
            />
            {results.length < total && (
              <div style={{ textAlign: 'center', padding: '12px 0' }}>
                <Button
                  type="link"
                  loading={loadingMore}
                  onClick={() => {
                    const newOffset = offset + 20;
                    setOffset(newOffset);
                    handleSearch(query, newOffset);
                  }}
                >
                  載入更多
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default NaturalSearchPanel;

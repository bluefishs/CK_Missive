/**
 * AI 自然語言公文搜尋面板
 *
 * 支援自然語言輸入搜尋公文，顯示結果列表與附件
 * - 搜尋歷史 (localStorage 持久化，最多 10 筆)
 * - 結果快取 (記憶體，5 分鐘 TTL)
 *
 * 邏輯已提取至 useNaturalSearch hook，本元件僅負責 UI 渲染。
 *
 * @version 2.0.0
 * @created 2026-02-05
 * @updated 2026-02-19 - 提取 useNaturalSearch hook，元件僅保留渲染邏輯
 */

import React, { useMemo } from 'react';
import {
  AutoComplete,
  Button as AntButton,
  Space,
  Tag,
  Button,
  Empty,
  Spin,
  Tooltip,
  Typography,
} from 'antd';
import {
  SearchOutlined,
  PaperClipOutlined,
  DownloadOutlined,
  EyeOutlined,
  CalendarOutlined,
  UserOutlined,
  CloseOutlined,
  DeleteOutlined,
  ClockCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import type { DocumentSearchResult, AttachmentInfo } from '../../api/aiApi';
import { useNaturalSearch } from './hooks/useNaturalSearch';

const { Text } = Typography;

// ============================================================================
// 壓縮結果項目子元件
// ============================================================================

interface CompactResultItemProps {
  item: DocumentSearchResult;
  isExpanded: boolean;
  onToggle: () => void;
  onDocumentClick: (docId: number) => void;
  onPreview: (att: AttachmentInfo) => void;
  onDownload: (att: AttachmentInfo) => void;
}

const CompactResultItem: React.FC<CompactResultItemProps> = React.memo(({
  item, isExpanded, onToggle, onDocumentClick, onPreview, onDownload,
}) => (
  <div
    onClick={onToggle}
    style={{
      cursor: 'pointer', borderRadius: 6, marginBottom: 2, overflow: 'hidden',
      background: isExpanded ? '#e6f7ff' : '#fafafa',
      border: `1px solid ${isExpanded ? '#91d5ff' : '#f0f0f0'}`,
      transition: 'all 0.15s',
    }}
    onMouseEnter={(e) => { if (!isExpanded) { e.currentTarget.style.background = '#f0f5ff'; e.currentTarget.style.borderColor = '#d6e4ff'; } }}
    onMouseLeave={(e) => { if (!isExpanded) { e.currentTarget.style.background = '#fafafa'; e.currentTarget.style.borderColor = '#f0f0f0'; } }}
  >
    {/* 壓縮行 */}
    <div style={{ display: 'flex', alignItems: 'center', height: 36, padding: '0 8px', gap: 6 }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: item.category === '收文' ? '#1890ff' : '#52c41a', flexShrink: 0 }} />
      <Text strong style={{ fontSize: 11, maxWidth: 100, flexShrink: 0 }} ellipsis>{item.doc_number}</Text>
      <Text style={{ fontSize: 11, flex: 1, color: '#555' }} ellipsis>{item.subject}</Text>
      {item.attachment_count > 0 && (
        <span style={{ fontSize: 10, color: '#999', flexShrink: 0, display: 'flex', alignItems: 'center', gap: 2 }}>
          <PaperClipOutlined style={{ fontSize: 10 }} />{item.attachment_count}
        </span>
      )}
      <span style={{ fontSize: 10, color: '#bbb', flexShrink: 0, width: 12, textAlign: 'center' }}>{isExpanded ? '▾' : '▸'}</span>
    </div>

    {/* 展開詳情 */}
    {isExpanded && (
      <div style={{ padding: '6px 10px 8px 20px', borderTop: '1px solid #f0f0f0', background: '#fafafa' }}>
        <div style={{ fontSize: 12, color: '#333', marginBottom: 6, lineHeight: 1.6 }}>{item.subject}</div>
        <div style={{ display: 'flex', gap: 12, fontSize: 11, color: '#888', marginBottom: 6 }}>
          {item.doc_date && <span><CalendarOutlined style={{ marginRight: 3 }} />{item.doc_date}</span>}
          {item.sender && <span><UserOutlined style={{ marginRight: 3 }} />{item.sender}</span>}
        </div>
        {item.attachments.length > 0 && (
          <div style={{ marginBottom: 6 }}>
            {item.attachments.map((att) => (
              <div key={att.id} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, padding: '2px 0' }}>
                <PaperClipOutlined style={{ color: '#1890ff', fontSize: 10 }} />
                <Text ellipsis style={{ flex: 1, fontSize: 11 }} title={att.original_name || att.file_name}>{att.original_name || att.file_name}</Text>
                <Button type="text" size="small" icon={<EyeOutlined style={{ fontSize: 11 }} />}
                  onClick={(e) => { e.stopPropagation(); onPreview(att); }} style={{ padding: '0 2px', height: 18, minWidth: 18 }} aria-label="預覽" />
                <Button type="text" size="small" icon={<DownloadOutlined style={{ fontSize: 11 }} />}
                  onClick={(e) => { e.stopPropagation(); onDownload(att); }} style={{ padding: '0 2px', height: 18, minWidth: 18 }} aria-label="下載" />
              </div>
            ))}
          </div>
        )}
        <Button type="link" size="small" onClick={(e) => { e.stopPropagation(); onDocumentClick(item.id); }}
          style={{ padding: 0, fontSize: 11, height: 'auto' }}>查看完整公文 →</Button>
      </div>
    )}
  </div>
));
CompactResultItem.displayName = 'CompactResultItem';

// ============================================================================
// 主元件
// ============================================================================

interface NaturalSearchPanelProps {
  height?: number | string;
  onSearchComplete?: (total: number) => void;
}

export const NaturalSearchPanel: React.FC<NaturalSearchPanelProps> = ({ height, onSearchComplete }) => {
  const {
    query, setQuery, loading, loadingMore, results, parsedIntent, total,
    searched, error, fromCache, searchSource,
    expandedId, setExpandedId, showIntentDetails, setShowIntentDetails,
    searchHistory, autoCompleteOpen, setAutoCompleteOpen,
    handleSearch, handleDocumentClick, handleDownloadAttachment, handlePreviewAttachment,
    handleAutoCompleteSelect, handleLoadMore, removeHistoryItem, clearAllHistory,
  } = useNaturalSearch({ onSearchComplete });

  // 搜尋意圖標籤
  const intentTagsNode = useMemo(() => {
    if (!parsedIntent || parsedIntent.confidence === 0) return null;
    const tags: React.ReactNode[] = [];
    if (parsedIntent.keywords?.length) {
      tags.push(<Tag key="keywords" color="blue" style={{ fontSize: 11, margin: 0 }}>關鍵字: {parsedIntent.keywords.join(', ')}</Tag>);
    }
    if (parsedIntent.category) tags.push(<Tag key="category" color="green" style={{ fontSize: 11, margin: 0 }}>{parsedIntent.category}</Tag>);
    if (parsedIntent.sender) tags.push(<Tag key="sender" color="orange" style={{ fontSize: 11, margin: 0 }}>發文: {parsedIntent.sender}</Tag>);
    if (parsedIntent.date_from || parsedIntent.date_to) {
      const dateRange = [parsedIntent.date_from, parsedIntent.date_to].filter(Boolean).join(' ~ ');
      tags.push(<Tag key="date" color="purple" style={{ fontSize: 11, margin: 0 }}>日期: {dateRange}</Tag>);
    }
    if (parsedIntent.status) tags.push(<Tag key="status" color="cyan" style={{ fontSize: 11, margin: 0 }}>{parsedIntent.status}</Tag>);
    if (parsedIntent.related_entity === 'dispatch_order') tags.push(<Tag key="entity" color="volcano" style={{ fontSize: 11, margin: 0 }}>派工單關聯</Tag>);
    else if (parsedIntent.related_entity === 'project') tags.push(<Tag key="entity" color="volcano" style={{ fontSize: 11, margin: 0 }}>專案關聯</Tag>);
    const sourceMap: Record<string, { color: string; label: string }> = {
      rule_engine: { color: 'green', label: '規則引擎' }, vector: { color: 'cyan', label: '向量匹配' },
      ai: { color: 'blue', label: 'AI 解析' }, merged: { color: 'purple', label: '混合解析' },
      fallback: { color: 'default', label: '降級搜尋' },
    };
    if (searchSource && sourceMap[searchSource]) {
      const s = sourceMap[searchSource];
      tags.push(<Tag key="source" color={s.color} style={{ fontSize: 11, margin: 0 }}>{s.label}</Tag>);
    }
    if (tags.length === 0) return null;
    return <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3, padding: '4px 0 6px' }}>{tags}</div>;
  }, [parsedIntent, searchSource]);

  // AutoComplete 歷史選項
  const autoCompleteOptions = useMemo(() => {
    if (query.trim() || searchHistory.length === 0) return [];
    const items = searchHistory.map((item) => ({
      value: item,
      label: (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Space size="small" style={{ flex: 1, overflow: 'hidden' }}>
            <ClockCircleOutlined style={{ color: '#999', fontSize: 12 }} />
            <Text ellipsis style={{ fontSize: 13, maxWidth: 200 }}>{item}</Text>
          </Space>
          <AntButton type="text" size="small" icon={<CloseOutlined style={{ fontSize: 10, color: '#999' }} />}
            onClick={(e) => removeHistoryItem(item, e)} style={{ minWidth: 20, padding: '0 4px' }} aria-label="移除此搜尋歷史" />
        </div>
      ),
    }));
    items.push({
      value: '__clear_history__',
      label: (
        <div style={{ textAlign: 'center', borderTop: '1px solid #f0f0f0', paddingTop: 4 }} onClick={clearAllHistory}>
          <AntButton type="text" size="small" icon={<DeleteOutlined style={{ fontSize: 11 }} />} style={{ color: '#999', fontSize: 12 }}>清除搜尋歷史</AntButton>
        </div>
      ),
    });
    return items;
  }, [query, searchHistory, removeHistoryItem, clearAllHistory]);

  return (
    <div style={{ flex: 1, minHeight: 200, display: 'flex', flexDirection: 'column', ...(height != null ? { height } : {}) }}>
      {/* 搜尋框 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <AutoComplete
          style={{ flex: 1 }} options={autoCompleteOptions} value={query}
          onChange={(value) => setQuery(value)} onSelect={handleAutoCompleteSelect}
          open={autoCompleteOpen}
          onFocus={() => { if (!query.trim() && searchHistory.length > 0) setAutoCompleteOpen(true); }}
          onBlur={() => setTimeout(() => setAutoCompleteOpen(false), 200)}
          onSearch={(value) => { if (value.trim()) setAutoCompleteOpen(false); else if (searchHistory.length > 0) setAutoCompleteOpen(true); }}
          placeholder="輸入自然語言搜尋，例如：找桃園市政府上個月的公文"
        >
          <input
            style={{ width: '100%', padding: '4px 11px', border: '1px solid #d9d9d9', borderRadius: 6, outline: 'none', fontSize: 14, lineHeight: '22px' }}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); setAutoCompleteOpen(false); handleSearch(query); } }}
          />
        </AutoComplete>
        <Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={() => handleSearch(query)}>搜尋</Button>
      </div>

      {/* 搜尋結果區 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 30 }}>
            <Spin tip="AI 正在搜尋中..."><div style={{ padding: '20px 40px' }} /></Spin>
          </div>
        ) : error ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<Text type="danger" style={{ fontSize: 12 }}>{error}</Text>} />
        ) : !searched ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>輸入自然語言搜尋公文</Text>
              <div style={{ marginTop: 8 }}>
                <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 6 }}>試試看：</Text>
                <Space size={[4, 6]} wrap>
                  {['找桃園市政府上個月的公文', '有截止日的待處理收文', '今年度的會勘通知', '乾坤測字 1140 開頭的公文'].map((s) => (
                    <Tag key={s} color="blue" style={{ cursor: 'pointer', fontSize: 11 }} onClick={() => { setQuery(s); handleSearch(s); }}>{s}</Tag>
                  ))}
                </Space>
              </div>
            </div>
          } />
        ) : results.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="未找到符合條件的公文" />
        ) : (
          <>
            {/* 統計 + 快取 + 意圖 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <Space size={4}>
                <Text type="secondary" style={{ fontSize: 11 }}>{total} 筆結果，顯示 {results.length} 筆</Text>
                <Tooltip title="搜尋範圍為全系統公文（documents 表），結果包含主旨、內容含關鍵字的所有公文。若需查看特定派工單，請至「派工管理」頁面。">
                  <InfoCircleOutlined style={{ fontSize: 11, color: '#999', cursor: 'help' }} />
                </Tooltip>
              </Space>
              <Space size={4}>
                {fromCache && <Tag color="blue" style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}>快取</Tag>}
                {parsedIntent && parsedIntent.confidence > 0 && (
                  <Tag color="cyan" style={{ cursor: 'pointer', fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}
                    onClick={() => setShowIntentDetails(!showIntentDetails)}>
                    AI 解析 {Math.round(parsedIntent.confidence * 100)}% {showIntentDetails ? '▾' : '▸'}
                  </Tag>
                )}
              </Space>
            </div>
            {showIntentDetails && intentTagsNode}
            <div>
              {results.map((item) => (
                <CompactResultItem key={item.id} item={item} isExpanded={expandedId === item.id}
                  onToggle={() => setExpandedId(expandedId === item.id ? null : item.id)}
                  onDocumentClick={handleDocumentClick} onPreview={handlePreviewAttachment} onDownload={handleDownloadAttachment} />
              ))}
            </div>
            {results.length < total && (
              <div style={{ textAlign: 'center', padding: '6px 0' }}>
                <Button type="link" size="small" loading={loadingMore} onClick={handleLoadMore}>載入更多</Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default NaturalSearchPanel;

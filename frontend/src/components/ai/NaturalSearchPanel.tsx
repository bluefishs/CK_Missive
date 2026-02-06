/**
 * AI 自然語言公文搜尋面板
 *
 * 支援自然語言輸入搜尋公文，顯示結果列表與附件
 *
 * @version 1.0.0
 * @created 2026-02-05
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
  Input,
  List,
  Space,
  Tag,
  Button,
  Empty,
  Spin,
  Typography,
  Collapse,
  Tooltip,
  message,
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
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { aiApi, abortNaturalSearch, DocumentSearchResult, ParsedSearchIntent, AttachmentInfo } from '../../api/aiApi';
import { filesApi } from '../../api/filesApi';

const { Search } = Input;
const { Text, Paragraph } = Typography;

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
  height = 280,
  onSearchComplete,
}) => {
  const navigate = useNavigate();

  // 狀態
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<DocumentSearchResult[]>([]);
  const [parsedIntent, setParsedIntent] = useState<ParsedSearchIntent | null>(null);
  const [total, setTotal] = useState(0);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 元件卸載時取消進行中的搜尋
  useEffect(() => {
    return () => {
      abortNaturalSearch();
    };
  }, []);

  // 執行搜尋（防止重複提交）
  const handleSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      message.warning('請輸入搜尋內容');
      return;
    }

    // 防止重複提交
    if (loading) return;

    setLoading(true);
    setError(null);

    try {
      const response = await aiApi.naturalSearch(searchQuery, 20, true);

      if (response.success) {
        setResults(response.results);
        setParsedIntent(response.parsed_intent);
        setTotal(response.total);
        setSearched(true);
        onSearchComplete?.(response.total);

        if (response.total === 0) {
          message.info('未找到符合條件的公文');
        }
      } else {
        setError(response.error || '搜尋失敗');
        message.error(response.error || '搜尋失敗');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '搜尋發生錯誤';
      setError(errorMsg);
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [onSearchComplete, loading]);

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
    <div style={{ height, display: 'flex', flexDirection: 'column' }}>
      {/* 搜尋框 */}
      <Search
        placeholder="輸入自然語言搜尋，例如：找桃園市政府上個月的公文"
        enterButton={<><SearchOutlined /> 搜尋</>}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onSearch={handleSearch}
        loading={loading}
        style={{ marginBottom: 12 }}
        allowClear
      />

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
                <Text type="secondary">請輸入搜尋條件</Text>
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    範例: "找有截止日的待處理公文"、"桃園市政府的會勘通知"
                  </Text>
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
                找到 {total} 筆公文
              </Text>
            </div>
            <List
              size="small"
              dataSource={results}
              renderItem={renderResultItem}
            />
          </>
        )}
      </div>
    </div>
  );
};

export default NaturalSearchPanel;

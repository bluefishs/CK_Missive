/**
 * AI 分類建議面板元件
 *
 * 顯示 AI 建議的公文分類
 *
 * @version 1.0.0
 * @created 2026-02-04
 */

import React, { useState, useCallback } from 'react';
import { Card, Button, Typography, Space, Spin, Tag, Descriptions, App } from 'antd';
import {
  RobotOutlined,
  TagsOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { aiApi, ClassifyResponse } from '../../api/aiApi';
import { AI_CONFIG, getAISourceColor, getAISourceLabel, AISource } from '../../config/aiConfig';

const { Text } = Typography;

interface AIClassifyPanelProps {
  /** 公文主旨 */
  subject: string;
  /** 公文內容（可選） */
  content?: string;
  /** 發文機關（可選） */
  sender?: string;
  /** 是否顯示完整面板 */
  showCard?: boolean;
  /** 選擇分類後的回調 */
  onSelect?: (docType: string, category: '收文' | '發文') => void;
  /** 自訂樣式 */
  style?: React.CSSProperties;
}

/**
 * AI 分類建議面板
 *
 * 提供公文分類建議功能的 UI 元件
 */
export const AIClassifyPanel: React.FC<AIClassifyPanelProps> = ({
  subject,
  content,
  sender,
  showCard = true,
  onSelect,
  style,
}) => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ClassifyResponse | null>(null);

  // 取得分類建議
  const handleSuggest = useCallback(async () => {
    if (!subject) {
      message.warning('請先輸入公文主旨');
      return;
    }

    setLoading(true);
    try {
      const response = await aiApi.suggestClassification({
        subject,
        content,
        sender,
      });
      setResult(response);

      if (response.source === 'fallback') {
        message.warning('AI 服務暫時不可用，使用預設分類');
      } else if (response.source === 'disabled') {
        message.info('AI 服務未啟用');
      }
    } catch {
      message.error('取得分類建議失敗');
    } finally {
      setLoading(false);
    }
  }, [subject, content, sender, message]);

  // 套用建議
  const handleApply = useCallback(() => {
    if (result) {
      onSelect?.(result.doc_type, result.category);
      message.success('已套用 AI 建議的分類');
    }
  }, [result, onSelect, message]);

  // 渲染信心度指示器 (使用集中配置閾值)
  const renderConfidence = (confidence: number, label: string) => {
    const threshold = AI_CONFIG.classify.confidenceThreshold;
    let color = 'default';
    let icon = <InfoCircleOutlined />;

    if (confidence >= threshold + 0.1) {  // 高信心度: 閾值 + 10%
      color = 'success';
      icon = <CheckCircleOutlined />;
    } else if (confidence >= threshold) {  // 中信心度: 達到閾值
      color = 'warning';
      icon = <ExclamationCircleOutlined />;
    } else if (confidence > 0) {  // 低信心度: 低於閾值
      color = 'error';
      icon = <ExclamationCircleOutlined />;
    }

    return (
      <Tag icon={icon} color={color}>
        {label}: {Math.round(confidence * 100)}%
      </Tag>
    );
  };

  // 面板內容
  const panelContent = (
    <Space direction="vertical" style={{ width: '100%' }}>
      {/* 操作按鈕 */}
      <Space>
        <Button
          type="primary"
          icon={<TagsOutlined />}
          onClick={handleSuggest}
          loading={loading}
          disabled={!subject}
        >
          {result ? '重新分析' : '取得建議'}
        </Button>

        {result && onSelect && (
          <Button type="default" onClick={handleApply}>
            套用建議
          </Button>
        )}
      </Space>

      {/* 載入中 */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <Spin tip="AI 正在分析公文...">
            <div style={{ padding: '30px 50px' }} />
          </Spin>
        </div>
      )}

      {/* 分類結果 */}
      {result && !loading && (
        <div>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="公文類型">
              <Space>
                <Tag color="blue">{result.doc_type}</Tag>
                {renderConfidence(result.doc_type_confidence, '信心度')}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="收發類別">
              <Space>
                <Tag color={result.category === '收文' ? 'green' : 'orange'}>
                  {result.category}
                </Tag>
                {renderConfidence(result.category_confidence, '信心度')}
              </Space>
            </Descriptions.Item>
            {result.reasoning && (
              <Descriptions.Item label="判斷理由">
                <Text type="secondary">{result.reasoning}</Text>
              </Descriptions.Item>
            )}
          </Descriptions>

          {/* 來源標籤 (使用集中配置) */}
          <div style={{ marginTop: 8 }}>
            <Tag color={getAISourceColor(result.source as AISource)}>
              {getAISourceLabel(result.source as AISource)}
            </Tag>
          </div>

          {result.error && (
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 8 }}>
              備註：{result.error}
            </Text>
          )}
        </div>
      )}

      {/* 提示 */}
      {!result && !loading && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          點擊「取得建議」按鈕，AI 將根據公文主旨分析適合的分類
        </Text>
      )}
    </Space>
  );

  if (!showCard) {
    return <div style={style}>{panelContent}</div>;
  }

  return (
    <Card
      title={
        <Space>
          <RobotOutlined />
          <span>AI 分類建議</span>
        </Space>
      }
      size="small"
      style={style}
    >
      {panelContent}
    </Card>
  );
};

export default AIClassifyPanel;

/**
 * AI 摘要面板元件
 *
 * 顯示 AI 生成的公文摘要
 *
 * @version 1.0.0
 * @created 2026-02-04
 */

import React, { useState, useCallback } from 'react';
import { Card, Button, Typography, Space, Spin, Tag, Tooltip, App } from 'antd';
import {
  RobotOutlined,
  CopyOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { aiApi, SummaryResponse } from '../../api/aiApi';
import { AI_CONFIG, getAISourceColor, getAISourceLabel } from '../../config/aiConfig';

const { Paragraph, Text } = Typography;

interface AISummaryPanelProps {
  /** 公文主旨 */
  subject: string;
  /** 公文內容（可選） */
  content?: string;
  /** 發文機關（可選） */
  sender?: string;
  /** 摘要最大長度 */
  maxLength?: number;
  /** 是否顯示完整面板 */
  showCard?: boolean;
  /** 自訂樣式 */
  style?: React.CSSProperties;
}

/**
 * AI 摘要面板
 *
 * 提供公文摘要生成功能的 UI 元件
 */
export const AISummaryPanel: React.FC<AISummaryPanelProps> = ({
  subject,
  content,
  sender,
  maxLength = AI_CONFIG.summary.defaultMaxLength,
  showCard = true,
  style,
}) => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SummaryResponse | null>(null);

  // 生成摘要
  const handleGenerate = useCallback(async () => {
    if (!subject) {
      message.warning('請先輸入公文主旨');
      return;
    }

    setLoading(true);
    try {
      const response = await aiApi.generateSummary({
        subject,
        content,
        sender,
        max_length: maxLength,
      });
      setResult(response);

      if (response.source === 'fallback') {
        message.warning('AI 服務暫時不可用，使用預設摘要');
      } else if (response.source === 'disabled') {
        message.info('AI 服務未啟用');
      }
    } catch {
      message.error('生成摘要失敗');
    } finally {
      setLoading(false);
    }
  }, [subject, content, sender, maxLength]);

  // 複製摘要
  const handleCopy = useCallback(() => {
    if (result?.summary) {
      navigator.clipboard.writeText(result.summary);
      message.success('摘要已複製');
    }
  }, [result]);

  // 渲染信心度標籤
  const renderConfidenceTag = (confidence: number) => {
    if (confidence >= 0.8) {
      return (
        <Tag icon={<CheckCircleOutlined />} color="success">
          高信心度 ({Math.round(confidence * 100)}%)
        </Tag>
      );
    } else if (confidence >= 0.5) {
      return (
        <Tag icon={<ExclamationCircleOutlined />} color="warning">
          中信心度 ({Math.round(confidence * 100)}%)
        </Tag>
      );
    } else if (confidence > 0) {
      return (
        <Tag icon={<ExclamationCircleOutlined />} color="error">
          低信心度 ({Math.round(confidence * 100)}%)
        </Tag>
      );
    }
    return null;
  };

  // 渲染來源標籤 (使用集中配置)
  const renderSourceTag = (source: string) => {
    const label = getAISourceLabel(source as 'ai' | 'fallback' | 'disabled' | 'rate_limited');
    const color = getAISourceColor(source as 'ai' | 'fallback' | 'disabled' | 'rate_limited');
    return <Tag color={color}>{label}</Tag>;
  };

  // 面板內容
  const panelContent = (
    <Space direction="vertical" style={{ width: '100%' }}>
      {/* 操作按鈕 */}
      <Space>
        <Button
          type="primary"
          icon={<RobotOutlined />}
          onClick={handleGenerate}
          loading={loading}
          disabled={!subject}
        >
          {result ? '重新生成' : '生成摘要'}
        </Button>

        {result && (
          <>
            <Tooltip title="複製摘要">
              <Button icon={<CopyOutlined />} onClick={handleCopy} />
            </Tooltip>
            <Tooltip title="重新生成">
              <Button icon={<ReloadOutlined />} onClick={handleGenerate} />
            </Tooltip>
          </>
        )}
      </Space>

      {/* 載入中 */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <Spin tip="AI 正在生成摘要...">
            <div style={{ padding: '30px 50px' }} />
          </Spin>
        </div>
      )}

      {/* 摘要結果 */}
      {result && !loading && (
        <div>
          <Space style={{ marginBottom: 8 }}>
            {renderSourceTag(result.source)}
            {renderConfidenceTag(result.confidence)}
          </Space>

          <Paragraph
            style={{
              background: '#f5f5f5',
              padding: '12px',
              borderRadius: '4px',
              marginBottom: 0,
            }}
          >
            {result.summary}
          </Paragraph>

          {result.error && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              備註：{result.error}
            </Text>
          )}
        </div>
      )}

      {/* 提示 */}
      {!result && !loading && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          點擊「生成摘要」按鈕，AI 將根據公文主旨和內容生成簡潔的摘要
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
          <span>AI 摘要</span>
        </Space>
      }
      size="small"
      style={style}
    >
      {panelContent}
    </Card>
  );
};

export default AISummaryPanel;

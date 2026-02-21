/**
 * AI 摘要面板元件
 *
 * 顯示 AI 生成的公文摘要，支援串流模式 (SSE) 逐字顯示
 *
 * @version 2.0.0
 * @created 2026-02-04
 * @updated 2026-02-08 - 新增串流模式 SSE 支援
 */

import React, { useState, useCallback, useRef } from 'react';
import { Card, Button, Typography, Space, Spin, Tag, Tooltip, Switch, App } from 'antd';
import {
  RobotOutlined,
  CopyOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { aiApi, SummaryResponse } from '../../api/aiApi';
import { AI_CONFIG, getAISourceColor, getAISourceLabel } from '../../config/aiConfig';
import { StreamingText } from './StreamingText';

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
 * 提供公文摘要生成功能的 UI 元件，支援串流模式逐字顯示
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
  const [streamingEnabled, setStreamingEnabled] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedText, setStreamedText] = useState('');
  const abortControllerRef = useRef<AbortController | null>(null);

  // 串流生成摘要
  const handleStreamGenerate = useCallback(() => {
    if (!subject) {
      message.warning('請先輸入公文主旨');
      return;
    }

    // 取消上一次串流
    abortControllerRef.current?.abort();

    setLoading(true);
    setIsStreaming(true);
    setStreamedText('');
    setResult(null);

    const controller = aiApi.streamSummary(
      {
        subject,
        content,
        sender,
        max_length: maxLength,
      },
      // onToken
      (token: string) => {
        setStreamedText((prev) => prev + token);
      },
      // onDone
      () => {
        setIsStreaming(false);
        setLoading(false);
        // 設定最終結果
        setStreamedText((prev) => {
          setResult({
            summary: prev,
            confidence: 0.85,
            source: 'ai',
          });
          return prev;
        });
      },
      // onError
      (error: string) => {
        setIsStreaming(false);
        setLoading(false);
        message.error(`串流摘要失敗: ${error}`);
        // 發生錯誤時回退到一般模式
        handleNonStreamGenerate();
      },
    );

    abortControllerRef.current = controller;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- handleNonStreamGenerate is stable, adding it would cause unnecessary re-creation
  }, [subject, content, sender, maxLength, message]);

  // 一般模式生成摘要（非串流）
  const handleNonStreamGenerate = useCallback(async () => {
    if (!subject) {
      message.warning('請先輸入公文主旨');
      return;
    }

    setLoading(true);
    setStreamedText('');
    setIsStreaming(false);
    try {
      const response = await aiApi.generateSummary({
        subject,
        content,
        sender,
        max_length: maxLength,
      });
      setResult(response);
      setStreamedText(response.summary);

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
  }, [subject, content, sender, maxLength, message]);

  // 統一入口
  const handleGenerate = useCallback(() => {
    if (streamingEnabled) {
      handleStreamGenerate();
    } else {
      handleNonStreamGenerate();
    }
  }, [streamingEnabled, handleStreamGenerate, handleNonStreamGenerate]);

  // 複製摘要
  const handleCopy = useCallback(() => {
    const textToCopy = result?.summary || streamedText;
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
      message.success('摘要已複製');
    }
  }, [result, streamedText, message]);

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

  // 是否有顯示內容（串流中或已完成）
  const hasContent = isStreaming || result || streamedText;

  // 面板內容
  const panelContent = (
    <Space direction="vertical" style={{ width: '100%' }}>
      {/* 操作按鈕列 */}
      <Space wrap>
        <Button
          type="primary"
          icon={streamingEnabled ? <ThunderboltOutlined /> : <RobotOutlined />}
          onClick={handleGenerate}
          loading={loading && !isStreaming}
          disabled={!subject || isStreaming}
        >
          {result ? '重新生成' : '生成摘要'}
        </Button>

        {hasContent && !isStreaming && (
          <>
            <Tooltip title="複製摘要">
              <Button icon={<CopyOutlined />} onClick={handleCopy} aria-label="複製摘要" />
            </Tooltip>
            <Tooltip title="重新生成">
              <Button icon={<ReloadOutlined />} onClick={handleGenerate} aria-label="重新生成" />
            </Tooltip>
          </>
        )}

        <Tooltip title="串流模式逐字顯示，降低等待感">
          <Switch
            checkedChildren="串流"
            unCheckedChildren="一般"
            checked={streamingEnabled}
            onChange={setStreamingEnabled}
            disabled={isStreaming}
            size="small"
          />
        </Tooltip>
      </Space>

      {/* 載入中（非串流模式） */}
      {loading && !isStreaming && (
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <Spin tip="AI 正在生成摘要...">
            <div style={{ padding: '30px 50px' }} />
          </Spin>
        </div>
      )}

      {/* 串流中或已完成的摘要結果 */}
      {(isStreaming || (result && !loading)) && (
        <div>
          {/* 標籤列（僅在完成後顯示） */}
          {result && !isStreaming && (
            <Space style={{ marginBottom: 8 }}>
              {renderSourceTag(result.source)}
              {renderConfidenceTag(result.confidence)}
            </Space>
          )}

          {/* 串流中的標籤 */}
          {isStreaming && (
            <Space style={{ marginBottom: 8 }}>
              <Tag icon={<ThunderboltOutlined />} color="processing">
                串流生成中...
              </Tag>
            </Space>
          )}

          <Paragraph
            style={{
              background: '#f5f5f5',
              padding: '12px',
              borderRadius: '4px',
              marginBottom: 0,
              minHeight: '40px',
            }}
          >
            <StreamingText
              text={streamedText}
              isStreaming={isStreaming}
            />
          </Paragraph>

          {result?.error && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              備註：{result.error}
            </Text>
          )}
        </div>
      )}

      {/* 提示 */}
      {!hasContent && !loading && (
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

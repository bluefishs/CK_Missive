/**
 * AI 助手按鈕元件
 *
 * 提供快速存取 AI 功能的浮動按鈕
 *
 * @version 1.0.0
 * @created 2026-02-04
 */

import React, { useState } from 'react';
import { FloatButton, Tooltip, Popover, Space, Button, Spin, Tag, message } from 'antd';
import {
  RobotOutlined,
  FileTextOutlined,
  TagsOutlined,
  BulbOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { aiApi, AIHealthStatus } from '../../api/aiApi';

interface AIAssistantButtonProps {
  /** 是否顯示 */
  visible?: boolean;
  /** 點擊摘要功能 */
  onSummaryClick?: () => void;
  /** 點擊分類功能 */
  onClassifyClick?: () => void;
  /** 點擊關鍵字功能 */
  onKeywordsClick?: () => void;
}

/**
 * AI 助手浮動按鈕
 *
 * 提供快速存取 AI 功能的入口
 */
export const AIAssistantButton: React.FC<AIAssistantButtonProps> = ({
  visible = true,
  onSummaryClick,
  onClassifyClick,
  onKeywordsClick,
}) => {
  const [open, setOpen] = useState(false);
  const [healthStatus, setHealthStatus] = useState<AIHealthStatus | null>(null);
  const [loading, setLoading] = useState(false);

  // 檢查 AI 服務健康狀態
  const checkHealth = async () => {
    setLoading(true);
    try {
      const status = await aiApi.checkHealth();
      setHealthStatus(status);
    } catch {
      message.error('無法檢查 AI 服務狀態');
    } finally {
      setLoading(false);
    }
  };

  // 開啟選單時檢查健康狀態
  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
    if (newOpen && !healthStatus) {
      checkHealth();
    }
  };

  // 渲染服務狀態標籤
  const renderStatusTag = (available: boolean, name: string) => (
    <Tag
      icon={available ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
      color={available ? 'success' : 'error'}
    >
      {name}
    </Tag>
  );

  // 功能選單內容
  const menuContent = (
    <Space direction="vertical" style={{ width: 200 }}>
      {/* 服務狀態 */}
      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
          AI 服務狀態
        </div>
        {loading ? (
          <Spin indicator={<LoadingOutlined spin />} size="small" />
        ) : healthStatus ? (
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Space wrap>
              {renderStatusTag(healthStatus.groq.available, 'Groq')}
              {renderStatusTag(healthStatus.ollama.available, 'Ollama')}
            </Space>
            {healthStatus.rate_limit && (
              <div style={{ fontSize: 11, color: '#888' }}>
                請求: {healthStatus.rate_limit.current_requests}/{healthStatus.rate_limit.max_requests}
                ({healthStatus.rate_limit.window_seconds}秒)
              </div>
            )}
          </Space>
        ) : (
          <Tag>未檢查</Tag>
        )}
      </div>

      {/* 功能按鈕 */}
      <Button
        type="text"
        icon={<FileTextOutlined />}
        onClick={() => {
          setOpen(false);
          onSummaryClick?.();
        }}
        style={{ width: '100%', textAlign: 'left' }}
        disabled={!healthStatus?.groq.available && !healthStatus?.ollama.available}
      >
        生成摘要
      </Button>

      <Button
        type="text"
        icon={<TagsOutlined />}
        onClick={() => {
          setOpen(false);
          onClassifyClick?.();
        }}
        style={{ width: '100%', textAlign: 'left' }}
        disabled={!healthStatus?.groq.available && !healthStatus?.ollama.available}
      >
        分類建議
      </Button>

      <Button
        type="text"
        icon={<BulbOutlined />}
        onClick={() => {
          setOpen(false);
          onKeywordsClick?.();
        }}
        style={{ width: '100%', textAlign: 'left' }}
        disabled={!healthStatus?.groq.available && !healthStatus?.ollama.available}
      >
        提取關鍵字
      </Button>

      {/* 重新檢查按鈕 */}
      <Button
        type="link"
        size="small"
        onClick={checkHealth}
        loading={loading}
        style={{ marginTop: 8 }}
      >
        重新檢查服務狀態
      </Button>
    </Space>
  );

  if (!visible) return null;

  return (
    <Popover
      content={menuContent}
      title="AI 助手"
      trigger="click"
      open={open}
      onOpenChange={handleOpenChange}
      placement="topRight"
    >
      <Tooltip title="AI 助手" placement="left">
        <FloatButton
          icon={<RobotOutlined />}
          type="primary"
          style={{
            right: 24,
            bottom: 24,
          }}
        />
      </Tooltip>
    </Popover>
  );
};

export default AIAssistantButton;

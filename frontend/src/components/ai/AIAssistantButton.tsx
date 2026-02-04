/**
 * AI 助手按鈕元件
 *
 * 提供快速存取 AI 功能的浮動按鈕
 *
 * @version 1.1.0
 * @created 2026-02-04
 * @updated 2026-02-05 - 修復 FloatButton 顯示問題
 */

import React, { useState, useEffect } from 'react';
import { FloatButton, Space, Button, Spin, Tag, message, Drawer } from 'antd';
import {
  RobotOutlined,
  FileTextOutlined,
  TagsOutlined,
  BulbOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  CloseOutlined,
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
  const [drawerOpen, setDrawerOpen] = useState(false);
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

  // 開啟抽屜時檢查健康狀態
  useEffect(() => {
    if (drawerOpen && !healthStatus) {
      checkHealth();
    }
  }, [drawerOpen]);

  // 渲染服務狀態標籤
  const renderStatusTag = (available: boolean, name: string) => (
    <Tag
      icon={available ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
      color={available ? 'success' : 'error'}
    >
      {name}
    </Tag>
  );

  // 檢查是否有可用的 AI 服務
  const isAIAvailable = healthStatus?.groq.available || healthStatus?.ollama.available;

  if (!visible) return null;

  return (
    <>
      {/* 浮動按鈕 */}
      <FloatButton
        icon={<RobotOutlined />}
        type="primary"
        tooltip="AI 助手"
        onClick={() => setDrawerOpen(true)}
        style={{
          right: 24,
          bottom: 24,
        }}
      />

      {/* AI 功能抽屜 */}
      <Drawer
        title={
          <Space>
            <RobotOutlined />
            AI 助手
          </Space>
        }
        placement="right"
        width={320}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        closeIcon={<CloseOutlined />}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* 服務狀態 */}
          <div>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
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
          <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16 }}>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
              AI 功能
            </div>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button
                block
                icon={<FileTextOutlined />}
                onClick={() => {
                  setDrawerOpen(false);
                  onSummaryClick?.();
                }}
                disabled={!isAIAvailable}
              >
                生成摘要
              </Button>

              <Button
                block
                icon={<TagsOutlined />}
                onClick={() => {
                  setDrawerOpen(false);
                  onClassifyClick?.();
                }}
                disabled={!isAIAvailable}
              >
                分類建議
              </Button>

              <Button
                block
                icon={<BulbOutlined />}
                onClick={() => {
                  setDrawerOpen(false);
                  onKeywordsClick?.();
                }}
                disabled={!isAIAvailable}
              >
                提取關鍵字
              </Button>
            </Space>
          </div>

          {/* 重新檢查按鈕 */}
          <Button
            type="link"
            size="small"
            onClick={checkHealth}
            loading={loading}
            style={{ padding: 0 }}
          >
            重新檢查服務狀態
          </Button>

          {/* 提示訊息 */}
          {!isAIAvailable && healthStatus && (
            <div style={{
              fontSize: 12,
              color: '#ff4d4f',
              background: '#fff2f0',
              padding: 8,
              borderRadius: 4,
            }}>
              AI 服務目前不可用，請稍後再試
            </div>
          )}
        </Space>
      </Drawer>
    </>
  );
};

export default AIAssistantButton;

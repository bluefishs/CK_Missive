/**
 * KGAdminPanel - 知識圖譜管理動作面板（公文圖譜專用）
 *
 * 只包含公文知識圖譜的管理操作：
 * - 批次提取實體 / 批次入圖
 * - 合併實體
 *
 * 代碼圖譜管理已獨立至 CodeGraphManagementPage (/admin/code-graph)
 *
 * @version 2.0.0
 * @created 2026-03-10
 */

import React, { useState, useCallback } from 'react';
import {
  Card,
  Space,
  Button,
  Popconfirm,
  Typography,
  App,
} from 'antd';
import {
  RocketOutlined,
  ExperimentOutlined,
  ApartmentOutlined,
  CodeOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import { aiApi } from '../../api/aiApi';
import type { EntityBatchResponse, KGIngestResponse } from '../../types/ai';
import { ROUTES } from '../../router/types';

const { Text } = Typography;

interface KGAdminPanelProps {
  /** 實體未提取數（用於停用按鈕） */
  withoutExtraction: number;
  /** 重新載入統計 */
  onReloadStats: () => void;
  /** 開啟合併實體 Modal */
  onOpenMergeModal: () => void;
}

export const KGAdminPanel: React.FC<KGAdminPanelProps> = ({
  withoutExtraction,
  onReloadStats,
  onOpenMergeModal,
}) => {
  const { message } = App.useApp();
  const navigate = useNavigate();

  const [entityBatchLoading, setEntityBatchLoading] = useState(false);
  const [graphIngestLoading, setGraphIngestLoading] = useState(false);

  const handleEntityBatch = useCallback(async () => {
    setEntityBatchLoading(true);
    try {
      const result: EntityBatchResponse | null = await aiApi.runEntityBatch({ limit: 200 });
      if (result?.success) {
        message.success(result.message);
        onReloadStats();
      } else {
        message.error(result?.message || '批次提取失敗');
      }
    } catch {
      message.error('批次提取請求失敗');
    } finally {
      setEntityBatchLoading(false);
    }
  }, [message, onReloadStats]);

  const handleGraphIngest = useCallback(async () => {
    setGraphIngestLoading(true);
    try {
      const result: KGIngestResponse | null = await aiApi.triggerGraphIngest({ limit: 200 });
      if (result?.success) {
        message.success(result.message || `入圖完成：處理 ${result.total_processed ?? 0} 筆`);
        onReloadStats();
      } else {
        message.error(result?.message || '批次入圖失敗');
      }
    } catch {
      message.error('批次入圖請求失敗');
    } finally {
      setGraphIngestLoading(false);
    }
  }, [message, onReloadStats]);

  return (
    <Card
      size="small"
      title={
        <span style={{ fontSize: 13 }}>
          <RocketOutlined /> 管理動作
        </span>
      }
      styles={{ body: { padding: '8px 12px' } }}
    >
      <Space vertical style={{ width: '100%' }} size={8}>
        <Popconfirm
          title="確定要批次提取實體？將處理最多 200 筆公文。"
          onConfirm={handleEntityBatch}
        >
          <Button
            block
            size="small"
            icon={<ExperimentOutlined />}
            loading={entityBatchLoading}
            disabled={withoutExtraction === 0}
          >
            批次提取實體
          </Button>
        </Popconfirm>
        <Popconfirm
          title="確定要批次入圖？將處理最多 200 筆已提取公文。"
          onConfirm={handleGraphIngest}
        >
          <Button
            block
            size="small"
            icon={<ApartmentOutlined />}
            loading={graphIngestLoading}
          >
            批次入圖
          </Button>
        </Popconfirm>
        <Button
          block
          size="small"
          icon={<SwapOutlined />}
          onClick={onOpenMergeModal}
        >
          合併實體
        </Button>

        {/* Link to Code Graph Management */}
        <Button
          block
          size="small"
          type="dashed"
          icon={<CodeOutlined />}
          onClick={() => navigate(ROUTES.CODE_GRAPH)}
        >
          <Text style={{ fontSize: 12 }}>代碼圖譜管理</Text>
        </Button>
      </Space>
    </Card>
  );
};

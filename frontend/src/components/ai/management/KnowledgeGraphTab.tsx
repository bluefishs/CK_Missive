/**
 * KnowledgeGraphTab - Knowledge graph with entity extraction
 *
 * Extracted from AIAssistantManagementPage.tsx
 */
import React, { useCallback, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Input,
  InputNumber,
  message,
  Row,
  Space,
  Statistic,
  Tag,
  Typography,
} from 'antd';
import {
  ApartmentOutlined,
  ClockCircleOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';

import { aiApi } from '../../../api/aiApi';
import { KnowledgeGraph } from '../KnowledgeGraph';

export const KnowledgeGraphTab: React.FC = () => {
  const [inputIds, setInputIds] = useState<string>('');
  const [documentIds, setDocumentIds] = useState<number[]>([]);
  const [autoMode, setAutoMode] = useState(true);
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchLimit, setBatchLimit] = useState(200);

  // 實體提取覆蓋統計
  const {
    data: entityStats = null,
    refetch: refetchEntityStats,
  } = useQuery({
    queryKey: ['ai-management', 'entity-stats'],
    queryFn: () => aiApi.getEntityStats(),
    staleTime: 60 * 1000,
  });

  const handleLoadGraph = useCallback(() => {
    const ids = inputIds
      .split(/[,，\s]+/)
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => !isNaN(n) && n > 0);

    if (ids.length === 0) {
      message.warning('請輸入至少一個有效的公文 ID');
      return;
    }
    setDocumentIds(ids);
    setAutoMode(false);
  }, [inputIds]);

  const handleLoadRecent = useCallback(() => {
    setDocumentIds([]);
    setInputIds('');
    setAutoMode(true);
  }, []);

  const handleEntityBatch = useCallback(async () => {
    setBatchLoading(true);
    try {
      const result = await aiApi.runEntityBatch({ limit: batchLimit });
      if (result?.success) {
        message.success(result.message);
      } else {
        message.error(result?.message || '批次提取失敗');
      }
    } catch {
      message.error('批次提取請求失敗');
    } finally {
      setBatchLoading(false);
      refetchEntityStats();
    }
  }, [refetchEntityStats, batchLimit]);

  return (
    <div>
      {/* 實體提取統計 */}
      {entityStats && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={4}>
              <Statistic
                title="實體覆蓋率"
                value={entityStats.coverage_percent}
                suffix="%"
                valueStyle={{ color: entityStats.coverage_percent > 50 ? '#52c41a' : '#fa8c16' }}
              />
            </Col>
            <Col span={3}>
              <Statistic title="已提取公文" value={entityStats.extracted_documents} suffix={`/ ${entityStats.total_documents}`} />
            </Col>
            <Col span={3}>
              <Statistic title="提取實體" value={entityStats.total_entities} />
            </Col>
            <Col span={3}>
              <Statistic title="提取關係" value={entityStats.total_relations} />
            </Col>
            <Col span={7}>
              <div style={{ fontSize: 12, color: '#666' }}>
                <div style={{ marginBottom: 4, fontWeight: 500 }}>實體類型分佈</div>
                {Object.entries(entityStats.entity_type_stats || {}).map(([type, count]) => (
                  <Tag key={type} style={{ marginBottom: 2 }}>
                    {type}: {count}
                  </Tag>
                ))}
                {Object.keys(entityStats.entity_type_stats || {}).length === 0 && (
                  <Typography.Text type="secondary">尚無提取資料</Typography.Text>
                )}
              </div>
            </Col>
            <Col span={4} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <InputNumber
                size="small"
                min={10}
                max={500}
                value={batchLimit}
                onChange={(v) => setBatchLimit(v ?? 200)}
                style={{ width: 70 }}
                addonAfter="筆"
              />
              <Button
                type="primary"
                size="small"
                loading={batchLoading}
                onClick={handleEntityBatch}
                disabled={entityStats.without_extraction === 0}
              >
                批次提取
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {/* 查詢工具列 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap style={{ marginBottom: autoMode ? 0 : 8 }}>
          <Button
            type={autoMode ? 'primary' : 'default'}
            icon={<ClockCircleOutlined />}
            onClick={handleLoadRecent}
          >
            最近公文
          </Button>
          <Typography.Text type="secondary">|</Typography.Text>
          <Input
            placeholder="輸入公文 ID（多筆以逗號分隔）"
            value={inputIds}
            onChange={(e) => setInputIds(e.target.value)}
            onPressEnter={handleLoadGraph}
            style={{ width: 280 }}
          />
          <Button
            type={!autoMode ? 'primary' : 'default'}
            icon={<SearchOutlined />}
            onClick={handleLoadGraph}
            disabled={!inputIds.trim()}
          >
            指定查詢
          </Button>
        </Space>
        {!autoMode && documentIds.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              查詢：{documentIds.map((id) => (
                <Tag key={id} color="blue" style={{ marginRight: 4 }}>ID {id}</Tag>
              ))}
            </Typography.Text>
          </div>
        )}
        {autoMode && (
          <div style={{ marginTop: 8 }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              <ApartmentOutlined /> 自動顯示最近 10 筆公文的關聯圖譜（含 NER 提取實體）
            </Typography.Text>
          </div>
        )}
      </Card>

      {/* 圖譜區域 */}
      <Card size="small" styles={{ body: { padding: 12 } }}>
        <KnowledgeGraph
          documentIds={documentIds}
          height={700}
        />
      </Card>
    </div>
  );
};

/**
 * QaImpactCard — Diff-aware QA 影響分析卡片 (V-3.3)
 *
 * 顯示 git diff 影響分析結果：受影響模組、風險等級、建議測試模式。
 *
 * @version 1.0.0
 * @created 2026-03-23
 */

import React, { useCallback, useEffect, useState } from 'react';
import {
  Badge,
  Card,
  Empty,
  Flex,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import {
  BugOutlined,
  CheckCircleOutlined,
  ExperimentOutlined,
  ReloadOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import type { QaAffectedModule, QaImpactResponse } from '../../../api/digitalTwin';
import { getQaImpact } from '../../../api/digitalTwin';

const { Text } = Typography;

const RISK_TAG: Record<string, { color: string; label: string }> = {
  high: { color: 'red', label: '高' },
  medium: { color: 'orange', label: '中' },
  low: { color: 'green', label: '低' },
};

const REC_CONFIG: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  full_qa: { color: 'red', icon: <BugOutlined />, label: '完整 QA' },
  diff_aware_qa: { color: 'orange', icon: <ExperimentOutlined />, label: 'Diff-aware QA' },
  quick_qa: { color: 'green', icon: <CheckCircleOutlined />, label: '快速 QA' },
  no_changes: { color: 'default', icon: <CheckCircleOutlined />, label: '無需 QA' },
};

const columns = [
  {
    title: '層級',
    dataIndex: 'layer',
    key: 'layer',
    width: 80,
    render: (v: string) => (
      <Tag color={v === 'backend' ? 'blue' : 'cyan'}>{v}</Tag>
    ),
  },
  {
    title: '類別',
    dataIndex: 'category',
    key: 'category',
    width: 100,
  },
  {
    title: '檔案數',
    dataIndex: 'count',
    key: 'count',
    width: 70,
    sorter: (a: QaAffectedModule, b: QaAffectedModule) => b.count - a.count,
  },
  {
    title: '風險',
    dataIndex: 'risk',
    key: 'risk',
    width: 70,
    render: (v: string) => {
      const cfg = RISK_TAG[v] ?? RISK_TAG['low']!;
      return <Tag color={cfg.color}>{cfg.label}</Tag>;
    },
    sorter: (a: QaAffectedModule, b: QaAffectedModule) => {
      const order: Record<string, number> = { high: 3, medium: 2, low: 1 };
      return (order[b.risk] ?? 0) - (order[a.risk] ?? 0);
    },
  },
  {
    title: '代表檔案',
    dataIndex: 'files',
    key: 'files',
    ellipsis: true,
    render: (files: string[]) => (
      <Text type="secondary" style={{ fontSize: 11 }}>
        {files.slice(0, 2).map((f) => f.split('/').pop()).join(', ')}
        {files.length > 2 ? ` (+${files.length - 2})` : ''}
      </Text>
    ),
  },
];

export const QaImpactCard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<QaImpactResponse | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getQaImpact();
      setData(result);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const rec = data?.recommendation
    ? (REC_CONFIG[data.recommendation] ?? REC_CONFIG['no_changes']!)
    : null;

  return (
    <Card
      title={
        <Space>
          <ExperimentOutlined />
          <span>Diff-aware QA 影響分析</span>
          {rec && (
            <Tag color={rec.color} icon={rec.icon}>
              {rec.label}
            </Tag>
          )}
        </Space>
      }
      extra={
        <a onClick={load} style={{ fontSize: 12 }}>
          <ReloadOutlined /> 重新分析
        </a>
      }
      size="small"
    >
      <Spin spinning={loading}>
        {!data || !data.success ? (
          <Empty
            description={data?.error ?? '無法取得 QA 影響分析'}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : data.changed_files_count === 0 ? (
          <Empty
            description="沒有偵測到變更檔案"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <Flex vertical gap={12}>
            {/* 統計摘要 */}
            <Flex gap={24} wrap="wrap">
              <Statistic
                title="變更檔案"
                value={data.changed_files_count}
                styles={{ content: { fontSize: 20 } }}
              />
              {data.summary && (
                <>
                  <Statistic
                    title="後端"
                    value={data.summary.backend_changes}
                    styles={{ content: { fontSize: 20, color: '#1677ff' } }}
                  />
                  <Statistic
                    title="前端"
                    value={data.summary.frontend_changes}
                    styles={{ content: { fontSize: 20, color: '#13c2c2' } }}
                  />
                  <Statistic
                    title="高風險模組"
                    value={data.summary.high_risk_modules}
                    styles={{ content: {
                      fontSize: 20,
                      color: data.summary.high_risk_modules > 0 ? '#ff4d4f' : '#52c41a',
                    } }}
                    prefix={data.summary.high_risk_modules > 0 ? <WarningOutlined /> : undefined}
                  />
                </>
              )}
              {data.summary?.has_migrations && (
                <Badge status="error" text="含 DB 遷移" />
              )}
            </Flex>

            {/* 建議訊息 */}
            <Text type="secondary" style={{ fontSize: 12 }}>{data.message}</Text>

            {/* 受影響模組表格 */}
            {data.affected.length > 0 && (
              <Table
                dataSource={data.affected}
                columns={columns}
                rowKey={(r) => `${r.layer}-${r.category}`}
                size="small"
                pagination={false}
                scroll={{ x: 500 }}
              />
            )}

            {/* 建議命令 */}
            {data.suggested_commands && (
              <Flex gap={8} wrap="wrap">
                <Text type="secondary" style={{ fontSize: 11 }}>建議：</Text>
                {Object.entries(data.suggested_commands).map(([mode, cmd]) => (
                  <Tag key={mode} style={{ fontSize: 11 }}>
                    <code>{cmd}</code>
                  </Tag>
                ))}
              </Flex>
            )}
          </Flex>
        )}
      </Spin>
    </Card>
  );
};

export default QaImpactCard;

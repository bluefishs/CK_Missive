import React from 'react';
import { Divider, Progress, Spin, Tooltip, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { getFederationHealth } from '../../api/ai/knowledgeGraph';
import { SOURCE_PROJECT_COLORS, SOURCE_PROJECT_LABELS } from '../../config/graphNodeConfig';

const { Text } = Typography;

const FederationHealthMini: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['kg-federation-health'],
    queryFn: () => getFederationHealth(),
    staleTime: 120_000,
  });

  if (isLoading) return <Spin size="small" />;

  const projects = data?.projects ?? [];
  if (projects.length === 0) {
    return <Text type="secondary" style={{ fontSize: 11 }}>尚無跨專案資料</Text>;
  }

  const embCoverage = data?.embedding_coverage ?? {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {projects.map((p) => {
        const color = SOURCE_PROJECT_COLORS[p.source_project] ?? '#999';
        const label = SOURCE_PROJECT_LABELS[p.source_project] ?? p.source_project;
        const cov = embCoverage[p.source_project];
        const lastUpdated = p.last_updated
          ? new Date(p.last_updated).toLocaleDateString('zh-TW', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
          : null;
        return (
          <div key={p.source_project} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{
                display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                background: color, flexShrink: 0,
              }} />
              <Text style={{ fontSize: 12, flex: 1 }}>{label}</Text>
              <Text strong style={{ fontSize: 12 }}>{p.entity_count}</Text>
            </div>
            {cov && (
              <Tooltip title={`Embedding: ${cov.with_embedding}/${cov.total}`}>
                <Progress
                  percent={cov.coverage_pct}
                  size="small"
                  strokeColor={color}
                  format={(pct) => `${pct}%`}
                  style={{ marginLeft: 16, marginRight: 0 }}
                />
              </Tooltip>
            )}
            {lastUpdated && (
              <Text type="secondary" style={{ fontSize: 10, marginLeft: 16 }}>
                更新: {lastUpdated}
              </Text>
            )}
          </div>
        );
      })}
      <Divider style={{ margin: '4px 0' }} />
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Text type="secondary" style={{ fontSize: 11 }}>跨專案關係</Text>
        <Text strong style={{ fontSize: 12 }}>{data?.cross_project_relations ?? 0}</Text>
      </div>
    </div>
  );
};

export default FederationHealthMini;

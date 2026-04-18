/**
 * Wiki ↔ KG 比對 Tab — 從 WikiPage.tsx 拆分（v1.0 2026-04-18）
 */
import React from 'react';
import { Card, Spin, Tag, Row, Col, Statistic, Empty } from 'antd';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import type { CoverageData } from './wikiTypes';

const WikiCoverageTab: React.FC = () => {
  const { data, isLoading } = useQuery<CoverageData>({
    queryKey: ['wiki-coverage'],
    queryFn: async () => {
      const resp = await apiClient.post<{ success: boolean; data: CoverageData }>(
        API_ENDPOINTS.WIKI.COVERAGE, {},
      );
      return resp.data;
    },
    staleTime: 5 * 60_000,
  });

  if (isLoading) return <Spin style={{ display: 'block', margin: '40px auto' }} />;
  if (!data) return <Empty description="無比對資料" />;

  const s = data.summary;

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}><Card size="small"><Statistic title="Wiki 頁面" value={s.wiki_total} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="KG 實體" value={s.kg_total} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="完全匹配" value={s.exact_match} valueStyle={{ color: '#52c41a' }} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="Wiki 獨有" value={s.wiki_only} valueStyle={{ color: '#1890ff' }} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="KG 獨有" value={s.kg_only} valueStyle={{ color: '#faad14' }} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="覆蓋率" value={s.coverage_pct} suffix="%" /></Card></Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Card title={`KG 獨有 (Top 30) — Wiki 缺少`} size="small" style={{ marginBottom: 16 }}>
            <div style={{ maxHeight: 400, overflow: 'auto' }}>
              {data.kg_only_top.slice(0, 30).map((e) => (
                <div key={e.name} style={{ padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                  <Tag color={e.type === 'org' ? 'blue' : e.type === 'project' ? 'green' : 'default'}>{e.type}</Tag>
                  {e.name.slice(0, 35)} <Tag>{e.mentions} mentions</Tag>
                </div>
              ))}
            </div>
          </Card>
        </Col>
        <Col span={12}>
          <Card title={`完全匹配 (${s.exact_match} 筆)`} size="small" style={{ marginBottom: 16 }}>
            <div style={{ maxHeight: 400, overflow: 'auto' }}>
              {data.exact_matches.slice(0, 30).map((e) => (
                <div key={e.name} style={{ padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                  <Tag color="success">match</Tag>
                  {e.name.slice(0, 30)} <Tag>{e.kg_mentions}</Tag>
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default WikiCoverageTab;

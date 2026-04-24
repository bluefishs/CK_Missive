/**
 * 坤哥 — 技能星雲板塊
 *
 * 復用既有的 SkillNebulaTab（Memory Wiki Phase 5 Slice 4）— force-graph 2D 視覺化
 * pattern 節點，結晶過的 pattern 有金色外圈。
 *
 * 靈感：Muse（muse.cheyuwu.com）星雲設計。
 *
 * @version 1.0.0 — D5-B 填充
 */

import React, { lazy, Suspense } from 'react';
import { Card, Typography, Spin, Alert } from 'antd';
import { DeploymentUnitOutlined } from '@ant-design/icons';

const SkillNebulaTab = lazy(() => import('../memoryWiki/SkillNebulaTab'));

const { Title, Paragraph, Text } = Typography;

export const NebulaTab: React.FC = () => (
  <div>
    <Card bordered={false}>
      <Title level={3} style={{ marginTop: 0 }}>
        <DeploymentUnitOutlined /> 技能星雲
      </Title>
      <Paragraph type="secondary" style={{ fontSize: 15 }}>
        每顆節點是一種<Text strong>技能模式</Text>（tool_sequence 聚合後的 pattern），
        邊代表兩個 pattern 共用工具。結晶過的 pattern 有<Text strong style={{ color: '#faad14' }}>金色外圈</Text>
        — 代表已沉澱為永久能力。
      </Paragraph>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 8 }}
        message="星雲的密度會隨時間增加"
        description="每次成功 query 都會在 pattern 檔案中累積 hit_count；達 5 次且成功率 ≥ 95% 後自動升為結晶候選。"
      />
    </Card>

    <Card bordered={false} style={{ marginTop: 16 }}>
      <Suspense fallback={<Spin style={{ display: 'block', margin: '40px auto' }} />}>
        <SkillNebulaTab />
      </Suspense>
    </Card>
  </div>
);

export default NebulaTab;

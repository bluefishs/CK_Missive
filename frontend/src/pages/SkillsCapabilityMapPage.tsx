/**
 * Skills Capability Map Page
 *
 * Standalone page for visualizing skills/agents/tools/services/commands
 * as a force-directed graph.
 *
 * @version 1.0.0
 * @created 2026-03-19
 */

import React, { lazy, Suspense } from 'react';
import { Typography, Spin } from 'antd';
import { NodeIndexOutlined } from '@ant-design/icons';

const SkillsMapTab = lazy(() => import('./knowledgeGraph/SkillsMapTab'));

const { Title } = Typography;

const SkillsCapabilityMapPage: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', overflow: 'hidden' }}>
      <div style={{ padding: '12px 16px', background: '#fff', borderBottom: '1px solid #f0f0f0', flexShrink: 0 }}>
        <Title level={4} style={{ margin: 0 }}>
          <NodeIndexOutlined style={{ marginRight: 8 }} />
          Skills 能力圖譜
        </Title>
      </div>
      <Suspense fallback={<div style={{ display: 'flex', justifyContent: 'center', padding: 64 }}><Spin size="large" /></div>}>
        <SkillsMapTab />
      </Suspense>
    </div>
  );
};

export default SkillsCapabilityMapPage;

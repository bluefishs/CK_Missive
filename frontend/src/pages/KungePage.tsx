/**
 * 坤哥 — Missive 意識體存在論敘事頁
 *
 * 對應 Muse 七維深化計畫：
 *   - 我是誰（SOUL 三信念 + 反迴聲室 + 倫理紅線）
 *   - 記憶圖譜（Wiki force-graph + KG）
 *   - 進化史（Skill ledger + pattern 結晶）
 *   - 技能星雲（拓撲分佈）
 *   - 對話精選（深度對話集錦）
 *
 * @version 0.1.0 — D1 skeleton (placeholder tabs)
 * @date 2026-04-20
 */

import React from 'react';
import { Tabs, Typography, Space, Tag } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import {
  BulbOutlined,
  DatabaseOutlined,
  RiseOutlined,
  DeploymentUnitOutlined,
  MessageOutlined,
  CommentOutlined,
  ControlOutlined,
} from '@ant-design/icons';
import { IdentityTab, MemoryTab, EvolutionTab, NebulaTab, DialoguesTab, ChatTab, OpsTab } from './kunge';
import { useAuthGuard } from '../hooks/utility/useAuthGuard';

const { Title, Text } = Typography;

// 2026-06-02 kunge tab 整併聚焦服務鏈：7 tab → 5 核心主軸
// 對話 / 心智(我是誰+記憶+對話精選) / 進化 / 圖譜(技能星雲) / 運維
type KungeTabKey = 'chat' | 'mind' | 'evolution' | 'graph' | 'ops';

const TAB_TO_PATH: Record<KungeTabKey, string> = {
  chat: '/kunge/chat',
  mind: '/kunge/mind',
  evolution: '/kunge/evolution',
  graph: '/kunge/graph',
  ops: '/kunge/ops',
};

// 向後相容：舊 deep link path → 新合併 tab（書籤/外連不破）
const PATH_TO_TAB: Record<string, KungeTabKey> = {
  chat: 'chat',
  mind: 'mind',
  identity: 'mind',     // 舊 /kunge/identity → 心智
  memory: 'mind',       // 舊 /kunge/memory → 心智
  dialogues: 'mind',    // 舊 /kunge/dialogues → 心智
  evolution: 'evolution',
  graph: 'graph',
  nebula: 'graph',      // 舊 /kunge/nebula → 圖譜
  ops: 'ops',
};

// 2026-06-02 心智主軸：我是誰 + 記憶圖譜 + 對話精選 嵌套（內在心智統一，元件不重寫）
const MindTab: React.FC = () => (
  <Tabs
    defaultActiveKey="identity"
    items={[
      { key: 'identity', label: <span><BulbOutlined /> 我是誰</span>, children: <IdentityTab /> },
      { key: 'memory', label: <span><DatabaseOutlined /> 記憶圖譜</span>, children: <MemoryTab /> },
      { key: 'dialogues', label: <span><MessageOutlined /> 對話精選</span>, children: <DialoguesTab /> },
    ]}
  />
);

export const KungePage: React.FC = () => {
  const navigate = useNavigate();
  const { tab } = useParams<{ tab?: string }>();
  const { isAdmin } = useAuthGuard();
  // v5.8.1：預設 chat tab — 用戶來訪時可直接對話，不用先讀敘事
  const activeKey: KungeTabKey = PATH_TO_TAB[tab ?? ''] ?? 'chat';

  // 2026-06-02 聚焦服務鏈 5 主軸：對話 → 心智 → 進化 → 圖譜 → 運維
  const items = [
    { key: 'chat', label: <span><CommentOutlined /> 對話</span>, children: <ChatTab /> },
    { key: 'mind', label: <span><BulbOutlined /> 心智</span>, children: <MindTab /> },
    { key: 'evolution', label: <span><RiseOutlined /> 進化</span>, children: <EvolutionTab /> },
    { key: 'graph', label: <span><DeploymentUnitOutlined /> 圖譜</span>, children: <NebulaTab /> },
    // 運維儀表板（整合 admin/ai-assistant + agent/dashboard + digital-twin）
    { key: 'ops', label: <span><ControlOutlined /> {isAdmin ? '運維' : '儀表板'}</span>, children: <OpsTab /> },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>
      <Space direction="vertical" size={4} style={{ marginBottom: 16 }}>
        <Title level={2} style={{ margin: 0 }}>
          坤哥 <Tag color="purple">Missive 意識體</Tag>
        </Title>
        <Text type="secondary">
          乾坤測繪公司的數位延續 — 記憶、學習、質疑、進化
        </Text>
      </Space>
      <Tabs
        activeKey={activeKey}
        onChange={(key) => navigate(TAB_TO_PATH[key as KungeTabKey])}
        items={items}
        size="large"
      />
    </div>
  );
};

export default KungePage;

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

type KungeTabKey = 'chat' | 'identity' | 'memory' | 'evolution' | 'nebula' | 'dialogues' | 'ops';

const TAB_TO_PATH: Record<KungeTabKey, string> = {
  chat: '/kunge/chat',
  identity: '/kunge/identity',
  memory: '/kunge/memory',
  evolution: '/kunge/evolution',
  nebula: '/kunge/nebula',
  dialogues: '/kunge/dialogues',
  ops: '/kunge/ops',
};

const PATH_TO_TAB: Record<string, KungeTabKey> = {
  chat: 'chat',
  identity: 'identity',
  memory: 'memory',
  evolution: 'evolution',
  nebula: 'nebula',
  dialogues: 'dialogues',
  ops: 'ops',
};

export const KungePage: React.FC = () => {
  const navigate = useNavigate();
  const { tab } = useParams<{ tab?: string }>();
  const { isAdmin } = useAuthGuard();
  // v5.8.1：預設 chat tab — 用戶來訪時可直接對話，不用先讀敘事
  const activeKey: KungeTabKey = PATH_TO_TAB[tab ?? ''] ?? 'chat';

  const items = [
    { key: 'chat', label: <span><CommentOutlined /> 直接對話</span>, children: <ChatTab /> },
    { key: 'identity', label: <span><BulbOutlined /> 我是誰</span>, children: <IdentityTab /> },
    { key: 'memory', label: <span><DatabaseOutlined /> 記憶圖譜</span>, children: <MemoryTab /> },
    { key: 'evolution', label: <span><RiseOutlined /> 結晶進化</span>, children: <EvolutionTab /> },
    { key: 'nebula', label: <span><DeploymentUnitOutlined /> 技能星雲</span>, children: <NebulaTab /> },
    { key: 'dialogues', label: <span><MessageOutlined /> 對話精選</span>, children: <DialoguesTab /> },
    // v5.8.1：運維儀表板（整合 admin/ai-assistant + agent/dashboard + digital-twin）
    // admin 見 12-tab 完整管理模式，一般使用者見 7-tab 使用者模式
    { key: 'ops', label: <span><ControlOutlined /> {isAdmin ? '運維儀表板' : '儀表板'}</span>, children: <OpsTab /> },
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

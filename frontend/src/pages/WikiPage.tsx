/**
 * WikiPage — LLM Wiki 獨立頁面（v2.0 2026-04-18 拆分版）
 *
 * 四個 Tab：
 * 1. Wiki 圖譜 (force-graph 2D) — knowledgeBase/WikiGraphTab
 * 2. Wiki 頁面瀏覽 (搜尋 + 列表) — knowledgeBase/WikiBrowseTab
 * 3. Wiki ↔ KG 比對 — knowledgeBase/WikiCoverageTab
 * 4. Wiki 管理 (統計 + 編譯 + Lint + Scheduler + Token) — knowledgeBase/WikiAdminTab
 *
 * @version 2.0.0
 * @created 2026-04-13
 * @updated 2026-04-18 — 從 573L 拆分為 4 子檔，主頁維持佈局邏輯
 */

import React, { lazy, Suspense, useState } from 'react';
import { Typography, Tabs, Spin } from 'antd';
import {
  DeploymentUnitOutlined, SearchOutlined, SettingOutlined, NodeIndexOutlined,
} from '@ant-design/icons';

const WikiGraphTab = lazy(() => import('./knowledgeBase/WikiGraphTab'));
const WikiBrowseTab = lazy(() => import('./knowledgeBase/WikiBrowseTab'));
const WikiCoverageTab = lazy(() => import('./knowledgeBase/WikiCoverageTab'));
const WikiAdminTab = lazy(() => import('./knowledgeBase/WikiAdminTab'));

const WikiPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('graph');
  const isGraphTab = activeTab === 'graph';

  // 圖譜 tab: 脫離 Tabs 容器，直接佔滿版面 (避免 Antd Tabs flex 不穩定)
  if (isGraphTab) {
    return (
      <div style={{ height: 'calc(100vh - 88px)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Tabs
          activeKey="graph"
          onChange={setActiveTab}
          tabBarStyle={{ margin: 0, flex: '0 0 auto', padding: '0 8px' }}
          items={[
            { key: 'graph', label: <span><DeploymentUnitOutlined /> Wiki 圖譜</span> },
            { key: 'browse', label: <span><SearchOutlined /> 頁面瀏覽</span> },
            { key: 'coverage', label: <span><NodeIndexOutlined /> KG 比對</span> },
            { key: 'admin', label: <span><SettingOutlined /> 管理</span> },
          ]}
          renderTabBar={(props, DefaultTabBar) => <DefaultTabBar {...props} />}
        />
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <Suspense fallback={<Spin style={{ display: 'block', margin: '60px auto' }} />}>
            <WikiGraphTab />
          </Suspense>
        </div>
      </div>
    );
  }

  // 其他 tab: 正常 Tabs 渲染
  const fallback = <Spin style={{ display: 'block', margin: '40px auto' }} />;
  return (
    <div style={{ padding: '0 4px' }}>
      <Typography.Title level={4} style={{ marginBottom: 12 }}>
        LLM Wiki
      </Typography.Title>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          { key: 'graph', label: <span><DeploymentUnitOutlined /> Wiki 圖譜</span>, children: null },
          {
            key: 'browse',
            label: <span><SearchOutlined /> 頁面瀏覽</span>,
            children: <Suspense fallback={fallback}><WikiBrowseTab /></Suspense>,
          },
          {
            key: 'coverage',
            label: <span><NodeIndexOutlined /> KG 比對</span>,
            children: <Suspense fallback={fallback}><WikiCoverageTab /></Suspense>,
          },
          {
            key: 'admin',
            label: <span><SettingOutlined /> 管理</span>,
            children: <Suspense fallback={fallback}><WikiAdminTab /></Suspense>,
          },
        ]}
      />
    </div>
  );
};

export default WikiPage;

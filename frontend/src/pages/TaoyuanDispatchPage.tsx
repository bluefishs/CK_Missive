/**
 * 桃園查估派工管理系統
 *
 * 五頁籤架構:
 * - Tab 0: 派工總覽 (Kanban 看板)
 * - Tab 1: 派工紀錄
 * - Tab 2: 函文紀錄 (公文管理)
 * - Tab 3: 契金管控
 * - Tab 4: 工程資訊 (轄管工程清單 + 派工工程)
 *
 * 支援多年度專案切換（URL 持久化 ?project=XX&tab=N）
 *
 * @version 3.0.0
 * @date 2026-03-02
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Typography,
  Card,
  Tag,
  Tabs,
  Select,
} from 'antd';
import {
  ProjectOutlined,
  FileTextOutlined,
  SendOutlined,
  DollarOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';

import { useResponsive } from '../hooks';
import { useTaoyuanContractProjects } from '../hooks';
import { ProjectsTab } from '../components/taoyuan/ProjectsTab';
import { DocumentsTab } from '../components/taoyuan/DocumentsTab';
import { DispatchOrdersTab } from '../components/taoyuan/DispatchOrdersTab';
import { PaymentsTab } from '../components/taoyuan/PaymentsTab';
import { TAOYUAN_CONTRACT } from '../constants/taoyuanOptions';
import { DispatchOverviewTab } from '../components/taoyuan/DispatchOverviewTab';

const { Title, Text } = Typography;

/**
 * 桃園查估派工管理系統主頁面
 */
export const TaoyuanDispatchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  // tab=5 (舊晨報追蹤) → tab=0 (已整合到總覽)
  const rawTab = searchParams.get('tab') || '1';
  const initialTab = rawTab === '5' ? '0' : rawTab;
  const initialProjectId = Number(searchParams.get('project')) || TAOYUAN_CONTRACT.PROJECT_ID;
  const [activeTab, setActiveTab] = useState(initialTab);
  const [selectedProjectId, setSelectedProjectId] = useState(initialProjectId);
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  // 取得桃園派工承攬案件列表
  const { data: contractProjects = [], isLoading: projectsLoading } = useTaoyuanContractProjects();

  // 根據選中專案找出 code 和 name
  const selectedProject = useMemo(
    () => contractProjects.find(p => p.id === selectedProjectId),
    [contractProjects, selectedProjectId]
  );
  const contractCode = selectedProject?.project_code ?? TAOYUAN_CONTRACT.CODE;

  // 同步 URL 參數與 Tab 狀態
  useEffect(() => {
    const tabFromUrl = searchParams.get('tab');
    if (tabFromUrl && tabFromUrl !== activeTab) {
      setActiveTab(tabFromUrl);
    }
    const projectFromUrl = Number(searchParams.get('project'));
    if (projectFromUrl && projectFromUrl !== selectedProjectId) {
      setSelectedProjectId(projectFromUrl);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- activeTab/selectedProjectId intentionally excluded
  }, [searchParams]);

  // 更新 URL 的共用函數
  const updateSearchParams = (tab: string, projectId: number) => {
    setSearchParams({ project: String(projectId), tab }, { replace: true });
  };

  // Tab 切換時更新 URL
  const handleTabChange = (key: string) => {
    setActiveTab(key);
    updateSearchParams(key, selectedProjectId);
  };

  // 專案切換
  const handleProjectChange = (projectId: number) => {
    setSelectedProjectId(projectId);
    updateSearchParams(activeTab, projectId);
  };

  // 下拉選單選項（API 資料載入前提供預設項目，避免 Select 顯示 ID 數值）
  const projectOptions = useMemo(() => {
    if (contractProjects.length > 0) {
      return contractProjects.map(p => ({
        value: p.id,
        label: p.project_name,
      }));
    }
    return [{
      value: TAOYUAN_CONTRACT.PROJECT_ID,
      label: TAOYUAN_CONTRACT.NAME,
    }];
  }, [contractProjects]);

  return (
    <div style={{ padding: pagePadding }}>
      {/* 頁面標題 */}
      <div style={{ marginBottom: isMobile ? 12 : 16 }}>
        <Title level={isMobile ? 4 : 2} style={{ margin: 0 }}>
          {isMobile ? '桃園派工系統' : '桃園查估派工管理系統'}
        </Title>
        {!isMobile && (
          <Text type="secondary">派工管理 / 函文紀錄 / 契金管控</Text>
        )}
      </div>

      {/* 專案選擇卡片 */}
      <Card size="small" style={{ marginBottom: isMobile ? 12 : 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? 6 : 12, flexWrap: 'wrap' }}>
          <Tag color="blue">承攬案件</Tag>
          <Select
            value={selectedProjectId}
            onChange={handleProjectChange}
            loading={projectsLoading}
            style={{ flex: 1, minWidth: isMobile ? 180 : 360 }}
            options={projectOptions}
            placeholder="選擇承攬案件"
          />
        </div>
      </Card>

      {/* TAB 頁籤 */}
      <Tabs
        activeKey={activeTab}
        onChange={handleTabChange}
        type="card"
        size={isMobile ? 'middle' : 'large'}
        tabPlacement="top"
        items={[
          {
            key: '0',
            label: (
              <span>
                <AppstoreOutlined />
                {isMobile ? '總覽' : '派工總覽'}
              </span>
            ),
            children: (
              <DispatchOverviewTab
                contractProjectId={selectedProjectId}
              />
            ),
          },
          {
            key: '1',
            label: (
              <span>
                <SendOutlined />
                {isMobile ? '派工' : '派工紀錄'}
              </span>
            ),
            children: (
              <DispatchOrdersTab
                contractProjectId={selectedProjectId}
                contractCode={contractCode}
              />
            ),
          },
          {
            key: '2',
            label: (
              <span>
                <FileTextOutlined />
                {isMobile ? '函文' : '函文紀錄'}
              </span>
            ),
            children: <DocumentsTab contractCode={contractCode} />,
          },
          {
            key: '3',
            label: (
              <span>
                <DollarOutlined />
                {isMobile ? '契金' : '契金管控'}
              </span>
            ),
            children: <PaymentsTab contractProjectId={selectedProjectId} />,
          },
          {
            key: '4',
            label: (
              <span>
                <ProjectOutlined />
                {isMobile ? '工程' : '工程資訊'}
              </span>
            ),
            children: <ProjectsTab contractProjectId={selectedProjectId} />,
          },
        ]}
      />
    </div>
  );
};

export default TaoyuanDispatchPage;

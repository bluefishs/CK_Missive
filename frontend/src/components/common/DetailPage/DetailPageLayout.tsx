/**
 * 通用詳情頁佈局元件
 *
 * 提供統一的詳情頁面結構：
 * - Header（標題、返回按鈕、標籤、操作按鈕）
 * - Tab 分頁內容區
 * - Loading 狀態
 * - Empty 狀態
 *
 * @version 1.0.0
 * @date 2026-01-07
 */

import React, { useState } from 'react';
import { Card, Tabs, Spin, Empty, Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import { DetailPageHeader } from './DetailPageHeader';
import type { DetailPageLayoutProps } from './types';

/**
 * DetailPageLayout - 通用詳情頁佈局元件
 *
 * 使用範例：
 * ```tsx
 * <DetailPageLayout
 *   header={{
 *     title: '案件名稱',
 *     tags: [{ text: '執行中', color: 'processing' }],
 *     backPath: '/contract-cases',
 *   }}
 *   tabs={[
 *     { key: 'info', label: <span><InfoIcon /> 基本資訊</span>, children: <InfoTab /> },
 *     { key: 'staff', label: <span><TeamIcon /> 承辦同仁</span>, children: <StaffTab /> },
 *   ]}
 *   activeTab={activeTab}
 *   onTabChange={setActiveTab}
 *   loading={loading}
 *   hasData={!!data}
 * />
 * ```
 */
export const DetailPageLayout: React.FC<DetailPageLayoutProps> = ({
  header,
  tabs,
  activeTab: controlledActiveTab,
  onTabChange,
  loading = false,
  loadingTip = '載入中...',
  emptyContent,
  hasData = true,
  children,
}) => {
  const navigate = useNavigate();

  // 內部 activeTab 狀態（若未受控則使用內部狀態）
  const [internalActiveTab, setInternalActiveTab] = useState(tabs[0]?.key || '');
  const activeTab = controlledActiveTab ?? internalActiveTab;
  const handleTabChange = onTabChange ?? setInternalActiveTab;

  // Loading 狀態
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" tip={loadingTip} />
      </div>
    );
  }

  // Empty 狀態
  if (!hasData) {
    return (
      <Card>
        {emptyContent || (
          <Empty
            description="找不到資料"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button type="primary" onClick={() => navigate(-1)}>
              返回
            </Button>
          </Empty>
        )}
      </Card>
    );
  }

  return (
    <div>
      {/* Header */}
      <DetailPageHeader {...header} />

      {/* Tab 分頁內容 */}
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={handleTabChange}
          items={tabs}
          size="large"
        />
      </Card>

      {/* 額外內容（Modal、Drawer 等） */}
      {children}
    </div>
  );
};

export default DetailPageLayout;

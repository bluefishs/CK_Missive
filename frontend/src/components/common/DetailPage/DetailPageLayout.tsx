/**
 * 通用詳情頁佈局元件
 *
 * 提供統一的詳情頁面結構：
 * - Header（標題、返回按鈕、標籤、操作按鈕）
 * - Tab 分頁內容區
 * - Loading 狀態
 * - Empty 狀態
 * - RWD 響應式支援
 *
 * @version 1.1.0
 * @date 2026-01-22
 */

import React, { useState } from 'react';
import { Card, Tabs, Spin, Empty, Button } from 'antd';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useResponsive } from '../../../hooks';
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
  const { isMobile, responsiveValue } = useResponsive();

  // 2026-08-15：未受控時，分頁狀態與網址 `?tab=` 同步。
  //
  // 原本分頁只存在元件內部 state，於是：
  // ① **無法深連結**——晨報或 LINE 指到某筆費用，點進來永遠落在第一個分頁；
  //    分享連結給同事，對方看到的也不是你要他看的那一頁。
  // ② **非預設分頁從來沒被量過 RWD**——行動觀測打開頁面只會渲染第一個分頁，
  //    所以財務詳情頁量到 0 溢出，而另外兩頁根本沒被渲染過。
  //
  // `TaoyuanDispatchPage` 早就用 `?tab=` 做對了（2026-08-02），只是沒有擴散 ——
  // 所以修在共用元件而不是各頁補一次，否則下一個新詳情頁又會漏掉。
  //
  // ⚠️ 只在**未受控**時接管：頁面自己傳 activeTab/onTabChange 時完全不介入，
  // 否則會和該頁自己的網址同步邏輯打架。
  const [searchParams, setSearchParams] = useSearchParams();
  const firstTabKey = tabs[0]?.key || '';
  const urlTab = searchParams.get('tab');
  const [internalActiveTab, setInternalActiveTab] = useState(firstTabKey);

  // 網址指定的分頁若存在就用它；不存在（拼錯、舊連結）則回落第一個，不讓頁面空白
  const uncontrolledTab =
    urlTab && tabs.some(t => t.key === urlTab)
      ? urlTab
      : internalActiveTab && tabs.some(t => t.key === internalActiveTab)
        ? internalActiveTab
        : firstTabKey;

  const activeTab = controlledActiveTab ?? uncontrolledTab;
  const handleTabChange = onTabChange ?? ((key: string) => {
    setInternalActiveTab(key);
    // replace 而非 push：切分頁不該把上一頁塞進瀏覽器歷史，
    // 否則使用者按返回鍵是在分頁之間繞，回不到清單頁。
    const next = new URLSearchParams(searchParams);
    next.set('tab', key);
    setSearchParams(next, { replace: true });
  });

  // 響應式間距
  const padding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  // Loading 狀態
  if (loading) {
    return (
      <Spin size="large" description={loadingTip} fullscreen />
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
    <div style={{ padding }}>
      {/* Header */}
      <DetailPageHeader {...header} />

      {/* Tab 分頁內容 */}
      <Card styles={{ body: { padding: isMobile ? 12 : 24 } }}>
        <Tabs
          activeKey={activeTab}
          onChange={handleTabChange}
          items={tabs}
          size={isMobile ? 'middle' : 'large'}
          tabPlacement={isMobile ? 'top' : 'top'}
        />
      </Card>

      {/* 額外內容（Modal、Drawer 等） */}
      {children}
    </div>
  );
};

export default DetailPageLayout;

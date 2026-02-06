/**
 * 儀表板總覽頁面
 *
 * 架構說明：
 * - React Query: 唯一的伺服器資料來源（行事曆事件）
 * - Zustand: 不使用（本頁面無需跨頁面共享狀態）
 *
 * 設計理念：
 * - 以「我的待辦事項」為核心，呈現使用者最需關注的行事曆事件
 * - 下方搭配公文趨勢圖，提供整體收發文量變化
 * - 滿版設計，充分利用螢幕空間
 *
 * @version 3.0.0 - 新增公文趨勢圖
 * @date 2026-02-07
 */
import React from 'react';
import { Typography } from 'antd';
import { useResponsive } from '../hooks';
import { DashboardCalendarSection, DocumentTrendsChart } from '../components/dashboard';

const { Title } = Typography;

// ============================================================================
// 元件
// ============================================================================

export const DashboardPage: React.FC = () => {
  // ============================================================================
  // 響應式設計
  // ============================================================================

  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 8, tablet: 16, desktop: 24 });

  // ============================================================================
  // 渲染
  // ============================================================================

  return (
    <div
      style={{
        padding: pagePadding,
        background: '#f5f5f5',
        minHeight: '100vh',
      }}
    >
      <Title
        level={isMobile ? 4 : 3}
        style={{
          marginBottom: isMobile ? 12 : 20,
          color: '#1976d2',
        }}
      >
        {isMobile ? '儀表板' : '儀表板總覽'}
      </Title>

      {/* 我的待辦事項 - 滿版 */}
      <DashboardCalendarSection maxEvents={15} />

      {/* 公文趨勢圖 */}
      <div style={{ marginTop: isMobile ? 12 : 20 }}>
        <DocumentTrendsChart />
      </div>
    </div>
  );
};

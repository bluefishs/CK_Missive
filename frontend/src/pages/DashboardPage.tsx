/**
 * 儀表板總覽頁面
 *
 * 架構說明：
 * - React Query: 唯一的伺服器資料來源（行事曆事件）
 * - Zustand: 不使用（本頁面無需跨頁面共享狀態）
 *
 * 設計理念：
 * - 以「我的待辦事項」為核心，呈現使用者最需關注的行事曆事件
 * - 滿版設計，充分利用螢幕空間
 * - 公文趨勢圖已移至「統計報表 > 公文數量分析」
 *
 * @version 3.2.0 - 移除 PM/ERP 統計概況，整合至 Reports 頁
 * @date 2026-03-23
 */
import React from 'react';
import { Typography } from 'antd';
import { useResponsive } from '../hooks';
import { DashboardCalendarSection, MyFilingGapsCard, MyErpSummaryCard } from '../components/dashboard';

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

      {/* 我的專案統整（承辦視角：案件／待收／逾期）—— 2026-09-03 owner：個人儀表板核心 */}
      <MyErpSummaryCard />
      {/* 我的待填報（0 項時整張不顯示）—— 2026-08-16 */}
      <MyFilingGapsCard />

      {/* 我的待辦事項 - 滿版 */}
      <DashboardCalendarSection maxEvents={15} />
    </div>
  );
};

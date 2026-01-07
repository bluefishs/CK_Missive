/**
 * 通用詳情頁元件 - 型別定義
 *
 * 提供 DetailPageLayout 的統一型別介面
 *
 * @version 1.0.0
 * @date 2026-01-07
 */

import type { ReactNode } from 'react';

// =============================================================================
// 標籤配置
// =============================================================================

/** 標籤配置 */
export interface TagConfig {
  /** 標籤文字 */
  text: string;
  /** 標籤顏色 */
  color: string;
}

// =============================================================================
// Tab 配置
// =============================================================================

/** Tab 項目配置 */
export interface TabItemConfig {
  /** Tab 識別鍵 */
  key: string;
  /** Tab 標籤（圖示 + 文字） */
  label: ReactNode;
  /** Tab 內容 */
  children: ReactNode;
  /** 是否禁用 */
  disabled?: boolean;
}

/** Tab 標籤輔助配置（用於建立標籤） */
export interface TabLabelConfig {
  /** 圖示元件 */
  icon: ReactNode;
  /** 標籤文字 */
  text: string;
  /** 計數（顯示 badge） */
  count?: number;
  /** badge 顏色 */
  badgeColor?: string;
}

// =============================================================================
// Header 配置
// =============================================================================

/** 頁面標題配置 */
export interface HeaderConfig {
  /** 主標題 */
  title: string;
  /** 副標題（可選） */
  subtitle?: string;
  /** 標籤列表 */
  tags?: TagConfig[];
  /** 返回按鈕文字（預設：返回） */
  backText?: string;
  /** 返回路徑（不設定則使用 navigate(-1)） */
  backPath?: string;
  /** 右側操作按鈕區域 */
  extra?: ReactNode;
  /** 標題圖示 */
  icon?: ReactNode;
}

// =============================================================================
// DetailPageLayout Props
// =============================================================================

/** DetailPageLayout 元件 Props */
export interface DetailPageLayoutProps {
  /** 頁面 Header 配置 */
  header: HeaderConfig;
  /** Tab 項目列表 */
  tabs: TabItemConfig[];
  /** 當前啟用的 Tab key */
  activeTab?: string;
  /** Tab 切換事件 */
  onTabChange?: (key: string) => void;
  /** 載入中狀態 */
  loading?: boolean;
  /** 載入提示文字 */
  loadingTip?: string;
  /** 資料不存在時顯示的內容 */
  emptyContent?: ReactNode;
  /** 是否顯示資料（用於判斷是否顯示 emptyContent） */
  hasData?: boolean;
  /** 額外的 Modal 或 Drawer 內容 */
  children?: ReactNode;
}

// =============================================================================
// DetailPageHeader Props
// =============================================================================

/** DetailPageHeader 元件 Props */
export interface DetailPageHeaderProps extends HeaderConfig {
  /** 返回事件處理（優先於 backPath） */
  onBack?: () => void;
}

// =============================================================================
// 輔助函數型別
// =============================================================================

/** 建立 Tab 標籤的輔助函數型別 */
export type CreateTabLabelFn = (config: TabLabelConfig) => ReactNode;

/** 取得標籤顏色的輔助函數型別 */
export type GetTagColorFn = (value: string | undefined, options: { value: string; color: string }[]) => string;

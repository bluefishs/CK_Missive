/**
 * 通用詳情頁元件模組
 *
 * 提供統一的詳情頁面結構設計：
 * - DetailPageLayout: 主佈局元件
 * - DetailPageHeader: 頁面標題元件
 * - 輔助工具函數
 *
 * @version 1.0.0
 * @date 2026-01-07
 *
 * 使用範例：
 * ```tsx
 * import {
 *   DetailPageLayout,
 *   createTabItem,
 *   createTabLabel,
 *   getTagColor,
 * } from '@/components/common/DetailPage';
 *
 * // 建立 Tab 項目
 * const tabs = [
 *   createTabItem('info', { icon: <InfoIcon />, text: '基本資訊' }, <InfoContent />),
 *   createTabItem('staff', { icon: <TeamIcon />, text: '承辦同仁', count: 5 }, <StaffContent />),
 * ];
 *
 * // 使用佈局
 * <DetailPageLayout
 *   header={{ title: '案件名稱', tags: [...] }}
 *   tabs={tabs}
 * />
 * ```
 */

// 元件匯出
export { DetailPageLayout } from './DetailPageLayout';
export { DetailPageHeader } from './DetailPageHeader';

// 型別匯出
export type {
  DetailPageLayoutProps,
  DetailPageHeaderProps,
  TabItemConfig,
  TabLabelConfig,
  TagConfig,
  HeaderConfig,
  CreateTabLabelFn,
  GetTagColorFn,
} from './types';

// 工具函數匯出
export {
  createTabLabel,
  createTabItem,
  getTagColor,
  getTagText,
  createTagConfig,
  formatFileSize,
  formatCurrency,
} from './utils';

/**
 * 通用詳情頁元件 - 輔助工具函數
 *
 * @version 1.0.0
 * @date 2026-01-07
 */

import React, { type ReactNode } from 'react';
import { Tag, Space } from 'antd';
import type { TabLabelConfig, TabItemConfig, TagConfig } from './types';

// =============================================================================
// Tab 相關工具
// =============================================================================

/**
 * 建立 Tab 標籤
 *
 * @param config Tab 標籤配置
 * @returns Tab 標籤 ReactNode
 *
 * @example
 * ```tsx
 * const label = createTabLabel({
 *   icon: <InfoCircleOutlined />,
 *   text: '基本資訊',
 *   count: 5,
 * });
 * ```
 */
export function createTabLabel(config: TabLabelConfig): ReactNode {
  const { icon, text, count, badgeColor = 'blue' } = config;

  return (
    <Space size={4}>
      {icon}
      <span>{text}</span>
      {count !== undefined && count >= 0 && (
        <Tag color={badgeColor} style={{ marginLeft: 4 }}>
          {count}
        </Tag>
      )}
    </Space>
  );
}

/**
 * 建立 Tab 項目
 *
 * @param key Tab 識別鍵
 * @param labelConfig Tab 標籤配置
 * @param children Tab 內容
 * @param disabled 是否禁用
 * @returns Tab 項目配置
 */
export function createTabItem(
  key: string,
  labelConfig: TabLabelConfig,
  children: ReactNode,
  disabled = false
): TabItemConfig {
  return {
    key,
    label: createTabLabel(labelConfig),
    children,
    disabled,
  };
}

// =============================================================================
// 標籤顏色工具
// =============================================================================

/** 選項配置 */
interface OptionConfig {
  value: string;
  color: string;
  label?: string;
}

/**
 * 根據值取得對應的標籤顏色
 *
 * @param value 當前值
 * @param options 選項配置陣列
 * @param defaultColor 預設顏色
 * @returns 標籤顏色
 *
 * @example
 * ```tsx
 * const STATUS_OPTIONS = [
 *   { value: '執行中', color: 'processing' },
 *   { value: '已結案', color: 'success' },
 * ];
 * const color = getTagColor(status, STATUS_OPTIONS);
 * ```
 */
export function getTagColor(
  value: string | undefined,
  options: OptionConfig[],
  defaultColor = 'default'
): string {
  if (!value) return defaultColor;
  const option = options.find((opt) => opt.value === value);
  return option?.color || defaultColor;
}

/**
 * 根據值取得對應的標籤文字
 *
 * @param value 當前值
 * @param options 選項配置陣列
 * @param defaultText 預設文字
 * @returns 標籤文字
 */
export function getTagText(
  value: string | undefined,
  options: OptionConfig[],
  defaultText = '未設定'
): string {
  if (!value) return defaultText;
  const option = options.find((opt) => opt.value === value);
  return option?.label || value;
}

/**
 * 建立標籤配置
 *
 * @param value 值
 * @param options 選項配置
 * @returns TagConfig
 */
export function createTagConfig(
  value: string | undefined,
  options: OptionConfig[]
): TagConfig | null {
  if (!value) return null;
  const option = options.find((opt) => opt.value === value);
  return {
    text: option?.label || value,
    color: option?.color || 'default',
  };
}

// =============================================================================
// 格式化工具
// =============================================================================

/**
 * 格式化檔案大小
 *
 * @param bytes 位元組數
 * @returns 格式化後的字串
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * 格式化金額
 *
 * @param amount 金額
 * @returns 格式化後的字串
 */
export function formatCurrency(amount: number | undefined | null): string {
  if (amount === undefined || amount === null) return '-';
  return `NT$ ${amount.toLocaleString()}`;
}

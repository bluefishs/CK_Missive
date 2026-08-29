/**
 * 契金管控 - 表格欄位定義與工具函數
 *
 * 從 PaymentsTab.tsx 提取，包含：
 * - WORK_TYPE_COLUMNS 作業類別常數
 * - formatDate / formatAmount 工具函數
 * - usePaymentColumns 自訂 Hook
 *
 * @version 1.0.0
 * @date 2026-02-27
 */

import React, { useMemo } from 'react';
import { Typography, Button, Tooltip } from 'antd';
import type { ColumnGroupType, ColumnType } from 'antd/es/table';
import type { NavigateFunction } from 'react-router-dom';
import dayjs from 'dayjs';

import type { PaymentControlItem } from '../../../types/api';

const { Text } = Typography;

/** 作業類別定義 */
export const WORK_TYPE_COLUMNS = [
  { key: '01', label: '01.地上物查估', dateField: 'work_01_date', amountField: 'work_01_amount', color: '#e6fffb' },
  { key: '02', label: '02.土地協議市價查估', dateField: 'work_02_date', amountField: 'work_02_amount', color: '#fffbe6' },
  { key: '03', label: '03.土地徵收市價查估', dateField: 'work_03_date', amountField: 'work_03_amount', color: '#fff2e8' },
  { key: '04', label: '04.相關計畫書製作', dateField: 'work_04_date', amountField: 'work_04_amount', color: '#f9f0ff' },
  { key: '05', label: '05.測量作業', dateField: 'work_05_date', amountField: 'work_05_amount', color: '#e6f7ff' },
  { key: '06', label: '06.樁位測釘作業', dateField: 'work_06_date', amountField: 'work_06_amount', color: '#f6ffed' },
  { key: '07', label: '07.辦理教育訓練', dateField: 'work_07_date', amountField: 'work_07_amount', color: '#fff0f6' },
];

/** 格式化日期 */
export const formatDate = (val?: string | null) => {
  if (!val) return '-';
  const d = dayjs(val);
  // 使用民國年格式
  const rocYear = d.year() - 1911;
  return `${rocYear}.${d.format('M.D')}`;
};

/** 格式化金額（整數，無小數） */
export const formatAmount = (val?: number | null) => {
  if (val === undefined || val === null || val === 0) return '-';
  return Math.round(val).toLocaleString();
};

/**
 * 契金管控表格欄位定義 Hook
 *
 * @param navigate - React Router navigate 函數
 * @returns 完整的表格欄位定義陣列
 */
// 2026-08-29 owner「表格皆需提供篩選排序機制」：本表用 Table.Summary 合計列，
// 不能靠 EnhancedTable 自動增強（那是函式包裝、沒有靜態成員），故逐欄手動宣告。
// '序'（列序號）與群組表頭刻意不排序 —— 序號排序沒有意義。
export const usePaymentColumns = (
  navigate: NavigateFunction,
  items: PaymentControlItem[] = [],
): (ColumnGroupType<PaymentControlItem> | ColumnType<PaymentControlItem>)[] => {
  return useMemo(() => {
    // 基本欄位
    const baseColumns: ColumnType<PaymentControlItem>[] = [
      {
        title: '序',
        key: 'index',
        width: 40,
        fixed: 'left',
        align: 'center',
        render: (_, __, index) => index + 1,
      },
      {
        title: '派工單號',
        sorter: (a: PaymentControlItem, b: PaymentControlItem) => String(a.dispatch_no || '').localeCompare(String(b.dispatch_no || '')),
        dataIndex: 'dispatch_no',
        width: 120,
        fixed: 'left',
        render: (val: string, record) => (
          React.createElement(Button, {
            type: 'link',
            size: 'small',
            style: { padding: 0, color: '#1890ff' },
            onClick: () => navigate(`/taoyuan/dispatch/${record.dispatch_order_id}`),
          }, val)
        ),
      },
      {
        title: '工程名稱/派工事項',
        sorter: (a: PaymentControlItem, b: PaymentControlItem) => String(a.project_name || '').localeCompare(String(b.project_name || '')),
        dataIndex: 'project_name',
        width: 280,
        fixed: 'left',
        ellipsis: { showTitle: false },
        render: (val: string) => (
          React.createElement(Tooltip, { title: val },
            React.createElement('span', { style: { whiteSpace: 'normal', lineHeight: 1.3 } }, val || '-')
          )
        ),
      },
    ];

    // 2026-08-29 owner 回報「/taoyuan/dispatch 資訊完全超出頁框」：
    // 這張表原本**無條件展開 7 種作業類別 × 2 欄**，桌面 1409px 下表格寬 2200、
    // 容器只有 1112 ⇒ 要橫向捲 1088px，一次只看得到一半。
    //
    // 只渲染「這批資料真的用到」的類別。判準是該類別在**任何一列**有日期或金額；
    // 全部沒有的類別對使用者是 14 欄的「-」，佔掉的正是他要看的空間。
    // ⚠️ 開口契約常常七類全用（實測 project=21 就是），那時本節省不下來 ——
    // 所以另外還做了兩件事：金額欄改 fixed:'right'、scroll.x 改由欄寬推導。
    const usedWorkTypes = WORK_TYPE_COLUMNS.filter((wt) =>
      items.length === 0 || items.some((it) => {
        const rec = it as unknown as Record<string, unknown>;
        return Boolean(rec[wt.dateField]) || Boolean(rec[wt.amountField]);
      })
    );
    const workTypeColumnGroups: ColumnGroupType<PaymentControlItem>[] = usedWorkTypes.map(
      (workType) => ({
        title: React.createElement('span', { style: { fontWeight: 600, color: '#262626' } }, workType.label),
        key: workType.key,
        align: 'center' as const,
        onHeaderCell: () => ({
          style: {
            background: workType.color,
            textAlign: 'center',
            fontWeight: 600,
            padding: '8px 4px',
          },
        }),
        children: [
          {
            title: '派工日期',
            dataIndex: workType.dateField,
            key: `${workType.key}_date`,
            width: 76,
            align: 'center' as const,
            onCell: () => ({
              style: {
                background: workType.color,
                fontSize: 12,
                padding: '6px 4px',
                textAlign: 'center',
              },
            }),
            onHeaderCell: () => ({
              style: {
                background: workType.color,
                fontSize: 11,
                padding: '6px 4px',
                textAlign: 'center',
                fontWeight: 500,
              },
            }),
            render: (val: string | null) => (
              React.createElement('span', { style: { color: val ? '#595959' : '#bfbfbf' } }, formatDate(val))
            ),
          },
          {
            title: '派工金額',
            dataIndex: workType.amountField,
            key: `${workType.key}_amount`,
            width: 82,
            align: 'right' as const,
            onCell: () => ({
              style: {
                background: workType.color,
                fontSize: 12,
                padding: '6px 6px',
              },
            }),
            onHeaderCell: () => ({
              style: {
                background: workType.color,
                fontSize: 11,
                padding: '6px 4px',
                textAlign: 'center',
                fontWeight: 500,
              },
            }),
            render: (val: number | null) => (
              React.createElement('span', {
                style: { color: val ? '#1890ff' : '#bfbfbf', fontWeight: val ? 500 : 400 },
              }, formatAmount(val))
            ),
          },
        ],
      })
    );

    // 彙總欄位
    const summaryColumns: ColumnType<PaymentControlItem>[] = [
      {
        title: '本次派工總金額',
        fixed: 'right' as const,
        sorter: (a: PaymentControlItem, b: PaymentControlItem) => (a.current_amount || 0) - (b.current_amount || 0),
        dataIndex: 'current_amount',
        key: 'current_amount',
        width: 110,
        align: 'right',
        onCell: () => ({ style: { background: '#fffbe6' } }),
        onHeaderCell: () => ({ style: { background: '#fffbe6' } }),
        render: (val?: number) => (
          React.createElement(Text, { strong: true, style: { color: '#1890ff' } },
            formatAmount(val ? Math.round(val) : undefined)
          )
        ),
      },
      {
        title: '累進派工金額',
        fixed: 'right' as const,
        sorter: (a: PaymentControlItem, b: PaymentControlItem) => (a.cumulative_amount || 0) - (b.cumulative_amount || 0),
        dataIndex: 'cumulative_amount',
        key: 'cumulative_amount',
        width: 110,
        align: 'right',
        onCell: () => ({ style: { background: '#e6f7ff' } }),
        onHeaderCell: () => ({ style: { background: '#e6f7ff' } }),
        render: (val?: number) => formatAmount(val ? Math.round(val) : undefined),
      },
      {
        title: '剩餘金額',
        fixed: 'right' as const,
        sorter: (a: PaymentControlItem, b: PaymentControlItem) => (a.remaining_amount || 0) - (b.remaining_amount || 0),
        dataIndex: 'remaining_amount',
        key: 'remaining_amount',
        width: 110,
        align: 'right',
        onCell: (record) => ({
          style: {
            background: (record.remaining_amount ?? 0) < 1000000 ? '#fff2e8' : '#f6ffed',
          },
        }),
        onHeaderCell: () => ({ style: { background: '#f6ffed' } }),
        render: (val?: number) => (
          React.createElement(Text, { type: (val ?? 0) < 1000000 ? 'warning' : undefined },
            formatAmount(val ? Math.round(val) : undefined)
          )
        ),
      },
    ];

    return [...baseColumns, ...workTypeColumnGroups, ...summaryColumns];
  }, [navigate, items]);
};

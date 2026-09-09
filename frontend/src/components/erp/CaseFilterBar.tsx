/**
 * CaseFilterBar —— 案件類列表的**宣告式篩選列**（2026-09-09 晚，篩選模組化最後一步）。
 *
 * 維度集合對應後端 `schemas/erp/case_filters.CaseListFilters`（年度／類別／關鍵字／承辦）
 * 加上報價單頁特有的委託單位／金流異常。頁面只宣告「我這頁支援哪幾個」（`dims`），
 * 元件負責畫、負責選項的單一定義（年度選項、類別選項、承辦選項 hook）；
 * 新增一個維度＝改後端 schema ＋ 本元件各一處，所有頁面同時拿到。
 *
 * 此前三個財務分頁各自畫：年度選項三份（報價單 `YEAR_OPTIONS`、帳款兩頁各一份 `yearOptions`，
 * 其中一份還沒有「全部年度」）、承辦下拉三份、類別下拉三份——同一件事三種畫法（FILTER_MODULARIZATION §四）。
 *
 * 狀態不在元件裡：`value`／`onChange(patch)` 由頁面持有，與表頭漏斗共用同一份 params（規範 §2.6 ④）。
 * 年度：`0`＝全部年度（後端約定：None 走預設當年、0 才是不篩）；頁面若用 `undefined` 表示全部，自行在 onChange 轉。
 */
import React from 'react';
import { Input, Select } from 'antd';
import { FilterBar } from '../common/FilterBar';
import { CASE_CATEGORY_OPTIONS } from '../../constants/projectOptions';
import { useStaffAssigneeOptions } from '../../hooks/business/useDropdownData';
import { ANOMALY_FILTER_OPTIONS, CURRENT_CASE_YEAR, caseYearOptions } from './caseFilterOptions';

export type CaseFilterDim = 'keyword' | 'year' | 'category' | 'staff' | 'client' | 'anomaly';

export interface CaseFilterValues {
  keyword?: string;
  year?: number;          // 0＝全部年度
  category?: string;
  staff_user_id?: number;
  client_name?: string;
  anomaly?: 'open' | 'all';
}

export interface CaseFilterBarProps {
  dims: CaseFilterDim[];
  value: CaseFilterValues;
  onChange: (patch: Partial<CaseFilterValues>) => void;
  /** 委託單位選項（只有報價單頁有這個維度，資料由頁面的 hook 供給） */
  clientOptions?: Array<{ name: string; count?: number }>;
  keywordPlaceholder?: string;
  /** 關鍵字即時（每個按鍵）回 patch；預設是按 Enter／放大鏡才送（Search 語意）。承攬案頁是前端全量列表，用即時。 */
  liveKeyword?: boolean;
  /** 年度選項改由頁面供給（例如承攬案頁用資料裡實際存在的年度）；預設近五年＋全部年度 */
  yearOptions?: Array<{ value: number; label: string }>;
  /** 額外的活動條件數（例如卡片篩選），加進「篩選 (n)」計數 */
  extraActiveCount?: number;
  /** 篩選列裡的其他控制項／按鈕（匯出、匯入…），放在維度之後 */
  children?: React.ReactNode;
  style?: React.CSSProperties;
  defaultOpen?: boolean;
}

export const CaseFilterBar: React.FC<CaseFilterBarProps> = ({
  dims, value, onChange, clientOptions = [], keywordPlaceholder = '搜尋案號／案名', extraActiveCount = 0, children, style, defaultOpen,
  liveKeyword = false, yearOptions,
}) => {
  const has = (d: CaseFilterDim) => dims.includes(d);
  const { staffOptions } = useStaffAssigneeOptions();

  // 「活動中的條件」：年度只有在**不是當年度**時才算（預設當年度不是使用者的選擇）
  const active =
    (has('year') && value.year !== undefined && value.year !== CURRENT_CASE_YEAR ? 1 : 0) +
    (has('category') && value.category ? 1 : 0) +
    (has('staff') && value.staff_user_id ? 1 : 0) +
    (has('client') && value.client_name ? 1 : 0) +
    (has('anomaly') && value.anomaly ? 1 : 0) +
    extraActiveCount;

  return (
    <FilterBar
      style={style}
      defaultOpen={defaultOpen}
      activeCount={active}
      summary={has('keyword') ? (liveKeyword ? (
        <Input
          placeholder={keywordPlaceholder}
          allowClear
          value={value.keyword ?? ''}
          onChange={(e) => onChange({ keyword: e.target.value || undefined })}
          style={{ width: 240 }}
          aria-label="關鍵字"
        />
      ) : (
        <Input.Search
          placeholder={keywordPlaceholder}
          allowClear
          defaultValue={value.keyword}
          onSearch={(v) => onChange({ keyword: v.trim() || undefined })}
          style={{ width: 240 }}
          aria-label="關鍵字"
        />
      )) : undefined}
    >
      {has('year') && (
        <Select
          value={value.year ?? CURRENT_CASE_YEAR}
          onChange={(v) => onChange({ year: v })}
          options={yearOptions ?? caseYearOptions()}
          style={{ width: 130 }}
          aria-label="年度"
        />
      )}
      {has('category') && (
        <Select
          placeholder="計畫類別" allowClear style={{ width: 130 }} value={value.category}
          onChange={(v) => onChange({ category: v || undefined })}
          options={[...CASE_CATEGORY_OPTIONS]}
          aria-label="計畫類別"
        />
      )}
      {has('staff') && (
        <Select
          placeholder="承辦同仁" allowClear showSearch style={{ width: 170 }} value={value.staff_user_id}
          optionFilterProp="label"
          onChange={(v) => onChange({ staff_user_id: v ?? undefined })}
          options={staffOptions.map((o) => ({ value: o.user_id, label: `${o.name}（${o.case_count}）` }))}
          aria-label="承辦同仁"
        />
      )}
      {has('client') && (
        <Select
          placeholder="委託單位" allowClear showSearch style={{ width: 220 }} value={value.client_name}
          optionFilterProp="label"
          onChange={(v) => onChange({ client_name: v || undefined })}
          options={clientOptions.map((c) => ({ value: c.name, label: c.count != null ? `${c.name}（${c.count}）` : c.name }))}
          aria-label="委託單位"
        />
      )}
      {has('anomaly') && (
        <Select
          placeholder="金流異常" allowClear style={{ width: 150 }} value={value.anomaly}
          onChange={(v) => onChange({ anomaly: (v || undefined) as 'open' | 'all' | undefined })}
          options={ANOMALY_FILTER_OPTIONS}
          aria-label="金流異常"
        />
      )}
      {children}
    </FilterBar>
  );
};

export default CaseFilterBar;

/**
 * 帳款列表的「計畫類別」「案件狀態」兩欄（owner 2026-09-07：兩頁在統一編號後新增）。
 *
 * 為什麼做成共用而不是各頁一份：委託單位帳款與協力廠商帳款是同一件事的兩端，
 * 兩頁各寫一份 Tag 顏色與空值符號，下一次只會改到其中一頁 ——
 * 本 repo 對「同一件事有兩份實作」已經付過很多次代價（最近一次是報價單工項容量）。
 *
 * 資料來源是後端 `repositories/erp/case_profile.py`，標籤映射（01→委辦招標、
 * contracted→已承攬…）只在那一份裡；這裡不做任何翻譯，只負責呈現。
 */
import { Tag, Tooltip } from 'antd';
import { clientFilterAny, distinctOptions } from '../../utils/tableFilters';
import type { ResponsiveColumn } from '../common/EnhancedTable';
import type { CaseStaffRef, CaseStatusCount } from '../../types/erp';

/** 案件狀態的顏色：只分「還在進行」「已結束」「其他」，不逐值配色（值會增加） */
const STATUS_COLOR: Record<string, string> = {
  執行中: 'processing',
  已承攬: 'processing',
  待執行: 'default',
  評估中: 'default',
  已結案: 'success',
  未得標: 'default',
  已取消: 'default',
};

export interface CaseProfileRow {
  categories?: string[];
  statuses?: CaseStatusCount[];
  staff?: CaseStaffRef[];
}

/** 承辦同仁：一案可能多人，一家往來對象名下更可能有數人 —— 顯示前兩位，其餘進 tooltip */
export function renderStaff(staff?: CaseStaffRef[]) {
  if (!staff || staff.length === 0) return <span style={{ color: '#bfbfbf' }}>—</span>;
  const names = staff.map((s) => s.name).filter(Boolean);
  const head = names.slice(0, 2).join('、');
  const body = names.length > 2 ? `${head} +${names.length - 2}` : head;
  return names.length > 2 ? <Tooltip title={names.join('、')}><span>{body}</span></Tooltip> : <span>{body}</span>;
}

export function renderCategories(categories?: string[]) {
  if (!categories || categories.length === 0) return <span style={{ color: '#bfbfbf' }}>—</span>;
  return (
    <>
      {categories.map((c) => (
        <Tag key={c} color={c === '委辦招標' ? 'geekblue' : 'cyan'} style={{ marginInlineEnd: 4 }}>
          {c}
        </Tag>
      ))}
    </>
  );
}

export function renderStatuses(statuses?: CaseStatusCount[]) {
  if (!statuses || statuses.length === 0) return <span style={{ color: '#bfbfbf' }}>—</span>;
  // 一家往來對象名下常有多種狀態，全列會把欄寬吃光 ⇒ 顯示前兩種，其餘進 tooltip。
  const head = statuses.slice(0, 2);
  const rest = statuses.slice(2);
  const body = (
    <>
      {head.map((s) => (
        <Tag key={s.label} color={STATUS_COLOR[s.label] ?? 'default'} style={{ marginInlineEnd: 4 }}>
          {s.label} {s.count}
        </Tag>
      ))}
      {rest.length > 0 && <Tag style={{ marginInlineEnd: 0 }}>+{rest.length}</Tag>}
    </>
  );
  if (rest.length === 0) return body;
  return (
    <Tooltip title={statuses.map((s) => `${s.label} ${s.count}`).join('、')}>
      <span>{body}</span>
    </Tooltip>
  );
}

/**
 * 三欄的定義；插在「統一編號」之後。泛型讓兩頁各自的列型別都能用。
 *
 * 2026-09-09 owner「表頭篩選請完善」：這三欄加上表頭漏斗。
 * 兩頁都是**全量在手**（`limit: 1000` 前端分頁）⇒ 用 `clientFilterAny`（必須帶 `onFilter`），
 * 而且語意是「**包含**」不是「等於」——一個委託單位名下有多個類別／承辦／狀態。
 * 選項由當下的資料推導（全量在手時這樣做選項必然與資料一致）。
 *
 * @param rows 目前載入的全部列，用來推導漏斗選項。不傳則不加漏斗（詳情頁等場合）。
 */
export function caseProfileColumns<T extends CaseProfileRow>(rows?: T[]): ResponsiveColumn<T>[] {
  const catOpts = distinctOptions(rows, (r) => r.categories);
  const staffOpts = distinctOptions(rows, (r) => (r.staff ?? []).map((s) => s.name));
  const statusOpts = distinctOptions(rows, (r) => (r.statuses ?? []).map((s) => s.label));
  return [
    {
      title: '計畫類別',
      hideOnMobile: true,
      dataIndex: 'categories',
      key: 'categories',
      width: 150,
      ...(catOpts.length ? clientFilterAny<T>(catOpts, (r) => r.categories) : {}),
      render: (_: unknown, r: T) => renderCategories(r.categories),
    },
    {
      title: '承辦同仁',
      hideOnMobile: true,
      dataIndex: 'staff',
      key: 'staff',
      width: 140,
      ellipsis: true,
      // 承辦同仁基數中等（十幾人），給搜尋框避免下拉太長
      ...(staffOpts.length ? clientFilterAny<T>(staffOpts, (r) => (r.staff ?? []).map((s) => s.name), { search: true }) : {}),
      render: (_: unknown, r: T) => renderStaff(r.staff),
    },
    {
      title: '案件狀態',
      hideOnMobile: true,
      dataIndex: 'statuses',
      key: 'statuses',
      width: 170,
      ...(statusOpts.length ? clientFilterAny<T>(statusOpts, (r) => (r.statuses ?? []).map((s) => s.label)) : {}),
      render: (_: unknown, r: T) => renderStatuses(r.statuses),
    },
  ];
}

/** 手機卡片用：把類別與狀態併成 MobileCard 的 tags（桌面兩欄在手機是隱藏的） */
export function caseProfileTags(row: CaseProfileRow): { text: string; color?: string }[] {
  const tags: { text: string; color?: string }[] = [];
  (row.categories ?? []).forEach((c) => tags.push({ text: c, color: c === '委辦招標' ? 'geekblue' : 'cyan' }));
  (row.statuses ?? []).slice(0, 2).forEach((s) =>
    tags.push({ text: `${s.label} ${s.count}`, color: STATUS_COLOR[s.label] ?? undefined }),
  );
  // 承辦同仁在手機的兩欄是隱藏的 —— 用 tag 帶出來，否則手機上完全看不到「這是誰的案」
  (row.staff ?? []).slice(0, 2).forEach((s) => tags.push({ text: s.name, color: 'purple' }));
  return tags;
}

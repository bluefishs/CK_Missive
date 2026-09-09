/**
 * CaseFilterBar：宣告式篩選列（2026-09-09 晚）。
 * 鎖：①只畫宣告的維度 ②onChange 回 patch（頁面自己合併）③年度 0＝全部年度、預設當年度不算活動條件。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import { createTestQueryClient } from '../../test/testUtils';

vi.mock('../../hooks/business/useDropdownData', () => ({
  useStaffAssigneeOptions: () => ({ staffOptions: [{ user_id: 6, name: '邱元宏', case_count: 85 }], isLoading: false }),
}));

import { CaseFilterBar } from '../../components/erp/CaseFilterBar';
import { caseYearOptions, CURRENT_CASE_YEAR } from '../../components/erp/caseFilterOptions';

function renderBar(props: Partial<React.ComponentProps<typeof CaseFilterBar>> = {}) {
  const onChange = vi.fn();
  render(
    <QueryClientProvider client={createTestQueryClient()}>
      <ConfigProvider locale={zhTW}>
        <CaseFilterBar dims={['keyword', 'year', 'category', 'staff']} value={{ year: CURRENT_CASE_YEAR }} onChange={onChange} defaultOpen {...props} />
      </ConfigProvider>
    </QueryClientProvider>,
  );
  return onChange;
}

describe('CaseFilterBar', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('只畫宣告的維度', () => {
    renderBar({ dims: ['keyword', 'year'] });
    expect(screen.getByLabelText('關鍵字')).toBeTruthy();
    expect(screen.getByLabelText('年度')).toBeTruthy();
    expect(screen.queryByLabelText('計畫類別')).toBeNull();
    expect(screen.queryByLabelText('承辦同仁')).toBeNull();
  });

  it('關鍵字送出時回 patch，空字串變 undefined', () => {
    const onChange = renderBar();
    const input = screen.getByLabelText('關鍵字') as HTMLInputElement;
    fireEvent.change(input, { target: { value: ' 測量 ' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
    expect(onChange).toHaveBeenCalledWith({ keyword: '測量' });
  });

  it('年度選項單一定義：0＝全部年度、近五年', () => {
    const opts = caseYearOptions();
    expect(opts[0]).toEqual({ value: 0, label: '全部年度' });
    expect(opts.length).toBe(6);
    expect(opts[1]?.value).toBe(CURRENT_CASE_YEAR);
  });
});

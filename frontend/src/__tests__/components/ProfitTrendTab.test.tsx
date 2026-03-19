/**
 * ProfitTrendTab 單元測試
 *
 * 測試 ERP 損益趨勢頁籤的三種狀態：載入中 / 空資料 / 有資料（含彙總統計）
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('../../hooks/business/useERPQuotations', () => ({
  useERPProfitTrend: vi.fn(),
}));

import ProfitTrendTab from '../../pages/erpQuotation/ProfitTrendTab';
import { useERPProfitTrend } from '../../hooks/business/useERPQuotations';

describe('ProfitTrendTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading spinner', () => {
    vi.mocked(useERPProfitTrend).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as unknown as ReturnType<typeof useERPProfitTrend>);

    render(<ProfitTrendTab />);
    expect(screen.getByText('載入趨勢...')).toBeTruthy();
  });

  it('shows empty state when no data', () => {
    vi.mocked(useERPProfitTrend).mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useERPProfitTrend>);

    render(<ProfitTrendTab />);
    expect(screen.getByText('尚無多年度資料')).toBeTruthy();
  });

  it('renders trend table with data and summary statistics', () => {
    vi.mocked(useERPProfitTrend).mockReturnValue({
      data: [
        { year: 113, case_count: 5, revenue: '1000000', cost: '700000', gross_profit: '300000', gross_margin: '30.0' },
        { year: 114, case_count: 3, revenue: '500000', cost: '300000', gross_profit: '200000', gross_margin: '40.0' },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof useERPProfitTrend>);

    render(<ProfitTrendTab />);
    expect(screen.getByText('年度損益趨勢')).toBeTruthy();
    expect(screen.getByText('累計收入')).toBeTruthy();
    expect(screen.getByText('累計成本')).toBeTruthy();
    expect(screen.getByText('累計毛利')).toBeTruthy();
    expect(screen.getByText('平均毛利率')).toBeTruthy();
  });
});

/**
 * YearlyTrendCard 單元測試
 *
 * 測試 PM 多年度趨勢卡片的三種狀態：載入中 / 空資料 / 有資料
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('../../hooks', () => ({
  usePMYearlyTrend: vi.fn(),
}));

import YearlyTrendCard from '../../pages/pmCase/YearlyTrendCard';
import { usePMYearlyTrend } from '../../hooks';

describe('YearlyTrendCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading spinner when data is being fetched', () => {
    vi.mocked(usePMYearlyTrend).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as unknown as ReturnType<typeof usePMYearlyTrend>);

    const { container } = render(<YearlyTrendCard />);
    expect(container.querySelector('.ant-spin')).toBeTruthy();
  });

  it('renders title and table with data', () => {
    vi.mocked(usePMYearlyTrend).mockReturnValue({
      data: [
        { year: 113, case_count: 10, total_contract: '5000000', closed_count: 7, in_progress_count: 3, avg_progress: 85 },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof usePMYearlyTrend>);

    render(<YearlyTrendCard />);
    expect(screen.getByText('多年度案件趨勢')).toBeTruthy();
  });

  it('renders empty table when no data', () => {
    vi.mocked(usePMYearlyTrend).mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof usePMYearlyTrend>);

    render(<YearlyTrendCard />);
    expect(screen.getByText('多年度案件趨勢')).toBeTruthy();
  });
});

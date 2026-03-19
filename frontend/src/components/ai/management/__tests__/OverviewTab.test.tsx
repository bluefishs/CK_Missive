/**
 * OverviewTab 元件測試
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ── Mock setup ──
const { mockAiApi } = vi.hoisted(() => ({
  mockAiApi: {
    getSearchStats: vi.fn(),
  },
}));

vi.mock('../../../../api/aiApi', () => ({
  aiApi: mockAiApi,
}));

import { OverviewTab } from '../OverviewTab';

// ── Test data ──
const mockStats = {
  total_searches: 150,
  today_searches: 12,
  rule_engine_hit_rate: 0.65,
  avg_latency_ms: 320,
  avg_confidence: 0.78,
  strategy_distribution: { hybrid: 80, similarity: 50, keyword: 20 },
  source_distribution: { rule_engine: 60, vector: 50, ai: 30, error: 10 },
  entity_distribution: { dispatch_order: 45, project: 30 },
  top_queries: [
    { query: '桃園市公文', count: 15, avg_results: 5.2 },
    { query: '派工單進度', count: 10, avg_results: 3.1 },
  ],
  daily_trend: [
    { date: '2026-03-14', count: 22 },
    { date: '2026-03-13', count: 18 },
  ],
};

const mockEmptyStats = {
  total_searches: 0,
  today_searches: 0,
  rule_engine_hit_rate: 0,
  avg_latency_ms: 0,
  avg_confidence: null,
  strategy_distribution: {},
  source_distribution: {},
  entity_distribution: {},
  top_queries: [],
  daily_trend: [],
};

// ── Helpers ──
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  Wrapper.displayName = 'TestWrapper';
  return Wrapper;
}

// ── Tests ──
describe('OverviewTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('載入中顯示 spinner', () => {
    mockAiApi.getSearchStats.mockReturnValue(new Promise(() => {}));
    render(<OverviewTab />, { wrapper: createWrapper() });
    expect(document.querySelector('.ant-spin')).toBeTruthy();
  });

  it('API 返回 null 顯示空狀態', async () => {
    mockAiApi.getSearchStats.mockResolvedValue(null);
    render(<OverviewTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('無法載入統計資料')).toBeInTheDocument();
    });
  });

  it('搜尋次數為 0 顯示空紀錄提示', async () => {
    mockAiApi.getSearchStats.mockResolvedValue(mockEmptyStats);
    render(<OverviewTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/尚無搜尋紀錄/)).toBeInTheDocument();
      expect(screen.getByText('重新整理')).toBeInTheDocument();
    });
  });

  it('正確渲染統計卡片', async () => {
    mockAiApi.getSearchStats.mockResolvedValue(mockStats);
    render(<OverviewTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('總搜尋次數')).toBeInTheDocument();
      expect(screen.getByText('今日搜尋')).toBeInTheDocument();
      expect(screen.getByText('規則引擎命中率')).toBeInTheDocument();
      expect(screen.getByText('平均回應時間')).toBeInTheDocument();
    });
  });

  it('渲染信心度與品質統計', async () => {
    mockAiApi.getSearchStats.mockResolvedValue(mockStats);
    render(<OverviewTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('平均信心度')).toBeInTheDocument();
      expect(screen.getByText('錯誤源比例')).toBeInTheDocument();
      expect(screen.getByText('同義詞擴展使用')).toBeInTheDocument();
      expect(screen.getByText('派工搜尋次數')).toBeInTheDocument();
    });
  });

  it('渲染分佈區塊（策略/來源/實體）', async () => {
    mockAiApi.getSearchStats.mockResolvedValue(mockStats);
    render(<OverviewTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('搜尋策略分佈')).toBeInTheDocument();
      expect(screen.getByText('解析來源分佈')).toBeInTheDocument();
      expect(screen.getByText('實體類型分佈')).toBeInTheDocument();
    });
  });

  it('無分佈資料時不顯示分佈區塊', async () => {
    mockAiApi.getSearchStats.mockResolvedValue({
      ...mockStats,
      strategy_distribution: {},
      source_distribution: {},
      entity_distribution: {},
    });
    render(<OverviewTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('總搜尋次數')).toBeInTheDocument();
    });
    expect(screen.queryByText('搜尋策略分佈')).not.toBeInTheDocument();
  });

  it('渲染熱門查詢表格', async () => {
    mockAiApi.getSearchStats.mockResolvedValue(mockStats);
    render(<OverviewTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('熱門查詢 Top 10')).toBeInTheDocument();
      expect(screen.getByText('桃園市公文')).toBeInTheDocument();
      expect(screen.getByText('派工單進度')).toBeInTheDocument();
    });
  });

  it('渲染趨勢表格', async () => {
    mockAiApi.getSearchStats.mockResolvedValue(mockStats);
    render(<OverviewTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('近 30 天搜尋趨勢')).toBeInTheDocument();
      expect(screen.getByText('2026-03-14')).toBeInTheDocument();
    });
  });

  it('呼叫 getSearchStats API', async () => {
    mockAiApi.getSearchStats.mockResolvedValue(mockStats);
    render(<OverviewTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(mockAiApi.getSearchStats).toHaveBeenCalledTimes(1);
    });
  });

  it('重新整理按鈕觸發 refetch', async () => {
    mockAiApi.getSearchStats.mockResolvedValue(mockStats);
    const user = userEvent.setup();
    render(<OverviewTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('近 30 天搜尋趨勢')).toBeInTheDocument();
    });

    // Click the refresh button in trend card
    const refreshButtons = screen.getAllByText('重新整理');
    await user.click(refreshButtons[refreshButtons.length - 1]!);

    await waitFor(() => {
      expect(mockAiApi.getSearchStats).toHaveBeenCalledTimes(2);
    });
  });
});

/**
 * HistoryTab 元件測試
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const { mockAiApi, mockMessage } = vi.hoisted(() => ({
  mockAiApi: {
    listSearchHistory: vi.fn(),
    clearSearchHistory: vi.fn(),
  },
  mockMessage: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
    loading: vi.fn(),
    destroy: vi.fn(),
    open: vi.fn(),
    config: vi.fn(),
  },
}));

vi.mock('../../../../api/aiApi', () => ({
  aiApi: mockAiApi,
}));

vi.mock('antd', async () => {
  const actual = await vi.importActual<typeof import('antd')>('antd');
  return {
    ...actual,
    message: mockMessage,
  };
});

import { HistoryTab } from '../HistoryTab';

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  Wrapper.displayName = 'TestWrapper';
  return Wrapper;
}

const mockHistoryData = {
  items: [
    {
      id: 1,
      query: '桃園市公文',
      results_count: 5,
      source: 'rule_engine',
      confidence: 0.85,
      latency_ms: 120,
      created_at: '2026-03-14T10:30:00Z',
      user_name: '管理員',
      search_strategy: 'hybrid',
      synonym_expanded: true,
      related_entity: 'dispatch_order',
      parsed_intent: null,
    },
    {
      id: 2,
      query: '派工進度查詢',
      results_count: 3,
      source: 'ai',
      confidence: 0.72,
      latency_ms: 350,
      created_at: '2026-03-14T11:00:00Z',
      user_name: null,
      search_strategy: 'similarity',
      synonym_expanded: false,
      related_entity: null,
      parsed_intent: null,
    },
  ],
  total: 2,
};

describe('HistoryTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('載入中顯示 spinner', () => {
    mockAiApi.listSearchHistory.mockReturnValue(new Promise(() => {}));
    render(<HistoryTab />, { wrapper: createWrapper() });
    expect(document.querySelector('.ant-spin')).toBeTruthy();
  });

  it('渲染搜尋歷史表格', async () => {
    mockAiApi.listSearchHistory.mockResolvedValue(mockHistoryData);
    render(<HistoryTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('桃園市公文')).toBeInTheDocument();
      expect(screen.getByText('派工進度查詢')).toBeInTheDocument();
    });
  });

  it('渲染表格欄位標題', async () => {
    mockAiApi.listSearchHistory.mockResolvedValue(mockHistoryData);
    render(<HistoryTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      // antd Table renders column headers as th elements
      const bodyText = document.body.textContent || '';
      expect(bodyText).toContain('查詢內容');
      expect(bodyText).toContain('結果數');
      expect(bodyText).toContain('來源');
      expect(bodyText).toContain('信心度');
      expect(bodyText).toContain('延遲');
    });
  });

  it('渲染篩選控制項', async () => {
    mockAiApi.listSearchHistory.mockResolvedValue(mockHistoryData);
    render(<HistoryTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜尋查詢內容')).toBeInTheDocument();
      expect(screen.getByText('清除歷史')).toBeInTheDocument();
    });
  });

  it('顯示使用者名稱或匿名', async () => {
    mockAiApi.listSearchHistory.mockResolvedValue(mockHistoryData);
    render(<HistoryTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('管理員')).toBeInTheDocument();
      expect(screen.getByText('匿名')).toBeInTheDocument();
    });
  });

  it('渲染信心度百分比', async () => {
    mockAiApi.listSearchHistory.mockResolvedValue(mockHistoryData);
    render(<HistoryTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('85%')).toBeInTheDocument();
      expect(screen.getByText('72%')).toBeInTheDocument();
    });
  });

  it('渲染延遲數值', async () => {
    mockAiApi.listSearchHistory.mockResolvedValue(mockHistoryData);
    render(<HistoryTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('120ms')).toBeInTheDocument();
      expect(screen.getByText('350ms')).toBeInTheDocument();
    });
  });

  it('顯示總筆數', async () => {
    mockAiApi.listSearchHistory.mockResolvedValue(mockHistoryData);
    render(<HistoryTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('共 2 筆')).toBeInTheDocument();
    });
  });

  it('空歷史不崩潰', async () => {
    mockAiApi.listSearchHistory.mockResolvedValue({ items: [], total: 0 });
    render(<HistoryTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Empty table renders without crash — filter controls are still present
      expect(screen.getByPlaceholderText('搜尋查詢內容')).toBeInTheDocument();
    });
  });
});

/**
 * AgentPerformanceTab 元件測試
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ── Mock setup (vi.hoisted) ──
const { mockAiApi } = vi.hoisted(() => ({
  mockAiApi: {
    getToolSuccessRates: vi.fn(),
    getAgentTraces: vi.fn(),
    getLearnedPatterns: vi.fn(),
    getPersistentLearnings: vi.fn(),
    getProactiveAlerts: vi.fn(),
    getDailyTrend: vi.fn(),
  },
}));

vi.mock('../../../../api/aiApi', () => ({
  aiApi: mockAiApi,
}));

// Mock recharts ResponsiveContainer (has sizing issues in test env)
vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) =>
      React.createElement('div', { 'data-testid': 'responsive-container' }, children),
  };
});

import { AgentPerformanceTab } from '../AgentPerformanceTab';

// ── Test data ──
const mockToolStats = {
  tools: [
    {
      tool_name: 'search_documents',
      total_calls: 120,
      success_count: 108,
      success_rate: 0.9,
      avg_latency_ms: 350,
      avg_result_count: 5.2,
    },
    {
      tool_name: 'get_statistics',
      total_calls: 45,
      success_count: 42,
      success_rate: 0.933,
      avg_latency_ms: 200,
      avg_result_count: 1.0,
    },
  ],
  degraded_tools: [],
  source: 'db+redis',
};

const mockTraces = {
  traces: [{ id: 1, route_type: 'llm' }, { id: 2, route_type: 'pattern' }],
  total_count: 2,
  route_distribution: { llm: 5, pattern: 3, chitchat: 2, rule: 1 },
};

const mockPatterns = {
  patterns: [
    {
      pattern_key: 'abc123',
      template: '{ORG}的{DOC_TYPE}有幾件',
      tool_sequence: ['search_documents', 'get_statistics'],
      hit_count: 15,
      success_rate: 1.0,
      avg_latency_ms: 280,
      score: 12.5,
    },
  ],
  total_count: 1,
};

const mockLearnings = {
  learnings: [
    { id: 1, type: 'preference', content: '使用者偏好簡短回答' },
  ],
  stats: {
    by_type: { preference: 3, entity: 5, tool_combo: 2 },
  },
};

const mockAlerts = {
  total_alerts: 3,
  by_severity: { warning: 2, info: 1 },
  by_type: { deadline: 2, data_quality: 1 },
  alerts: [
    { alert_type: 'deadline', severity: 'warning', title: '公文即將到期', message: '3 天內到期', entity_type: 'document', entity_id: 1, metadata: {} },
    { alert_type: 'deadline', severity: 'warning', title: '專案即將到期', message: '5 天內到期', entity_type: 'project', entity_id: 2, metadata: {} },
    { alert_type: 'data_quality', severity: 'info', title: '資料品質', message: '2 筆公文缺少主旨', entity_type: 'document', entity_id: null, metadata: {} },
  ],
};

const mockEmptyAlerts = {
  total_alerts: 0,
  by_severity: {},
  by_type: {},
  alerts: [],
};

const mockTrend = {
  trend: [
    { date: '2026-03-13', query_count: 15, avg_latency_ms: 320, avg_results: 4.2, avg_feedback: null },
    { date: '2026-03-14', query_count: 22, avg_latency_ms: 280, avg_results: 5.1, avg_feedback: 1.0 },
  ],
  days: 14,
};

// Helper to set all mocks to default resolved values
function setupDefaultMocks() {
  mockAiApi.getToolSuccessRates.mockResolvedValue(mockToolStats);
  mockAiApi.getAgentTraces.mockResolvedValue(mockTraces);
  mockAiApi.getLearnedPatterns.mockResolvedValue(mockPatterns);
  mockAiApi.getPersistentLearnings.mockResolvedValue(mockLearnings);
  mockAiApi.getProactiveAlerts.mockResolvedValue(mockEmptyAlerts);
  mockAiApi.getDailyTrend.mockResolvedValue(mockTrend);
}

// ── Helpers ──
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  Wrapper.displayName = 'TestWrapper';
  return Wrapper;
}

// ── Tests ──
describe('AgentPerformanceTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    mockAiApi.getToolSuccessRates.mockReturnValue(new Promise(() => {}));
    mockAiApi.getAgentTraces.mockReturnValue(new Promise(() => {}));
    mockAiApi.getLearnedPatterns.mockReturnValue(new Promise(() => {}));
    mockAiApi.getPersistentLearnings.mockReturnValue(new Promise(() => {}));
    mockAiApi.getProactiveAlerts.mockReturnValue(new Promise(() => {}));
    mockAiApi.getDailyTrend.mockReturnValue(new Promise(() => {}));

    render(<AgentPerformanceTab />, { wrapper: createWrapper() });
    expect(document.querySelector('.ant-spin-spinning')).toBeTruthy();
  });

  it('renders empty state when all APIs return null', async () => {
    mockAiApi.getToolSuccessRates.mockResolvedValue(null);
    mockAiApi.getAgentTraces.mockResolvedValue(null);
    mockAiApi.getLearnedPatterns.mockResolvedValue(null);
    mockAiApi.getPersistentLearnings.mockResolvedValue(null);
    mockAiApi.getProactiveAlerts.mockResolvedValue(null);
    mockAiApi.getDailyTrend.mockResolvedValue(null);

    render(<AgentPerformanceTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/無法取得 Agent 效能資料/)).toBeInTheDocument();
    });
  });

  it('renders tool success rates with stats cards', async () => {
    setupDefaultMocks();

    render(<AgentPerformanceTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Tool stats section renders
      expect(screen.getByText(/工具成功率/)).toBeInTheDocument();
      expect(screen.getByText('活躍工具數')).toBeInTheDocument();
      expect(screen.getByText('總呼叫次數')).toBeInTheDocument();
      expect(screen.getByText('平均成功率')).toBeInTheDocument();
    });
  });

  it('shows degraded tools warning', async () => {
    setupDefaultMocks();
    mockAiApi.getToolSuccessRates.mockResolvedValue({
      ...mockToolStats,
      degraded_tools: ['search_documents'],
    });

    render(<AgentPerformanceTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Warning banner should show degraded tool name
      const container = document.body;
      expect(container.textContent).toContain('降級工具');
      expect(container.textContent).toContain('search_documents');
    });
  });

  it('renders route distribution section', async () => {
    setupDefaultMocks();

    render(<AgentPerformanceTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('路由分佈')).toBeInTheDocument();
      expect(screen.getByText(/共 2 筆追蹤記錄/)).toBeInTheDocument();
    });
  });

  it('renders learning statistics', async () => {
    setupDefaultMocks();

    render(<AgentPerformanceTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('持久化學習統計')).toBeInTheDocument();
      expect(screen.getByText(/共 1 條活躍學習記錄/)).toBeInTheDocument();
    });
  });

  it('renders pattern table with correct data', async () => {
    setupDefaultMocks();

    render(<AgentPerformanceTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('學習模式 Top 30')).toBeInTheDocument();
      // Pattern template text
      expect(screen.getByText('{ORG}的{DOC_TYPE}有幾件')).toBeInTheDocument();
      // Tool tags
      expect(screen.getByText('search_documents')).toBeInTheDocument();
    });
  });

  it('calls all 6 API endpoints on mount', async () => {
    setupDefaultMocks();

    render(<AgentPerformanceTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(mockAiApi.getToolSuccessRates).toHaveBeenCalledTimes(1);
      expect(mockAiApi.getAgentTraces).toHaveBeenCalledWith({ limit: 100 });
      expect(mockAiApi.getLearnedPatterns).toHaveBeenCalledTimes(1);
      expect(mockAiApi.getPersistentLearnings).toHaveBeenCalledTimes(1);
      expect(mockAiApi.getProactiveAlerts).toHaveBeenCalledTimes(1);
      expect(mockAiApi.getDailyTrend).toHaveBeenCalledTimes(1);
    });
  });

  it('renders empty patterns table gracefully', async () => {
    setupDefaultMocks();
    mockAiApi.getLearnedPatterns.mockResolvedValue({ patterns: [], total_count: 0 });

    render(<AgentPerformanceTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('尚無學習模式')).toBeInTheDocument();
    });
  });

  it('renders proactive alerts panel when alerts exist', async () => {
    setupDefaultMocks();
    mockAiApi.getProactiveAlerts.mockResolvedValue(mockAlerts);

    render(<AgentPerformanceTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/主動警報/)).toBeInTheDocument();
      expect(screen.getByText('公文即將到期')).toBeInTheDocument();
      expect(screen.getByText('專案即將到期')).toBeInTheDocument();
    });
  });

  it('hides alerts panel when no alerts', async () => {
    setupDefaultMocks();
    mockAiApi.getProactiveAlerts.mockResolvedValue(mockEmptyAlerts);

    render(<AgentPerformanceTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/工具成功率/)).toBeInTheDocument();
    });

    expect(screen.queryByText(/主動警報/)).not.toBeInTheDocument();
  });
});

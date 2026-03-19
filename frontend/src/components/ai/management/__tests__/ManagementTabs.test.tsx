/**
 * AI Management Tabs 元件測試
 *
 * 測試 OverviewTab, ServiceMonitorTab, DataAnalyticsTab, ServiceStatusTab, DataPipelineTab
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ── Mock setup ──
const { mockAiApi } = vi.hoisted(() => ({
  mockAiApi: {
    getSearchStats: vi.fn(),
    checkHealth: vi.fn(),
    getEmbeddingStats: vi.fn(),
    getConfig: vi.fn(),
    getEntityStats: vi.fn(),
    runEmbeddingBatch: vi.fn(),
    getGraphStats: vi.fn(),
    triggerGraphIngest: vi.fn(),
  },
}));

vi.mock('../../../../api/aiApi', () => ({
  aiApi: mockAiApi,
}));

// Mock recharts
vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) =>
      React.createElement('div', { 'data-testid': 'chart' }, children),
  };
});

import { OverviewTab } from '../OverviewTab';
import { ServiceMonitorTab } from '../ServiceMonitorTab';
import { DataAnalyticsTab } from '../DataAnalyticsTab';
import { ServiceStatusTab } from '../ServiceStatusTab';
import { DataPipelineTab } from '../DataPipelineTab';

// ── Test data ──
const mockSearchStats = {
  total_searches: 150,
  today_searches: 12,
  avg_latency_ms: 320,
  rule_engine_hit_rate: 0.65,
  avg_confidence: 0.78,
  strategy_distribution: { keyword: 80, similarity: 50, hybrid: 20 },
  source_distribution: { rule_engine: 60, vector: 50, ai: 40 },
  entity_distribution: { dispatch_order: 30, project: 20 },
  top_queries: [
    { query: '工務局的函', count: 15, avg_results: 5.2 },
    { query: '桃園市政府', count: 10, avg_results: 3.1 },
  ],
  daily_trend: [
    { date: '2026-03-10', count: 8 },
    { date: '2026-03-11', count: 12 },
  ],
};

const mockHealth = {
  groq: { available: true, model: 'llama-3.3-70b' },
  ollama: { available: true, model: 'qwen3:4b' },
  rate_limit: {
    current_requests: 5,
    max_requests: 30,
    window_seconds: 60,
    can_proceed: true,
  },
};

const mockEmbeddingStats = {
  pgvector_enabled: true,
  total_documents: 100,
  with_embedding: 85,
  coverage_percent: 85.0,
};

const mockConfig = {
  enabled: true,
  providers: {
    groq: { model: 'llama-3.3-70b-versatile' },
    ollama: { model: 'qwen3:4b', url: 'http://localhost:11434' },
  },
  rate_limit: { max_requests: 30, window_seconds: 60 },
  cache: { enabled: true, ttl_summary: 3600, ttl_classify: 3600 },
};

// ── Helpers ──
function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  Wrapper.displayName = 'TestWrapper';
  return Wrapper;
}

// ── OverviewTab Tests ──
describe('OverviewTab', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('shows loading spinner while fetching', () => {
    mockAiApi.getSearchStats.mockReturnValue(new Promise(() => {}));
    render(<OverviewTab />, { wrapper: createWrapper() });
    expect(document.querySelector('.ant-spin')).toBeTruthy();
  });

  it('shows empty state when stats is null', async () => {
    mockAiApi.getSearchStats.mockResolvedValue(null);
    render(<OverviewTab />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('無法載入統計資料')).toBeInTheDocument();
    });
  });

  it('shows empty state when total_searches is 0', async () => {
    mockAiApi.getSearchStats.mockResolvedValue({ ...mockSearchStats, total_searches: 0 });
    render(<OverviewTab />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText(/尚無搜尋紀錄/)).toBeInTheDocument();
    });
  });

  it('renders statistics cards with data', async () => {
    mockAiApi.getSearchStats.mockResolvedValue(mockSearchStats);
    render(<OverviewTab />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('總搜尋次數')).toBeInTheDocument();
      expect(screen.getByText('今日搜尋')).toBeInTheDocument();
      expect(screen.getByText('規則引擎命中率')).toBeInTheDocument();
      expect(screen.getByText('平均回應時間')).toBeInTheDocument();
    });
  });

  it('renders distribution sections', async () => {
    mockAiApi.getSearchStats.mockResolvedValue(mockSearchStats);
    render(<OverviewTab />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('搜尋策略分佈')).toBeInTheDocument();
      expect(screen.getByText('解析來源分佈')).toBeInTheDocument();
    });
  });

  it('renders top queries table', async () => {
    mockAiApi.getSearchStats.mockResolvedValue(mockSearchStats);
    render(<OverviewTab />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('熱門查詢 Top 10')).toBeInTheDocument();
      expect(screen.getByText('工務局的函')).toBeInTheDocument();
    });
  });
});

// ── ServiceMonitorTab Tests ──
describe('ServiceMonitorTab', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('shows loading state', () => {
    mockAiApi.checkHealth.mockReturnValue(new Promise(() => {}));
    mockAiApi.getEmbeddingStats.mockReturnValue(new Promise(() => {}));
    mockAiApi.getConfig.mockResolvedValue(null);
    render(<ServiceMonitorTab />, { wrapper: createWrapper() });
    expect(document.querySelector('.ant-spin')).toBeTruthy();
  });

  it('renders pgvector status', async () => {
    mockAiApi.checkHealth.mockResolvedValue(mockHealth);
    mockAiApi.getEmbeddingStats.mockResolvedValue(mockEmbeddingStats);
    mockAiApi.getConfig.mockResolvedValue(mockConfig);
    render(<ServiceMonitorTab />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('pgvector')).toBeInTheDocument();
      // pgvector enabled renders Badge text "已啟用"
      const container = document.body.textContent ?? '';
      expect(container).toContain('已啟用');
    });
  });

  it('renders rate limit monitoring', async () => {
    mockAiApi.checkHealth.mockResolvedValue(mockHealth);
    mockAiApi.getEmbeddingStats.mockResolvedValue(mockEmbeddingStats);
    mockAiApi.getConfig.mockResolvedValue(mockConfig);
    render(<ServiceMonitorTab />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('Rate Limit 監控')).toBeInTheDocument();
      expect(screen.getByText('目前使用量')).toBeInTheDocument();
    });
  });

  it('renders AI config section', async () => {
    mockAiApi.checkHealth.mockResolvedValue(mockHealth);
    mockAiApi.getEmbeddingStats.mockResolvedValue(mockEmbeddingStats);
    mockAiApi.getConfig.mockResolvedValue(mockConfig);
    render(<ServiceMonitorTab />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('AI 服務配置')).toBeInTheDocument();
    });
  });

  it('shows pgvector disabled state', async () => {
    mockAiApi.checkHealth.mockResolvedValue(mockHealth);
    mockAiApi.getEmbeddingStats.mockResolvedValue({ ...mockEmbeddingStats, pgvector_enabled: false });
    mockAiApi.getConfig.mockResolvedValue(null);
    render(<ServiceMonitorTab />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('未啟用')).toBeInTheDocument();
    });
  });
});

// ── Wrapper Tab Tests ──
describe('DataAnalyticsTab', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders both OverviewTab and HistoryTab sections', async () => {
    mockAiApi.getSearchStats.mockResolvedValue(mockSearchStats);
    render(<DataAnalyticsTab />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('搜尋歷史明細')).toBeInTheDocument();
    });
  });
});

describe('ServiceStatusTab', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders OllamaManagement and ServiceMonitor sections', async () => {
    mockAiApi.checkHealth.mockResolvedValue(mockHealth);
    mockAiApi.getEmbeddingStats.mockResolvedValue(mockEmbeddingStats);
    mockAiApi.getConfig.mockResolvedValue(mockConfig);
    render(<ServiceStatusTab />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('系統監控與配置')).toBeInTheDocument();
    });
  });
});

describe('DataPipelineTab', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', () => {
    mockAiApi.getEmbeddingStats.mockResolvedValue(mockEmbeddingStats);
    mockAiApi.getEntityStats.mockResolvedValue(null);
    mockAiApi.getGraphStats.mockResolvedValue(null);
    render(<DataPipelineTab />, { wrapper: createWrapper() });
    // DataPipelineTab is a thin wrapper - just verify it mounts
    expect(document.body).toBeTruthy();
  });
});

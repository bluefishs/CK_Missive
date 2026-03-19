/**
 * Dashboard Components - Smoke & Basic Behavior Tests
 *
 * Tests: AIStatsPanel, SystemHealthDashboard
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

// ============================================================================
// Hoisted mocks (must be before vi.mock calls)
// ============================================================================

const { mockApiClient, mockAiApi } = vi.hoisted(() => ({
  mockApiClient: {
    get: vi.fn().mockResolvedValue(null),
    post: vi.fn().mockResolvedValue(null),
    put: vi.fn().mockResolvedValue(null),
    patch: vi.fn().mockResolvedValue(null),
    delete: vi.fn().mockResolvedValue(null),
  },
  mockAiApi: {
    getStats: vi.fn().mockResolvedValue(null),
    getSearchStats: vi.fn().mockResolvedValue(null),
    checkHealth: vi.fn().mockResolvedValue(null),
    getEmbeddingStats: vi.fn().mockResolvedValue(null),
  },
}));

// ============================================================================
// Mocks
// ============================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

// Mock Recharts to avoid SVG rendering issues in jsdom
vi.mock('recharts', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => null,
  Cell: () => null,
  Tooltip: () => null,
  Legend: () => null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
}));

vi.mock('../../api/client', () => ({
  apiClient: mockApiClient,
}));

vi.mock('../../api/aiApi', () => ({
  aiApi: mockAiApi,
}));

import { AIStatsPanel } from '../../components/dashboard/AIStatsPanel';
import { SystemHealthDashboard } from '../../components/dashboard/SystemHealthDashboard';

// ============================================================================
// Helpers
// ============================================================================

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
};

// ============================================================================
// AIStatsPanel Tests
// ============================================================================

describe('AIStatsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderWithProviders(<AIStatsPanel />);
    expect(document.body).toBeTruthy();
  });

  it('shows empty state when no stats available', async () => {
    mockAiApi.getStats.mockResolvedValue(null);
    renderWithProviders(<AIStatsPanel />);

    await waitFor(() => {
      expect(screen.getByText('AI 使用統計')).toBeInTheDocument();
    });
  });

  it('renders stats when data is available', async () => {
    mockAiApi.getStats.mockResolvedValue({
      total_requests: 42,
      rate_limit_hits: 3,
      groq_requests: 30,
      ollama_requests: 10,
      fallback_requests: 2,
      by_feature: {
        summary: { count: 20, cache_hits: 5, cache_misses: 15, total_latency_ms: 2000 },
        keywords: { count: 22, cache_hits: 8, cache_misses: 14, total_latency_ms: 1500 },
      },
    });
    mockAiApi.checkHealth.mockResolvedValue(null);
    mockAiApi.getSearchStats.mockResolvedValue(null);
    mockAiApi.getEmbeddingStats.mockResolvedValue(null);

    renderWithProviders(<AIStatsPanel />);

    await waitFor(() => {
      expect(screen.getByText('AI 使用統計')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText(/Groq:/)).toBeInTheDocument();
      expect(screen.getByText(/Ollama:/)).toBeInTheDocument();
    });
  });

  it('renders health status when available', async () => {
    mockAiApi.getStats.mockResolvedValue({
      total_requests: 10,
      rate_limit_hits: 0,
      groq_requests: 5,
      ollama_requests: 5,
      fallback_requests: 0,
      by_feature: {},
    });
    mockAiApi.checkHealth.mockResolvedValue({
      groq: { available: true },
      ollama: { available: false },
      rate_limit: { can_proceed: true, current_requests: 1, max_requests: 30 },
    });
    mockAiApi.getSearchStats.mockResolvedValue(null);
    mockAiApi.getEmbeddingStats.mockResolvedValue(null);

    renderWithProviders(<AIStatsPanel />);

    await waitFor(() => {
      expect(screen.getByText('AI 服務狀態')).toBeInTheDocument();
    });
  });
});

// ============================================================================
// SystemHealthDashboard Tests
// ============================================================================

describe('SystemHealthDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading spinner initially', () => {
    mockApiClient.post.mockReturnValue(new Promise(() => {})); // never resolves
    renderWithProviders(<SystemHealthDashboard />);
    expect(document.querySelector('.ant-spin')).toBeInTheDocument();
  });

  it('renders health data when available', async () => {
    mockApiClient.post.mockResolvedValue({
      timestamp: '2026-03-14T00:00:00Z',
      uptime: '5d 3h',
      overall_status: 'healthy',
      components: {
        database: { status: 'ok', response_ms: 5 },
        connection_pool: { status: 'ok', active: 3 },
        system: { status: 'ok', memory_percent: 45, cpu_percent: 12 },
      },
    });

    renderWithProviders(<SystemHealthDashboard />);

    await waitFor(() => {
      expect(screen.getByText('系統健康狀態')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText('服務狀態')).toBeInTheDocument();
      expect(screen.getByText('記憶體使用率')).toBeInTheDocument();
      expect(screen.getByText('資料庫活躍連線')).toBeInTheDocument();
      expect(screen.getByText('系統運行時間')).toBeInTheDocument();
    });
  });

  it('shows degraded status correctly', async () => {
    mockApiClient.post.mockResolvedValue({
      timestamp: '2026-03-14T00:00:00Z',
      uptime: '1h',
      overall_status: 'degraded',
      components: {
        system: { status: 'warning', memory_percent: 85, cpu_percent: 75 },
      },
      issues: ['High memory usage'],
    });

    renderWithProviders(<SystemHealthDashboard />);

    await waitFor(() => {
      expect(screen.getByText('警告')).toBeInTheDocument();
    });
  });

  it('renders refresh button', async () => {
    mockApiClient.post.mockResolvedValue({
      timestamp: '2026-03-14T00:00:00Z',
      uptime: '1h',
      overall_status: 'healthy',
      components: {},
    });

    renderWithProviders(<SystemHealthDashboard />);

    await waitFor(() => {
      expect(screen.getByText('重新整理')).toBeInTheDocument();
    });
  });

  it('renders data quality metrics when available', async () => {
    mockApiClient.post.mockResolvedValue({
      timestamp: '2026-03-14T00:00:00Z',
      uptime: '2h',
      overall_status: 'healthy',
      components: {
        system: { status: 'ok', memory_percent: 30, cpu_percent: 10 },
        data_quality: {
          status: 'ok',
          agency_fk: { sender_pct: 95, receiver_pct: 88 },
          ner_coverage_pct: 72,
        },
      },
    });

    renderWithProviders(<SystemHealthDashboard />);

    await waitFor(() => {
      expect(screen.getByText('發文機關 FK')).toBeInTheDocument();
      expect(screen.getByText('受文機關 FK')).toBeInTheDocument();
      expect(screen.getByText('NER 覆蓋率')).toBeInTheDocument();
    });
  });
});

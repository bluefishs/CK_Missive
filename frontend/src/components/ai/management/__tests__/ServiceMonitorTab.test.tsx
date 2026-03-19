/**
 * ServiceMonitorTab 元件測試
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const { mockAiApi } = vi.hoisted(() => ({
  mockAiApi: {
    checkHealth: vi.fn(),
    getEmbeddingStats: vi.fn(),
    getConfig: vi.fn(),
  },
}));

vi.mock('../../../../api/aiApi', () => ({
  aiApi: mockAiApi,
}));

import { ServiceMonitorTab } from '../ServiceMonitorTab';

// ── Test data ──
const mockHealth = {
  rate_limit: {
    current_requests: 15,
    max_requests: 100,
    window_seconds: 60,
  },
};

const mockEmbStats = {
  pgvector_enabled: true,
  total_documents: 200,
  with_embedding: 150,
  without_embedding: 50,
  coverage_percent: 75.0,
};

const mockConfig = {
  enabled: true,
  providers: {
    groq: { model: 'llama-3.3-70b-versatile' },
    ollama: { model: 'nomic-embed-text', url: 'http://localhost:11434' },
  },
  rate_limit: { max_requests: 100, window_seconds: 60 },
  cache: { enabled: true, ttl_summary: 3600, ttl_classify: 3600 },
};

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  Wrapper.displayName = 'TestWrapper';
  return Wrapper;
}

function setupMocks() {
  mockAiApi.checkHealth.mockResolvedValue(mockHealth);
  mockAiApi.getEmbeddingStats.mockResolvedValue(mockEmbStats);
  mockAiApi.getConfig.mockResolvedValue(mockConfig);
}

describe('ServiceMonitorTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('載入中顯示 spinner', () => {
    mockAiApi.checkHealth.mockReturnValue(new Promise(() => {}));
    mockAiApi.getEmbeddingStats.mockReturnValue(new Promise(() => {}));
    mockAiApi.getConfig.mockResolvedValue(null);
    render(<ServiceMonitorTab />, { wrapper: createWrapper() });
    expect(document.querySelector('.ant-spin')).toBeTruthy();
  });

  it('顯示 pgvector 狀態', async () => {
    setupMocks();
    render(<ServiceMonitorTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('pgvector')).toBeInTheDocument();
      // pgvector_enabled=true → Badge text "已啟用" and description "可用"
      expect(document.body.textContent).toContain('已啟用');
      expect(document.body.textContent).toContain('可用');
    });
  });

  it('pgvector 未啟用時顯示未啟用', async () => {
    setupMocks();
    mockAiApi.getEmbeddingStats.mockResolvedValue({ ...mockEmbStats, pgvector_enabled: false });
    render(<ServiceMonitorTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(document.body.textContent).toContain('未啟用');
      expect(document.body.textContent).toContain('不可用');
    });
  });

  it('顯示 Rate Limit 監控', async () => {
    setupMocks();
    render(<ServiceMonitorTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Rate Limit 監控')).toBeInTheDocument();
      expect(screen.getByText('目前使用量')).toBeInTheDocument();
      expect(screen.getByText('使用率')).toBeInTheDocument();
      expect(screen.getByText('時間窗口')).toBeInTheDocument();
    });
  });

  it('無 Rate Limit 時顯示空狀態', async () => {
    setupMocks();
    mockAiApi.checkHealth.mockResolvedValue({});
    render(<ServiceMonitorTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('無 Rate Limit 資訊')).toBeInTheDocument();
    });
  });

  it('顯示 AI 服務配置', async () => {
    setupMocks();
    render(<ServiceMonitorTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('AI 服務配置')).toBeInTheDocument();
      expect(screen.getByText('llama-3.3-70b-versatile')).toBeInTheDocument();
      expect(screen.getByText('nomic-embed-text')).toBeInTheDocument();
    });
  });

  it('重新整理按鈕觸發 refetch', async () => {
    setupMocks();
    const user = userEvent.setup();
    render(<ServiceMonitorTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Rate Limit 監控')).toBeInTheDocument();
    });

    await user.click(screen.getByText('重新整理'));

    await waitFor(() => {
      expect(mockAiApi.checkHealth).toHaveBeenCalledTimes(2);
    });
  });
});

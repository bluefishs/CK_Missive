/**
 * EmbeddingTab 元件測試
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const { mockAiApi, mockMessage } = vi.hoisted(() => {
  const msg = {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
    loading: vi.fn(),
    destroy: vi.fn(),
    open: vi.fn(),
    config: vi.fn(),
  };
  return {
    mockAiApi: {
      getEmbeddingStats: vi.fn(),
      runEmbeddingBatch: vi.fn(),
    },
    mockMessage: msg,
  };
});

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

import { EmbeddingTab } from '../EmbeddingTab';

// ── Test data ──
const mockEmbStats = {
  pgvector_enabled: true,
  total_documents: 200,
  with_embedding: 150,
  without_embedding: 50,
  coverage_percent: 75.0,
};

const mockFullCoverage = {
  pgvector_enabled: true,
  total_documents: 200,
  with_embedding: 200,
  without_embedding: 0,
  coverage_percent: 100.0,
};

const mockNoPgvector = {
  pgvector_enabled: false,
  total_documents: 200,
  with_embedding: 0,
  without_embedding: 200,
  coverage_percent: 0,
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

describe('EmbeddingTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('載入中顯示 spinner', () => {
    mockAiApi.getEmbeddingStats.mockReturnValue(new Promise(() => {}));
    render(<EmbeddingTab />, { wrapper: createWrapper() });
    expect(document.querySelector('.ant-spin')).toBeTruthy();
  });

  it('渲染統計卡片', async () => {
    mockAiApi.getEmbeddingStats.mockResolvedValue(mockEmbStats);
    render(<EmbeddingTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('公文總數')).toBeInTheDocument();
      expect(screen.getByText('已生成 Embedding')).toBeInTheDocument();
      expect(screen.getByText('未生成 Embedding')).toBeInTheDocument();
      expect(screen.getByText('覆蓋率')).toBeInTheDocument();
    });
  });

  it('渲染覆蓋率進度條', async () => {
    mockAiApi.getEmbeddingStats.mockResolvedValue(mockEmbStats);
    render(<EmbeddingTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Embedding 覆蓋率')).toBeInTheDocument();
      expect(screen.getByText(/150 \/ 200 筆公文已生成向量/)).toBeInTheDocument();
    });
  });

  it('pgvector 未啟用時顯示警告', async () => {
    mockAiApi.getEmbeddingStats.mockResolvedValue(mockNoPgvector);
    render(<EmbeddingTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(document.body.textContent).toContain('pgvector 未啟用');
    });
  });

  it('pgvector 未啟用時批次按鈕禁用', async () => {
    mockAiApi.getEmbeddingStats.mockResolvedValue(mockNoPgvector);
    render(<EmbeddingTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      const btn = screen.getByText('開始批次處理').closest('button');
      expect(btn).toBeDisabled();
    });
  });

  it('全覆蓋時批次按鈕禁用', async () => {
    mockAiApi.getEmbeddingStats.mockResolvedValue(mockFullCoverage);
    render(<EmbeddingTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      const btn = screen.getByText('開始批次處理').closest('button');
      expect(btn).toBeDisabled();
    });
  });

  it('渲染批次處理區塊', async () => {
    mockAiApi.getEmbeddingStats.mockResolvedValue(mockEmbStats);
    render(<EmbeddingTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('手動批次生成 Embedding')).toBeInTheDocument();
      expect(screen.getByText('每批處理筆數：')).toBeInTheDocument();
      expect(screen.getByText('開始批次處理')).toBeInTheDocument();
    });
  });

  it('重新整理按鈕觸發 refetch', async () => {
    mockAiApi.getEmbeddingStats.mockResolvedValue(mockEmbStats);
    const user = userEvent.setup();
    render(<EmbeddingTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('重新整理')).toBeInTheDocument();
    });

    await user.click(screen.getByText('重新整理'));

    await waitFor(() => {
      expect(mockAiApi.getEmbeddingStats).toHaveBeenCalledTimes(2);
    });
  });
});

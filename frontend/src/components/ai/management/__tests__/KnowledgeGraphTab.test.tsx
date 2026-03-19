/**
 * KnowledgeGraphTab 元件測試
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const { mockAiApi, mockMessage } = vi.hoisted(() => ({
  mockAiApi: {
    getEntityStats: vi.fn(),
    runEntityBatch: vi.fn(),
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

// Mock KnowledgeGraph component to avoid complex dependency chain
vi.mock('../../KnowledgeGraph', () => ({
  KnowledgeGraph: ({ documentIds, height }: { documentIds?: number[]; height?: number }) => (
    <div data-testid="knowledge-graph" data-doc-ids={JSON.stringify(documentIds)} data-height={height}>
      KnowledgeGraph Mock
    </div>
  ),
}));

import { KnowledgeGraphTab } from '../KnowledgeGraphTab';

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  Wrapper.displayName = 'TestWrapper';
  return Wrapper;
}

const mockEntityStats = {
  coverage_percent: 65.5,
  total_documents: 200,
  extracted_documents: 131,
  without_extraction: 69,
  total_entities: 450,
  total_relations: 320,
  entity_type_stats: {
    organization: 150,
    person: 100,
    location: 80,
    project: 120,
  },
};

describe('KnowledgeGraphTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('渲染查詢工具列', async () => {
    mockAiApi.getEntityStats.mockResolvedValue(mockEntityStats);
    render(<KnowledgeGraphTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('最近公文')).toBeInTheDocument();
      expect(screen.getByText('指定查詢')).toBeInTheDocument();
    });
  });

  it('渲染 KnowledgeGraph 子元件', async () => {
    mockAiApi.getEntityStats.mockResolvedValue(mockEntityStats);
    render(<KnowledgeGraphTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('knowledge-graph')).toBeInTheDocument();
    });
  });

  it('預設為自動模式', async () => {
    mockAiApi.getEntityStats.mockResolvedValue(mockEntityStats);
    render(<KnowledgeGraphTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/自動顯示最近 10 筆公文/)).toBeInTheDocument();
    });
  });

  it('渲染統計卡片', async () => {
    mockAiApi.getEntityStats.mockResolvedValue(mockEntityStats);
    render(<KnowledgeGraphTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('實體覆蓋率')).toBeInTheDocument();
      expect(screen.getByText('已提取公文')).toBeInTheDocument();
      expect(screen.getByText('提取實體')).toBeInTheDocument();
      expect(screen.getByText('提取關係')).toBeInTheDocument();
    });
  });

  it('渲染實體類型分佈標籤', async () => {
    mockAiApi.getEntityStats.mockResolvedValue(mockEntityStats);
    render(<KnowledgeGraphTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('實體類型分佈')).toBeInTheDocument();
      expect(screen.getByText(/organization: 150/)).toBeInTheDocument();
    });
  });

  it('空輸入時指定查詢禁用', async () => {
    mockAiApi.getEntityStats.mockResolvedValue(mockEntityStats);
    render(<KnowledgeGraphTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      const btn = screen.getByText('指定查詢').closest('button');
      expect(btn).toBeDisabled();
    });
  });

  it('輸入 ID 後可點擊指定查詢', async () => {
    mockAiApi.getEntityStats.mockResolvedValue(mockEntityStats);
    const user = userEvent.setup();
    render(<KnowledgeGraphTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/輸入公文 ID/)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/輸入公文 ID/);
    await user.type(input, '1,2,3');

    const btn = screen.getByText('指定查詢').closest('button');
    expect(btn).not.toBeDisabled();
  });

  it('渲染批次提取按鈕', async () => {
    mockAiApi.getEntityStats.mockResolvedValue(mockEntityStats);
    render(<KnowledgeGraphTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('批次提取')).toBeInTheDocument();
    });
  });

  it('無實體時顯示尚無提取資料', async () => {
    mockAiApi.getEntityStats.mockResolvedValue({
      ...mockEntityStats,
      entity_type_stats: {},
    });
    render(<KnowledgeGraphTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('尚無提取資料')).toBeInTheDocument();
    });
  });

  it('所有公文已提取時批次按鈕禁用', async () => {
    mockAiApi.getEntityStats.mockResolvedValue({
      ...mockEntityStats,
      without_extraction: 0,
    });
    render(<KnowledgeGraphTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      const btn = screen.getByText('批次提取').closest('button');
      expect(btn).toBeDisabled();
    });
  });
});

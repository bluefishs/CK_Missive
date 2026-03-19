/**
 * OllamaManagementTab 元件測試
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
    getOllamaStatus: vi.fn(),
    ensureOllamaModels: vi.fn(),
    warmupOllamaModels: vi.fn(),
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

vi.mock('../statusUtils', () => ({
  StatusIcon: ({ ok }: { ok: boolean }) => (
    <span data-testid="status-icon" data-ok={ok}>
      {ok ? '✓' : '✗'}
    </span>
  ),
}));

import { OllamaManagementTab } from '../OllamaManagementTab';

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  Wrapper.displayName = 'TestWrapper';
  return Wrapper;
}

const mockStatus = {
  available: true,
  groq_available: true,
  required_models_ready: true,
  message: 'Ollama 正常運行',
  groq_message: 'Groq API 正常',
  models: ['llama3.2:3b', 'nomic-embed-text:latest'],
  required_models: ['llama3.2:3b', 'nomic-embed-text:latest'],
  missing_models: [],
  gpu_info: {
    loaded_models: [
      { name: 'llama3.2:3b', size: 2000000000, size_vram: 1800000000 },
    ],
  },
};

describe('OllamaManagementTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('載入中顯示 spinner', () => {
    mockAiApi.getOllamaStatus.mockReturnValue(new Promise(() => {}));
    render(<OllamaManagementTab />, { wrapper: createWrapper() });
    expect(document.querySelector('.ant-spin')).toBeTruthy();
  });

  it('渲染 Ollama 連線狀態卡片', async () => {
    mockAiApi.getOllamaStatus.mockResolvedValue(mockStatus);
    render(<OllamaManagementTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Ollama')).toBeInTheDocument();
      expect(screen.getByText('Groq API')).toBeInTheDocument();
      expect(screen.getByText('必要模型')).toBeInTheDocument();
    });
  });

  it('Ollama 線上時顯示正確狀態', async () => {
    mockAiApi.getOllamaStatus.mockResolvedValue(mockStatus);
    render(<OllamaManagementTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(document.body.textContent).toContain('線上');
      expect(document.body.textContent).toContain('正常運作');
      expect(document.body.textContent).toContain('全部就緒');
    });
  });

  it('渲染已安裝模型列表', async () => {
    mockAiApi.getOllamaStatus.mockResolvedValue(mockStatus);
    render(<OllamaManagementTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/已安裝模型/)).toBeInTheDocument();
      // Model names may appear in multiple places (installed + GPU list)
      expect(screen.getAllByText('llama3.2:3b').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('nomic-embed-text:latest').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('渲染 GPU 載入模型區塊', async () => {
    mockAiApi.getOllamaStatus.mockResolvedValue(mockStatus);
    render(<OllamaManagementTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/GPU 載入模型/)).toBeInTheDocument();
    });
  });

  it('渲染管理動作區塊', async () => {
    mockAiApi.getOllamaStatus.mockResolvedValue(mockStatus);
    render(<OllamaManagementTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('管理動作')).toBeInTheDocument();
      expect(screen.getByText('檢查並拉取模型')).toBeInTheDocument();
      expect(screen.getByText('預熱模型')).toBeInTheDocument();
    });
  });

  it('Ollama 離線時顯示離線狀態', async () => {
    mockAiApi.getOllamaStatus.mockResolvedValue({
      ...mockStatus,
      available: false,
      message: 'Ollama 無法連線',
    });
    render(<OllamaManagementTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(document.body.textContent).toContain('離線');
    });
  });

  it('有缺少模型時顯示警告', async () => {
    mockAiApi.getOllamaStatus.mockResolvedValue({
      ...mockStatus,
      required_models_ready: false,
      missing_models: ['nomic-embed-text:latest'],
    });
    render(<OllamaManagementTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(document.body.textContent).toContain('nomic-embed-text:latest');
      expect(document.body.textContent).toContain('有缺少模型');
    });
  });

  it('Ollama 離線時按鈕禁用', async () => {
    mockAiApi.getOllamaStatus.mockResolvedValue({
      ...mockStatus,
      available: false,
    });
    render(<OllamaManagementTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      const pullBtn = screen.getByText('檢查並拉取模型').closest('button');
      expect(pullBtn).toBeDisabled();
      const warmupBtn = screen.getByText('預熱模型').closest('button');
      expect(warmupBtn).toBeDisabled();
    });
  });

  it('渲染重新整理按鈕', async () => {
    mockAiApi.getOllamaStatus.mockResolvedValue(mockStatus);
    render(<OllamaManagementTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('重新整理')).toBeInTheDocument();
    });
  });

  it('API 錯誤時顯示錯誤訊息', async () => {
    mockAiApi.getOllamaStatus.mockRejectedValue(new Error('fail'));
    render(<OllamaManagementTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(document.body.textContent).toContain('Ollama 狀態取得失敗');
    });
  });

  it('null 狀態顯示空狀態', async () => {
    mockAiApi.getOllamaStatus.mockResolvedValue(null);
    render(<OllamaManagementTab />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('無法取得 Ollama 狀態')).toBeInTheDocument();
    });
  });
});

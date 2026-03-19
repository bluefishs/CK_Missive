/**
 * DocumentEditPage Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate, useParams: () => ({ id: '1' }) };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false, isTablet: false, isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({ id: 1, doc_number: 'DOC-001', subject: 'Test', doc_type: '收文' }),
  },
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    DOCUMENTS: {
      DETAIL: vi.fn(() => '/documents/1'),
      UPDATE: vi.fn(() => '/documents/1/update'),
    },
  },
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>{ui}</MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

describe('DocumentEditPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/DocumentEditPage');
    renderWithProviders(<mod.DocumentEditPage />);
    // After data loads, should show the edit form
    await waitFor(() => {
      const el = screen.queryByText(/編輯公文|公文基本資訊|返回列表|返回/)
        || document.querySelector('.ant-spin');
      expect(el).not.toBeNull();
    }, { timeout: 3000 });
  });
});

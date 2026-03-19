/**
 * WorkRecordFormPage Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ dispatchId: '1', recordId: '2' }),
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/taoyuan', () => ({
  workflowApi: {
    getById: vi.fn().mockResolvedValue({ data: {} }),
    list: vi.fn().mockResolvedValue({ data: [] }),
    create: vi.fn().mockResolvedValue({ data: { id: 1 } }),
    update: vi.fn().mockResolvedValue({ data: { id: 1 } }),
  },
}));

vi.mock('../../api/taoyuanDispatchApi', () => ({
  dispatchOrdersApi: {
    getById: vi.fn().mockResolvedValue({ data: { id: 1, dispatch_number: 'D001' } }),
    list: vi.fn().mockResolvedValue({ data: [] }),
  },
}));

vi.mock('../../api/client', () => ({
  apiClient: {
    post: vi.fn().mockResolvedValue({ data: { data: [] } }),
    get: vi.fn().mockResolvedValue({ data: { data: [] } }),
  },
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    DOCUMENTS_ENDPOINTS: { LIST: '/documents/list' },
  },
  DOCUMENTS_ENDPOINTS: { LIST: '/documents/list' },
}));

vi.mock('../../types/api', () => ({
  isReceiveDocument: vi.fn(() => true),
}));

vi.mock('../../hooks', () => ({
  useResponsive: () => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  }),
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

describe('WorkRecordFormPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/WorkRecordFormPage');
    const Component = mod.default;
    const { unmount } = renderWithProviders(<Component />);
    await waitFor(() => {
      expect(document.body).toBeTruthy();
    }, { timeout: 8000 });
    unmount();
  });
});

/**
 * ReportsPage Smoke Test
 */
import { describe, it, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate, useParams: () => ({}) };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../hooks')>();
  return {
    ...actual,
    useResponsive: () => ({
      isMobile: false,
      responsiveValue: ({ desktop }: { desktop: unknown }) => desktop,
    }),
    usePMCaseSummary: () => ({ data: null, isLoading: false }),
    useERPProfitSummary: () => ({ data: null, isLoading: false }),
  };
});

vi.mock('../../api', () => ({
  documentsApi: {
    getList: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    getStatistics: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../../api/client', () => ({
  API_BASE_URL: 'http://localhost:8001/api',
  apiClient: {
    post: vi.fn().mockResolvedValue({ data: {} }),
    get: vi.fn().mockResolvedValue({ data: {} }),
  },
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {},
  DOCUMENTS_ENDPOINTS: {},
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

describe('ReportsPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', { timeout: 15000 }, async () => {
    const mod = await import('../../pages/ReportsPage');
    const Component = mod.default;
    const { unmount } = renderWithProviders(<Component />);
    // Unmount to prevent hanging API calls from incomplete mocks
    unmount();
  });
});

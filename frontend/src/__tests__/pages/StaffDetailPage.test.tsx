/**
 * StaffDetailPage Smoke Test
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
  return { ...actual, useNavigate: () => mockNavigate, useParams: () => ({ id: '1' }) };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/client', () => ({
  apiClient: {
    post: vi.fn().mockResolvedValue({ data: {} }),
    get: vi.fn().mockResolvedValue({ data: {} }),
  },
  SERVER_BASE_URL: 'http://localhost:8001',
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    STAFF_DETAIL: '/staff/detail',
  },
}));

vi.mock('../../api/certificationsApi', () => ({
  certificationsApi: {
    list: vi.fn().mockResolvedValue([]),
    create: vi.fn().mockResolvedValue({ id: 1 }),
    delete: vi.fn().mockResolvedValue({ success: true }),
  },
  Certification: {},
}));

vi.mock('../../router/types', () => ({
  ROUTES: { STAFF: '/staff', STAFF_EDIT: '/staff/:id/edit' },
}));

vi.mock('../../hooks', () => ({
  useResponsive: () => ({
    isMobile: false,
    responsiveValue: ({ desktop }: { desktop: unknown }) => desktop,
  }),
}));

vi.mock('../../hooks/system', () => ({
  useDepartments: () => ({ data: ['工程部', '行政部'], isLoading: false }),
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

describe('StaffDetailPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/StaffDetailPage');
    const Component = mod.StaffDetailPage || mod.default;
    renderWithProviders(<Component />);
  });
});

/**
 * TaoyuanDispatchCreatePage Smoke Test
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
    useParams: () => ({ id: '1' }),
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/taoyuanDispatchApi', () => ({
  dispatchOrdersApi: {
    create: vi.fn().mockResolvedValue({ data: { id: 1 } }),
    list: vi.fn().mockResolvedValue({ data: [] }),
  },
  taoyuanProjectsApi: {
    list: vi.fn().mockResolvedValue({ data: [] }),
  },
  contractPaymentsApi: {
    list: vi.fn().mockResolvedValue({ data: [] }),
  },
}));

vi.mock('../../api/documentsApi', () => ({
  documentsApi: {
    list: vi.fn().mockResolvedValue({ data: [] }),
  },
}));

vi.mock('../../api/projectAgencyContacts', () => ({
  getProjectAgencyContacts: vi.fn().mockResolvedValue({ data: [] }),
}));

vi.mock('../../api/projectVendorsApi', () => ({
  projectVendorsApi: {
    list: vi.fn().mockResolvedValue({ data: [] }),
  },
}));

vi.mock('../../hooks', () => ({
  useResponsive: () => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  }),
  useTaoyuanContractProjects: vi.fn(() => ({ data: [], isLoading: false })),
}));

vi.mock('../../constants/taoyuanOptions', () => ({
  TAOYUAN_CONTRACT: { PROJECT_ID: 21, CODE: 'CK2025_01_03_001', NAME: 'Test' },
  CASE_TYPE_OPTIONS: [],
  DISTRICT_OPTIONS: [],
}));

vi.mock('../../components/taoyuan/DispatchFormFields', () => ({
  DispatchFormFields: () => <div data-testid="mock-dispatch-form-fields">DispatchFormFields</div>,
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

describe('TaoyuanDispatchCreatePage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/TaoyuanDispatchCreatePage');
    const Component = mod.TaoyuanDispatchCreatePage || mod.default;
    renderWithProviders(<Component />);
    await waitFor(() => {
      expect(document.body).toBeTruthy();
    });
  });
});

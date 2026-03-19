/**
 * TaoyuanProjectCreatePage Smoke Test
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
  return { ...actual, useNavigate: () => mockNavigate, useParams: () => ({ id: '1' }) };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/taoyuanDispatchApi', () => ({
  taoyuanProjectsApi: {
    create: vi.fn().mockResolvedValue({ data: { id: 1 } }),
    list: vi.fn().mockResolvedValue({ data: [] }),
  },
  dispatchOrdersApi: {
    list: vi.fn().mockResolvedValue({ data: [] }),
  },
  contractPaymentsApi: {
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
}));

vi.mock('../../constants/taoyuanOptions', () => ({
  TAOYUAN_CONTRACT: { PROJECT_ID: 21, CODE: 'CK2025_01_03_001', NAME: 'Test' },
  CASE_TYPE_OPTIONS: [],
  DISTRICT_OPTIONS: [],
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

describe('TaoyuanProjectCreatePage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/TaoyuanProjectCreatePage');
    const Component = mod.TaoyuanProjectCreatePage || mod.default;
    renderWithProviders(<Component />);
    await waitFor(() => {
      expect(document.body).toBeTruthy();
    });
  });
});

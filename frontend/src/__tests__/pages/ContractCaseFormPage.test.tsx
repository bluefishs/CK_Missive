/**
 * ContractCaseFormPage Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
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

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false, isTablet: false, isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

vi.mock('../../api/projectsApi', () => ({
  projectsApi: { getById: vi.fn().mockResolvedValue(null), create: vi.fn().mockResolvedValue({ id: 1 }) },
}));

vi.mock('../../api/agenciesApi', () => ({
  agenciesApi: { search: vi.fn().mockResolvedValue([]), getList: vi.fn().mockResolvedValue({ items: [] }) },
}));

vi.mock('../../api/vendorsApi', () => ({
  vendorsApi: { getList: vi.fn().mockResolvedValue({ items: [] }) },
}));

vi.mock('../../api/usersApi', () => ({
  usersApi: { getList: vi.fn().mockResolvedValue({ items: [] }) },
}));

vi.mock('../../router/types', () => ({
  ROUTES: { CONTRACT_CASES: '/contract-case', CONTRACT_CASE_DETAIL: '/contract-case/:id' },
}));

vi.mock('../../config/queryConfig', () => ({
  queryKeys: { projects: { all: ['projects'] } },
}));

vi.mock('../../pages/contractCase/tabs/constants', () => ({
  CATEGORY_OPTIONS: [{ value: 'A', label: 'A' }],
  CASE_NATURE_OPTIONS: [{ value: 'B', label: 'B' }],
  STATUS_OPTIONS: [{ value: 'in_progress', label: '執行中' }],
}));

vi.mock('../../pages/contractCase/AddAgencyModal', () => ({
  AddAgencyModal: () => null,
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

describe('ContractCaseFormPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing in create mode', async () => {
    const mod = await import('../../pages/ContractCaseFormPage');
    renderWithProviders(<mod.ContractCaseFormPage />);
    expect(screen.getByText(/新增承攬案件|承攬案件/)).toBeInTheDocument();
  });
});

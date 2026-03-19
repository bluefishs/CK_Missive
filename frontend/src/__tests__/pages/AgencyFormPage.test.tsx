/**
 * AgencyFormPage Smoke Test
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

vi.mock('../../api', () => ({
  agenciesApi: {
    getById: vi.fn().mockResolvedValue(null),
    create: vi.fn().mockResolvedValue({ id: 1 }),
    update: vi.fn().mockResolvedValue({ id: 1 }),
    delete: vi.fn().mockResolvedValue({ success: true }),
  },
}));

vi.mock('../../router/types', () => ({
  ROUTES: { AGENCIES: '/agencies' },
}));

vi.mock('../../constants', () => ({
  AGENCY_CATEGORY_OPTIONS: [
    { value: '政府機關', label: '政府機關' },
    { value: '民間企業', label: '民間企業' },
  ],
}));

vi.mock('../../components/common/FormPage', () => ({
  FormPageLayout: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div data-testid="form-page-layout"><h1>{title}</h1>{children}</div>
  ),
}));

vi.mock('../../components/common/ResponsiveFormRow', () => ({
  ResponsiveFormRow: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
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

describe('AgencyFormPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing in create mode', async () => {
    const mod = await import('../../pages/AgencyFormPage');
    renderWithProviders(<mod.AgencyFormPage />);
    expect(screen.getByTestId('form-page-layout')).toBeInTheDocument();
  });
});

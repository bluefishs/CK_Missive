/**
 * StaffCreatePage Smoke Test
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

vi.mock('../../api/client', () => ({
  apiClient: {
    post: vi.fn().mockResolvedValue({ data: {} }),
    get: vi.fn().mockResolvedValue({ data: {} }),
  },
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    STAFF_CREATE: '/staff/create',
  },
}));

vi.mock('../../router/types', () => ({
  ROUTES: { STAFF: '/staff' },
}));

vi.mock('../../hooks/system', () => ({
  useDepartments: () => ({ data: ['工程部', '行政部'], isLoading: false }),
}));

vi.mock('../../components/common/FormPage', () => ({
  FormPageLayout: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div data-testid="form-page-layout"><h1>{title}</h1>{children}</div>
  ),
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

describe('StaffCreatePage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/StaffCreatePage');
    const Component = mod.StaffCreatePage || mod.default;
    renderWithProviders(<Component />);
    expect(screen.getByTestId('form-page-layout')).toBeInTheDocument();
  });
});

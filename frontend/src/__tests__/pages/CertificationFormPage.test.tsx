/**
 * CertificationFormPage Smoke Test
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
  return { ...actual, useNavigate: () => mockNavigate, useParams: () => ({ userId: '1' }) };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/certificationsApi', () => ({
  certificationsApi: {
    getById: vi.fn().mockResolvedValue(null),
    create: vi.fn().mockResolvedValue({ id: 1 }),
    update: vi.fn().mockResolvedValue({ id: 1 }),
    delete: vi.fn().mockResolvedValue({ success: true }),
    getByStaff: vi.fn().mockResolvedValue([]),
  },
  CERT_TYPES: [{ value: 'professional', label: '專業證照' }],
  CERT_STATUS: [{ value: 'valid', label: '有效' }],
}));

vi.mock('../../api/client', () => ({
  apiClient: { get: vi.fn().mockResolvedValue({}), post: vi.fn().mockResolvedValue({}) },
  SERVER_BASE_URL: 'http://localhost:8001',
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

describe('CertificationFormPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/CertificationFormPage');
    renderWithProviders(<mod.CertificationFormPage />);
    expect(screen.getByTestId('form-page-layout')).toBeInTheDocument();
  });
});

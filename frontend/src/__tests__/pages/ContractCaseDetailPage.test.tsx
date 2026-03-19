/**
 * ContractCaseDetailPage Smoke Test
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

vi.mock('../../api/projectsApi', () => ({
  projectsApi: {
    getById: vi.fn().mockResolvedValue({
      id: 1, project_name: 'Test', project_code: 'P-001', status: 'in_progress',
      year: 2026, created_at: '2026-01-01T00:00:00Z',
    }),
  },
}));

vi.mock('../../api/usersApi', () => ({
  usersApi: { getList: vi.fn().mockResolvedValue({ items: [], pagination: { total: 0 } }) },
}));

vi.mock('../../api/vendorsApi', () => ({
  vendorsApi: { getList: vi.fn().mockResolvedValue({ items: [], pagination: { total: 0 } }) },
}));

vi.mock('../../api/documentsApi', () => ({
  documentsApi: { getList: vi.fn().mockResolvedValue({ items: [], pagination: { total: 0 } }) },
}));

vi.mock('../../api/filesApi', () => ({
  filesApi: { getByEntity: vi.fn().mockResolvedValue([]) },
  FileAttachment: {},
}));

vi.mock('../../api/projectStaffApi', () => ({
  projectStaffApi: { getByProject: vi.fn().mockResolvedValue([]) },
}));

vi.mock('../../api/projectVendorsApi', () => ({
  projectVendorsApi: { getByProject: vi.fn().mockResolvedValue([]) },
}));

vi.mock('../../api/projectAgencyContacts', () => ({
  getProjectAgencyContacts: vi.fn().mockResolvedValue([]),
  createAgencyContact: vi.fn(),
  updateAgencyContact: vi.fn(),
  deleteAgencyContact: vi.fn(),
}));

vi.mock('../../router/types', () => ({
  ROUTES: {
    CONTRACT_CASES: '/contract-case',
    CONTRACT_CASE_EDIT: '/contract-case/:id/edit',
  },
}));

vi.mock('../../config/queryConfig', () => ({
  queryKeys: { projects: { all: ['projects'] } },
}));

vi.mock('../../pages/contractCase/DetailPageHeader', () => ({
  DetailPageHeader: ({ title }: { title?: string }) => (
    <div data-testid="mock-detail-header">{title || 'DetailHeader'}</div>
  ),
}));

vi.mock('../../pages/contractCase/tabs', () => ({
  CaseInfoTab: () => <div>CaseInfoTab</div>,
  AgencyContactTab: () => <div>AgencyContactTab</div>,
  StaffTab: () => <div>StaffTab</div>,
  VendorsTab: () => <div>VendorsTab</div>,
  AttachmentsTab: () => <div>AttachmentsTab</div>,
  RelatedDocumentsTab: () => <div>RelatedDocumentsTab</div>,
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

describe('ContractCaseDetailPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/ContractCaseDetailPage');
    renderWithProviders(<mod.ContractCaseDetailPage />);
    await waitFor(() => {
      // Page renders either the detail view or "案件不存在" when data doesn't match
      const el = screen.queryByTestId('mock-detail-header')
        || screen.queryByText(/承攬案件|案件不存在|載入/);
      expect(el).not.toBeNull();
    });
  });
});

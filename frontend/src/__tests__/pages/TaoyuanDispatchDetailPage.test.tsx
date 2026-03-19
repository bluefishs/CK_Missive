/**
 * TaoyuanDispatchDetailPage Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

// Dynamic import needs a longer timeout for module resolution in full test suite
const WAIT_OPTS = { timeout: 8000 };

// ==========================================================================
// Mocks
// ==========================================================================

const mockNavigate = vi.fn();
const mockSetSearchParams = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: '1' }),
    useSearchParams: () => [new URLSearchParams(), mockSetSearchParams],
  };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../hooks', () => ({
  useAuthGuard: () => ({
    hasPermission: vi.fn(() => true),
  }),
  useResponsive: () => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  }),
}));

const mockDispatch = {
  id: 1,
  dispatch_no: 'D-2026-001',
  project_name: 'Test Project',
  work_type: '01, 02',
  sub_case_name: 'Sub Case',
  deadline: '2026-12-31',
  case_handler: 'Handler',
  survey_unit: 'Unit',
  contact_note: 'Note',
  cloud_folder: '',
  project_folder: '',
  batch_no: null,
  linked_projects: [],
  linked_documents: [],
};

vi.mock('../../hooks/taoyuan/useDispatchQueries', () => ({
  useDispatchQueries: vi.fn(() => ({
    dispatch: mockDispatch,
    isLoading: false,
    refetch: vi.fn(),
    agencyContacts: [],
    projectVendors: [],
    availableProjects: [],
    linkedProjectIds: [],
    filteredProjects: [],
    attachments: [],
    refetchAttachments: vi.fn(),
    paymentData: null,
    refetchPayment: vi.fn(),
  })),
}));

vi.mock('../../hooks/taoyuan/useDispatchMutations', () => ({
  useDispatchMutations: vi.fn(() => ({
    paymentMutation: { mutate: vi.fn(), isPending: false },
    updateMutation: { mutateAsync: vi.fn(), isPending: false },
    deleteMutation: { mutate: vi.fn(), isPending: false },
    linkProjectMutation: { mutate: vi.fn(), isPending: false },
    createProjectMutation: { mutate: vi.fn(), isPending: false },
    unlinkProjectMutation: { mutate: vi.fn(), isPending: false },
    uploadAttachmentsMutation: { mutate: vi.fn(), isPending: false },
    deleteAttachmentMutation: { mutate: vi.fn(), isPending: false },
  })),
}));

vi.mock('./taoyuanDispatch/DispatchDetailHeader', () => ({
  buildDispatchDetailHeader: vi.fn(() => ({
    title: 'D-2026-001',
    backPath: '/taoyuan-dispatch',
  })),
}));

vi.mock('../../pages/taoyuanDispatch/DispatchDetailHeader', () => ({
  buildDispatchDetailHeader: vi.fn(() => ({
    title: 'D-2026-001',
    backPath: '/taoyuan-dispatch',
  })),
}));

vi.mock('../../pages/taoyuanDispatch/tabs', () => ({
  DispatchInfoTab: () => <div data-testid="dispatch-info-tab">DispatchInfoTab</div>,
  DispatchProjectsTab: () => <div data-testid="dispatch-projects-tab">DispatchProjectsTab</div>,
  DispatchAttachmentsTab: () => <div data-testid="dispatch-attachments-tab">DispatchAttachmentsTab</div>,
  DispatchPaymentTab: () => <div data-testid="dispatch-payment-tab">DispatchPaymentTab</div>,
  DispatchWorkflowTab: () => <div data-testid="dispatch-workflow-tab">DispatchWorkflowTab</div>,
}));

vi.mock('../../pages/taoyuanDispatch/tabs/paymentUtils', () => ({
  parseWorkTypeCodes: vi.fn(() => []),
  validatePaymentConsistency: vi.fn(() => []),
}));

vi.mock('../../components/common/DetailPage', () => ({
  DetailPageLayout: ({ loading, hasData }: { loading: boolean; hasData: boolean }) => (
    <div data-testid="detail-page-layout">
      {loading && <div data-testid="loading">Loading...</div>}
      {hasData && <div data-testid="has-data">Data loaded</div>}
    </div>
  ),
  createTabItem: vi.fn((_key: string, _label: unknown, children: React.ReactNode) => ({
    key: _key,
    children,
  })),
}));

// ==========================================================================
// Helpers
// ==========================================================================

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

// ==========================================================================
// Tests
// ==========================================================================

describe('TaoyuanDispatchDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/TaoyuanDispatchDetailPage');
    const Component = mod.TaoyuanDispatchDetailPage || mod.default;
    renderWithProviders(<Component />);
    await waitFor(() => {
      expect(document.body).toBeTruthy();
    }, WAIT_OPTS);
  });

  it('renders the detail page layout', async () => {
    const mod = await import('../../pages/TaoyuanDispatchDetailPage');
    const Component = mod.TaoyuanDispatchDetailPage || mod.default;
    const { getByTestId } = renderWithProviders(<Component />);
    await waitFor(() => {
      expect(getByTestId('detail-page-layout')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('shows data loaded state when dispatch is available', async () => {
    const mod = await import('../../pages/TaoyuanDispatchDetailPage');
    const Component = mod.TaoyuanDispatchDetailPage || mod.default;
    const { getByTestId } = renderWithProviders(<Component />);
    await waitFor(() => {
      expect(getByTestId('has-data')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('shows loading state when data is loading', async () => {
    const { useDispatchQueries } = await import('../../hooks/taoyuan/useDispatchQueries');
    vi.mocked(useDispatchQueries).mockReturnValue({
      dispatch: undefined,
      isLoading: true,
      refetch: vi.fn(),
      agencyContacts: [],
      projectVendors: [],
      availableProjects: [],
      linkedProjectIds: [],
      filteredProjects: [],
      attachments: [],
      refetchAttachments: vi.fn(),
      paymentData: null,
      refetchPayment: vi.fn(),
    } as ReturnType<typeof useDispatchQueries>);

    const mod = await import('../../pages/TaoyuanDispatchDetailPage');
    const Component = mod.TaoyuanDispatchDetailPage || mod.default;
    const { getByTestId } = renderWithProviders(<Component />);
    await waitFor(() => {
      expect(getByTestId('loading')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

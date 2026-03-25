/**
 * PMCaseDetailPage Tests
 *
 * Tests for the PM case detail page including:
 * - Loading spinner display
 * - Case not found display
 * - Case details with tabs
 * - Milestones tab rendering
 * - Staff tab rendering
 * - Back navigation
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/PMCaseDetailPage.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

const WAIT_OPTS = { timeout: 5000 };

// ==========================================================================
// Mocks
// ==========================================================================

const mockNavigate = vi.fn();
const mockParams: Record<string, string> = { id: '1' };
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => mockParams,
  };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({}),
    put: vi.fn().mockResolvedValue({}),
    patch: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue({}),
  },
}));

const mockUsePMCase = vi.fn((): { data: Record<string, unknown> | null | undefined; isLoading: boolean } => ({
  data: {
    id: 1,
    case_code: 'CK2025_PM_01_001',
    case_name: '桃園測量案',
    year: 114,
    category: '01',
    client_name: '桃園市政府',
    client_contact: '王先生',
    client_phone: '03-1234567',
    contract_amount: '1500000',
    status: 'in_progress' as const,
    progress: 55,
    start_date: '2025-01-15',
    end_date: '2025-12-31',
    actual_end_date: null,
    location: '桃園市中壢區',
    description: '測量專案',
    notes: '備註資訊',
    milestone_count: 3,
    staff_count: 5,
    created_by: 1,
    created_at: '2025-01-01',
    updated_at: '2025-01-15',
  },
  isLoading: false,
}));

vi.mock('../../hooks', () => ({
  useAuthGuard: () => ({ hasPermission: () => true }),
  useResponsive: () => ({ isMobile: false, isTablet: false, isDesktop: true, breakpoint: 'lg' }),
  usePMCase: (..._args: unknown[]) => mockUsePMCase(),
  useCrossModuleLookup: () => ({ data: null, isLoading: false }),
  useProjectFinancialSummary: () => ({ data: null, isLoading: false }),
  useExpenses: () => ({ data: null, isLoading: false }),
}));

vi.mock('../../api/projectsApi', () => ({
  projectsApi: {
    getProjects: vi.fn().mockResolvedValue({ items: [], pagination: { total: 0 } }),
  },
}));

vi.mock('../../pages/ContractCaseDetailPage', () => ({
  ContractCaseDetailContent: () => <div data-testid="mock-shared-template">SharedTemplate</div>,
}));

vi.mock('../../hooks/business/useDropdownData', () => ({
  useClientOptions: () => ({ clients: [{ id: 1, vendor_name: '測試委託單位' }], isLoading: false }),
}));

vi.mock('../../api/vendorsApi', () => ({
  vendorsApi: { createVendor: vi.fn() },
}));

vi.mock('../../api/pm/casesApi', () => ({
  pmCasesApi: { update: vi.fn(), delete: vi.fn() },
}));

vi.mock('../../pages/pmCase/MilestonesGanttTab', () => ({
  default: ({ pmCaseId }: { pmCaseId: number }) => (
    <div data-testid="mock-milestones-tab">MilestonesGanttTab (caseId: {pmCaseId})</div>
  ),
}));
vi.mock('../../pages/pmCase/StaffTab', () => ({
  default: ({ caseCode }: { caseCode: string }) => (
    <div data-testid="mock-staff-tab">StaffTab (caseCode: {caseCode})</div>
  ),
}));
vi.mock('../../pages/pmCase/QuotationRecordsTab', () => ({
  default: ({ caseCode }: { caseCode: string }) => (
    <div data-testid="mock-quotation-tab">QuotationRecordsTab (caseCode: {caseCode})</div>
  ),
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <PageWrapper />
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function PageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/PMCaseDetailPage').then((mod) => {
      setPage(() => mod.PMCaseDetailPage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('PMCaseDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockParams.id = '1';
  });

  it('renders loading spinner when data is loading', async () => {
    mockUsePMCase.mockReturnValueOnce({ data: undefined, isLoading: true });
    renderPage();
    await waitFor(() => {
      // Page shows <Spin> without text when loading
      expect(document.querySelector('.ant-spin')).toBeTruthy();
    }, WAIT_OPTS);
  });

  it('renders case not found when data is null', async () => {
    mockUsePMCase.mockReturnValueOnce({ data: null, isLoading: false });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('案件不存在')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders case title with name', async () => {
    renderPage();
    await waitFor(() => {
      // Name appears in both title and Descriptions
      expect(screen.getAllByText('桃園測量案').length).toBeGreaterThan(0);
    }, WAIT_OPTS);
  });

  it('renders status tag', async () => {
    renderPage();
    await waitFor(() => {
      // Status appears in both header tag and Descriptions
      expect(screen.getAllByText('執行中').length).toBeGreaterThan(0);
    }, WAIT_OPTS);
  });

  it('renders back button', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('返回')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('navigates back when back button is clicked', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('返回')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('返回'));
    expect(mockNavigate).toHaveBeenCalledWith('/pm/cases');
  });

  it('renders info tab with case details', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('案件資訊')).toBeInTheDocument();
      expect(screen.getByText('桃園市政府')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders milestones tab label', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('里程碑/甘特圖')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders staff tab label', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('承辦同仁')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders descriptions items correctly', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('桃園市中壢區')).toBeInTheDocument();
      expect(screen.getByText('備註資訊')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

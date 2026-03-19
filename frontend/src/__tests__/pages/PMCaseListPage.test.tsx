/**
 * PMCaseListPage Tests
 *
 * Tests for the PM case management list page including:
 * - Page title rendering
 * - Summary cards display
 * - Loading state
 * - Table rendering with data
 * - Navigation to create page
 * - Navigation to detail page
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/PMCaseListPage.test.tsx
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
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
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

const mockRefetch = vi.fn();
const mockMutateAsync = vi.fn();

const mockUsePMCases = vi.fn((): { data: Record<string, unknown> | undefined; isLoading: boolean; refetch: typeof mockRefetch } => ({
  data: {
    items: [
      {
        id: 1, case_code: 'CK2025_PM_01_001', case_name: '測量案件A',
        year: 114, client_name: '桃園市政府', contract_amount: '1500000',
        status: 'in_progress' as const, progress: 45,
      },
      {
        id: 2, case_code: 'CK2025_PM_02_001', case_name: '資訊案件B',
        year: 114, client_name: '新北市政府', contract_amount: '800000',
        status: 'completed' as const, progress: 100,
      },
    ],
    pagination: { total: 2, page: 1, limit: 20, total_pages: 1 },
  },
  isLoading: false,
  refetch: mockRefetch,
}));

const mockUsePMCaseSummary = vi.fn((): { data: Record<string, unknown> | null } => ({
  data: {
    total_cases: 15,
    by_status: { in_progress: 8, completed: 7 },
    by_year: { '114': 10, '113': 5 },
    total_contract_amount: '25000000',
  },
}));

const mockUseDeletePMCase = vi.fn(() => ({
  mutateAsync: mockMutateAsync,
  isPending: false,
}));

vi.mock('../../hooks', () => ({
  useAuthGuard: () => ({ hasPermission: () => true }),
  useResponsive: () => ({ isMobile: false, isTablet: false, isDesktop: true, breakpoint: 'lg' }),
  usePMCases: (..._args: unknown[]) => mockUsePMCases(),
  usePMCaseSummary: (..._args: unknown[]) => mockUsePMCaseSummary(),
  useDeletePMCase: () => mockUseDeletePMCase(),
  usePMYearlyTrend: () => ({ data: [], isLoading: false }),
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
    import('../../pages/PMCaseListPage').then((mod) => {
      setPage(() => mod.PMCaseListPage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('PMCaseListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('PM 專案管理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders create button', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('新增案件')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders summary cards with total cases', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('總案件數')).toBeInTheDocument();
      expect(screen.getByText('15')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders summary cards with total contract amount', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('合約總額')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders loading state when data is loading', async () => {
    mockUsePMCases.mockReturnValueOnce({
      data: undefined,
      isLoading: true,
      refetch: mockRefetch,
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('PM 專案管理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('does not render summary cards when summary is null', async () => {
    mockUsePMCaseSummary.mockReturnValueOnce({ data: null });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('PM 專案管理')).toBeInTheDocument();
    }, WAIT_OPTS);
    expect(screen.queryByText('總案件數')).not.toBeInTheDocument();
  });

  it('renders search input with placeholder', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜尋案號/案名...')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders reload button', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByLabelText('reload')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('navigates to create page when create button is clicked', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('新增案件')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('新增案件'));
    expect(mockNavigate).toHaveBeenCalledWith('/pm/cases/create');
  });

  it('navigates to detail page when table row is clicked', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('CK2025_PM_01_001')).toBeInTheDocument();
    }, WAIT_OPTS);
    // Page uses onRow click to navigate
    fireEvent.click(screen.getByText('CK2025_PM_01_001'));
    expect(mockNavigate).toHaveBeenCalledWith('/pm/cases/1');
  });
});

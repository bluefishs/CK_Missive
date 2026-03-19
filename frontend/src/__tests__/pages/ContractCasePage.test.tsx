/**
 * ContractCasePage Tests
 *
 * Tests for the contract case (project) management page including:
 * - Page title rendering
 * - Statistics cards display
 * - Search input rendering
 * - Filter controls (year, category, status)
 * - Action buttons (create, reload, reset)
 * - Permission-based UI (create button visibility)
 * - View mode toggle (list/board)
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/ContractCasePage.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

// Dynamic import needs a longer timeout for module resolution
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

const mockHasPermission = vi.fn(() => true);

const mockRefetch = vi.fn();
vi.mock('../../hooks', () => ({
  useProjectsPage: vi.fn(() => ({
    projects: [
      { id: 1, project_name: 'Project A', project_code: 'P001', year: 114, status: '執行中', category: '01' },
      { id: 2, project_name: 'Project B', project_code: 'P002', year: 113, status: '已結案', category: '02' },
    ],
    pagination: { total: 2, page: 1, limit: 20, total_pages: 1, has_next: false, has_prev: false },
    isLoading: false,
    statistics: {
      total_projects: 10,
      status_breakdown: [
        { status: '執行中', count: 6 },
        { status: '已結案', count: 4 },
      ],
    },
    availableYears: [114, 113, 112],
    availableStatuses: ['執行中', '已結案'],
    refetch: mockRefetch,
    isDeleting: false,
  })),
  useAuthGuard: vi.fn(() => ({
    hasPermission: mockHasPermission,
    isAdmin: true,
    isAuthenticated: true,
    user: { id: 1, role: 'admin' },
  })),
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

vi.mock('@ck-shared/ui-components', () => ({
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('../../components/common', () => ({
  ResponsiveTable: (props: { dataSource: unknown[]; columns: unknown[] }) => (
    <div data-testid="mock-responsive-table">
      Table ({(props.dataSource as unknown[]).length} rows)
    </div>
  ),
}));

vi.mock('../../components/project/ProjectVendorManagement', () => ({
  __esModule: true,
  default: () => <div data-testid="mock-vendor-management">VendorManagement</div>,
}));

vi.mock('react-highlight-words', () => ({
  __esModule: true,
  default: ({ textToHighlight }: { textToHighlight: string }) => <span>{textToHighlight}</span>,
}));

vi.mock('../../pages/contractCase/tabs/constants', () => ({
  CATEGORY_OPTIONS: [
    { value: '01', label: '01委辦案件', color: 'blue' },
    { value: '02', label: '02協力計畫', color: 'green' },
    { value: '03', label: '03小額採購', color: 'orange' },
    { value: '04', label: '04其他類別', color: 'default' },
  ],
  CASE_NATURE_OPTIONS: [
    { value: '01', label: '01測量案', color: 'cyan' },
    { value: '02', label: '02資訊案', color: 'purple' },
    { value: '03', label: '03複合案', color: 'gold' },
  ],
  STATUS_OPTIONS: [
    { value: '執行中', label: '執行中' },
    { value: '已結案', label: '已結案' },
    { value: '未得標', label: '未得標' },
  ],
  STAFF_ROLE_OPTIONS: [
    { value: '計畫主持', label: '計畫主持', color: 'red' },
  ],
  VENDOR_ROLE_OPTIONS: [
    { value: '測量業務', label: '測量業務', color: 'blue' },
  ],
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderContractCasePage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <ContractCasePageWrapper />
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function ContractCasePageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/ContractCasePage').then((mod) => {
      setPage(() => mod.ContractCasePage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('ContractCasePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockHasPermission.mockReturnValue(true);
  });

  it('renders the page title', async () => {
    renderContractCasePage();
    await waitFor(() => {
      expect(screen.getByText('承攬案件管理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders statistics cards with correct values', async () => {
    renderContractCasePage();
    await waitFor(() => {
      expect(screen.getByText('總計案件')).toBeInTheDocument();
      expect(screen.getByText('執行中')).toBeInTheDocument();
      expect(screen.getByText('已結案')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('displays total project count from statistics', async () => {
    renderContractCasePage();
    await waitFor(() => {
      expect(screen.getByText('10')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders search input with placeholder', async () => {
    renderContractCasePage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜尋專案名稱、編號、委託單位')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders reset filter button', async () => {
    renderContractCasePage();
    await waitFor(() => {
      expect(screen.getByText('重置篩選')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders reload button', async () => {
    renderContractCasePage();
    await waitFor(() => {
      expect(screen.getByText('重新載入')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders create button when user has write permission', async () => {
    renderContractCasePage();
    await waitFor(() => {
      expect(screen.getByText('新增案件')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('hides create button when user lacks write permission', async () => {
    mockHasPermission.mockReturnValue(false);
    renderContractCasePage();
    await waitFor(() => {
      expect(screen.getByText('承攬案件管理')).toBeInTheDocument();
    }, WAIT_OPTS);
    expect(screen.queryByText('新增案件')).not.toBeInTheDocument();
  });

  it('renders table in list view mode by default', async () => {
    renderContractCasePage();
    await waitFor(() => {
      expect(screen.getByTestId('mock-responsive-table')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the data table with correct row count', async () => {
    renderContractCasePage();
    await waitFor(() => {
      expect(screen.getByText('Table (2 rows)')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('navigates to create page when create button is clicked', async () => {
    renderContractCasePage();
    await waitFor(() => {
      expect(screen.getByText('新增案件')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('新增案件'));
    expect(mockNavigate).toHaveBeenCalled();
  });
});

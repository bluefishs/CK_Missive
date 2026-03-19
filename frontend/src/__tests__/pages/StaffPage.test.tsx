/**
 * StaffPage Tests
 *
 * Tests for the staff management page including:
 * - Page title renders
 * - Statistics cards display
 * - Search input and filter controls
 * - Action buttons (add, refresh)
 * - Table renders with data
 * - Navigation on row click
 * - Toggle active status
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

// Dynamic import needs a longer timeout for module resolution in full test suite
const WAIT_OPTS = { timeout: 5000 };

// ==========================================================================
// Mocks
// ==========================================================================

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

const mockStaffList = [
  {
    id: 1,
    username: 'alice',
    full_name: 'Alice Wang',
    email: 'alice@example.com',
    role: 'admin',
    is_admin: true,
    is_active: true,
    department: 'Engineering',
    position: 'Manager',
    last_login: '2026-03-01T10:00:00Z',
    created_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 2,
    username: 'bob',
    full_name: 'Bob Chen',
    email: 'bob@example.com',
    role: 'user',
    is_admin: false,
    is_active: false,
    department: 'Sales',
    position: 'Staff',
    last_login: null,
    created_at: '2025-06-01T00:00:00Z',
  },
];

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({ items: mockStaffList, total: 2 }),
    put: vi.fn().mockResolvedValue({}),
    patch: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    USERS: {
      LIST: '/users/list',
      STATUS: (id: number) => `/users/${id}/status`,
    },
  },
}));

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
  useTableColumnSearch: vi.fn(() => ({
    getColumnSearchProps: vi.fn(() => ({})),
  })),
}));

vi.mock('../../hooks/system', () => ({
  useDepartments: vi.fn(() => ({
    data: ['Engineering', 'Sales'],
    isLoading: false,
  })),
}));

vi.mock('../../config/queryConfig', () => ({
  defaultQueryOptions: {
    list: { staleTime: 0 },
    detail: { staleTime: 0 },
  },
}));

vi.mock('../../router/types', () => ({
  ROUTES: {
    STAFF_DETAIL: '/staff/:id',
    STAFF_CREATE: '/staff/create',
  },
}));

vi.mock('../../components/common', () => ({
  ResponsiveTable: (props: Record<string, unknown>) => {
    const dataSource = props.dataSource as Array<Record<string, unknown>> || [];
    return (
      <div data-testid="responsive-table">
        <table>
          <tbody>
            {dataSource.map((item: Record<string, unknown>) => (
              <tr
                key={item.id as number}
                data-testid={`staff-row-${item.id}`}
                onClick={() => {
                  const onRow = props.onRow as ((record: Record<string, unknown>) => { onClick: () => void }) | undefined;
                  if (onRow) onRow(item).onClick();
                }}
              >
                <td>{item.full_name as string}</td>
                <td>{item.email as string}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  },
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderStaffPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <React.Suspense fallback={<div>Loading...</div>}>
              <StaffPageWrapper />
            </React.Suspense>
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function StaffPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/StaffPage').then((mod) => {
      setPage(() => mod.StaffPage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('StaffPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    renderStaffPage();
    await waitFor(() => {
      expect(screen.getByText('承辦同仁管理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders statistics cards', async () => {
    renderStaffPage();
    await waitFor(() => {
      expect(screen.getByText('總人數')).toBeInTheDocument();
      expect(screen.getByText('啟用中')).toBeInTheDocument();
      expect(screen.getByText('已停用')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the search input', async () => {
    renderStaffPage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜尋姓名、帳號、Email...')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the add staff button', async () => {
    renderStaffPage();
    await waitFor(() => {
      expect(screen.getByText('新增同仁')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the refresh button', async () => {
    renderStaffPage();
    await waitFor(() => {
      expect(screen.getByText('重新整理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the data table', async () => {
    renderStaffPage();
    await waitFor(() => {
      expect(screen.getByTestId('responsive-table')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders staff data rows in the table', async () => {
    renderStaffPage();
    await waitFor(() => {
      expect(screen.getByText('Alice Wang')).toBeInTheDocument();
      expect(screen.getByText('Bob Chen')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('navigates to create page when add button is clicked', async () => {
    renderStaffPage();
    await waitFor(() => {
      expect(screen.getByText('新增同仁')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('新增同仁'));
    expect(mockNavigate).toHaveBeenCalledWith('/staff/create');
  });

  it('navigates to detail page when a row is clicked', async () => {
    renderStaffPage();
    await waitFor(() => {
      expect(screen.getByTestId('staff-row-1')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByTestId('staff-row-1'));
    expect(mockNavigate).toHaveBeenCalledWith('/staff/1');
  });

  it('updates search text when typing in search input', async () => {
    renderStaffPage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜尋姓名、帳號、Email...')).toBeInTheDocument();
    }, WAIT_OPTS);
    const searchInput = screen.getByPlaceholderText('搜尋姓名、帳號、Email...');
    fireEvent.change(searchInput, { target: { value: 'alice' } });
    expect(searchInput).toHaveValue('alice');
  });

  it('renders department filter select', async () => {
    renderStaffPage();
    await waitFor(() => {
      // The department filter placeholder should be visible
      expect(screen.getByText('部門篩選')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders status filter select', async () => {
    renderStaffPage();
    await waitFor(() => {
      expect(screen.getByText('狀態篩選')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

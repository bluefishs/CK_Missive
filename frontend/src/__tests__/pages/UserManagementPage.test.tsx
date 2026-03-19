/**
 * UserManagementPage Tests
 *
 * Tests for the user management page including:
 * - Page title renders
 * - Create user button
 * - Search input and filter controls
 * - Table renders with user data
 * - Navigation on row click
 * - Role filter select
 * - Search button
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
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

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

const mockUsers = [
  {
    id: 1,
    username: 'admin1',
    full_name: 'Admin One',
    email: 'admin1@example.com',
    role: 'admin',
    is_admin: true,
    is_active: true,
    auth_provider: 'email',
    status: 'active',
    created_at: '2025-01-01T00:00:00Z',
    last_login: '2026-03-01T10:00:00Z',
  },
  {
    id: 2,
    username: 'user1',
    full_name: 'User One',
    email: 'user1@example.com',
    role: 'user',
    is_admin: false,
    is_active: true,
    auth_provider: 'google',
    status: 'active',
    created_at: '2025-06-01T00:00:00Z',
    last_login: '2026-03-10T15:00:00Z',
  },
  {
    id: 3,
    username: 'inactive1',
    full_name: 'Inactive User',
    email: 'inactive@example.com',
    role: 'user',
    is_admin: false,
    is_active: false,
    auth_provider: 'email',
    status: 'inactive',
    created_at: '2025-03-01T00:00:00Z',
    last_login: null,
  },
];

const mockRefetch = vi.fn();

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
  useAdminUsersPage: vi.fn(() => ({
    users: mockUsers,
    total: 3,
    isLoading: false,
    isError: false,
    error: null,
    refetch: mockRefetch,
    roles: [],
    isPermissionsLoading: false,
    createUser: vi.fn(),
    updateUser: vi.fn(),
    deleteUser: vi.fn(),
    updatePermissions: vi.fn(),
    batchUpdateStatus: vi.fn(),
    batchDelete: vi.fn(),
    batchUpdateRole: vi.fn(),
    isCreating: false,
    isUpdating: false,
    isDeleting: false,
    isUpdatingPermissions: false,
    isBatchUpdating: false,
  })),
}));

vi.mock('../../router/types', () => ({
  ROUTES: {
    USER_CREATE: '/admin/users/create',
    USER_EDIT: '/admin/users/:id/edit',
  },
}));

vi.mock('../../constants/permissions', () => ({
  getRoleDisplayName: vi.fn((role: string) => {
    const map: Record<string, string> = { admin: '管理員', user: '一般使用者', superuser: '超級管理員' };
    return map[role] || role;
  }),
  getStatusDisplayName: vi.fn((status: string) => {
    const map: Record<string, string> = { active: '啟用', inactive: '停用' };
    return map[status] || status;
  }),
}));

vi.mock('react-highlight-words', () => ({
  __esModule: true,
  default: ({ textToHighlight }: { textToHighlight: string }) => <span>{textToHighlight}</span>,
}));

vi.mock('lodash/debounce', () => ({
  __esModule: true,
  default: (fn: (...args: unknown[]) => unknown) => fn,
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
                data-testid={`user-row-${item.id}`}
                onClick={() => {
                  const onRow = props.onRow as ((record: Record<string, unknown>) => { onClick: () => void }) | undefined;
                  if (onRow) onRow(item).onClick();
                }}
              >
                <td>{item.full_name as string}</td>
                <td>{item.email as string}</td>
                <td>{item.role as string}</td>
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

function renderUserManagementPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <React.Suspense fallback={<div>Loading...</div>}>
              <UserManagementPageWrapper />
            </React.Suspense>
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function UserManagementPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/UserManagementPage').then((mod) => {
      setPage(() => mod.default);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('UserManagementPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    renderUserManagementPage();
    await waitFor(() => {
      expect(screen.getByText('使用者管理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the create user button', async () => {
    renderUserManagementPage();
    await waitFor(() => {
      expect(screen.getByText('新增使用者')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the search input', async () => {
    renderUserManagementPage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜尋使用者名稱或電子郵件')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders multiple action buttons', async () => {
    renderUserManagementPage();
    await waitFor(() => {
      // Page should have at least the create user button
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThanOrEqual(2);
    }, WAIT_OPTS);
  });

  it('renders the data table', async () => {
    renderUserManagementPage();
    await waitFor(() => {
      expect(screen.getByTestId('responsive-table')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders user data rows in the table', async () => {
    renderUserManagementPage();
    await waitFor(() => {
      expect(screen.getByText('Admin One')).toBeInTheDocument();
      expect(screen.getByText('User One')).toBeInTheDocument();
      expect(screen.getByText('Inactive User')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('navigates to create page when create button is clicked', async () => {
    renderUserManagementPage();
    await waitFor(() => {
      expect(screen.getByText('新增使用者')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('新增使用者'));
    expect(mockNavigate).toHaveBeenCalledWith('/admin/users/create');
  });

  it('navigates to edit page when a row is clicked', async () => {
    renderUserManagementPage();
    await waitFor(() => {
      expect(screen.getByTestId('user-row-1')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByTestId('user-row-1'));
    expect(mockNavigate).toHaveBeenCalledWith('/admin/users/1/edit');
  });

  it('updates search text when typing in search input', async () => {
    renderUserManagementPage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜尋使用者名稱或電子郵件')).toBeInTheDocument();
    }, WAIT_OPTS);
    const searchInput = screen.getByPlaceholderText('搜尋使用者名稱或電子郵件');
    fireEvent.change(searchInput, { target: { value: 'admin' } });
    expect(searchInput).toHaveValue('admin');
  });

  it('renders role filter select', async () => {
    renderUserManagementPage();
    await waitFor(() => {
      // Role filter placeholder
      expect(screen.getByText('角色篩選')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders auth provider filter select', async () => {
    renderUserManagementPage();
    await waitFor(() => {
      expect(screen.getByText('認證方式')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders user emails in the table', async () => {
    renderUserManagementPage();
    await waitFor(() => {
      expect(screen.getByText('admin1@example.com')).toBeInTheDocument();
      expect(screen.getByText('user1@example.com')).toBeInTheDocument();
      expect(screen.getByText('inactive@example.com')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

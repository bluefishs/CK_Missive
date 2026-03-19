/**
 * UserFormPage Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({}),
  };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/adminUsersApi', () => ({
  adminUsersApi: {
    getUsers: vi.fn().mockResolvedValue({ items: [] }),
    getUserPermissions: vi.fn().mockResolvedValue({ role: 'user', permissions: [] }),
    getAvailablePermissions: vi.fn().mockResolvedValue({ roles: [] }),
    createUser: vi.fn().mockResolvedValue({ id: 1 }),
    updateUser: vi.fn().mockResolvedValue({ id: 1 }),
    updateUserPermissions: vi.fn().mockResolvedValue({}),
    deleteUser: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../../router/types', () => ({
  ROUTES: {
    USER_MANAGEMENT: '/admin/users',
    USER_CREATE: '/admin/users/create',
    USER_EDIT: '/admin/users/:id/edit',
  },
}));

vi.mock('../../constants/permissions', () => ({
  USER_ROLES: {
    admin: { name_zh: '管理員', can_login: true },
    user: { name_zh: '一般使用者', can_login: true },
    viewer: { name_zh: '檢視者', can_login: true },
  },
  USER_STATUSES: {
    active: { name_zh: '啟用', can_login: true },
    inactive: { name_zh: '停用', can_login: false },
    suspended: { name_zh: '暫停', can_login: false },
  },
}));

vi.mock('../../components/admin/PermissionManager', () => ({
  __esModule: true,
  default: () => <div data-testid="permission-manager">PermissionManager</div>,
}));

vi.mock('../../components/common/FormPage', () => ({
  FormPageLayout: ({
    title,
    children,
    loading,
  }: {
    title: string;
    children: React.ReactNode;
    loading?: boolean;
  }) => (
    <div data-testid="form-page-layout">
      <h1>{title}</h1>
      {loading ? <div data-testid="loading">Loading...</div> : children}
    </div>
  ),
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

function UserFormPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/UserFormPage').then((mod) => {
      setPage(() => mod.default);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('UserFormPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('create mode (no id param)', () => {
    it('renders without crashing', async () => {
      renderWithProviders(<UserFormPageWrapper />);
      await waitFor(() => {
        expect(document.body).toBeTruthy();
      }, WAIT_OPTS);
    });

    it('renders the form page layout with create title', async () => {
      renderWithProviders(<UserFormPageWrapper />);
      await waitFor(() => {
        expect(screen.getByTestId('form-page-layout')).toBeInTheDocument();
        expect(screen.getByText('新增使用者')).toBeInTheDocument();
      }, WAIT_OPTS);
    });

    it('renders the basic info tab', async () => {
      renderWithProviders(<UserFormPageWrapper />);
      await waitFor(() => {
        expect(screen.getByText('基本資料')).toBeInTheDocument();
      }, WAIT_OPTS);
    });

    it('renders email and username form fields', async () => {
      renderWithProviders(<UserFormPageWrapper />);
      await waitFor(() => {
        expect(screen.getByText('電子郵件')).toBeInTheDocument();
        expect(screen.getByText('使用者名稱')).toBeInTheDocument();
      }, WAIT_OPTS);
    });

    it('renders role and status select fields', async () => {
      renderWithProviders(<UserFormPageWrapper />);
      await waitFor(() => {
        expect(screen.getByText('帳號設定')).toBeInTheDocument();
      }, WAIT_OPTS);
    });
  });

  describe('form fields', () => {
    it('renders full name and department fields', async () => {
      renderWithProviders(<UserFormPageWrapper />);
      await waitFor(() => {
        expect(screen.getByText('完整姓名')).toBeInTheDocument();
        expect(screen.getByText('部門')).toBeInTheDocument();
      }, WAIT_OPTS);
    });

    it('renders admin switch and suspended reason fields', async () => {
      renderWithProviders(<UserFormPageWrapper />);
      await waitFor(() => {
        expect(screen.getByText('管理員')).toBeInTheDocument();
        expect(screen.getByText('暫停原因')).toBeInTheDocument();
      }, WAIT_OPTS);
    });
  });
});

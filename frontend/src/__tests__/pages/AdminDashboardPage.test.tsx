/**
 * AdminDashboardPage Tests
 *
 * Tests for the admin dashboard page including:
 * - Page title rendering
 * - Statistics cards (totalUsers, activeUsers, pendingUsers, suspendedUsers)
 * - System notifications section
 * - Quick action panels
 * - Refresh button
 * - Document statistics section
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/AdminDashboardPage.test.tsx
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

const mockUsersData = {
  users: [
    { id: 1, full_name: 'Admin', email: 'admin@test.com', role: 'admin', status: 'active', auth_provider: 'email', created_at: '2026-01-01T00:00:00Z' },
    { id: 2, full_name: 'User1', email: 'user1@test.com', role: 'user', status: 'active', auth_provider: 'google', created_at: '2026-01-02T00:00:00Z' },
    { id: 3, full_name: 'Pending', email: 'pending@test.com', role: 'unverified', status: 'pending', auth_provider: 'email', created_at: '2026-03-01T00:00:00Z' },
  ],
};

const mockEfficiency = {
  total: 100,
  overdue_count: 5,
  overdue_rate: 0.05,
  status_distribution: [
    { status: '處理中', count: 60 },
    { status: '已結案', count: 40 },
  ],
};

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockImplementation((url: string) => {
      if (url.includes('users')) return Promise.resolve(mockUsersData);
      return Promise.resolve({});
    }),
    put: vi.fn().mockResolvedValue({}),
    patch: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    ADMIN_USER_MANAGEMENT: {
      USERS_LIST: '/admin/user-management/users/list',
      USERS_UPDATE: (id: number) => `/admin/user-management/users/${id}/update`,
      USERS_DELETE: (id: number) => `/admin/user-management/users/${id}/delete`,
    },
  },
}));

vi.mock('../../api/documentsApi', () => ({
  documentsApi: {
    getDocumentEfficiency: vi.fn().mockResolvedValue(mockEfficiency),
  },
}));

vi.mock('../../router/types', () => ({
  ROUTES: {
    USER_MANAGEMENT: '/admin/users',
    PERMISSION_MANAGEMENT: '/admin/permissions',
    BACKUP_MANAGEMENT: '/admin/backup',
  },
}));

vi.mock('../../constants/permissions', () => ({
  USER_ROLES: {
    admin: { name_zh: '管理員', description_zh: '系統管理員', can_login: true, default_permissions: ['all'] },
    user: { name_zh: '一般使用者', description_zh: '一般使用者', can_login: true, default_permissions: ['read'] },
  },
  USER_STATUSES: {
    active: { name_zh: '啟用', description_zh: '帳戶已啟用', can_login: true },
    pending: { name_zh: '待驗證', description_zh: '等待管理者驗證', can_login: false },
  },
}));

vi.mock('@ck-shared/ui-components', () => ({
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('../../components/dashboard', () => ({
  SystemHealthDashboard: () => <div data-testid="system-health">SystemHealth</div>,
  AIStatsPanel: () => <div data-testid="ai-stats">AIStats</div>,
  DocumentTrendsChart: () => <div data-testid="doc-trends">DocumentTrends</div>,
}));

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderAdminDashboardPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <React.Suspense fallback={<div>Loading...</div>}>
              <AdminDashboardPageWrapper />
            </React.Suspense>
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function AdminDashboardPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/AdminDashboardPage').then((mod) => {
      setPage(() => mod.default);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('AdminDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    // Re-establish matchMedia mock after restoreAllMocks (required by Ant Design Row/Col)
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  it('renders the page title', async () => {
    renderAdminDashboardPage();
    await waitFor(() => {
      expect(screen.getByText('管理員控制台')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders subtitle text', async () => {
    renderAdminDashboardPage();
    await waitFor(() => {
      expect(screen.getByText('系統管理概覽和使用者權限管理中心')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders refresh button', async () => {
    renderAdminDashboardPage();
    await waitFor(() => {
      expect(screen.getByText('重新整理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders statistics card titles', async () => {
    renderAdminDashboardPage();
    await waitFor(() => {
      expect(screen.getByText('總使用者數')).toBeInTheDocument();
      expect(screen.getByText('啟用使用者')).toBeInTheDocument();
      expect(screen.getByText('待驗證使用者')).toBeInTheDocument();
      expect(screen.getByText('暫停使用者')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders system notification section', async () => {
    renderAdminDashboardPage();
    await waitFor(() => {
      expect(screen.getByText('系統通知')).toBeInTheDocument();
      expect(screen.getByText('系統狀態')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders quick action panels', async () => {
    renderAdminDashboardPage();
    await waitFor(() => {
      expect(screen.getByText('使用者管理')).toBeInTheDocument();
      expect(screen.getByText('權限管理')).toBeInTheDocument();
      expect(screen.getByText('備份與部署')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders system monitoring section', async () => {
    renderAdminDashboardPage();
    await waitFor(() => {
      expect(screen.getByText('系統監控')).toBeInTheDocument();
      expect(screen.getByTestId('system-health')).toBeInTheDocument();
      expect(screen.getByTestId('ai-stats')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders role explanation section', async () => {
    renderAdminDashboardPage();
    await waitFor(() => {
      expect(screen.getByText('系統角色說明')).toBeInTheDocument();
      expect(screen.getByText('使用者狀態說明')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

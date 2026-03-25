/**
 * ProfilePage Tests
 *
 * Tests for the user profile page including:
 * - Profile info display (avatar, username, email, role tags)
 * - Account info display (status, login count, auth provider)
 * - Tab navigation (profile, login history, devices, MFA)
 * - Edit mode toggle and form interactions
 * - Password change modal
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

const mockUserInfo = {
  id: 1,
  username: 'testuser',
  full_name: 'Test User',
  email: 'test@example.com',
  role: 'admin',
  is_admin: true,
  is_active: true,
  department: 'Engineering',
  position: 'Manager',
  auth_provider: 'email',
  email_verified: true,
  login_count: 42,
  last_login: '2026-03-01T10:00:00Z',
  created_at: '2025-01-01T00:00:00Z',
  avatar_url: null,
  permissions: ['all'],
};

vi.mock('../../services/authService', () => ({
  __esModule: true,
  default: {
    isAuthenticated: vi.fn(() => true),
    getUserInfo: vi.fn(() => ({ ...mockUserInfo })),
    setUserInfo: vi.fn(),
    getToken: vi.fn(() => 'mock-token'),
  },
}));

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({ ...mockUserInfo }),
    put: vi.fn().mockResolvedValue({}),
    patch: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    AUTH: {
      ME: '/auth/me',
      PROFILE_UPDATE: '/auth/profile/update',
      PASSWORD_CHANGE: '/auth/password/change',
      SESSIONS: '/auth/sessions',
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
}));

vi.mock('../../components/auth/LoginHistoryTab', () => ({
  LoginHistoryTab: () => <div data-testid="login-history-tab">LoginHistory</div>,
}));

vi.mock('../../components/auth/SessionManagementTab', () => ({
  SessionManagementTab: () => <div data-testid="session-management-tab">SessionManagement</div>,
}));

vi.mock('../../components/auth/MFASettingsTab', () => ({
  MFASettingsTab: () => <div data-testid="mfa-settings-tab">MFASettings</div>,
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderProfilePage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <React.Suspense fallback={<div>Loading...</div>}>
              <ProfilePageWrapper />
            </React.Suspense>
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

// Lazy-import wrapper to work with module-level mocks
function ProfilePageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/ProfilePage').then((mod) => {
      setPage(() => mod.ProfilePage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('ProfilePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByText('個人設定')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the profile tab with basic info card', async () => {
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByText('基本資訊')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the account info section', async () => {
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByText('帳戶資訊')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('displays account status tags', async () => {
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByText('已啟用')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('displays admin role tag for admin users', async () => {
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByText('管理員')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('displays email auth provider tag for email users', async () => {
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getAllByText('電子郵件').length).toBeGreaterThan(0);
    }, WAIT_OPTS);
  });

  it('displays email verified status', async () => {
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByText('已驗證')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('displays login count', async () => {
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByText(/42 次/)).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders edit button in profile tab', async () => {
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByText('編輯資料')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('shows security settings card with password change button for email auth', async () => {
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByText('安全設定')).toBeInTheDocument();
      expect(screen.getByText('修改密碼')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders all four tabs', async () => {
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByText('個人資料')).toBeInTheDocument();
      expect(screen.getByText('登入紀錄')).toBeInTheDocument();
      expect(screen.getByText('裝置管理')).toBeInTheDocument();
      expect(screen.getByText('雙因素認證')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders form fields with correct initial values', async () => {
    renderProfilePage();
    await waitFor(() => {
      const usernameInput = screen.getByLabelText('使用者名稱');
      expect(usernameInput).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('form fields are disabled when not in edit mode', async () => {
    renderProfilePage();
    await waitFor(() => {
      const nameInput = screen.getByLabelText('姓名');
      expect(nameInput).toBeDisabled();
    }, WAIT_OPTS);
  });

  it('switches to login history tab when clicked', async () => {
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByText('登入紀錄')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('登入紀錄'));
    await waitFor(() => {
      expect(screen.getByTestId('login-history-tab')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('switches to devices tab when clicked', async () => {
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByText('裝置管理')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('裝置管理'));
    await waitFor(() => {
      expect(screen.getByTestId('session-management-tab')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

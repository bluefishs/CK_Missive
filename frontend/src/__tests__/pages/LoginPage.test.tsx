/**
 * LoginPage Tests
 *
 * Tests for the login page including:
 * - Page title and branding rendering
 * - Login form fields (username, password)
 * - Submit button
 * - Form validation (required fields)
 * - Quick entry button (env-dependent)
 * - Registration link
 * - Environment tag display
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/LoginPage.test.tsx
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
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/authService', () => ({
  __esModule: true,
  default: {
    isAuthenticated: vi.fn(() => false),
    login: vi.fn().mockResolvedValue({ user_info: { is_admin: false } }),
    getCurrentUser: vi.fn().mockResolvedValue({ username: 'testuser', full_name: 'Test' }),
    setUserInfo: vi.fn(),
    getUserInfo: vi.fn(() => null),
    googleLogin: vi.fn(),
  },
  MFARequiredError: class MFARequiredError extends Error {
    mfa_token: string;
    constructor(token: string) {
      super('MFA required');
      this.mfa_token = token;
    }
  },
}));

vi.mock('../../config/env', () => ({
  detectEnvironment: vi.fn(() => 'localhost'),
  isAuthDisabled: vi.fn(() => true),
  GOOGLE_CLIENT_ID: '',
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

function renderLoginPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <LoginPageWrapper />
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function LoginPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/LoginPage').then((mod) => {
      setPage(() => mod.default);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the brand title', async () => {
    renderLoginPage();
    await waitFor(() => {
      expect(screen.getByText('乾坤測繪')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the system subtitle', async () => {
    renderLoginPage();
    await waitFor(() => {
      expect(screen.getByText('公文管理系統')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders username input field with placeholder', async () => {
    renderLoginPage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('帳號或電子郵件')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders password input field with placeholder', async () => {
    renderLoginPage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('密碼')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the login submit button', async () => {
    renderLoginPage();
    await waitFor(() => {
      expect(screen.getByText('帳號密碼登入')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders quick entry button in localhost environment', async () => {
    renderLoginPage();
    await waitFor(() => {
      expect(screen.getByText('快速進入系統')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders registration link', async () => {
    renderLoginPage();
    await waitFor(() => {
      expect(screen.getByText('立即註冊')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders forgot password link', async () => {
    renderLoginPage();
    await waitFor(() => {
      expect(screen.getByText('忘記密碼？')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders environment tag for localhost', async () => {
    renderLoginPage();
    await waitFor(() => {
      expect(screen.getByText('localhost')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('shows validation error when submitting empty username', async () => {
    renderLoginPage();
    await waitFor(() => {
      expect(screen.getByText('帳號密碼登入')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('帳號密碼登入'));
    await waitFor(() => {
      const errorEl = screen.queryByText('請輸入帳號或電子郵件')
        || screen.queryByText(/請輸入帳號/);
      expect(errorEl).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('shows validation error when submitting empty password', async () => {
    renderLoginPage();
    await waitFor(() => {
      expect(screen.getByText('帳號密碼登入')).toBeInTheDocument();
    }, WAIT_OPTS);
    // Fill username but leave password empty
    fireEvent.change(screen.getByPlaceholderText('帳號或電子郵件'), { target: { value: 'user' } });
    fireEvent.click(screen.getByText('帳號密碼登入'));
    await waitFor(() => {
      expect(screen.getByText('請輸入密碼')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders divider text between quick entry and form', async () => {
    renderLoginPage();
    await waitFor(() => {
      expect(screen.getByText('或使用帳號登入')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

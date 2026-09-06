/**
 * EntryPage Tests
 *
 * Tests for the system entry/login page including:
 * - Title rendering
 * - Login button rendering (password login always visible)
 * - Environment tag display
 * - Loading state
 * - Redirect when already authenticated
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/EntryPage.test.tsx
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';

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

vi.mock('../../services/authService', () => ({
  __esModule: true,
  default: {
    isAuthenticated: vi.fn(() => false),
    getCurrentUser: vi.fn().mockResolvedValue({ full_name: 'Test', username: 'test' }),
    setUserInfo: vi.fn(),
    googleLogin: vi.fn(),
    // 2026-09-06：store/sessionStore 也吃這支 mock —— markAuthenticated 會呼叫 getUserInfo()，
    // mock 少了它就在 set 之前丟 TypeError（async effect 吞掉）⇒ status 永遠停在 resolving。
    getUserInfo: vi.fn(() => null),
    ssoBridge: vi.fn().mockResolvedValue(null),
    logout: vi.fn(),
  },
}));

vi.mock('../../config/env', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  detectEnvironment: () => 'localhost',
  isAuthDisabled: () => false,
  GOOGLE_CLIENT_ID: '',
}));

// Mock CSS import
vi.mock('../../pages/EntryPage.css', () => ({}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderEntryPage() {
  return render(
    <ConfigProvider locale={zhTW}>
      <AntApp>
        <MemoryRouter>
          <React.Suspense fallback={<div>Loading...</div>}>
            <EntryPageWrapper />
          </React.Suspense>
        </MemoryRouter>
      </AntApp>
    </ConfigProvider>,
  );
}

function EntryPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/EntryPage').then((mod) => {
      setPage(() => mod.default);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('EntryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the main title text', async () => {
    renderEntryPage();
    await waitFor(() => {
      expect(screen.getByText('乾坤測繪')).toBeInTheDocument();
      expect(screen.getByText('公文系統入口')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('does not render the password login button (ADR-0033：SHOW_PASSWORD_LOGIN=false)', async () => {
    renderEntryPage();
    await waitFor(() => {
      expect(document.querySelector('.entry-page')).not.toBeNull();
    }, WAIT_OPTS);
    expect(screen.queryByText('帳號密碼登入')).toBeNull();
  });

  it('renders the quick entry button for localhost', async () => {
    renderEntryPage();
    await waitFor(() => {
      expect(screen.getByText('快速進入系統')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the environment tag', async () => {
    renderEntryPage();
    await waitFor(() => {
      expect(screen.getByText('localhost')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('redirects to dashboard when already authenticated', async () => {
    // Re-mock authService to return authenticated
    const authService = await import('../../services/authService');
    vi.mocked(authService.default.isAuthenticated).mockReturnValue(true);

    renderEntryPage();
    // 2026-06-16 起導向改宣告式：頁面把 sessionStore 標成 authenticated，由 <Navigate> 依 store 狀態離開，
    // 不再 imperative navigate('/dashboard')（那條路在 useEffect re-run 的 mounted 守衛下會被跳過）。
    const { useSessionStore } = await import('../../store/sessionStore');
    await waitFor(() => {
      expect(useSessionStore.getState().status).toBe('authenticated');
    }, WAIT_OPTS);
  });
});

/**
 * Layout Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
  useIdleTimeout: vi.fn(),
}));

vi.mock('../../hooks/business/useTaoyuanDispatch', () => ({
  useDispatchProjectIds: vi.fn(),
}));

vi.mock('../../components/layout/hooks/useNavigationData', () => ({
  useNavigationData: vi.fn(() => ({
    menuItems: [],
    navigationLoading: false,
    permissionsLoading: false,
    currentUser: { id: 1, username: 'test', email_verified: true },
  })),
}));

vi.mock('../../components/layout/Sidebar', () => ({
  default: () => <div data-testid="sidebar">Sidebar</div>,
}));

vi.mock('../../components/layout/Header', () => ({
  default: (_props: {
    collapsed: boolean;
    onToggleCollapse: () => void;
    currentUser: unknown;
  }) => <div data-testid="header">Header</div>,
}));

vi.mock('../../components/layout/SidebarContent', () => ({
  default: () => <div data-testid="sidebar-content">SidebarContent</div>,
}));

vi.mock('../../components/ai', () => ({
  AIAssistantButton: ({ visible }: { visible: boolean }) => (
    visible ? <div data-testid="ai-button">AI</div> : null
  ),
}));

vi.mock('../../api/authApi', () => ({
  sendVerificationEmail: vi.fn(),
}));

// ============================================================================
// Helpers
// ============================================================================

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter initialEntries={['/documents']}>
            {ui}
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

// ============================================================================
// Tests
// ============================================================================

describe('Layout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', async () => {
    const Layout = (await import('../../components/Layout')).default;
    const { container } = renderWithProviders(
      <Layout><div>Child Content</div></Layout>
    );
    expect(container).toBeTruthy();
  });

  it('renders children content', async () => {
    const Layout = (await import('../../components/Layout')).default;
    const { getByText } = renderWithProviders(
      <Layout><div>Test Child</div></Layout>
    );
    expect(getByText('Test Child')).toBeInTheDocument();
  });

  it('renders public route without layout chrome', async () => {
    const Layout = (await import('../../components/Layout')).default;
    const queryClient = createTestQueryClient();
    const { getByText, queryByTestId } = render(
      <QueryClientProvider client={queryClient}>
        <ConfigProvider locale={zhTW}>
          <AntApp>
            <MemoryRouter initialEntries={['/login']}>
              <Layout><div>Login Page</div></Layout>
            </MemoryRouter>
          </AntApp>
        </ConfigProvider>
      </QueryClientProvider>,
    );
    expect(getByText('Login Page')).toBeInTheDocument();
    expect(queryByTestId('sidebar')).not.toBeInTheDocument();
  });
});

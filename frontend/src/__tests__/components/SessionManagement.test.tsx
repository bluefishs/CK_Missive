/**
 * SessionManagementTab Tests
 *
 * Tests for the session/device management component including:
 * - Session list rendering
 * - Current device indicator
 * - Device info parsing from user-agent
 * - Revoke session button
 * - Revoke all other sessions button
 * - Refresh button
 * - Empty state
 * - Loading state
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import { createTestQueryClient } from '../../test/testUtils';
import { SessionManagementTab } from '../../components/auth/SessionManagementTab';

// ==========================================================================
// Mocks
// ==========================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

const mockSessions = [
  {
    id: 1,
    ip_address: '192.168.1.100',
    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
    device_info: null,
    created_at: '2026-03-01T10:00:00Z',
    last_activity: '2026-03-14T08:00:00Z',
    is_active: true,
    is_current: true,
  },
  {
    id: 2,
    ip_address: '10.0.0.50',
    user_agent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605 Safari/604',
    device_info: null,
    created_at: '2026-03-10T14:00:00Z',
    last_activity: '2026-03-13T18:30:00Z',
    is_active: true,
    is_current: false,
  },
  {
    id: 3,
    ip_address: '172.16.0.5',
    user_agent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0',
    device_info: null,
    created_at: '2026-03-12T09:00:00Z',
    last_activity: null,
    is_active: true,
    is_current: false,
  },
];

const mockListSessions = vi.fn().mockResolvedValue({ sessions: mockSessions, total: 3 });
const mockRevokeSession = vi.fn().mockResolvedValue({ message: 'ok' });
const mockRevokeAllSessions = vi.fn().mockResolvedValue({ message: 'ok', revoked_count: 2 });

vi.mock('../../api/sessionApi', () => ({
  listSessions: (...args: unknown[]) => mockListSessions(...args),
  revokeSession: (...args: unknown[]) => mockRevokeSession(...args),
  revokeAllSessions: (...args: unknown[]) => mockRevokeAllSessions(...args),
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderSessionManagement(props: { isMobile?: boolean } = {}) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <SessionManagementTab isMobile={props.isMobile} />
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

// ==========================================================================
// Tests
// ==========================================================================

describe('SessionManagementTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListSessions.mockResolvedValue({ sessions: mockSessions, total: 3 });
  });

  it('renders the active device count header', async () => {
    renderSessionManagement();
    await waitFor(() => {
      expect(screen.getByText(/共 3 個活躍裝置/)).toBeInTheDocument();
    });
  });

  it('renders the current device tag', async () => {
    renderSessionManagement();
    await waitFor(() => {
      expect(screen.getByText('目前裝置')).toBeInTheDocument();
    });
  });

  it('renders current device with green "in use" tag', async () => {
    renderSessionManagement();
    await waitFor(() => {
      expect(screen.getByText('目前使用中')).toBeInTheDocument();
    });
  });

  it('renders Windows Chrome device info from user-agent', async () => {
    renderSessionManagement();
    await waitFor(() => {
      expect(screen.getByText('Windows Chrome')).toBeInTheDocument();
    });
  });

  it('renders iPhone Safari device info from user-agent', async () => {
    renderSessionManagement();
    await waitFor(() => {
      expect(screen.getByText('iPhone Safari')).toBeInTheDocument();
    });
  });

  it('renders macOS Chrome device info from user-agent', async () => {
    renderSessionManagement();
    await waitFor(() => {
      expect(screen.getByText('macOS Chrome')).toBeInTheDocument();
    });
  });

  it('renders IP addresses for sessions', async () => {
    renderSessionManagement();
    await waitFor(() => {
      expect(screen.getByText('192.168.1.100')).toBeInTheDocument();
      expect(screen.getByText('10.0.0.50')).toBeInTheDocument();
    });
  });

  it('renders revoke all button when there are other sessions', async () => {
    renderSessionManagement();
    await waitFor(() => {
      expect(screen.getByText('登出所有其他裝置')).toBeInTheDocument();
    });
  });

  it('renders refresh button', async () => {
    renderSessionManagement();
    await waitFor(() => {
      expect(screen.getByLabelText('重新整理')).toBeInTheDocument();
    });
  });

  it('renders logout buttons for non-current sessions', async () => {
    renderSessionManagement();
    await waitFor(() => {
      // Two non-current sessions should have revoke buttons
      const logoutButtons = screen.getAllByText('登出');
      expect(logoutButtons.length).toBeGreaterThanOrEqual(2);
    });
  });

  it('renders empty state when no sessions', async () => {
    mockListSessions.mockResolvedValue({ sessions: [], total: 0 });
    renderSessionManagement();
    await waitFor(() => {
      expect(screen.getByText(/沒有活躍的 Session/)).toBeInTheDocument();
    });
  });

  it('does not render revoke all button when only current session exists', async () => {
    mockListSessions.mockResolvedValue({
      sessions: [mockSessions[0]], // only current session
      total: 1,
    });
    renderSessionManagement();
    await waitFor(() => {
      expect(screen.getByText(/共 1 個活躍裝置/)).toBeInTheDocument();
    });
    expect(screen.queryByText('登出所有其他裝置')).not.toBeInTheDocument();
  });
});

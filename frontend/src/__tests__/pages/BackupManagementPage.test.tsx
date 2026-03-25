/**
 * BackupManagementPage Tests
 *
 * Tests for the backup management page including:
 * - Page title rendering
 * - Statistics cards (database/attachment backup count, total size, Docker status)
 * - Tabs rendering (備份列表, 異地備份, 排程器, 備份日誌)
 * - Refresh button
 * - Create backup button
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/BackupManagementPage.test.tsx
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
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

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

const mockBackups = {
  database_backups: [
    { path: '/backup/db1.sql', filename: 'db1.sql', type: 'database', size_kb: 1024, created_at: '2026-03-01T00:00:00Z' },
  ],
  attachment_backups: [
    { path: '/backup/att1', dirname: 'att1', type: 'attachment', file_count: 10, created_at: '2026-03-01T00:00:00Z' },
  ],
  statistics: {
    database_backup_count: 3,
    attachment_backup_count: 2,
    total_size_mb: 150.5,
  },
};

const mockEnvStatus = {
  docker_available: true,
  docker_path: '/usr/bin/docker',
  last_success_time: '2026-03-01T00:00:00Z',
  consecutive_failures: 0,
  backup_dir_exists: true,
  uploads_dir_exists: true,
};

const mockRemoteConfig = {
  remote_path: '/mnt/backup',
  sync_enabled: true,
  sync_interval_hours: 24,
  sync_status: 'idle',
  last_sync_time: '2026-03-01T00:00:00Z',
};

const mockSchedulerStatus = {
  running: true,
  backup_time: '03:00',
  next_backup: '2026-03-15T03:00:00Z',
  last_backup: '2026-03-14T03:00:00Z',
  stats: {
    total_backups: 50,
    successful_backups: 48,
    failed_backups: 2,
  },
};

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>();
  return {
    ...actual,
    apiClient: {
      get: vi.fn().mockResolvedValue({}),
      post: vi.fn().mockImplementation((url: string) => {
        if (url === '/backup/environment-status') return Promise.resolve(mockEnvStatus);
        if (url === '/backup/list') return Promise.resolve(mockBackups);
        if (url === '/backup/remote-config') return Promise.resolve(mockRemoteConfig);
        if (url === '/backup/scheduler-status') return Promise.resolve(mockSchedulerStatus);
        if (url === '/backup/logs') return Promise.resolve({ logs: [], total: 0, page: 1, page_size: 20 });
        return Promise.resolve({});
      }),
      put: vi.fn().mockResolvedValue({}),
      patch: vi.fn().mockResolvedValue({}),
      delete: vi.fn().mockResolvedValue({}),
    },
  };
});

vi.mock('../../api/endpoints', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/endpoints')>();
  return {
    ...actual,
    API_ENDPOINTS: {
      ...actual.API_ENDPOINTS,
      BACKUP: {
      LIST: '/backup/list',
      CREATE: '/backup/create',
      DELETE: '/backup/delete',
      RESTORE: '/backup/restore',
      ENVIRONMENT_STATUS: '/backup/environment-status',
      REMOTE_CONFIG: '/backup/remote-config',
      REMOTE_CONFIG_UPDATE: '/backup/remote-config/update',
      REMOTE_SYNC: '/backup/remote-sync',
      CLEANUP: '/backup/cleanup',
      SCHEDULER_STATUS: '/backup/scheduler-status',
      SCHEDULER_START: '/backup/scheduler/start',
      SCHEDULER_STOP: '/backup/scheduler/stop',
      LOGS: '/backup/logs',
    },
    },
  };
});

vi.mock('@ck-shared/ui-components', () => ({
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('../../components/common', () => ({
  ResponsiveTable: (props: { dataSource: unknown[] }) => (
    <div data-testid="mock-responsive-table">
      Table ({(props.dataSource as unknown[]).length} rows)
    </div>
  ),
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderBackupManagementPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <React.Suspense fallback={<div>Loading...</div>}>
              <BackupManagementPageWrapper />
            </React.Suspense>
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function BackupManagementPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/BackupManagementPage').then((mod) => {
      setPage(() => mod.BackupManagementPage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('BackupManagementPage', () => {
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
    renderBackupManagementPage();
    await waitFor(() => {
      // Title is an h2 element
      const headings = screen.getAllByText('備份管理');
      expect(headings.length).toBeGreaterThanOrEqual(1);
      // Verify the h2 page title exists
      const h2 = headings.find(el => el.tagName === 'H2');
      expect(h2).toBeDefined();
    }, WAIT_OPTS);
  });

  it('renders the subtitle', async () => {
    renderBackupManagementPage();
    await waitFor(() => {
      expect(screen.getByText('管理系統備份、異地同步與排程設定')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders refresh button', async () => {
    renderBackupManagementPage();
    await waitFor(() => {
      expect(screen.getByText('重新整理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders statistics card titles', async () => {
    renderBackupManagementPage();
    await waitFor(() => {
      // Statistics cards use Statistic component with title prop
      expect(screen.getByText('總備份大小')).toBeInTheDocument();
      expect(screen.getByText('Docker 狀態')).toBeInTheDocument();
      // "資料庫備份" and "附件備份" appear in both statistics and tab content
      expect(screen.getAllByText('資料庫備份').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('附件備份').length).toBeGreaterThanOrEqual(1);
    }, WAIT_OPTS);
  });

  it('renders tab labels', async () => {
    renderBackupManagementPage();
    await waitFor(() => {
      expect(screen.getByText('備份列表')).toBeInTheDocument();
      expect(screen.getByText('異地備份')).toBeInTheDocument();
      expect(screen.getByText('排程器')).toBeInTheDocument();
      expect(screen.getByText('備份日誌')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders create backup button on default list tab', async () => {
    renderBackupManagementPage();
    await waitFor(() => {
      expect(screen.getByText('立即備份')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders backup tables on list tab', async () => {
    renderBackupManagementPage();
    await waitFor(() => {
      // The backup list tab renders ResponsiveTable components
      const tables = screen.getAllByTestId('mock-responsive-table');
      expect(tables.length).toBeGreaterThanOrEqual(1);
    }, WAIT_OPTS);
  });

  it('switches to scheduler tab when clicked', async () => {
    renderBackupManagementPage();
    await waitFor(() => {
      expect(screen.getByText('排程器')).toBeInTheDocument();
    }, WAIT_OPTS);

    fireEvent.click(screen.getByText('排程器'));
    await waitFor(() => {
      expect(screen.getByText('排程器狀態')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

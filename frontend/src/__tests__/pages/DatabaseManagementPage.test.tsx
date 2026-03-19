/**
 * DatabaseManagementPage Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({ data: { tables: [], size: '0 MB', version: '16' } }),
  },
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    DATABASE: {
      INFO: '/database/info',
      TABLES: '/database/tables',
      TABLE_DATA: vi.fn(() => '/database/table-data'),
      QUERY: '/database/query',
      INTEGRITY: '/database/integrity',
    },
  },
}));

vi.mock('@ck-shared/ui-components', () => ({
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('../../components/admin/SimpleDatabaseViewer', () => ({
  SimpleDatabaseViewer: () => <div data-testid="mock-db-viewer">DBViewer</div>,
}));

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

describe('DatabaseManagementPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/DatabaseManagementPage');
    renderWithProviders(<mod.DatabaseManagementPage />);
    expect(screen.getAllByText(/資料庫管理/).length).toBeGreaterThan(0);
  });
});

/**
 * SimpleDatabaseViewer Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import { createTestQueryClient } from '../../test/testUtils';

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({
      name: 'ck_documents',
      size: '8597 kB',
      status: 'healthy',
      totalRecords: 15,
      tables: [],
    }),
    put: vi.fn().mockResolvedValue({}),
    patch: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    ADMIN_DATABASE: {
      INFO: '/admin/database/info',
    },
  },
}));

vi.mock('../../config/databaseMetadata', () => ({
  databaseMetadata: { table_metadata: {} },
  getCategoryDisplayName: vi.fn((cat: string) => cat),
  getCategoryColor: vi.fn(() => '#1890ff'),
}));

import { SimpleDatabaseViewer } from '../../components/admin/SimpleDatabaseViewer';

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

describe('SimpleDatabaseViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderWithProviders(<SimpleDatabaseViewer />);
  });

  it('displays title heading', () => {
    const { container } = renderWithProviders(<SimpleDatabaseViewer />);
    const heading = container.querySelector('h3');
    expect(heading).toBeTruthy();
  });
});

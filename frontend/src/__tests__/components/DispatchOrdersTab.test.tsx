/**
 * DispatchOrdersTab Smoke Test
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
    post: vi.fn().mockResolvedValue({}),
    put: vi.fn().mockResolvedValue({}),
    patch: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
  useTaoyuanDispatchOrders: vi.fn(() => ({
    dispatchOrders: [],
    isLoading: false,
    refetch: vi.fn(),
  })),
}));

vi.mock('../../hooks/utility/useTableColumnSearch', () => ({
  useTableColumnSearch: vi.fn(() => ({
    searchText: '',
    searchedColumn: '',
    getColumnSearchProps: vi.fn(() => ({})),
  })),
}));

vi.mock('../../api/taoyuanDispatchApi', () => ({
  dispatchOrdersApi: {
    importExcel: vi.fn().mockResolvedValue({ success: true, imported_count: 0 }),
    downloadImportTemplate: vi.fn(),
    batchSetBatch: vi.fn(),
  },
}));

vi.mock('../../components/common', () => ({
  ResponsiveTable: (props: Record<string, unknown>) => (
    <div data-testid="mock-responsive-table">
      Table with {Array.isArray(props.dataSource) ? (props.dataSource as unknown[]).length : 0} rows
    </div>
  ),
}));

vi.mock('../../components/taoyuan/dispatchOrders/useDispatchOrderColumns', () => ({
  useDispatchOrderColumns: vi.fn(() => [
    { title: '派工單號', dataIndex: 'dispatch_no', key: 'dispatch_no' },
  ]),
}));

vi.mock('../../components/taoyuan/dispatchOrders/useDispatchOrderExport', () => ({
  useDispatchOrderExport: vi.fn(() => ({
    exporting: false,
    exportProgress: null,
    handleExportMasterExcel: vi.fn(),
  })),
}));

import { DispatchOrdersTab } from '../../components/taoyuan/DispatchOrdersTab';

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

describe('DispatchOrdersTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderWithProviders(<DispatchOrdersTab contractProjectId={1} contractCode="TEST-001" />);
  });

  it('displays statistics headers', () => {
    const { getByText } = renderWithProviders(
      <DispatchOrdersTab contractProjectId={1} contractCode="TEST-001" />,
    );
    expect(getByText('總派工單數')).toBeInTheDocument();
  });
});

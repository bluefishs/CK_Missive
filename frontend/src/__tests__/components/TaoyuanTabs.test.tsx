/**
 * Taoyuan Tab Components - Smoke Render Tests
 *
 * Tests: DispatchOrdersTab, ProjectsTab, PaymentsTab
 * Verifies each tab component renders without crashing with empty data.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
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
  useTaoyuanProjects: vi.fn(() => ({
    projects: [],
    isLoading: false,
    refetch: vi.fn(),
  })),
  useTaoyuanPaymentControl: vi.fn(() => ({
    items: [],
    contractName: 'Test Contract',
    totalBudget: 10000000,
    totalDispatched: 5000000,
    totalClaimed: 3000000,
    isLoading: false,
    refetch: vi.fn(),
  })),
  useTableColumnSearch: vi.fn(() => ({
    searchText: '',
    searchedColumn: '',
    getColumnSearchProps: vi.fn(() => ({})),
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
  taoyuanProjectsApi: {
    importExcel: vi.fn().mockResolvedValue({ success: true, imported_count: 0 }),
    downloadImportTemplate: vi.fn(),
  },
}));

vi.mock('../../components/common', () => ({
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  ResponsiveTable: (props: Record<string, unknown>) => (
    <div data-testid="mock-responsive-table">
      Table with {Array.isArray(props.dataSource) ? (props.dataSource as unknown[]).length : 0} rows
    </div>
  ),
}));

vi.mock('../../constants/taoyuanOptions', () => ({
  TAOYUAN_CONTRACT: { PROJECT_ID: 1, CODE: 'TEST-001' },
  DISTRICT_OPTIONS: [
    { value: '桃園區', label: '桃園區' },
    { value: '中壢區', label: '中壢區' },
  ],
  CASE_TYPE_OPTIONS: [
    { value: '一般', label: '一般' },
    { value: '特殊', label: '特殊' },
  ],
}));

// Mock Highlighter
vi.mock('react-highlight-words', () => ({
  default: ({ textToHighlight }: { textToHighlight: string }) => <span>{textToHighlight}</span>,
}));

// Mock dispatch order sub-hooks
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

// Mock payment sub-modules
vi.mock('../../components/taoyuan/payments/usePaymentColumns', () => ({
  WORK_TYPE_COLUMNS: [
    { key: 'wt1', label: '地上物', amountField: 'amount_wt1', color: '#e6f7ff' },
    { key: 'wt2', label: '土地協議', amountField: 'amount_wt2', color: '#f0f5ff' },
  ],
  formatAmount: vi.fn((val?: number) => val != null ? val.toLocaleString() : '-'),
  usePaymentColumns: vi.fn(() => [
    { title: '派工單號', dataIndex: 'dispatch_no', key: 'dispatch_no' },
  ]),
}));

vi.mock('../../components/taoyuan/payments/paymentExport', () => ({
  exportPaymentExcel: vi.fn(),
}));

// ============================================================================
// Imports (after mocks)
// ============================================================================

import { DispatchOrdersTab } from '../../components/taoyuan/DispatchOrdersTab';
import { ProjectsTab } from '../../components/taoyuan/ProjectsTab';
import { PaymentsTab } from '../../components/taoyuan/PaymentsTab';

// ============================================================================
// Helpers
// ============================================================================

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
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

describe('DispatchOrdersTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderWithProviders(
      <DispatchOrdersTab contractProjectId={1} contractCode="TEST-001" />,
    );
    // Should show statistics headers
    expect(screen.getByText('總派工單數')).toBeInTheDocument();
  });

  it('shows statistics cards with zero values', () => {
    renderWithProviders(
      <DispatchOrdersTab contractProjectId={1} contractCode="TEST-001" />,
    );
    expect(screen.getByText('關聯公文')).toBeInTheDocument();
    expect(screen.getByText('關聯工程')).toBeInTheDocument();
    expect(screen.getByText('作業類別數')).toBeInTheDocument();
  });

  it('renders search input', () => {
    renderWithProviders(
      <DispatchOrdersTab contractProjectId={1} contractCode="TEST-001" />,
    );
    expect(screen.getByPlaceholderText('搜尋派工單號、工程名稱')).toBeInTheDocument();
  });

  it('renders action buttons', () => {
    renderWithProviders(
      <DispatchOrdersTab contractProjectId={1} contractCode="TEST-001" />,
    );
    expect(screen.getByText('新增派工單')).toBeInTheDocument();
    expect(screen.getByText('Excel 匯入')).toBeInTheDocument();
    expect(screen.getByText('匯出總表')).toBeInTheDocument();
  });

  it('shows hint text about clicking rows', () => {
    renderWithProviders(
      <DispatchOrdersTab contractProjectId={1} contractCode="TEST-001" />,
    );
    expect(screen.getByText('點擊列表項目可進入詳情頁進行編輯')).toBeInTheDocument();
  });
});

describe('ProjectsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderWithProviders(<ProjectsTab contractProjectId={1} />);
    expect(screen.getByText('總工程數')).toBeInTheDocument();
  });

  it('shows statistics cards', () => {
    renderWithProviders(<ProjectsTab contractProjectId={1} />);
    expect(screen.getByText('已派工')).toBeInTheDocument();
    expect(screen.getByText('已完成')).toBeInTheDocument();
    expect(screen.getByText('完成率')).toBeInTheDocument();
  });

  it('renders search input', () => {
    renderWithProviders(<ProjectsTab contractProjectId={1} />);
    expect(screen.getByPlaceholderText('搜尋工程名稱、承辦人')).toBeInTheDocument();
  });

  it('renders action buttons', () => {
    renderWithProviders(<ProjectsTab contractProjectId={1} />);
    expect(screen.getByText('新增工程')).toBeInTheDocument();
    expect(screen.getByText('Excel 匯入')).toBeInTheDocument();
  });

  it('shows hint text', () => {
    renderWithProviders(<ProjectsTab contractProjectId={1} />);
    expect(screen.getByText('點擊列表項目可進入詳情頁進行編輯')).toBeInTheDocument();
  });
});

describe('PaymentsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderWithProviders(<PaymentsTab contractProjectId={1} />);
    expect(screen.getByText('Test Contract')).toBeInTheDocument();
  });

  it('shows budget and financial stats', () => {
    renderWithProviders(<PaymentsTab contractProjectId={1} />);
    expect(screen.getByText('總預算金額')).toBeInTheDocument();
    expect(screen.getByText('累計派工金額')).toBeInTheDocument();
    expect(screen.getByText('剩餘金額')).toBeInTheDocument();
    expect(screen.getByText('已請款金額')).toBeInTheDocument();
  });

  it('shows dispatch count and claim rate', () => {
    renderWithProviders(<PaymentsTab contractProjectId={1} />);
    expect(screen.getByText('派工單數')).toBeInTheDocument();
    expect(screen.getByText('請款率')).toBeInTheDocument();
  });

  it('renders work type statistics section', () => {
    renderWithProviders(<PaymentsTab contractProjectId={1} />);
    expect(screen.getByText('作業類別派工金額統計')).toBeInTheDocument();
  });

  it('renders action buttons', () => {
    renderWithProviders(<PaymentsTab contractProjectId={1} />);
    expect(screen.getByText('重新整理')).toBeInTheDocument();
    expect(screen.getByText('匯出 Excel')).toBeInTheDocument();
  });

  it('shows contract amount', () => {
    renderWithProviders(<PaymentsTab contractProjectId={1} />);
    expect(screen.getByText('契約金額：')).toBeInTheDocument();
    expect(screen.getByText('$10,000,000')).toBeInTheDocument();
  });
});

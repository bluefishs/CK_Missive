/**
 * PaymentsTab Smoke Test
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
  useTaoyuanPaymentControl: vi.fn(() => ({
    items: [],
    contractName: 'Test Contract',
    totalBudget: 10000000,
    totalDispatched: 5000000,
    totalClaimed: 3000000,
    isLoading: false,
    refetch: vi.fn(),
  })),
}));

vi.mock('../../components/taoyuan/payments/usePaymentColumns', () => ({
  WORK_TYPE_COLUMNS: [
    { key: 'wt1', label: '地上物', amountField: 'amount_wt1', color: '#e6f7ff' },
  ],
  formatAmount: vi.fn((val?: number) => (val != null ? val.toLocaleString() : '-')),
  usePaymentColumns: vi.fn(() => [
    { title: '派工單號', dataIndex: 'dispatch_no', key: 'dispatch_no' },
  ]),
}));

vi.mock('../../components/taoyuan/payments/paymentExport', () => ({
  exportPaymentExcel: vi.fn(),
}));

import { PaymentsTab } from '../../components/taoyuan/PaymentsTab';

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

describe('PaymentsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderWithProviders(<PaymentsTab contractProjectId={1} />);
  });

  it('displays contract name', () => {
    const { getByText } = renderWithProviders(<PaymentsTab contractProjectId={1} />);
    expect(getByText('Test Contract')).toBeInTheDocument();
  });
});

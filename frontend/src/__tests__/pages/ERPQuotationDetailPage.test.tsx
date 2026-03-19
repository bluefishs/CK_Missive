/**
 * ERPQuotationDetailPage Tests
 *
 * Tests for the ERP quotation detail page including:
 * - Loading spinner display
 * - Quotation not found display
 * - Detail rendering with financial statistics
 * - Tab rendering (cost structure, invoices, billings, vendor payables)
 * - Back navigation
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/ERPQuotationDetailPage.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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

const mockNavigate = vi.fn();
const mockParams: Record<string, string> = { id: '1' };
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => mockParams,
  };
});

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

const mockUseERPQuotation = vi.fn((): { data: Record<string, unknown> | null | undefined; isLoading: boolean } => ({
  data: {
    id: 1,
    case_code: 'CK2025_FN_01_001',
    case_name: '報價案件A',
    year: 114,
    total_price: '2000000',
    tax_amount: '100000',
    outsourcing_fee: '500000',
    personnel_fee: '300000',
    overhead_fee: '200000',
    other_cost: '50000',
    status: 'confirmed' as const,
    notes: '備註內容',
    created_by: 1,
    created_at: '2025-01-01',
    updated_at: '2025-01-15',
    total_cost: '1150000',
    gross_profit: '850000',
    gross_margin: '42.5',
    net_profit: '750000',
    invoice_count: 3,
    billing_count: 2,
    total_billed: '1000000',
    total_received: '800000',
    total_payable: '400000',
    total_paid: '300000',
  },
  isLoading: false,
}));

vi.mock('../../hooks', () => ({
  useAuthGuard: () => ({ hasPermission: () => true }),
  useResponsive: () => ({ isMobile: false, isTablet: false, isDesktop: true, breakpoint: 'lg' }),
  useERPQuotation: (..._args: unknown[]) => mockUseERPQuotation(),
}));

vi.mock('../../pages/erpQuotation', () => ({
  InvoicesTab: ({ erpQuotationId }: { erpQuotationId: number }) => (
    <div data-testid="mock-invoices-tab">InvoicesTab (id: {erpQuotationId})</div>
  ),
  BillingsTab: ({ erpQuotationId }: { erpQuotationId: number }) => (
    <div data-testid="mock-billings-tab">BillingsTab (id: {erpQuotationId})</div>
  ),
  VendorPayablesTab: ({ erpQuotationId }: { erpQuotationId: number }) => (
    <div data-testid="mock-vendor-payables-tab">VendorPayablesTab (id: {erpQuotationId})</div>
  ),
  ProfitTrendTab: () => (
    <div data-testid="mock-profit-trend-tab">ProfitTrendTab</div>
  ),
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <PageWrapper />
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function PageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/ERPQuotationDetailPage').then((mod) => {
      setPage(() => mod.ERPQuotationDetailPage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('ERPQuotationDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockParams.id = '1';
  });

  it('renders loading spinner when data is loading', async () => {
    mockUseERPQuotation.mockReturnValueOnce({ data: undefined, isLoading: true });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('載入中...')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders quotation not found when data is null', async () => {
    mockUseERPQuotation.mockReturnValueOnce({ data: null, isLoading: false });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('報價不存在')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders quotation title with case code and name', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('CK2025_FN_01_001 - 報價案件A')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders status tag', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('已確認')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders back button', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('返回')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('navigates back when back button is clicked', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('返回')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('返回'));
    expect(mockNavigate).toHaveBeenCalledWith('/erp/quotations');
  });

  it('renders financial statistic cards', async () => {
    renderPage();
    await waitFor(() => {
      // Some labels like "總價" appear in both Statistic cards and Descriptions, so check at least one exists
      expect(screen.getAllByText('總價').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('成本')).toBeInTheDocument();
      expect(screen.getByText('毛利率')).toBeInTheDocument();
      expect(screen.getByText('已請款')).toBeInTheDocument();
      expect(screen.getByText('已收款')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders cost structure tab', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('成本結構')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders invoices tab label with count', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('發票 (3)')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders billings tab label with count', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('請款 (2)')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders vendor payables tab', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('廠商應付')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders cost description items in info tab', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('備註內容')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

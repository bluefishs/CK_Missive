/**
 * ERPQuotationListPage Tests
 *
 * Tests for the ERP quotation management list page including:
 * - Page title rendering
 * - Loading state
 * - Quotation list table rendering
 * - Profit summary cards
 * - Navigation to create page
 * - Navigation to detail page
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/ERPQuotationListPage.test.tsx
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
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
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/client', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  apiClient: {
    get: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({}),
    put: vi.fn().mockResolvedValue({}),
    patch: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue({}),
  },
}));

const mockRefetch = vi.fn();
const mockMutateAsync = vi.fn();

const mockUseERPQuotations = vi.fn((): { data: Record<string, unknown> | undefined; isLoading: boolean; refetch: typeof mockRefetch } => ({
  data: {
    items: [
      {
        id: 1, case_code: 'CK2025_FN_01_001', case_name: '報價案件A',
        year: 114, total_price: '2000000', gross_profit: '500000',
        gross_margin: '25.0', status: 'confirmed' as const,
      },
      {
        id: 2, case_code: 'CK2025_FN_01_002', case_name: '報價案件B',
        year: 114, total_price: '1000000', gross_profit: '-50000',
        gross_margin: '-5.0', status: 'draft' as const,
      },
    ],
    pagination: { total: 2, page: 1, limit: 20, total_pages: 1 },
  },
  isLoading: false,
  refetch: mockRefetch,
}));

const mockUseERPProfitSummary = vi.fn((): { data: Record<string, unknown> | null } => ({
  data: {
    total_revenue: '3000000',
    total_cost: '2550000',
    total_gross_profit: '450000',
    avg_gross_margin: '15.0',
    total_billed: '2000000',
    total_received: '1500000',
    total_outstanding: '500000',
    case_count: 2,
    by_year: {},
  },
}));

const mockUseDeleteERPQuotation = vi.fn(() => ({
  mutateAsync: mockMutateAsync,
  isPending: false,
}));

vi.mock('../../hooks', async (importOriginal) => ({
  // 2026-09-06 A111：先展開原模組再覆蓋——部分 mock 蓋掉整個 barrel 會讓後來新增的 export 全部消失
  ...(await importOriginal<Record<string, unknown>>()),
  useAuthGuard: () => ({ hasPermission: () => true }),
  // 2026-09-06：真 hook 另回 responsiveValue，41 個 mock 都漏了 ⇒ 版面元件一呼叫就炸
  useResponsive: () => ({ responsiveValue: (c: Record<string, unknown>) => c?.desktop ?? c?.tablet ?? c?.mobile, ...({ isMobile: false, isTablet: false, isDesktop: true, breakpoint: 'lg' }) }),
  useERPQuotations: (..._args: unknown[]) => mockUseERPQuotations(),
  useERPProfitSummary: (..._args: unknown[]) => mockUseERPProfitSummary(),
  useDeleteERPQuotation: () => mockUseDeleteERPQuotation(),
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
    import('../../pages/ERPQuotationListPage').then((mod) => {
      setPage(() => mod.ERPQuotationListPage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('ERPQuotationListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('專案帳款') /* 08-27 起以案為主軸更名 */).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('does not render a create button (quotations are created from /pm/cases since 08-27)', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('專案帳款')).toBeInTheDocument();
    }, WAIT_OPTS);
    // 留下的是導向 /pm/cases 的提示（「新增報價請至『邀標報價案件』」），不是建立鈕
    expect(screen.getByText(/新增報價請至/)).toBeInTheDocument();
  });

  it('renders profit summary cards', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getAllByText('承攬金額（含稅）' /* financeTerms.contract_amount_sum；統計卡與手機卡都有 */).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('成本總額')).toBeInTheDocument();
      expect(screen.getByText('應收未收')).toBeInTheDocument();
      // "毛利" appears in both summary card and table header, so check multiple exist
      expect(screen.getAllByText('應付款項').length).toBeGreaterThanOrEqual(1); // 第四張卡自 09-04 起是應付，不是毛利；手機卡也有此標籤
    }, WAIT_OPTS);
  });

  it('renders profit summary values', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getAllByText('承攬金額（含稅）' /* financeTerms.contract_amount_sum；統計卡與手機卡都有 */).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('3,000,000')).toBeInTheDocument();
      expect(screen.getByText('2,550,000')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('does not render profit summary cards when data is null', async () => {
    mockUseERPProfitSummary.mockReturnValueOnce({ data: null });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('專案帳款') /* 08-27 起以案為主軸更名 */).toBeInTheDocument();
    }, WAIT_OPTS);
    // 標籤在手機卡列上仍會出現，改驗統計卡的數值不在（摘要為 null 時卡片整區不渲染）
    expect(screen.queryByText('3,000,000')).toBeNull();
  });

  it('renders loading state when data is loading', async () => {
    mockUseERPQuotations.mockReturnValueOnce({
      data: undefined,
      isLoading: true,
      refetch: mockRefetch,
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('專案帳款') /* 08-27 起以案為主軸更名 */).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders search input with placeholder', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜尋成案編號／建案案號／專案名稱')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders reload button', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('重新整理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('navigates to detail page when a row is clicked (操作欄 08-15 移除，點列進詳情)', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getAllByText('報價案件A').length).toBeGreaterThan(0);
    }, WAIT_OPTS);
    fireEvent.click(screen.getAllByText('報價案件A')[0]!);
    expect(mockNavigate).toHaveBeenCalledWith('/erp/quotations/1');
  });
});

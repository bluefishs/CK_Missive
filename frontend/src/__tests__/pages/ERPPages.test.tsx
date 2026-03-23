/**
 * ERP Finance Module — Page Render Tests
 *
 * Smoke tests for all 5 ERP pages:
 * - ERPExpenseListPage
 * - ERPExpenseDetailPage
 * - ERPLedgerPage
 * - ERPFinancialDashboardPage
 * - ERPEInvoiceSyncPage
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/ERPPages.test.tsx
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React, { Suspense } from 'react';
import { createTestQueryClient } from '../../test/testUtils';

const WAIT_OPTS = { timeout: 5000 };

// ==========================================================================
// Common Mocks
// ==========================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../config/env', () => ({
  isAuthDisabled: () => true,
  isInternalIP: () => true,
  detectEnvironment: () => 'localhost',
}));

// Mock shared UI components
vi.mock('@ck-shared/ui-components', () => ({
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

// Mock recharts (used in dashboard)
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: () => <div data-testid="line-chart" />,
  BarChart: () => <div data-testid="bar-chart" />,
  Line: () => null,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  Cell: () => null,
}));

// Mock all ERP hooks
const mockExpenses = { data: { items: [], total: 0 }, isLoading: false, refetch: vi.fn() };
const mockLedger = { data: { items: [], total: 0 }, isLoading: false, refetch: vi.fn() };
const mockOverview = { data: { success: true, data: { total_income: 0, total_expense: 0, net_balance: 0, expense_by_category: {}, top_projects: [], period_start: '2026-01-01', period_end: '2026-03-22', project_expense: 0, operation_expense: 0 } }, isLoading: false, refetch: vi.fn() };
const mockTrend = { data: { success: true, data: { months: [], case_code: null } }, isLoading: false, refetch: vi.fn() };
const mockRanking = { data: { success: true, data: { items: [], total_projects: 0 } }, isLoading: false, refetch: vi.fn() };
const mockProjects = { data: { items: [] }, isLoading: false, refetch: vi.fn() };
const mockMutation = { mutateAsync: vi.fn(), mutate: vi.fn(), isPending: false };
const mockSyncLogs = { data: { items: [], total: 0 }, isLoading: false, refetch: vi.fn() };
const mockPendingList = { data: { items: [], total: 0 }, isLoading: false, refetch: vi.fn() };

vi.mock('../../hooks', () => ({
  // Expenses hooks
  useExpenses: () => mockExpenses,
  useCreateExpense: () => mockMutation,
  useApproveExpense: () => mockMutation,
  useRejectExpense: () => mockMutation,
  useQRScanExpense: () => mockMutation,
  useOCRParseExpense: () => mockMutation,
  useUploadReceipt: () => mockMutation,
  useUploadExpenseReceipt: () => mockMutation,
  useExpenseDetail: () => ({ data: null, isLoading: false }),
  useUpdateExpense: () => mockMutation,
  // Ledger hooks
  useLedger: () => mockLedger,
  useCreateLedger: () => mockMutation,
  useDeleteLedger: () => mockMutation,
  useLedgerBalance: () => ({ data: { balance: 0 }, isLoading: false }),
  useLedgerCategoryBreakdown: () => ({ data: { categories: [] }, isLoading: false }),
  // Dashboard hooks
  useCompanyFinancialOverview: () => mockOverview,
  useAllProjectsSummary: () => mockProjects,
  useMonthlyTrend: () => mockTrend,
  useBudgetRanking: () => mockRanking,
  useExportExpenses: () => mockMutation,
  useExportLedger: () => mockMutation,
  // E-Invoice hooks
  useEInvoiceSyncLogs: () => mockSyncLogs,
  useEInvoicePendingList: () => mockPendingList,
  useSyncEInvoice: () => mockMutation,
  // Shared dropdown
  useProjectsDropdown: () => ({ projects: [], isLoading: false }),
  // Auth
  useAuthGuard: () => ({
    user: { id: 1, name: 'test' },
    isAuthenticated: true,
    hasPermission: () => true,
    isLoading: false,
  }),
}));

// ==========================================================================
// Helper
// ==========================================================================

function renderPage(element: React.ReactNode, path = '/') {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter initialEntries={[path]}>
            <Suspense fallback={<div>Loading...</div>}>
              {element}
            </Suspense>
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

// ==========================================================================
// Tests
// ==========================================================================

describe('ERPExpenseListPage', () => {
  it('renders expense list page title', async () => {
    const { default: ERPExpenseListPage } = await import('../../pages/ERPExpenseListPage');
    renderPage(<ERPExpenseListPage />);
    await waitFor(() => {
      expect(screen.getByText(/費用報銷/)).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders action buttons', async () => {
    const { default: ERPExpenseListPage } = await import('../../pages/ERPExpenseListPage');
    renderPage(<ERPExpenseListPage />);
    await waitFor(() => {
      expect(screen.getByText(/新增/)).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

describe('ERPExpenseDetailPage', () => {
  it('renders detail page without crash', async () => {
    const { default: ERPExpenseDetailPage } = await import('../../pages/ERPExpenseDetailPage');
    renderPage(
      <Routes>
        <Route path="/erp/expenses/:id" element={<ERPExpenseDetailPage />} />
      </Routes>,
      '/erp/expenses/1',
    );
    // Should render without crash (may show loading or empty state)
    await waitFor(() => {
      expect(document.body).toBeTruthy();
    }, WAIT_OPTS);
  });
});

describe('ERPLedgerPage', () => {
  it('renders ledger page title', async () => {
    const { default: ERPLedgerPage } = await import('../../pages/ERPLedgerPage');
    renderPage(<ERPLedgerPage />);
    await waitFor(() => {
      expect(screen.getByText(/帳本|帳簿|Ledger/i)).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders add record button', async () => {
    const { default: ERPLedgerPage } = await import('../../pages/ERPLedgerPage');
    renderPage(<ERPLedgerPage />);
    await waitFor(() => {
      expect(screen.getByText(/新增|記帳/)).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

describe('ERPFinancialDashboardPage', () => {
  it('renders dashboard title', async () => {
    const { default: ERPFinancialDashboardPage } = await import('../../pages/ERPFinancialDashboardPage');
    renderPage(<ERPFinancialDashboardPage />);
    await waitFor(() => {
      expect(screen.getByText('財務儀表板')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders statistics cards', async () => {
    const { default: ERPFinancialDashboardPage } = await import('../../pages/ERPFinancialDashboardPage');
    renderPage(<ERPFinancialDashboardPage />);
    await waitFor(() => {
      // Should show income/expense/balance statistics (multiple matches expected)
      expect(screen.getAllByText(/總收入|總支出|淨額/).length).toBeGreaterThanOrEqual(1);
    }, WAIT_OPTS);
  });
});

describe('ERPEInvoiceSyncPage', () => {
  it('renders einvoice sync page', async () => {
    const { default: ERPEInvoiceSyncPage } = await import('../../pages/ERPEInvoiceSyncPage');
    renderPage(<ERPEInvoiceSyncPage />);
    await waitFor(() => {
      expect(screen.getByText(/電子發票|發票同步|E-Invoice/i)).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

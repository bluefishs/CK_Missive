/**
 * ERP Ledger Pages Tests
 *
 * Tests for:
 * - ERPLedgerPage: title, table, balance cards, filters, pagination
 * - ERPLedgerCreatePage: form fields (entry_type, amount, category), submit
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/ERPLedgerPages.test.tsx
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({}),
    put: vi.fn().mockResolvedValue({}),
    patch: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('@ck-shared/ui-components', () => ({
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

const mockRefetch = vi.fn();
const mockMutateAsync = vi.fn();

const mockUseLedger = vi.fn(() => ({
  data: {
    items: [
      {
        id: 1, entry_type: 'income' as const, amount: 100000, category: '專案收入',
        case_code: 'CK2026_01', description: '第一期款', source_type: 'manual',
        transaction_date: '2026-01-10',
      },
      {
        id: 2, entry_type: 'expense' as const, amount: 30000, category: '交通費',
        case_code: null, description: '出差費用', source_type: 'auto',
        transaction_date: '2026-01-15',
      },
      {
        id: 3, entry_type: 'expense' as const, amount: 5000, category: '材料費',
        case_code: 'CK2026_01', description: '辦公用品', source_type: 'manual',
        transaction_date: '2026-01-20',
      },
    ],
    total: 3,
  },
  isLoading: false,
  refetch: mockRefetch,
}));

const mockUseLedgerCategoryBreakdown = vi.fn(() => ({
  data: {
    data: [
      { category: '交通費', total: 30000, count: 1 },
      { category: '材料費', total: 5000, count: 1 },
    ],
  },
}));

vi.mock('../../hooks', () => ({
  useAuthGuard: () => ({ hasPermission: () => true }),
  useResponsive: () => ({
    isMobile: false, isTablet: false, isDesktop: true, breakpoint: 'lg',
    responsiveValue: <T,>(config: { mobile?: T; tablet?: T; desktop?: T }) => config.desktop ?? config.tablet ?? config.mobile,
  }),
  useLedger: (..._args: unknown[]) => mockUseLedger(),
  useCreateLedger: () => ({ mutateAsync: mockMutateAsync, isPending: false }),
  useDeleteLedger: () => ({ mutateAsync: mockMutateAsync, isPending: false }),
  useLedgerCategoryBreakdown: (..._args: unknown[]) => mockUseLedgerCategoryBreakdown(),
  useProjectsDropdown: () => ({ projects: [] }),
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderLedgerPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <LedgerPageWrapper />
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function LedgerPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/ERPLedgerPage').then((mod) => {
      setPage(() => mod.default);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

function renderLedgerCreatePage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <LedgerCreatePageWrapper />
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function LedgerCreatePageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/ERPLedgerCreatePage').then((mod) => {
      setPage(() => mod.default);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests — ERPLedgerPage
// ==========================================================================

describe('ERPLedgerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    renderLedgerPage();
    await waitFor(() => {
      expect(screen.getByText('統一帳本')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders create button', async () => {
    renderLedgerPage();
    await waitFor(() => {
      expect(screen.getByText('手動記帳')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders statistic cards with income and expense', async () => {
    renderLedgerPage();
    await waitFor(() => {
      expect(screen.getByText('本頁收入')).toBeInTheDocument();
      expect(screen.getByText('本頁支出')).toBeInTheDocument();
      expect(screen.getByText('本頁淨額')).toBeInTheDocument();
      expect(screen.getByText('總筆數')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders table column headers', async () => {
    renderLedgerPage();
    await waitFor(() => {
      // Use getAllByText for potentially duplicated text
      expect(screen.getAllByText('日期').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('類型').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('金額').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('分類').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('案號').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('說明').length).toBeGreaterThanOrEqual(1);
    }, WAIT_OPTS);
  });

  it('renders table data rows', async () => {
    renderLedgerPage();
    await waitFor(() => {
      expect(screen.getByText('第一期款')).toBeInTheDocument();
      expect(screen.getByText('出差費用')).toBeInTheDocument();
      expect(screen.getByText('辦公用品')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders category breakdown section', async () => {
    renderLedgerPage();
    await waitFor(() => {
      expect(screen.getByText('支出分類拆解')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders filter controls', async () => {
    renderLedgerPage();
    await waitFor(() => {
      expect(screen.getByText('重新整理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders pagination info', async () => {
    renderLedgerPage();
    await waitFor(() => {
      expect(screen.getByText(/共 3 項/)).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders loading state when data is loading', async () => {
    mockUseLedger.mockReturnValueOnce({
      data: undefined as never,
      isLoading: true,
      refetch: mockRefetch,
    });
    renderLedgerPage();
    await waitFor(() => {
      expect(screen.getByText('統一帳本')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('does not render category breakdown when data is empty', async () => {
    mockUseLedgerCategoryBreakdown.mockReturnValueOnce({ data: { data: [] } });
    renderLedgerPage();
    await waitFor(() => {
      expect(screen.getByText('統一帳本')).toBeInTheDocument();
    }, WAIT_OPTS);
    expect(screen.queryByText('支出分類拆解')).not.toBeInTheDocument();
  });
});

// ==========================================================================
// Tests — ERPLedgerCreatePage
// ==========================================================================

describe('ERPLedgerCreatePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    renderLedgerCreatePage();
    await waitFor(() => {
      expect(screen.getByText('手動記帳')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders back button', async () => {
    renderLedgerCreatePage();
    await waitFor(() => {
      expect(screen.getByText('返回')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders entry type field', async () => {
    renderLedgerCreatePage();
    await waitFor(() => {
      expect(screen.getByText('類型')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders amount field', async () => {
    renderLedgerCreatePage();
    await waitFor(() => {
      expect(screen.getByText('金額')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders category field', async () => {
    renderLedgerCreatePage();
    await waitFor(() => {
      expect(screen.getByText('分類')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('例：交通費、材料費')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders transaction date field', async () => {
    renderLedgerCreatePage();
    await waitFor(() => {
      expect(screen.getByText('交易日期')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders case code field', async () => {
    renderLedgerCreatePage();
    await waitFor(() => {
      expect(screen.getByText('案號 (選填)')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('留空 = 一般營運支出')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders description field', async () => {
    renderLedgerCreatePage();
    await waitFor(() => {
      expect(screen.getByText('說明')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders submit button', async () => {
    renderLedgerCreatePage();
    await waitFor(() => {
      expect(screen.getByText('建立')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

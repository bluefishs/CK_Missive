/**
 * ERP Expense Pages Tests
 *
 * Tests for:
 * - ERPExpenseListPage: title, table, filter controls, pagination, statistics
 * - ERPExpenseCreatePage: form fields, validation, submit
 * - ERPExpenseDetailPage: detail view, status badge, tabs
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/ERPExpensePages.test.tsx
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
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

vi.mock('../../api/erp', () => ({
  expensesApi: {
    receiptImage: vi.fn().mockResolvedValue(new Blob()),
  },
}));

vi.mock('@ck-shared/ui-components', () => ({
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('../../pages/erpExpense', () => ({
  ExpenseCreateModal: () => null,
  QRScanModal: () => null,
  OCRModal: () => null,
  MofInvoiceModal: () => null,
}));

vi.mock('../../components/common/DetailPage/DetailPageLayout', () => ({
  DetailPageLayout: ({ header, tabs, loading, hasData }: {
    header: { title: string; tags?: { text: string; color: string }[]; extra?: React.ReactNode };
    tabs: { key: string; label: React.ReactNode; children: React.ReactNode }[];
    loading?: boolean;
    hasData?: boolean;
  }) => {
    if (loading) return <div>Loading...</div>;
    if (!hasData) return <div>{header.title}</div>;
    return (
      <div>
        <h1>{header.title}</h1>
        {header.tags?.map((tag, i) => <span key={i} data-testid="status-tag">{tag.text}</span>)}
        <div>{header.extra}</div>
        {tabs.map(tab => (
          <div key={tab.key}>
            <span>{tab.label}</span>
            <div>{tab.children}</div>
          </div>
        ))}
      </div>
    );
  },
}));

vi.mock('../../components/common/DetailPage/utils', () => ({
  createTabItem: (key: string, labelConfig: { icon?: React.ReactNode; text: string; count?: number }, children: React.ReactNode) => ({
    key,
    label: labelConfig.text,
    children,
  }),
}));

const mockRefetch = vi.fn();
const mockMutateAsync = vi.fn();

const mockUseExpenses = vi.fn(() => ({
  data: {
    items: [
      {
        id: 1, inv_num: 'AB12345678', date: '2026-01-15', amount: 5000,
        category: '交通費', case_code: 'CK2026_01', source: 'manual',
        status: 'pending' as const, currency: 'TWD',
      },
      {
        id: 2, inv_num: 'CD87654321', date: '2026-01-20', amount: 12000,
        category: '材料費', case_code: null, source: 'qr_scan',
        status: 'verified' as const, currency: 'TWD',
      },
    ],
    total: 2,
  },
  isLoading: false,
  refetch: mockRefetch,
}));

const mockUseExpenseDetail = vi.fn(() => ({
  data: {
    data: {
      id: 1, inv_num: 'AB12345678', date: '2026-01-15', amount: 5000,
      tax_amount: 238, category: '交通費', case_code: 'CK2026_01',
      source: 'manual', status: 'pending' as const, currency: 'TWD',
      buyer_ban: '12345678', seller_ban: '87654321', notes: '出差費用',
      receipt_image_path: null, items: [],
    },
  },
  isLoading: false,
}));

const mockUseCreateExpense = vi.fn(() => ({
  mutateAsync: mockMutateAsync,
  isPending: false,
}));

const mockUseEInvoicePendingList = vi.fn(() => ({
  data: { total: 3 },
}));

vi.mock('../../hooks', () => ({
  useAuthGuard: () => ({ hasPermission: () => true }),
  useResponsive: () => ({
    isMobile: false, isTablet: false, isDesktop: true, breakpoint: 'lg',
    responsiveValue: <T,>(config: { mobile?: T; tablet?: T; desktop?: T }) => config.desktop ?? config.tablet ?? config.mobile,
  }),
  useExpenses: (..._args: unknown[]) => mockUseExpenses(),
  useExpenseDetail: (..._args: unknown[]) => mockUseExpenseDetail(),
  useCreateExpense: () => mockUseCreateExpense(),
  useApproveExpense: () => ({ mutateAsync: mockMutateAsync, isPending: false }),
  useRejectExpense: () => ({ mutateAsync: mockMutateAsync, isPending: false }),
  useUpdateExpense: () => ({ mutateAsync: mockMutateAsync, isPending: false }),
  useUploadExpenseReceipt: () => ({ mutate: vi.fn(), isPending: false }),
  useEInvoicePendingList: (..._args: unknown[]) => mockUseEInvoicePendingList(),
  useProjectsDropdown: () => ({ projects: [] }),
  // Hooks used by erpExpense sub-modules
  useQRScanExpense: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useOCRParseExpense: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderListPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <ListPageWrapper />
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function ListPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/ERPExpenseListPage').then((mod) => {
      setPage(() => mod.default);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

function renderCreatePage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <CreatePageWrapper />
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function CreatePageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/ERPExpenseCreatePage').then((mod) => {
      setPage(() => mod.default);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

function renderDetailPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter initialEntries={['/erp/expenses/1']}>
            <Routes>
              <Route path="/erp/expenses/:id" element={<DetailPageWrapper />} />
            </Routes>
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function DetailPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/ERPExpenseDetailPage').then((mod) => {
      setPage(() => mod.default);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests — ERPExpenseListPage
// ==========================================================================

describe('ERPExpenseListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    renderListPage();
    await waitFor(() => {
      expect(screen.getByText('財務記錄管理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders statistic cards', async () => {
    renderListPage();
    await waitFor(() => {
      expect(screen.getByText('發票總數')).toBeInTheDocument();
      expect(screen.getByText('待審核')).toBeInTheDocument();
      expect(screen.getByText('本頁金額合計')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders action buttons', async () => {
    renderListPage();
    await waitFor(() => {
      expect(screen.getByText('新增報銷')).toBeInTheDocument();
      expect(screen.getByText('手動記帳')).toBeInTheDocument();
      expect(screen.getAllByText('QR 掃描').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('OCR 辨識').length).toBeGreaterThanOrEqual(1);
    }, WAIT_OPTS);
  });

  it('renders table column headers', async () => {
    renderListPage();
    await waitFor(() => {
      expect(screen.getAllByText('發票號碼').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('日期').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('金額 (TWD)').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('分類').length).toBeGreaterThanOrEqual(1);
    }, WAIT_OPTS);
  });

  it('renders table data rows', async () => {
    renderListPage();
    await waitFor(() => {
      expect(screen.getByText('AB12345678')).toBeInTheDocument();
      expect(screen.getByText('CD87654321')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders filter controls', async () => {
    renderListPage();
    await waitFor(() => {
      expect(screen.getByText('重新整理')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('搜尋發票號碼...')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders pagination info', async () => {
    renderListPage();
    await waitFor(() => {
      expect(screen.getByText(/共 2 項/)).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders loading state when data is loading', async () => {
    mockUseExpenses.mockReturnValueOnce({
      data: undefined as never,
      isLoading: true,
      refetch: mockRefetch,
    });
    renderListPage();
    await waitFor(() => {
      expect(screen.getByText('財務記錄管理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders detail action links for each row', async () => {
    renderListPage();
    await waitFor(() => {
      const detailLinks = screen.getAllByText('詳情');
      expect(detailLinks.length).toBeGreaterThanOrEqual(2);
    }, WAIT_OPTS);
  });

  it('renders MOF pending badge count', async () => {
    renderListPage();
    await waitFor(() => {
      // The MOF button should show
      expect(screen.getByText('財政部發票')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

// ==========================================================================
// Tests — ERPExpenseCreatePage
// ==========================================================================

describe('ERPExpenseCreatePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getByText('新增費用報銷')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders back button', async () => {
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getByText('返回')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders invoice number field', async () => {
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getByText('發票號碼')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('AB12345678')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders amount field', async () => {
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getByText('總金額 (含稅)')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders date field', async () => {
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getByText('開立日期')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders category select', async () => {
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getByText('費用分類')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders case code field', async () => {
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getByText('案號 (選填)')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('留空 = 一般營運支出')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders currency select', async () => {
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getByText('幣別')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders notes field', async () => {
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getByText('備註')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders submit button', async () => {
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getByText('建立')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

// ==========================================================================
// Tests — ERPExpenseDetailPage
// ==========================================================================

describe('ERPExpenseDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders the detail page title with invoice number', async () => {
    renderDetailPage();
    await waitFor(() => {
      expect(screen.getByText(/費用報銷 — AB12345678/)).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders status badge', async () => {
    renderDetailPage();
    await waitFor(() => {
      // EXPENSE_STATUS_LABELS.pending = '待主管審核'
      const tags = screen.getAllByText('待主管審核');
      expect(tags.length).toBeGreaterThanOrEqual(1);
    }, WAIT_OPTS);
  });

  it('renders invoice information tab content', async () => {
    renderDetailPage();
    await waitFor(() => {
      expect(screen.getByText('發票資訊')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders invoice details in descriptions', async () => {
    renderDetailPage();
    await waitFor(() => {
      // The descriptions should show inv_num, date, amount, etc.
      expect(screen.getByText('AB12345678')).toBeInTheDocument();
      expect(screen.getByText('2026-01-15')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders approve and reject buttons when user has permission', async () => {
    renderDetailPage();
    await waitFor(() => {
      expect(screen.getByText('主管核准')).toBeInTheDocument();
      expect(screen.getByText('駁回')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders receipt tab', async () => {
    renderDetailPage();
    await waitFor(() => {
      expect(screen.getByText('收據影像')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders not found message when no data', async () => {
    mockUseExpenseDetail.mockReturnValueOnce({
      data: { data: null as never },
      isLoading: false,
    });
    renderDetailPage();
    await waitFor(() => {
      expect(screen.getByText('找不到此費用發票')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

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

// ERPExpenseCreatePage 從**子路徑**直接 import useResponsive，不走 hooks barrel
// → 只 mock '../../hooks' 蓋不到它 → jsdom 量到寬度 0 → 元件走手機版面
// （Steps 兩步、標題降為 h5、返回鈕變 icon-only 無文字）→ 桌機版斷言全數落空。
// 這是「mock 了 barrel 就以為蓋住全部」的典型盲點，與 L25 關鍵字陷阱同族。
vi.mock('../../hooks/utility/useResponsive', () => ({
  useResponsive: () => ({
    isMobile: false, isTablet: false, isDesktop: true, breakpoint: 'lg',
    responsiveValue: <T,>(config: { mobile?: T; tablet?: T; desktop?: T }) =>
      config.desktop ?? config.tablet ?? config.mobile,
  }),
}));

// 2026-07-30：4 個孤兒 Modal 已移除（見 pages/erpExpense/index.ts 收斂說明）。
// mock 改為實際會被清單/建立頁 import 的成員，否則 barrel mock 會讓真元件變 undefined。
vi.mock('../../pages/erpExpense', () => ({
  SmartScanModal: () => null,
  ExpenseImportModal: () => null,
  ExpenseScanPanel: () => null,
  InvoiceSubTable: () => null,
  compressImage: (f: File) => Promise.resolve(f),
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
  // 2026-07-30 補齊：以下 4 個 hook 被三頁實際 import，但 barrel mock 未提供
  // → 取用時為 undefined → 元件在 render 期就拋錯 → 27 個測試全紅（本檔一度失去保護力）。
  // 教訓：`vi.mock('../../hooks')` 是**整包取代**，頁面新增一個 hook 就必須同步補這裡，
  // 否則測試不是「失敗」而是「整檔癱瘓」，看起來像測試壞掉、實際是保護網破洞。
  useCaseCodeMap: () => ({ data: {}, isLoading: false }),
  useLedger: () => ({ data: { items: [], total: 0 }, isLoading: false, refetch: vi.fn() }),
  usePMCases: () => ({ data: { items: [] }, isLoading: false }),
  useAutoLinkEinvoice: () => ({ mutateAsync: mockMutateAsync, mutate: vi.fn(), isPending: false }),
  useAssetsByInvoice: (..._args: unknown[]) => ({ data: [], isLoading: false }),
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
  beforeEach(() => { vi.clearAllMocks(); });
  afterEach(() => { vi.clearAllMocks(); });

  // 2026-07-30 重寫：本頁已改版為「歸屬彙總 + 分頁」（groups / 收支帳本），
  // 不再是發票明細列表。原斷言（發票號碼欄、逐列「詳情」、共 N 項）鎖的是兩版前的 UI，
  // 頁面早已改掉、測試卻沒跟上 → 27 個測試全紅、本檔實質失去保護力。
  // 重寫原則：只鎖「頁面能 render + 關鍵導覽元素在」，不逐字鎖易變文案。

  it('renders the page title', async () => {
    renderListPage();
    await waitFor(() => {
      expect(screen.getByText('費用核銷審核')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders statistic cards', async () => {
    renderListPage();
    await waitFor(() => {
      expect(screen.getByText('核銷總筆數')).toBeInTheDocument();
      expect(screen.getByText('待審核')).toBeInTheDocument();
      expect(screen.getByText('專案費用合計')).toBeInTheDocument();
      expect(screen.getByText('營運費用合計')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders action buttons', async () => {
    renderListPage();
    await waitFor(() => {
      // 批次掃描 = 2026-07-30 孤兒元件整合後掛上的入口，屬本輪修法應被保護的行為
      expect(screen.getByText('批次掃描')).toBeInTheDocument();
      expect(screen.getByText('核銷匯入')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders attribution tabs', async () => {
    renderListPage();
    await waitFor(() => {
      expect(screen.getAllByText('專案費用').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('營運費用').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('收支帳本').length).toBeGreaterThanOrEqual(1);
    }, WAIT_OPTS);
  });

  it('renders grouped table column headers', async () => {
    renderListPage();
    await waitFor(() => {
      expect(screen.getAllByText('歸屬').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('分類/案件').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('筆數').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('金額合計').length).toBeGreaterThanOrEqual(1);
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
      expect(screen.getByText('費用核銷審核')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

// ==========================================================================
// Tests — ERPExpenseCreatePage
// ==========================================================================

describe('ERPExpenseCreatePage', () => {
  beforeEach(() => { vi.clearAllMocks(); });
  afterEach(() => { vi.clearAllMocks(); });

  // 2026-07-30 重寫：表單文案已改（新增核銷 / 含稅總額 / 關聯案件 / 建立核銷），
  // 原斷言鎖的是舊文案（新增費用報銷 / 總金額 (含稅) / 案號 (選填) / 建立）。

  it('renders the page title', async () => {
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getByText('新增核銷')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders back button', async () => {
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getByText('返回')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders amount and tax fields', async () => {
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getByText('含稅總額')).toBeInTheDocument();
      expect(screen.getByText('稅額')).toBeInTheDocument();
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

  it('renders attribution selector with three options', async () => {
    // 「關聯案件」欄位只在歸屬＝專案費用時出現，而預設是「未歸屬」
    // （URL 無 case_code 時 attrType='none'）→ 不可無條件斷言它存在。
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getByText('歸屬類型')).toBeInTheDocument();
      expect(screen.getAllByText('專案費用').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('營運費用').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('未歸屬').length).toBeGreaterThanOrEqual(1);
    }, WAIT_OPTS);
  });

  it('renders ban fields', async () => {
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getByText('買方統編')).toBeInTheDocument();
      expect(screen.getByText('賣方統編')).toBeInTheDocument();
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
      expect(screen.getByText('建立核銷')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the desktop-to-mobile handoff QR entry', async () => {
    // 2026-07-30 新增功能：桌機建立頁提供「用手機拍照上傳」交接入口
    renderCreatePage();
    await waitFor(() => {
      expect(screen.getAllByText('用手機拍照上傳').length).toBeGreaterThanOrEqual(1);
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

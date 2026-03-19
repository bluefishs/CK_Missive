/**
 * ERPQuotationFormPage Tests
 *
 * Tests for the ERP quotation create/edit form page including:
 * - Create mode rendering
 * - Edit mode rendering with existing data
 * - Generate case code button
 * - Form fields rendering
 * - Back navigation
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/ERPQuotationFormPage.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

const WAIT_OPTS = { timeout: 8000 };

// ==========================================================================
// Mocks
// ==========================================================================

const mockNavigate = vi.fn();
const mockParams: Record<string, string | undefined> = {};
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

const mockUseERPQuotation = vi.fn((): { data: Record<string, unknown> | null; isLoading: boolean } => ({
  data: null,
  isLoading: false,
}));

const mockCreateMutateAsync = vi.fn();
const mockUpdateMutateAsync = vi.fn();

vi.mock('../../hooks', () => ({
  useResponsive: () => ({ isMobile: false, isTablet: false, isDesktop: true, breakpoint: 'lg' }),
  useERPQuotation: (..._args: unknown[]) => mockUseERPQuotation(),
  useCreateERPQuotation: () => ({
    mutateAsync: mockCreateMutateAsync,
    isPending: false,
  }),
  useUpdateERPQuotation: () => ({
    mutateAsync: mockUpdateMutateAsync,
    isPending: false,
  }),
}));

const mockGenerateCode = vi.fn();
vi.mock('../../api/erp', () => ({
  erpQuotationsApi: {
    generateCode: (...args: unknown[]) => mockGenerateCode(...args),
  },
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
    import('../../pages/ERPQuotationFormPage').then((mod) => {
      setPage(() => mod.ERPQuotationFormPage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('ERPQuotationFormPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockParams.id = undefined;
  });

  describe('Create mode', () => {
    it('renders create mode title', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('新增報價')).toBeInTheDocument();
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

    it('renders form fields', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('案號')).toBeInTheDocument();
        expect(screen.getByText('案名')).toBeInTheDocument();
        expect(screen.getByText('年度')).toBeInTheDocument();
        expect(screen.getByText('報價類別')).toBeInTheDocument();
        expect(screen.getByText('狀態')).toBeInTheDocument();
        expect(screen.getByText('總價 (含稅)')).toBeInTheDocument();
        expect(screen.getByText('稅額')).toBeInTheDocument();
        expect(screen.getByText('外包費')).toBeInTheDocument();
        expect(screen.getByText('人事費')).toBeInTheDocument();
        expect(screen.getByText('管銷費')).toBeInTheDocument();
        expect(screen.getByText('其他成本')).toBeInTheDocument();
        expect(screen.getByText('備註')).toBeInTheDocument();
      }, WAIT_OPTS);
    });

    it('renders submit button with create label', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('建立')).toBeInTheDocument();
      }, WAIT_OPTS);
    });

    it('renders generate code button', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('產生')).toBeInTheDocument();
      }, WAIT_OPTS);
    });
  });

  describe('Edit mode', () => {
    beforeEach(() => {
      mockParams.id = '1';
      mockUseERPQuotation.mockReturnValue({
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
          status: 'confirmed',
          notes: '備註',
        },
        isLoading: false,
      });
    });

    it('renders edit mode title', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('編輯報價')).toBeInTheDocument();
      }, WAIT_OPTS);
    });

    it('renders submit button with update label', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('更新')).toBeInTheDocument();
      }, WAIT_OPTS);
    });

    it('returns null while loading existing quotation in edit mode', async () => {
      mockUseERPQuotation.mockReturnValueOnce({ data: null, isLoading: true });
      renderPage();
      await waitFor(() => {
        expect(screen.queryByText('編輯報價')).not.toBeInTheDocument();
      }, WAIT_OPTS);
    });
  });
});

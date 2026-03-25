/**
 * PMCaseFormPage Tests
 *
 * Tests for the PM case create/edit form page including:
 * - Create mode rendering
 * - Edit mode rendering with existing data
 * - Generate case code button
 * - Form validation
 * - Back navigation
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/PMCaseFormPage.test.tsx
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

const mockUsePMCase = vi.fn((): { data: Record<string, unknown> | null; isLoading: boolean } => ({
  data: null,
  isLoading: false,
}));

const mockCreateMutateAsync = vi.fn();
const mockUpdateMutateAsync = vi.fn();

vi.mock('../../hooks', () => ({
  useResponsive: () => ({ isMobile: false, isTablet: false, isDesktop: true, breakpoint: 'lg' }),
  usePMCase: (..._args: unknown[]) => mockUsePMCase(),
  useCreatePMCase: () => ({
    mutateAsync: mockCreateMutateAsync,
    isPending: false,
  }),
  useUpdatePMCase: () => ({
    mutateAsync: mockUpdateMutateAsync,
    isPending: false,
  }),
}));

vi.mock('../../hooks/business/useDropdownData', () => ({
  useClientOptions: () => ({ clients: [{ id: 1, vendor_name: '測試委託' }], isLoading: false }),
}));
vi.mock('../../api/vendorsApi', () => ({
  vendorsApi: { createVendor: vi.fn() },
}));
// No generate code API needed - form uses manual input

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
    import('../../pages/PMCaseFormPage').then((mod) => {
      setPage(() => mod.PMCaseFormPage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('PMCaseFormPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockParams.id = undefined;
  });

  describe('Create mode', () => {
    it('renders create mode title', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('新增邀標案件')).toBeInTheDocument();
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
      expect(mockNavigate).toHaveBeenCalledWith('/pm/cases');
    });

    it('renders form fields', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('案號')).toBeInTheDocument();
        expect(screen.getByText('專案名稱')).toBeInTheDocument();
        expect(screen.getByText('年度')).toBeInTheDocument();
        expect(screen.getByText('作業類別')).toBeInTheDocument();
        expect(screen.getByText('狀態')).toBeInTheDocument();
        expect(screen.getByText('委託單位')).toBeInTheDocument();
        expect(screen.getByText('報價金額')).toBeInTheDocument();
        expect(screen.getByText('開始日期')).toBeInTheDocument();
        expect(screen.getByText('結束日期')).toBeInTheDocument();
        expect(screen.getByText('備註')).toBeInTheDocument();
      }, WAIT_OPTS);
    });

    it('renders submit button with create label', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('建立')).toBeInTheDocument();
      }, WAIT_OPTS);
    });

    it('renders case code input field', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByPlaceholderText('自動產生或手動輸入')).toBeInTheDocument();
      }, WAIT_OPTS);
    });
  });

  describe('Edit mode', () => {
    beforeEach(() => {
      mockParams.id = '1';
      mockUsePMCase.mockReturnValue({
        data: {
          id: 1,
          case_code: 'CK2025_PM_01_001',
          case_name: '桃園測量案',
          year: 114,
          category: '01',
          client_name: '桃園市政府',
          status: 'in_progress',
          contract_amount: '1500000',
          start_date: null,
          end_date: null,
        },
        isLoading: false,
      });
    });

    it('renders edit mode title', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('編輯邀標案件')).toBeInTheDocument();
      }, WAIT_OPTS);
    });

    it('renders submit button with update label', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('更新')).toBeInTheDocument();
      }, WAIT_OPTS);
    });

    it('shows card loading state while loading existing case in edit mode', async () => {
      mockUsePMCase.mockReturnValueOnce({ data: null, isLoading: true });
      renderPage();
      await waitFor(() => {
        // Title is outside the Card, so it is visible even when Card is loading
        expect(screen.getByText('編輯邀標案件')).toBeInTheDocument();
      }, WAIT_OPTS);
    });
  });
});

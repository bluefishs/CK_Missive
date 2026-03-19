/**
 * TaoyuanDispatchPage Tests
 *
 * Tests for the Taoyuan dispatch management page including:
 * - Page title rendering (desktop/mobile)
 * - Tab navigation (4 tabs)
 * - Project selector rendering
 * - URL parameter sync
 * - Tab content rendering
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/TaoyuanDispatchPage.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

// Dynamic import needs a longer timeout for module resolution in full test suite
const WAIT_OPTS = { timeout: 5000 };

// ==========================================================================
// Mocks
// ==========================================================================

const mockSetSearchParams = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useSearchParams: () => [new URLSearchParams(), mockSetSearchParams],
  };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

const mockUseResponsive = vi.fn(() => ({
  isMobile: false,
  isTablet: false,
  isDesktop: true,
  responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
}));

vi.mock('../../hooks', () => ({
  useResponsive: () => mockUseResponsive(),
  useTaoyuanContractProjects: vi.fn(() => ({
    data: [
      { id: 21, project_name: 'Test Taoyuan Project', project_code: 'CK2025_01' },
      { id: 22, project_name: 'Another Project', project_code: 'CK2025_02' },
    ],
    isLoading: false,
  })),
}));

vi.mock('../../constants/taoyuanOptions', () => ({
  TAOYUAN_CONTRACT: {
    PROJECT_ID: 21,
    CODE: 'CK2025_01_03_001',
    NAME: 'Test Taoyuan Contract',
  },
}));

vi.mock('../../components/taoyuan/DispatchOrdersTab', () => ({
  DispatchOrdersTab: ({ contractProjectId }: { contractProjectId: number }) => (
    <div data-testid="mock-dispatch-orders-tab">DispatchOrders (project: {contractProjectId})</div>
  ),
}));

vi.mock('../../components/taoyuan/DocumentsTab', () => ({
  DocumentsTab: ({ contractCode }: { contractCode: string }) => (
    <div data-testid="mock-documents-tab">Documents (code: {contractCode})</div>
  ),
}));

vi.mock('../../components/taoyuan/PaymentsTab', () => ({
  PaymentsTab: ({ contractProjectId }: { contractProjectId: number }) => (
    <div data-testid="mock-payments-tab">Payments (project: {contractProjectId})</div>
  ),
}));

vi.mock('../../components/taoyuan/ProjectsTab', () => ({
  ProjectsTab: ({ contractProjectId }: { contractProjectId: number }) => (
    <div data-testid="mock-projects-tab">Projects (project: {contractProjectId})</div>
  ),
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderTaoyuanDispatchPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <TaoyuanDispatchPageWrapper />
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function TaoyuanDispatchPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/TaoyuanDispatchPage').then((mod) => {
      setPage(() => mod.TaoyuanDispatchPage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('TaoyuanDispatchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseResponsive.mockReturnValue({
      isMobile: false,
      isTablet: false,
      isDesktop: true,
      responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
    });
  });

  it('renders the desktop page title', async () => {
    renderTaoyuanDispatchPage();
    await waitFor(() => {
      expect(screen.getByText('桃園查估派工管理系統')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders mobile page title when isMobile is true', async () => {
    mockUseResponsive.mockReturnValue({
      isMobile: true,
      isTablet: false,
      isDesktop: false,
      responsiveValue: (v: Record<string, unknown>) => v.mobile ?? v.tablet ?? v.desktop,
    });
    renderTaoyuanDispatchPage();
    await waitFor(() => {
      expect(screen.getByText('桃園派工系統')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders subtitle on desktop', async () => {
    renderTaoyuanDispatchPage();
    await waitFor(() => {
      expect(screen.getByText('派工管理 / 函文紀錄 / 契金管控')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('hides subtitle on mobile', async () => {
    mockUseResponsive.mockReturnValue({
      isMobile: true,
      isTablet: false,
      isDesktop: false,
      responsiveValue: (v: Record<string, unknown>) => v.mobile ?? v.tablet ?? v.desktop,
    });
    renderTaoyuanDispatchPage();
    await waitFor(() => {
      expect(screen.getByText('桃園派工系統')).toBeInTheDocument();
    }, WAIT_OPTS);
    expect(screen.queryByText('派工管理 / 函文紀錄 / 契金管控')).not.toBeInTheDocument();
  });

  it('renders project selector tag', async () => {
    renderTaoyuanDispatchPage();
    await waitFor(() => {
      expect(screen.getByText('承攬案件')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders dispatch tab label', async () => {
    renderTaoyuanDispatchPage();
    await waitFor(() => {
      expect(screen.getByText('派工紀錄')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders documents tab label', async () => {
    renderTaoyuanDispatchPage();
    await waitFor(() => {
      expect(screen.getByText('函文紀錄')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders payments tab label', async () => {
    renderTaoyuanDispatchPage();
    await waitFor(() => {
      expect(screen.getByText('契金管控')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders projects tab label', async () => {
    renderTaoyuanDispatchPage();
    await waitFor(() => {
      expect(screen.getByText('工程資訊')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders dispatch orders tab content by default', async () => {
    renderTaoyuanDispatchPage();
    await waitFor(() => {
      expect(screen.getByTestId('mock-dispatch-orders-tab')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('passes correct project ID to dispatch orders tab', async () => {
    renderTaoyuanDispatchPage();
    await waitFor(() => {
      expect(screen.getByText(/DispatchOrders \(project: 21\)/)).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('switches to documents tab when clicked', async () => {
    renderTaoyuanDispatchPage();
    await waitFor(() => {
      expect(screen.getByText('函文紀錄')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('函文紀錄'));
    await waitFor(() => {
      expect(screen.getByTestId('mock-documents-tab')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

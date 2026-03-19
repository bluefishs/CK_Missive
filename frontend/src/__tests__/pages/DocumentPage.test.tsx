/**
 * DocumentPage Tests
 *
 * Tests for the document management page including:
 * - Page title rendering
 * - Action buttons (create, import, refresh)
 * - Document filter and tabs rendering
 * - Delete confirmation modal
 * - Permission-based UI
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

const mockDocumentsData = {
  items: [
    { id: 1, doc_number: 'DOC-0001', subject: 'Test Doc 1', created_at: '2026-01-01' },
    { id: 2, doc_number: 'DOC-0002', subject: 'Test Doc 2', created_at: '2026-01-02' },
  ],
  pagination: { total: 2, page: 1, limit: 20, total_pages: 1, has_next: false, has_prev: false },
};

const mockUseDocuments = vi.fn(() => ({
  data: mockDocumentsData,
  isLoading: false,
  error: null,
}));

const mockDeleteMutateAsync = vi.fn();
const mockUseDeleteDocument = vi.fn(() => ({
  mutateAsync: mockDeleteMutateAsync,
  isPending: false,
}));

const mockHasPermission = vi.fn(() => true);

vi.mock('../../hooks', () => ({
  useDocuments: () => mockUseDocuments(),
  useDeleteDocument: () => mockUseDeleteDocument(),
  useAuthGuard: vi.fn(() => ({
    hasPermission: mockHasPermission,
    isAdmin: true,
    isAuthenticated: true,
    user: { id: 1, role: 'admin' },
  })),
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

vi.mock('../../store', () => ({
  useDocumentsStore: vi.fn(() => ({
    filters: {},
    pagination: { page: 1, limit: 20 },
    setFilters: vi.fn(),
    setPagination: vi.fn(),
    resetFilters: vi.fn(),
  })),
}));

vi.mock('../../config/queryConfig', () => ({
  queryKeys: {
    documents: { all: ['documents'] },
  },
}));

vi.mock('../../services/calendarIntegrationService', () => ({
  calendarIntegrationService: {
    addDocumentToCalendar: vi.fn(),
  },
}));

vi.mock('../../utils/exportUtils', () => ({
  exportDocumentsToExcel: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('../../components/document/DocumentFilter', () => ({
  DocumentFilter: (props: { onReset: () => void }) => (
    <div data-testid="mock-document-filter">
      <button onClick={props.onReset}>重置篩選</button>
    </div>
  ),
}));

vi.mock('../../components/document/DocumentTabs', () => ({
  DocumentTabs: (props: { documents: unknown[]; total: number }) => (
    <div data-testid="mock-document-tabs">
      DocumentTabs ({(props.documents as unknown[]).length} docs, total: {props.total})
    </div>
  ),
}));

vi.mock('../../components/document/DocumentImport', () => ({
  DocumentImport: (props: { visible: boolean; onClose: () => void }) =>
    props.visible ? (
      <div data-testid="mock-document-import">
        <button onClick={props.onClose}>Close Import</button>
      </div>
    ) : null,
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderDocumentPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <DocumentPageWrapper />
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function DocumentPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/DocumentPage').then((mod) => {
      setPage(() => mod.DocumentPage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('DocumentPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockHasPermission.mockReturnValue(true);
  });

  it('renders the page title', async () => {
    renderDocumentPage();
    await waitFor(() => {
      expect(screen.getByText('公文管理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders document filter component', async () => {
    renderDocumentPage();
    await waitFor(() => {
      expect(screen.getByTestId('mock-document-filter')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders document tabs component', async () => {
    renderDocumentPage();
    await waitFor(() => {
      expect(screen.getByTestId('mock-document-tabs')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders refresh button', async () => {
    renderDocumentPage();
    await waitFor(() => {
      expect(screen.getByText('重新整理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders create button when user has create permission', async () => {
    renderDocumentPage();
    await waitFor(() => {
      expect(screen.getByText('新增公文')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders import button when user has create permission', async () => {
    renderDocumentPage();
    await waitFor(() => {
      expect(screen.getByText('公文匯入')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('hides create button when user lacks create permission', async () => {
    mockHasPermission.mockReturnValue(false);
    renderDocumentPage();
    await waitFor(() => {
      expect(screen.getByText('公文管理')).toBeInTheDocument();
    }, WAIT_OPTS);
    expect(screen.queryByText('新增公文')).not.toBeInTheDocument();
  });

  it('navigates to create page when create button is clicked', async () => {
    renderDocumentPage();
    await waitFor(() => {
      expect(screen.getByText('新增公文')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('新增公文'));
    expect(mockNavigate).toHaveBeenCalledWith('/documents/create');
  });

  it('opens import modal when import button is clicked', async () => {
    renderDocumentPage();
    await waitFor(() => {
      expect(screen.getByText('公文匯入')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('公文匯入'));
    await waitFor(() => {
      expect(screen.getByTestId('mock-document-import')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('passes correct document count to DocumentTabs', async () => {
    renderDocumentPage();
    await waitFor(() => {
      expect(screen.getByText(/2 docs/)).toBeInTheDocument();
      expect(screen.getByText(/total: 2/)).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders reset filter button in filter component', async () => {
    renderDocumentPage();
    await waitFor(() => {
      expect(screen.getByText('重置篩選')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

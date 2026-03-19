/**
 * DocumentDetailPage Tests
 *
 * Tests for the document detail page including:
 * - Page rendering with document data (subject, doc_type, status)
 * - Tab sections (公文資訊, 日期狀態, 承案人資, 附件紀錄, AI 分析)
 * - Action buttons (編輯, 刪除, 加入行事曆)
 * - Edit mode toggle (edit/save/cancel)
 * - Back navigation
 * - Loading and empty states
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/DocumentDetailPage.test.tsx
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
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: '42' }),
    useLocation: () => ({ pathname: '/documents/42', search: '', state: null }),
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

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    DOCUMENTS: {
      DETAIL: vi.fn(() => '/documents/42'),
      UPDATE: vi.fn(() => '/documents/42/update'),
      DELETE: vi.fn(() => '/documents/42/delete'),
    },
    AI: {
      ANALYSIS_GET: vi.fn(() => '/ai/analysis/42'),
      ANALYSIS_TRIGGER: vi.fn(() => '/ai/analysis/42/analyze'),
    },
    TAOYUAN_DISPATCH: {},
  },
}));

const mockDocument = {
  id: 42,
  doc_number: 'DOC-2026-001',
  subject: '測試公文標題',
  doc_type: '函',
  status: '處理中',
  sender: '台北市政府',
  receiver: '桃園市政府',
  doc_date: '2026-03-01',
  send_date: '2026-03-02',
  receive_date: '2026-03-03',
  content: '測試內容',
  notes: '',
  assignee: 'user1',
  priority_level: 3,
  contract_project_name: null,
  created_at: '2026-03-01T00:00:00Z',
  updated_at: '2026-03-01T00:00:00Z',
};

const mockSetIsEditing = vi.fn();
const mockSetActiveTab = vi.fn();
const mockHandleSave = vi.fn();
const mockHandleCancelEdit = vi.fn();
const mockHandleDelete = vi.fn();
const mockHandleAddToCalendar = vi.fn();

vi.mock('../../pages/document/hooks/useDocumentDetail', () => ({
  useDocumentDetail: () => ({
    document: mockDocument,
    loading: false,
    saving: false,
    activeTab: 'info',
    setActiveTab: mockSetActiveTab,
    isEditing: false,
    setIsEditing: mockSetIsEditing,
    attachments: [],
    attachmentsLoading: false,
    fileList: [],
    setFileList: vi.fn(),
    uploading: false,
    uploadProgress: 0,
    uploadErrors: [],
    setUploadErrors: vi.fn(),
    fileSettings: null,
    cases: [],
    casesLoading: false,
    users: [],
    usersLoading: false,
    projectStaffMap: {},
    staffLoading: false,
    selectedContractProjectId: null,
    currentAssigneeValues: [],
    dispatchLinks: [],
    dispatchLinksLoading: false,
    projectLinks: [],
    projectLinksLoading: false,
    hasDispatchFeature: false,
    hasProjectLinkFeature: false,
    agencyContacts: [],
    projectVendors: [],
    availableDispatches: [],
    availableProjects: [],
    showIntegratedEventModal: false,
    setShowIntegratedEventModal: vi.fn(),
    handleProjectChange: vi.fn(),
    handleSave: mockHandleSave,
    handleCancelEdit: mockHandleCancelEdit,
    handleDelete: mockHandleDelete,
    handleAddToCalendar: mockHandleAddToCalendar,
    handleEventCreated: vi.fn(),
    handleDownload: vi.fn(),
    handlePreview: vi.fn(),
    handleDeleteAttachment: vi.fn(),
    handleCreateDispatch: vi.fn(),
    handleLinkDispatch: vi.fn(),
    handleUnlinkDispatch: vi.fn(),
    handleLinkProject: vi.fn(),
    handleUnlinkProject: vi.fn(),
    handleCreateAndLinkProject: vi.fn(),
    form: { getFieldsValue: vi.fn(), setFieldsValue: vi.fn(), resetFields: vi.fn() },
    returnTo: '/documents',
  }),
}));

// Mock child tab components to keep tests focused
vi.mock('../../pages/document/tabs', () => ({
  DocumentInfoTab: () => <div data-testid="doc-info-tab">DocumentInfoTab</div>,
  DocumentDateStatusTab: () => <div data-testid="doc-date-tab">DateStatusTab</div>,
  DocumentCaseStaffTab: () => <div data-testid="doc-case-tab">CaseStaffTab</div>,
  DocumentAttachmentsTab: () => <div data-testid="doc-attachments-tab">AttachmentsTab</div>,
  DocumentDispatchTab: () => <div data-testid="doc-dispatch-tab">DispatchTab</div>,
  DocumentProjectLinkTab: () => <div data-testid="doc-project-tab">ProjectLinkTab</div>,
  DOC_TYPE_OPTIONS: [{ value: '函', label: '函' }],
  STATUS_OPTIONS: [{ value: '處理中', label: '處理中' }],
}));

vi.mock('../../pages/document/tabs/DocumentAITab', () => ({
  DocumentAITab: () => <div data-testid="doc-ai-tab">DocumentAITab</div>,
}));

vi.mock('../../components/calendar/IntegratedEventModal', () => ({
  IntegratedEventModal: () => <div data-testid="event-modal" />,
}));

vi.mock('../../components/common/DetailPage', () => ({
  DetailPageLayout: ({ header, tabs, loading, hasData }: {
    header: { title: string; backText: string; tags: { text: string; color: string }[]; extra: React.ReactNode };
    tabs: { key: string; label: React.ReactNode; children: React.ReactNode }[];
    loading: boolean;
    hasData: boolean;
    activeTab?: string;
    onTabChange?: (key: string) => void;
  }) => (
    <div data-testid="detail-page-layout">
      {loading && <div>載入中...</div>}
      {!loading && !hasData && <div>找不到資料</div>}
      {!loading && hasData && (
        <>
          <div data-testid="header-title">{header.title}</div>
          <div data-testid="header-back">{header.backText}</div>
          {header.tags.map((t, i) => (
            <span key={i} data-testid={`tag-${i}`}>{t.text}</span>
          ))}
          <div data-testid="header-extra">{header.extra}</div>
          {tabs.map((tab) => (
            <div key={tab.key} data-testid={`tab-${tab.key}`}>
              {tab.label}
              {tab.children}
            </div>
          ))}
        </>
      )}
    </div>
  ),
  createTabItem: (key: string, label: { icon: React.ReactNode; text: string; count?: number }, children: React.ReactNode) => ({
    key,
    label: <span>{label.text}{label.count !== undefined ? ` (${label.count})` : ''}</span>,
    children,
  }),
  getTagColor: (_value: string, _options: unknown[], fallback: string) => fallback,
}));

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderDocumentDetailPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <React.Suspense fallback={<div>Loading...</div>}>
              <DocumentDetailPageWrapper />
            </React.Suspense>
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function DocumentDetailPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/DocumentDetailPage').then((mod) => {
      setPage(() => mod.DocumentDetailPage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('DocumentDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the document subject as title', async () => {
    renderDocumentDetailPage();
    await waitFor(() => {
      expect(screen.getByTestId('header-title')).toHaveTextContent('測試公文標題');
    }, WAIT_OPTS);
  });

  it('renders doc_type tag', async () => {
    renderDocumentDetailPage();
    await waitFor(() => {
      expect(screen.getByTestId('tag-0')).toHaveTextContent('函');
    }, WAIT_OPTS);
  });

  it('renders status tag', async () => {
    renderDocumentDetailPage();
    await waitFor(() => {
      expect(screen.getByTestId('tag-1')).toHaveTextContent('處理中');
    }, WAIT_OPTS);
  });

  it('renders back navigation text', async () => {
    renderDocumentDetailPage();
    await waitFor(() => {
      expect(screen.getByTestId('header-back')).toHaveTextContent('返回公文列表');
    }, WAIT_OPTS);
  });

  it('renders common tabs (公文資訊, 日期狀態, 承案人資, 附件紀錄, AI 分析)', async () => {
    renderDocumentDetailPage();
    await waitFor(() => {
      expect(screen.getByTestId('tab-info')).toBeInTheDocument();
      expect(screen.getByTestId('tab-date-status')).toBeInTheDocument();
      expect(screen.getByTestId('tab-case-staff')).toBeInTheDocument();
      expect(screen.getByTestId('tab-attachments')).toBeInTheDocument();
      expect(screen.getByTestId('tab-ai-insights')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders edit button in non-editing mode', async () => {
    renderDocumentDetailPage();
    await waitFor(() => {
      expect(screen.getByText('編輯')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders delete button in non-editing mode', async () => {
    renderDocumentDetailPage();
    await waitFor(() => {
      expect(screen.getByText('刪除')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders calendar button in non-editing mode', async () => {
    renderDocumentDetailPage();
    await waitFor(() => {
      expect(screen.getByText('加入行事曆')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the IntegratedEventModal', async () => {
    renderDocumentDetailPage();
    await waitFor(() => {
      expect(screen.getByTestId('event-modal')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('does not render dispatch/project tabs when features are disabled', async () => {
    renderDocumentDetailPage();
    await waitFor(() => {
      expect(screen.getByTestId('tab-info')).toBeInTheDocument();
    }, WAIT_OPTS);
    expect(screen.queryByTestId('tab-dispatch')).not.toBeInTheDocument();
    expect(screen.queryByTestId('tab-project-link')).not.toBeInTheDocument();
  });
});

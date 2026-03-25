/**
 * Page Render Smoke Tests
 *
 * Verifies that key pages render without crashing when wrapped in
 * the required providers (QueryClientProvider, MemoryRouter, Ant Design App).
 *
 * These are NOT business-logic tests; they only assert the component
 * mounts and shows a recognisable piece of UI text.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

// ============================================================================
// Global mocks shared across all page tests
// ============================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
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

vi.mock('../../api/documentsApi', () => ({
  documentsApi: {
    getList: vi.fn().mockResolvedValue({ items: [], pagination: { total: 0, page: 1, limit: 20, total_pages: 0, has_next: false, has_prev: false } }),
    getDocumentEfficiency: vi.fn().mockResolvedValue({ total: 0, overdue_count: 0, overdue_rate: 0, status_distribution: [] }),
    getById: vi.fn().mockResolvedValue(null),
    delete: vi.fn().mockResolvedValue({ success: true }),
  },
}));

vi.mock('../../api/aiApi', () => ({
  aiApi: {
    getEmbeddingStats: vi.fn().mockResolvedValue({ total_documents: 0, with_embedding: 0, coverage_percent: 0 }),
    getEntityStats: vi.fn().mockResolvedValue({ total_documents: 0, extracted_documents: 0, coverage_percent: 0, total_entities: 0, total_relations: 0, without_extraction: 0 }),
    getGraphStats: vi.fn().mockResolvedValue({ total_entities: 0, total_relationships: 0, entity_type_distribution: {} }),
    getTopEntities: vi.fn().mockResolvedValue({ entities: [] }),
    getEntityGraph: vi.fn().mockResolvedValue({ success: true, nodes: [], edges: [] }),
    searchGraphEntities: vi.fn().mockResolvedValue({ results: [] }),
    findShortestPath: vi.fn().mockResolvedValue({ found: false }),
    mergeGraphEntities: vi.fn().mockResolvedValue({ success: true }),
  },
}));

vi.mock('../../services/calendarIntegrationService', () => ({
  calendarIntegrationService: {
    addDocumentToCalendar: vi.fn(),
  },
}));

vi.mock('../../utils/exportUtils', () => ({
  exportDocumentsToExcel: vi.fn(),
}));

// Mock hooks that perform API calls
vi.mock('../../hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../hooks')>();
  return {
    ...actual,
    useDocuments: vi.fn(() => ({ data: { items: [], pagination: { total: 0 } }, isLoading: false, error: null })),
    useDeleteDocument: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
    useAuthGuard: vi.fn(() => ({ hasPermission: () => true, isAdmin: false, isAuthenticated: true, user: { id: 1, role: 'admin' } })),
    useResponsive: vi.fn(() => ({ isMobile: false, isTablet: false, isDesktop: true, responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile })),
    useProjectsPage: vi.fn(() => ({
      projects: [], pagination: { total: 0 }, isLoading: false,
      statistics: { total_projects: 0, status_breakdown: [] },
      availableYears: [], availableStatuses: [], refetch: vi.fn(), isDeleting: false,
    })),
    useAgenciesPage: vi.fn(() => ({
      agencies: [], pagination: { total: 0 }, isLoading: false,
      statistics: { total_agencies: 0, categories: [] },
      refetch: vi.fn(), refetchStatistics: vi.fn(),
    })),
    useCalendarPage: vi.fn(() => ({
      events: [], categories: [], googleStatus: null,
      isLoading: false, updateEvent: vi.fn(), deleteEvent: vi.fn(),
      bulkSync: vi.fn(), isSyncing: false, refetch: vi.fn(),
    })),
    useAdminUsersPage: vi.fn(() => ({
      users: [], pagination: { total: 0 }, isLoading: false,
      refetch: vi.fn(),
    })),
    useTableColumnSearch: vi.fn(() => ({ getColumnSearchProps: vi.fn(() => ({})) })),
    useTaoyuanContractProjects: vi.fn(() => ({ data: [], isLoading: false })),
    usePMCaseSummary: vi.fn(() => ({ data: null, isLoading: false })),
    useERPProfitSummary: vi.fn(() => ({ data: null, isLoading: false })),
  };
});

vi.mock('../../hooks/utility/useAuthGuard', () => ({
  useAuthGuard: vi.fn(() => ({ hasPermission: () => true, isAdmin: false, isAuthenticated: true, user: { id: 1, role: 'admin' } })),
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

// Mock complex child components that have heavy deps
vi.mock('../../components/document/DocumentFilter', () => ({
  DocumentFilter: () => <div data-testid="mock-document-filter">DocumentFilter</div>,
}));

vi.mock('../../components/document/DocumentTabs', () => ({
  DocumentTabs: () => <div data-testid="mock-document-tabs">DocumentTabs</div>,
}));

vi.mock('../../components/document/DocumentImport', () => ({
  DocumentImport: () => null,
}));

vi.mock('../../components/dashboard', () => ({
  SystemHealthDashboard: () => <div data-testid="mock-health">SystemHealthDashboard</div>,
  AIStatsPanel: () => <div data-testid="mock-ai-stats">AIStatsPanel</div>,
  DocumentTrendsChart: () => <div data-testid="mock-trends">DocumentTrendsChart</div>,
  DashboardCalendarSection: () => <div data-testid="mock-calendar-section">DashboardCalendarSection</div>,
}));

vi.mock('../../components/dashboard/ProjectStatsPanel', () => ({
  ProjectStatsPanel: () => <div data-testid="mock-project-stats-panel">ProjectStatsPanel</div>,
}));

vi.mock('../../components/common', () => ({
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  ResponsiveTable: () => <div data-testid="mock-responsive-table">Table</div>,
}));

vi.mock('../../components/ai/KnowledgeGraph', () => ({
  KnowledgeGraph: () => <div data-testid="mock-knowledge-graph">KnowledgeGraph</div>,
}));

vi.mock('../../components/ai/RAGChatPanel', () => ({
  RAGChatPanel: () => <div data-testid="mock-rag-chat">RAGChatPanel</div>,
}));

vi.mock('../../components/ai/knowledgeGraph/GraphAgentBridge', () => ({
  GraphAgentBridgeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('../../pages/knowledgeGraph/KGAdminPanel', () => ({
  KGAdminPanel: () => null,
}));

vi.mock('../../config/graphNodeConfig', () => ({
  getAllMergedConfigs: vi.fn(() => ({})),
  getMergedNodeConfig: vi.fn(() => ({ label: 'test', color: '#999' })),
}));

vi.mock('../../constants/permissions', () => ({
  USER_ROLES: {
    admin: { name_zh: '管理員', description_zh: '系統管理者', default_permissions: ['all'], can_login: true },
    user: { name_zh: '一般使用者', description_zh: '一般角色', default_permissions: [], can_login: true },
  },
  USER_STATUSES: {
    active: { name_zh: '啟用', description_zh: '正常使用中', can_login: true },
    suspended: { name_zh: '暫停', description_zh: '帳號暫停', can_login: false },
  },
}));

vi.mock('../../config/queryConfig', () => ({
  queryKeys: {
    documents: { all: ['documents'] },
  },
  defaultQueryOptions: {
    list: { staleTime: 0, gcTime: 0 },
    detail: { staleTime: 0, gcTime: 0 },
  },
}));

vi.mock('../../router/types', () => ({
  ROUTES: {
    USER_MANAGEMENT: '/admin/users',
    PERMISSION_MANAGEMENT: '/admin/permissions',
    BACKUP_MANAGEMENT: '/admin/backup',
    CONTRACT_CASE_DETAIL: '/contract-case/:id',
    CONTRACT_CASE_CREATE: '/contract-case/create',
    AGENCY_CREATE: '/agencies/create',
    AGENCY_EDIT: '/agencies/:id/edit',
    STAFF_DETAIL: '/staff/:id',
    STAFF_CREATE: '/staff/create',
  },
}));

vi.mock('../../services/authService', () => {
  const mockService = {
    isAuthenticated: vi.fn(() => false),
    getCurrentUser: vi.fn(),
    login: vi.fn(),
    googleLogin: vi.fn(),
    setUserInfo: vi.fn(),
    getUserInfo: vi.fn(() => ({ id: 1, username: 'testuser', full_name: 'Test User', email: 'test@test.com', role: 'admin', is_admin: true, is_active: true })),
    getToken: vi.fn(() => null),
  };
  return {
    __esModule: true,
    default: mockService,
    ...mockService,
    MFARequiredError: class MFARequiredError extends Error {
      mfa_token: string;
      constructor(token: string) { super('MFA required'); this.mfa_token = token; }
    },
  };
});

vi.mock('../../config/env', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../config/env')>();
  return {
    ...actual,
    detectEnvironment: vi.fn(() => 'localhost'),
    isAuthDisabled: vi.fn(() => true),
    GOOGLE_CLIENT_ID: '',
  };
});

// Mock components for ContractCasePage
vi.mock('../../components/project/ProjectVendorManagement', () => ({
  default: () => null,
}));

vi.mock('../../components/common/ResponsiveTable', () => ({
  ResponsiveTable: () => <div data-testid="mock-responsive-table">Table</div>,
}));

// Mock for AgenciesPage
vi.mock('../../constants', () => ({
  AGENCY_CATEGORY_OPTIONS: [
    { value: '政府機關', label: '政府機關' },
    { value: '民間企業', label: '民間企業' },
    { value: '其他單位', label: '其他單位' },
  ],
}));

// Mock for StaffPage
vi.mock('../../hooks/system', () => ({
  useDepartments: vi.fn(() => ({ data: [] })),
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    USERS: {
      LIST: '/users/list',
      STATUS: (id: number) => `/users/${id}/status`,
    },
    BACKUP: {
      LIST: '/backup/list',
      STATS: '/backup/stats',
    },
  },
}));

// Mock for CalendarPage
vi.mock('../../components/calendar/EnhancedCalendarView', () => ({
  EnhancedCalendarView: () => <div data-testid="mock-calendar-view">Calendar</div>,
}));

// Mock for ProfilePage
vi.mock('../../components/auth/LoginHistoryTab', () => ({
  LoginHistoryTab: () => <div>LoginHistory</div>,
}));
vi.mock('../../components/auth/SessionManagementTab', () => ({
  SessionManagementTab: () => <div>SessionManagement</div>,
}));
vi.mock('../../components/auth/MFASettingsTab', () => ({
  MFASettingsTab: () => <div>MFASettings</div>,
}));

// Mock for TaoyuanDispatchPage
vi.mock('../../components/taoyuan/ProjectsTab', () => ({
  ProjectsTab: () => <div>ProjectsTab</div>,
}));
vi.mock('../../components/taoyuan/DocumentsTab', () => ({
  DocumentsTab: () => <div>DocumentsTab</div>,
}));
vi.mock('../../components/taoyuan/DispatchOrdersTab', () => ({
  DispatchOrdersTab: () => <div>DispatchOrdersTab</div>,
}));
vi.mock('../../components/taoyuan/PaymentsTab', () => ({
  PaymentsTab: () => <div>PaymentsTab</div>,
}));
vi.mock('../../constants/taoyuanOptions', () => ({
  TAOYUAN_CONTRACT: { PROJECT_ID: 1, CODE: 'TEST-001' },
}));

// Mock for ContractCasePage constants
vi.mock('../../pages/contractCase/tabs/constants', () => ({
  CATEGORY_OPTIONS: [
    { value: '01', label: '01委辦案件', color: 'blue' },
    { value: '02', label: '02協力計畫', color: 'green' },
    { value: '03', label: '03小額採購', color: 'orange' },
    { value: '04', label: '04其他類別', color: 'default' },
  ],
  CASE_NATURE_OPTIONS: [
    { value: '01', label: '01測量案', color: 'cyan' },
    { value: '02', label: '02資訊案', color: 'purple' },
    { value: '03', label: '03複合案', color: 'gold' },
  ],
  STATUS_OPTIONS: [
    { value: '執行中', label: '執行中' },
    { value: '已結案', label: '已結案' },
  ],
  STAFF_ROLE_OPTIONS: [
    { value: '計畫主持', label: '計畫主持', color: 'red' },
  ],
  VENDOR_ROLE_OPTIONS: [
    { value: '測量業務', label: '測量業務', color: 'blue' },
  ],
}));

// Mock react-highlight-words
vi.mock('react-highlight-words', () => ({
  default: ({ textToHighlight }: { textToHighlight: string }) => <span>{textToHighlight}</span>,
}));

// ============================================================================
// Helper: render inside all required providers
// ============================================================================

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            {ui}
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

// ============================================================================
// Tests
// ============================================================================

describe('Page Render Smoke Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('DocumentPage', () => {
    it('renders without crashing and shows page title', async () => {
      const { DocumentPage } = await import('../../pages/DocumentPage');
      renderWithProviders(<DocumentPage />);
      expect(screen.getByText('公文管理')).toBeInTheDocument();
    });
  });

  describe('AdminDashboardPage', () => {
    it('renders without crashing and shows page title', async () => {
      const AdminDashboardPage = (await import('../../pages/AdminDashboardPage')).default;
      renderWithProviders(<AdminDashboardPage />);
      expect(screen.getByText('管理員控制台')).toBeInTheDocument();
    });
  });

  describe('KnowledgeGraphPage', () => {
    it('renders without crashing and shows page title', async () => {
      const KnowledgeGraphPage = (await import('../../pages/KnowledgeGraphPage')).default;
      renderWithProviders(<KnowledgeGraphPage />);
      expect(screen.getByText('公文圖譜')).toBeInTheDocument();
    });
  });

  describe('DashboardPage', () => {
    it('renders without crashing and shows page title', async () => {
      const { DashboardPage } = await import('../../pages/DashboardPage');
      renderWithProviders(<DashboardPage />);
      expect(screen.getByText('儀表板總覽')).toBeInTheDocument();
    });
  });

  describe('ContractCasePage', () => {
    it('renders without crashing and shows page title', async () => {
      const { ContractCasePage } = await import('../../pages/ContractCasePage');
      renderWithProviders(<ContractCasePage />);
      expect(screen.getByText('承攬案件管理')).toBeInTheDocument();
    });
  });

  describe('AgenciesPage', () => {
    it('renders without crashing and shows page title', async () => {
      const { AgenciesPage } = await import('../../pages/AgenciesPage');
      renderWithProviders(<AgenciesPage />);
      expect(screen.getByText('機關單位管理')).toBeInTheDocument();
    });
  });

  describe('StaffPage', () => {
    it('renders without crashing and shows page title', async () => {
      const { StaffPage } = await import('../../pages/StaffPage');
      renderWithProviders(<StaffPage />);
      expect(screen.getByText('承辦同仁管理')).toBeInTheDocument();
    });
  });

  describe('CalendarPage', () => {
    it('renders without crashing and shows page title', async () => {
      const CalendarPage = (await import('../../pages/CalendarPage')).default;
      renderWithProviders(<CalendarPage />);
      expect(screen.getByText('行事曆管理')).toBeInTheDocument();
    });
  });

  describe('ProfilePage', () => {
    it('renders without crashing and shows page title', async () => {
      const { ProfilePage } = await import('../../pages/ProfilePage');
      renderWithProviders(<ProfilePage />);
      expect(screen.getByText('個人設定')).toBeInTheDocument();
    });
  });

  describe('LoginPage', () => {
    it('renders without crashing and shows app title', async () => {
      const LoginPage = (await import('../../pages/LoginPage')).default;
      renderWithProviders(<LoginPage />);
      expect(screen.getByText('乾坤測繪')).toBeInTheDocument();
    });
  });

  describe('UserManagementPage', () => {
    it('renders without crashing and shows page title', async () => {
      const UserManagementPage = (await import('../../pages/UserManagementPage')).default;
      renderWithProviders(<UserManagementPage />);
      expect(screen.getByText('使用者管理')).toBeInTheDocument();
    });
  });

  describe('TaoyuanDispatchPage', () => {
    it('renders without crashing and shows page title', async () => {
      const { TaoyuanDispatchPage } = await import('../../pages/TaoyuanDispatchPage');
      renderWithProviders(<TaoyuanDispatchPage />);
      expect(screen.getByText('桃園查估派工管理系統')).toBeInTheDocument();
    });
  });

  describe('BackupManagementPage', () => {
    it('renders without crashing and shows page title', async () => {
      const { BackupManagementPage } = await import('../../pages/BackupManagementPage');
      renderWithProviders(<BackupManagementPage />);
      expect(screen.getAllByText('備份管理').length).toBeGreaterThan(0);
    });
  });
});

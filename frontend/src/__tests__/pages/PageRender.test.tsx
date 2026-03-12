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
vi.mock('../../hooks', () => ({
  useDocuments: vi.fn(() => ({ data: { items: [], pagination: { total: 0 } }, isLoading: false, error: null })),
  useDeleteDocument: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useAuthGuard: vi.fn(() => ({ hasPermission: () => true, isAdmin: false, isAuthenticated: true, user: { id: 1, role: 'admin' } })),
  useResponsive: vi.fn(() => ({ isMobile: false, isTablet: false, isDesktop: true, responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile })),
}));

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
}));

vi.mock('../../components/common', () => ({
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
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
}));

vi.mock('../../router/types', () => ({
  ROUTES: {
    USER_MANAGEMENT: '/admin/users',
    PERMISSION_MANAGEMENT: '/admin/permissions',
    BACKUP_MANAGEMENT: '/admin/backup',
  },
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
});

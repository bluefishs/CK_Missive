/**
 * DatabaseGraphPage - Comprehensive Page-Level Tests
 *
 * Tests rendering, loading states, statistics display, and user interactions
 * for the database ER graph visualization page (資料庫圖譜).
 *
 * @version 1.0.0
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

const mockGraphData = {
  nodes: [
    { id: '1', label: 'official_documents', type: 'table' },
    { id: '2', label: 'agencies', type: 'table' },
    { id: '3', label: 'users', type: 'table' },
  ],
  edges: [
    { source: '1', target: '2', label: 'agency_id' },
    { source: '1', target: '3', label: 'created_by' },
  ],
};

const mockSchemaMap = new Map([
  ['official_documents', {
    name: 'official_documents',
    columns: [
      { name: 'id', type: 'INTEGER', nullable: false, primary_key: true },
      { name: 'doc_number', type: 'VARCHAR', nullable: true, primary_key: false },
    ],
    primary_key_columns: ['id'],
    foreign_keys: [{ constrained_columns: ['agency_id'], referred_table: 'agencies', referred_columns: ['id'] }],
    indexes: [{ name: 'ix_doc_number', columns: ['doc_number'], unique: true }],
  }],
]);

// Track the useQuery call to control data/loading
let mockQueryReturn: Record<string, unknown> = {
  data: null,
  isLoading: true,
};

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual('@tanstack/react-query');
  return {
    ...actual,
    useQuery: vi.fn(() => mockQueryReturn),
    useQueryClient: vi.fn(() => ({
      invalidateQueries: vi.fn(),
    })),
  };
});

vi.mock('../../api/aiApi', () => ({
  aiApi: {
    getDbSchemaGraph: vi.fn().mockResolvedValue({ success: true, nodes: [], edges: [] }),
    getDbSchema: vi.fn().mockResolvedValue({ success: true, tables: [] }),
  },
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
    ADMIN_DATABASE: {
      TABLE: (name: string) => `/admin/database/table/${name}`,
      INFO: '/admin/database/info',
    },
  },
}));

vi.mock('../../components/ai/KnowledgeGraph', () => ({
  KnowledgeGraph: (props: Record<string, unknown>) => (
    <div data-testid="mock-knowledge-graph" data-doc-ids={JSON.stringify(props.documentIds)}>
      KnowledgeGraph
    </div>
  ),
}));

// ============================================================================
// Helper
// ============================================================================

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <DatabaseGraphPage />
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

let DatabaseGraphPage: React.FC;

beforeEach(async () => {
  vi.clearAllMocks();
  // Default: loading state
  mockQueryReturn = { data: null, isLoading: true };
  const mod = await import('../../pages/DatabaseGraphPage');
  DatabaseGraphPage = mod.default;
});

// ============================================================================
// Tests
// ============================================================================

describe('DatabaseGraphPage', () => {
  it('renders page title "資料庫圖譜"', () => {
    renderPage();
    expect(screen.getByText('資料庫圖譜')).toBeInTheDocument();
  });

  it('renders page subtitle', () => {
    renderPage();
    expect(screen.getByText(/視覺化資料表 ER 關聯/)).toBeInTheDocument();
  });

  it('renders graph statistics card title', () => {
    renderPage();
    expect(screen.getByText('圖譜統計')).toBeInTheDocument();
  });

  it('shows loading indicator when data is loading', () => {
    mockQueryReturn = { data: null, isLoading: true };
    renderPage();
    expect(screen.getByText('載入資料庫圖譜...')).toBeInTheDocument();
  });

  it('renders table count statistic when data is loaded', () => {
    mockQueryReturn = {
      data: { graphData: mockGraphData, schemaMap: mockSchemaMap },
      isLoading: false,
    };
    renderPage();
    expect(screen.getByText('資料表')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('renders FK relationship count when data is loaded', () => {
    mockQueryReturn = {
      data: { graphData: mockGraphData, schemaMap: mockSchemaMap },
      isLoading: false,
    };
    renderPage();
    expect(screen.getByText('FK 關係')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders KnowledgeGraph component when data is loaded', () => {
    mockQueryReturn = {
      data: { graphData: mockGraphData, schemaMap: mockSchemaMap },
      isLoading: false,
    };
    renderPage();
    expect(screen.getByTestId('mock-knowledge-graph')).toBeInTheDocument();
  });

  it('renders refresh button in stats card', () => {
    renderPage();
    const statsCard = screen.getByText('圖譜統計').closest('.ant-card');
    expect(statsCard).toBeTruthy();
    const refreshBtn = statsCard?.querySelector('button');
    expect(refreshBtn).toBeTruthy();
  });

  it('shows "無資料" text when no graph data available', () => {
    mockQueryReturn = { data: null, isLoading: false };
    renderPage();
    expect(screen.getByText('無資料')).toBeInTheDocument();
  });

  it('passes empty documentIds to KnowledgeGraph', () => {
    mockQueryReturn = {
      data: { graphData: mockGraphData, schemaMap: mockSchemaMap },
      isLoading: false,
    };
    renderPage();
    const graph = screen.getByTestId('mock-knowledge-graph');
    expect(graph.getAttribute('data-doc-ids')).toBe('[]');
  });
});

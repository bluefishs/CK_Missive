/**
 * AgenciesPage Tests
 *
 * Tests for the agency management page including:
 * - Page title and description
 * - Statistics cards
 * - Search bar and category filter
 * - Action buttons (add, refresh)
 * - Table rendering
 * - Pagination
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

const mockRefetch = vi.fn();
const mockRefetchStatistics = vi.fn();

const mockStatistics = {
  total_agencies: 25,
  categories: [
    { category: '政府機關', count: 15, percentage: 60 },
    { category: '民間企業', count: 8, percentage: 32 },
    { category: '其他單位', count: 2, percentage: 8 },
  ],
};

const mockAgencies = [
  {
    id: 1,
    agency_name: 'Test Gov Agency',
    agency_short_name: 'TGA',
    agency_code: 'GOV-001',
    category: '政府機關',
    created_at: '2026-01-01T00:00:00Z',
    document_count: 0,
    sent_count: 0,
    received_count: 0,
    last_activity: null,
    primary_type: 'unknown',
  },
  {
    id: 2,
    agency_name: 'Test Private Corp',
    agency_short_name: null,
    agency_code: 'PVT-001',
    category: '民間企業',
    created_at: '2026-02-01T00:00:00Z',
    document_count: 0,
    sent_count: 0,
    received_count: 0,
    last_activity: null,
    primary_type: 'unknown',
  },
];

vi.mock('../../hooks', () => ({
  useAgenciesPage: vi.fn(() => ({
    agencies: mockAgencies,
    pagination: { total: 25 },
    isLoading: false,
    statistics: mockStatistics,
    refetch: mockRefetch,
    refetchStatistics: mockRefetchStatistics,
  })),
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

vi.mock('../../constants', () => ({
  AGENCY_CATEGORY_OPTIONS: [
    { value: '政府機關', label: '政府機關' },
    { value: '民間企業', label: '民間企業' },
    { value: '其他單位', label: '其他單位' },
  ],
}));

vi.mock('../../router/types', () => ({
  ROUTES: {
    AGENCY_CREATE: '/agencies/create',
    AGENCY_EDIT: '/agencies/:id/edit',
  },
}));

vi.mock('../../components/common', () => ({
  ResponsiveTable: (props: {
    dataSource: unknown[];
    loading: boolean;
    columns: { title: string }[];
  }) => (
    <div data-testid="mock-responsive-table">
      <table>
        <thead>
          <tr>
            {props.columns.map((col, i) => (
              <th key={i}>{typeof col.title === 'string' ? col.title : ''}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {(props.dataSource as { id: number; agency_name: string }[]).map((item) => (
            <tr key={item.id}>
              <td>{item.agency_name}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ),
}));

vi.mock('react-highlight-words', () => ({
  default: ({ textToHighlight }: { textToHighlight: string }) => <span>{textToHighlight}</span>,
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderAgenciesPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <AgenciesPageWrapper />
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function AgenciesPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/AgenciesPage').then((mod) => {
      setPage(() => mod.AgenciesPage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('AgenciesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders page title', async () => {
    renderAgenciesPage();
    await waitFor(() => {
      expect(screen.getByText('機關單位管理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders page description', async () => {
    renderAgenciesPage();
    await waitFor(() => {
      expect(screen.getByText('統計和管理公文往來的所有機關單位資訊')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders total agencies statistic card', async () => {
    renderAgenciesPage();
    await waitFor(() => {
      expect(screen.getByText('機關總數')).toBeInTheDocument();
      expect(screen.getByText('25')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders government agency statistic card', async () => {
    renderAgenciesPage();
    await waitFor(() => {
      expect(screen.getByText('政府機關')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders private enterprise statistic card', async () => {
    renderAgenciesPage();
    await waitFor(() => {
      expect(screen.getByText('民間企業')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders other category statistic card', async () => {
    renderAgenciesPage();
    await waitFor(() => {
      expect(screen.getByText('其他單位')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders search input', async () => {
    renderAgenciesPage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜尋機關名稱...')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders add agency button', async () => {
    renderAgenciesPage();
    await waitFor(() => {
      expect(screen.getByText('新增機關')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('navigates to create page when add button is clicked', async () => {
    renderAgenciesPage();
    await waitFor(() => {
      expect(screen.getByText('新增機關')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('新增機關'));
    expect(mockNavigate).toHaveBeenCalledWith('/agencies/create');
  });

  it('renders the table component', async () => {
    renderAgenciesPage();
    await waitFor(() => {
      expect(screen.getByTestId('mock-responsive-table')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders pagination showing total count', async () => {
    renderAgenciesPage();
    await waitFor(() => {
      // Ant Design Pagination renders total info
      expect(screen.getByText(/共 25 個機關/)).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

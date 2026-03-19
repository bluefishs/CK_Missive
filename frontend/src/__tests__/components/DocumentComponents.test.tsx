/**
 * Document Components - Smoke & Interaction Tests
 *
 * Tests: DocumentPagination, DocumentFilter
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { createTestQueryClient } from '../../test/testUtils';

// ============================================================================
// Mocks
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

// Mock hooks used by DocumentFilter
vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

import { DocumentPagination } from '../../components/document/DocumentPagination';

// ============================================================================
// Helpers
// ============================================================================

const defaultPaginationProps = {
  page: 1,
  limit: 20,
  total: 100,
  totalPages: 5,
  onPageChange: vi.fn(),
  onLimitChange: vi.fn(),
};

// ============================================================================
// DocumentPagination Tests
// ============================================================================

describe('DocumentPagination', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders total count', () => {
    render(<DocumentPagination {...defaultPaginationProps} />);
    const matches = screen.getAllByText(/共 100 筆/);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it('renders range text', () => {
    render(<DocumentPagination {...defaultPaginationProps} />);
    expect(screen.getByText(/顯示第 1 - 20 筆/)).toBeInTheDocument();
  });

  it('renders correct range for page 2', () => {
    render(<DocumentPagination {...defaultPaginationProps} page={2} />);
    expect(screen.getByText(/顯示第 21 - 40 筆/)).toBeInTheDocument();
  });

  it('renders statistics with receive/send counts', () => {
    const docs = [
      { id: 1, category: 'receive', status: '收文完成', doc_number: 'R1', subject: 'A', created_at: '', updated_at: '' },
      { id: 2, category: 'receive', status: '處理中', doc_number: 'R2', subject: 'B', created_at: '', updated_at: '' },
      { id: 3, category: 'send', status: '收文完成', doc_number: 'S1', subject: 'C', created_at: '', updated_at: '' },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ] as any[];

    render(
      <DocumentPagination {...defaultPaginationProps} documents={docs} />
    );

    // Check statistics rendered
    expect(screen.getByText('總計')).toBeInTheDocument();
    expect(screen.getByText('收文')).toBeInTheDocument();
    expect(screen.getByText('發文')).toBeInTheDocument();
    expect(screen.getByText('已完成')).toBeInTheDocument();
  });

  it('renders zero stats when no documents', () => {
    render(<DocumentPagination {...defaultPaginationProps} documents={[]} />);
    expect(screen.getByText('收文')).toBeInTheDocument();
  });

  it('renders pagination when totalPages > 1', () => {
    const { container } = render(
      <DocumentPagination {...defaultPaginationProps} totalPages={5} />
    );
    expect(container.querySelector('.ant-pagination')).toBeInTheDocument();
  });

  it('does not render pagination when totalPages is 1', () => {
    const { container } = render(
      <DocumentPagination {...defaultPaginationProps} totalPages={1} total={5} />
    );
    expect(container.querySelector('.ant-pagination')).not.toBeInTheDocument();
  });

  it('calculates endItem correctly on last page', () => {
    render(
      <DocumentPagination
        {...defaultPaginationProps}
        page={5}
        total={92}
        totalPages={5}
      />
    );
    // page 5: startItem=81, endItem=min(100, 92)=92
    expect(screen.getByText(/顯示第 81 - 92 筆/)).toBeInTheDocument();
  });
});

// ============================================================================
// DocumentFilter Tests (smoke test with mocked sub-components)
// ============================================================================

// Mock the sub-components and hooks that DocumentFilter depends on
vi.mock('../../components/document/DocumentFilter/hooks', () => ({
  useFilterOptions: vi.fn(() => ({
    yearOptions: [{ value: '113', label: '113' }],
    contractCaseOptions: [{ value: 'PROJ-1', label: 'Project 1' }],
    senderOptions: [{ value: 'Agency A', label: 'Agency A' }],
    receiverOptions: [{ value: 'Agency B', label: 'Agency B' }],
    isLoading: false,
  })),
  useAutocompleteSuggestions: vi.fn(() => ({
    suggestions: [],
    isLoading: false,
  })),
}));

vi.mock('../../components/document/DocumentFilter/components', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  PrimaryFilters: (props: any) => (
    <div data-testid="primary-filters">
      <button data-testid="apply-btn" onClick={props.onApplyFilters}>Apply</button>
    </div>
  ),
  AdvancedFilters: () => <div data-testid="advanced-filters">AdvancedFilters</div>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  FilterActions: (props: any) => (
    <div data-testid="filter-actions">
      <button data-testid="reset-btn" onClick={props.onReset}>Reset</button>
      <button data-testid="apply-action-btn" onClick={props.onApplyFilters}>Apply</button>
    </div>
  ),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  FilterFieldWrapper: ({ children }: any) => <div>{children}</div>,
}));

import { DocumentFilter } from '../../components/document/DocumentFilter';

describe('DocumentFilter', () => {
  const defaultProps = {
    filters: {},
    onFiltersChange: vi.fn(),
    onReset: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderFilter = (props = {}) =>
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter>
          <DocumentFilter {...defaultProps} {...props} />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it('renders without crashing', () => {
    renderFilter();
    expect(screen.getByTestId('primary-filters')).toBeInTheDocument();
    expect(screen.getByTestId('filter-actions')).toBeInTheDocument();
  });

  it('shows title text', () => {
    renderFilter();
    expect(screen.getByText('搜尋與篩選')).toBeInTheDocument();
  });

  it('calls onFiltersChange when apply is clicked', () => {
    renderFilter();
    fireEvent.click(screen.getByTestId('apply-btn'));
    expect(defaultProps.onFiltersChange).toHaveBeenCalledTimes(1);
  });

  it('calls onReset when reset is clicked', () => {
    renderFilter();
    fireEvent.click(screen.getByTestId('reset-btn'));
    expect(defaultProps.onReset).toHaveBeenCalledTimes(1);
  });

  it('shows active filter count when filters are present', () => {
    renderFilter({
      filters: { category: 'receive', keyword: 'test' },
    });
    // Active filter count badge
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('expands advanced filters on toggle click', () => {
    renderFilter();
    // Initially no advanced filters
    expect(screen.queryByTestId('advanced-filters')).not.toBeInTheDocument();

    // Click expand button
    const expandBtn = screen.getByRole('button', { name: /展開/i });
    fireEvent.click(expandBtn);

    expect(screen.getByTestId('advanced-filters')).toBeInTheDocument();
  });
});

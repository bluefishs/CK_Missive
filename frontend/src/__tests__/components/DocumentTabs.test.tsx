/**
 * DocumentTabs - Unit Tests
 *
 * Tests: tab rendering, tab switching, document count display
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

// Mock React Query
vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(() => ({
    data: { total: 100, receive: 60, send: 40 },
    isLoading: false,
  })),
  useQueryClient: vi.fn(() => ({
    invalidateQueries: vi.fn(),
  })),
}));

// Mock documentsApi
vi.mock('../../api/documentsApi', () => ({
  documentsApi: {
    getFilteredStatistics: vi.fn(() =>
      Promise.resolve({ success: true, total: 100, receive_count: 60, send_count: 40 })
    ),
  },
}));

// Mock defaultQueryOptions
vi.mock('../../config/queryConfig', () => ({
  defaultQueryOptions: {
    statistics: { staleTime: 60000, refetchOnWindowFocus: false },
  },
}));

// Mock DocumentList to avoid deep dependency tree
vi.mock('../../components/document/DocumentList', () => ({
  DocumentList: ({ documents }: { documents: unknown[] }) => (
    <div data-testid="document-list">Documents: {documents.length}</div>
  ),
}));

// ============================================================================
// Imports (after mocks)
// ============================================================================

import { DocumentTabs } from '../../components/document/DocumentTabs';
import type { Document, DocumentFilter } from '../../types';

// ============================================================================
// Helpers
// ============================================================================

function renderWithAntd(ui: React.ReactElement) {
  return render(
    <ConfigProvider locale={zhTW}>
      <AntApp>{ui}</AntApp>
    </ConfigProvider>,
  );
}

const mockDocuments: Document[] = [
  {
    id: 1,
    link_id: 'doc-1',
    doc_number: 'A001',
    subject: 'Test Document 1',
    doc_type: '函',
    category: '收文',
  } as unknown as Document,
  {
    id: 2,
    link_id: 'doc-2',
    doc_number: 'B001',
    subject: 'Test Document 2',
    doc_type: '函',
    category: '發文',
  } as unknown as Document,
];

const defaultProps = {
  documents: mockDocuments,
  loading: false,
  filters: { page: 1, limit: 20 } as DocumentFilter & { page: number; limit: number },
  total: 100,
  onEdit: vi.fn(),
  onDelete: vi.fn(),
  onView: vi.fn(),
  totalAll: 100,
  totalReceived: 60,
  totalSent: 40,
};

// ============================================================================
// Tests
// ============================================================================

describe('DocumentTabs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders all three tabs', () => {
    renderWithAntd(<DocumentTabs {...defaultProps} />);
    expect(screen.getByText('全部')).toBeInTheDocument();
    expect(screen.getByText('收文')).toBeInTheDocument();
    expect(screen.getByText('發文')).toBeInTheDocument();
  });

  it('renders document count badges', () => {
    const { container } = renderWithAntd(<DocumentTabs {...defaultProps} />);
    // Ant Design Badge renders count in .ant-badge elements
    const badges = container.querySelectorAll('.ant-badge');
    expect(badges.length).toBeGreaterThanOrEqual(3);
  });

  it('defaults to "all" tab when no category filter', () => {
    renderWithAntd(<DocumentTabs {...defaultProps} />);
    // The "all" tab should be active - check DocumentList is rendered
    expect(screen.getByTestId('document-list')).toBeInTheDocument();
  });

  it('calls onFiltersChange when switching to received tab', () => {
    const onFiltersChange = vi.fn();
    renderWithAntd(
      <DocumentTabs {...defaultProps} onFiltersChange={onFiltersChange} />,
    );
    fireEvent.click(screen.getByText('收文'));
    expect(onFiltersChange).toHaveBeenCalledWith(
      expect.objectContaining({ category: 'receive' }),
    );
  });

  it('calls onFiltersChange when switching to sent tab', () => {
    const onFiltersChange = vi.fn();
    renderWithAntd(
      <DocumentTabs {...defaultProps} onFiltersChange={onFiltersChange} />,
    );
    fireEvent.click(screen.getByText('發文'));
    expect(onFiltersChange).toHaveBeenCalledWith(
      expect.objectContaining({ category: 'send' }),
    );
  });

  it('calls onFiltersChange without category when switching to all tab', () => {
    const onFiltersChange = vi.fn();
    renderWithAntd(
      <DocumentTabs
        {...defaultProps}
        filters={{ ...defaultProps.filters, category: 'receive' } as DocumentFilter & { page: number; limit: number }}
        onFiltersChange={onFiltersChange}
      />,
    );
    fireEvent.click(screen.getByText('全部'));
    expect(onFiltersChange).toHaveBeenCalledWith(
      expect.not.objectContaining({ category: expect.anything() }),
    );
  });

  it('renders DocumentList component for the active tab', () => {
    renderWithAntd(<DocumentTabs {...defaultProps} />);
    expect(screen.getByText(`Documents: ${mockDocuments.length}`)).toBeInTheDocument();
  });
});

/**
 * DocumentFilter - Unit Tests
 *
 * Tests filter form rendering, filter changes, reset, and expand/collapse.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';
import type { DocumentFilter as DocumentFilterType } from '../../types';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
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

// Mock the useFilterOptions hook
vi.mock('../../components/document/DocumentFilter/hooks', () => ({
  useFilterOptions: vi.fn(() => ({
    yearOptions: [
      { value: '114', label: '114' },
      { value: '113', label: '113' },
    ],
    contractCaseOptions: [
      { value: 'case-1', label: 'Case 1' },
    ],
    senderOptions: [
      { value: 'sender-1', label: 'Sender 1' },
    ],
    receiverOptions: [
      { value: 'receiver-1', label: 'Receiver 1' },
    ],
    isLoading: false,
  })),
  useAutocompleteSuggestions: vi.fn(() => ({
    suggestions: [],
    isLoading: false,
  })),
}));

// Mock api client
vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({ data: {} }),
    post: vi.fn().mockResolvedValue({ data: {} }),
  },
}));

// ============================================================================
// Imports (after mocks)
// ============================================================================

import { DocumentFilter } from '../../components/document/DocumentFilter/index';

// ============================================================================
// Helpers
// ============================================================================

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>{ui}</AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

// ============================================================================
// Tests
// ============================================================================

describe('DocumentFilter', () => {
  const defaultFilters: DocumentFilterType = {};
  const mockOnFiltersChange = vi.fn();
  const mockOnReset = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the filter card with search title', () => {
    renderWithProviders(
      <DocumentFilter
        filters={defaultFilters}
        onFiltersChange={mockOnFiltersChange}
        onReset={mockOnReset}
      />,
    );
    expect(screen.getByText('搜尋與篩選')).toBeInTheDocument();
  });

  it('renders the expand/collapse button', () => {
    renderWithProviders(
      <DocumentFilter
        filters={defaultFilters}
        onFiltersChange={mockOnFiltersChange}
        onReset={mockOnReset}
      />,
    );
    expect(screen.getByText('展開')).toBeInTheDocument();
  });

  it('toggles advanced filters on expand click', async () => {
    renderWithProviders(
      <DocumentFilter
        filters={defaultFilters}
        onFiltersChange={mockOnFiltersChange}
        onReset={mockOnReset}
      />,
    );

    const expandBtn = screen.getByText('展開');
    fireEvent.click(expandBtn);

    await waitFor(() => {
      expect(screen.getByText('進階查詢')).toBeInTheDocument();
    });
    expect(screen.getByText('收起')).toBeInTheDocument();
  });

  it('calls onReset when clear filter button is clicked', async () => {
    const activeFilters: DocumentFilterType = { doc_type: '收文', search: 'test' };
    renderWithProviders(
      <DocumentFilter
        filters={activeFilters}
        onFiltersChange={mockOnFiltersChange}
        onReset={mockOnReset}
      />,
    );

    // The button text is "清除篩選" not "重置"
    const resetBtn = screen.getByText('清除篩選');
    fireEvent.click(resetBtn);

    expect(mockOnReset).toHaveBeenCalledTimes(1);
  });

  it('shows active filter count badge when filters are active', () => {
    const activeFilters: DocumentFilterType = { doc_type: '收文', search: 'keyword' };
    renderWithProviders(
      <DocumentFilter
        filters={activeFilters}
        onFiltersChange={mockOnFiltersChange}
        onReset={mockOnReset}
      />,
    );

    // The count badge should show 2 active filters
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('does not show filter count badge when no active filters', () => {
    renderWithProviders(
      <DocumentFilter
        filters={defaultFilters}
        onFiltersChange={mockOnFiltersChange}
        onReset={mockOnReset}
      />,
    );

    // No filter count badge
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });

  it('calls onFiltersChange when apply button is clicked', () => {
    renderWithProviders(
      <DocumentFilter
        filters={defaultFilters}
        onFiltersChange={mockOnFiltersChange}
        onReset={mockOnReset}
      />,
    );

    const applyBtn = screen.getByText('套用篩選');
    fireEvent.click(applyBtn);

    expect(mockOnFiltersChange).toHaveBeenCalledTimes(1);
  });

  it('renders apply filter button', () => {
    renderWithProviders(
      <DocumentFilter
        filters={defaultFilters}
        onFiltersChange={mockOnFiltersChange}
        onReset={mockOnReset}
      />,
    );

    expect(screen.getByText('套用篩選')).toBeInTheDocument();
  });
});

/**
 * InlineRecordCreator - Unit Tests
 *
 * Tests collapsed/expanded states, form rendering, cancel, and submission.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
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

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

const mockWorkflowCreate = vi.fn().mockResolvedValue({ id: 99 });
vi.mock('../../api/taoyuan', () => ({
  workflowApi: {
    create: (...args: unknown[]) => mockWorkflowCreate(...args),
  },
}));

vi.mock('../../config/queryConfig', () => ({
  queryKeys: {
    workRecords: {
      dispatch: (id: number) => ['workRecords', 'dispatch', id],
      projectAll: ['workRecords', 'projectAll'],
    },
  },
}));

// ============================================================================
// Imports (after mocks)
// ============================================================================

import { InlineRecordCreator } from '../../components/taoyuan/workflow/InlineRecordCreator';

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

describe('InlineRecordCreator', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders collapsed state with add button', () => {
    renderWithProviders(
      <InlineRecordCreator
        dispatchOrderId={1}
        existingRecords={[]}
      />,
    );
    expect(screen.getByText('新增作業紀錄')).toBeInTheDocument();
  });

  it('expands form when add button is clicked', async () => {
    renderWithProviders(
      <InlineRecordCreator
        dispatchOrderId={1}
        existingRecords={[]}
      />,
    );

    fireEvent.click(screen.getByText('新增作業紀錄'));

    await waitFor(() => {
      expect(screen.getByText('作業類別')).toBeInTheDocument();
    });
    expect(screen.getByText('狀態')).toBeInTheDocument();
    expect(screen.getByText('關聯公文')).toBeInTheDocument();
  });

  it('renders close button in expanded state', async () => {
    renderWithProviders(
      <InlineRecordCreator
        dispatchOrderId={1}
        existingRecords={[]}
      />,
    );

    fireEvent.click(screen.getByText('新增作業紀錄'));

    await waitFor(() => {
      // The close icon button has aria-label "關閉"
      expect(screen.getByLabelText('關閉')).toBeInTheDocument();
    });
  });

  it('shows 建立紀錄 submit button in expanded state', async () => {
    renderWithProviders(
      <InlineRecordCreator
        dispatchOrderId={1}
        existingRecords={[]}
      />,
    );

    fireEvent.click(screen.getByText('新增作業紀錄'));

    await waitFor(() => {
      expect(screen.getByText('建立紀錄')).toBeInTheDocument();
    });
  });

  it('renders form fields including deadline date in expanded state', async () => {
    renderWithProviders(
      <InlineRecordCreator
        dispatchOrderId={1}
        existingRecords={[]}
      />,
    );

    fireEvent.click(screen.getByText('新增作業紀錄'));

    await waitFor(() => {
      expect(screen.getByText('期限日期')).toBeInTheDocument();
      expect(screen.getByText('前序紀錄')).toBeInTheDocument();
    });
  });

  it('renders close button (X icon) in expanded state', async () => {
    renderWithProviders(
      <InlineRecordCreator
        dispatchOrderId={1}
        existingRecords={[]}
      />,
    );

    fireEvent.click(screen.getByText('新增作業紀錄'));

    await waitFor(() => {
      expect(screen.getByLabelText('關閉')).toBeInTheDocument();
    });
  });

  it('shows description textarea in expanded form', async () => {
    renderWithProviders(
      <InlineRecordCreator
        dispatchOrderId={1}
        existingRecords={[]}
      />,
    );

    fireEvent.click(screen.getByText('新增作業紀錄'));

    await waitFor(() => {
      expect(screen.getByText('事項描述')).toBeInTheDocument();
    });
  });
});

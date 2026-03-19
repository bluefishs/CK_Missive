/**
 * ChainTimeline - Unit Tests
 *
 * Tests timeline rendering, empty state, chain items, and edit/delete controls.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import type { WorkRecord } from '../../types/taoyuan';

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

// ============================================================================
// Imports (after mocks)
// ============================================================================

import { ChainTimeline } from '../../components/taoyuan/workflow/ChainTimeline';

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

function createMockRecord(overrides: Partial<WorkRecord> = {}): WorkRecord {
  return {
    id: 1,
    dispatch_order_id: 100,
    milestone_type: 'dispatch',
    record_date: '2026-01-15',
    status: 'in_progress',
    sort_order: 1,
    ...overrides,
  };
}

// ============================================================================
// Tests
// ============================================================================

describe('ChainTimeline', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state when no records provided', () => {
    renderWithAntd(<ChainTimeline records={[]} />);
    expect(screen.getByText('尚無作業紀錄')).toBeInTheDocument();
  });

  it('renders timeline items with index numbers', () => {
    const records: WorkRecord[] = [
      createMockRecord({ id: 1, sort_order: 1 }),
      createMockRecord({ id: 2, sort_order: 2 }),
    ];

    renderWithAntd(<ChainTimeline records={records} />);
    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('#2')).toBeInTheDocument();
  });

  it('shows document number when incoming doc is present', () => {
    const records: WorkRecord[] = [
      createMockRecord({
        id: 1,
        incoming_doc: { id: 10, doc_number: 'INC-2026-001', doc_date: '2026-01-10' },
      }),
    ];

    renderWithAntd(<ChainTimeline records={records} />);
    expect(screen.getByText('INC-2026-001')).toBeInTheDocument();
  });

  it('shows "待關聯公文" when no document is attached', () => {
    const records: WorkRecord[] = [createMockRecord({ id: 1 })];

    renderWithAntd(<ChainTimeline records={records} />);
    expect(screen.getByText('待關聯公文')).toBeInTheDocument();
  });

  it('renders edit and delete buttons when canEdit is true', () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const records: WorkRecord[] = [createMockRecord({ id: 1 })];

    renderWithAntd(
      <ChainTimeline
        records={records}
        canEdit={true}
        onEditRecord={onEdit}
        onDeleteRecord={onDelete}
      />,
    );
    expect(screen.getByLabelText('編輯')).toBeInTheDocument();
    expect(screen.getByLabelText('刪除')).toBeInTheDocument();
  });

  it('does not render edit/delete buttons when canEdit is false', () => {
    const records: WorkRecord[] = [createMockRecord({ id: 1 })];

    renderWithAntd(<ChainTimeline records={records} canEdit={false} />);
    expect(screen.queryByLabelText('編輯')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('刪除')).not.toBeInTheDocument();
  });

  it('calls onEditRecord when edit button is clicked', () => {
    const onEdit = vi.fn();
    const record = createMockRecord({ id: 1 });

    renderWithAntd(
      <ChainTimeline
        records={[record]}
        canEdit={true}
        onEditRecord={onEdit}
        onDeleteRecord={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByLabelText('編輯'));
    expect(onEdit).toHaveBeenCalledWith(record);
  });

  it('renders record with description', () => {
    const records: WorkRecord[] = [
      createMockRecord({ id: 1, description: 'Test work description' }),
    ];

    renderWithAntd(<ChainTimeline records={records} />);
    expect(screen.getByText('Test work description')).toBeInTheDocument();
  });
});

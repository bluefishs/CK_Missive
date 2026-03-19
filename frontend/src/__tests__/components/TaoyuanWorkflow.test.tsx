/**
 * Taoyuan Workflow Components - Smoke & Interaction Tests
 *
 * Tests: WorkRecordStatsCard, ChainTimeline, workCategoryConstants
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
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

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

vi.mock('../../components/taoyuan/workflow/useDeleteWorkRecord', () => ({
  useDeleteWorkRecord: vi.fn(() => ({ deleteRecord: vi.fn() })),
}));

// ============================================================================
// Imports (after mocks)
// ============================================================================

import { WorkRecordStatsCard } from '../../components/taoyuan/workflow/WorkRecordStatsCard';
import { ChainTimeline } from '../../components/taoyuan/workflow/ChainTimeline';
import {
  MILESTONE_LABELS,
  MILESTONE_COLORS,
  STATUS_LABELS,
  STATUS_COLORS,
  WORK_CATEGORY_GROUPS,
  WORK_CATEGORY_LABELS,
  WORK_CATEGORY_COLORS,
  getCategoryLabel,
  getCategoryColor,
  milestoneLabel,
  milestoneColor,
  statusLabel,
  statusColor,
} from '../../components/taoyuan/workflow/workCategoryConstants';
import type { WorkRecord } from '../../types/taoyuan';

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

const baseStats = {
  total: 10,
  completed: 6,
  inProgress: 3,
  incomingDocs: 4,
  outgoingDocs: 2,
  currentStage: '查估中',
};

function createMockWorkRecord(overrides: Partial<WorkRecord> = {}): WorkRecord {
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
// WorkRecordStatsCard Tests
// ============================================================================

describe('WorkRecordStatsCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders in dispatch mode with stats', () => {
    renderWithAntd(
      <WorkRecordStatsCard
        mode="dispatch"
        stats={baseStats}
        onHold={1}
        linkedDocCount={5}
        unassignedDocCount={2}
        workType="01.地上物查估作業"
      />,
    );
    // Check stats text is present
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('6 完成')).toBeInTheDocument();
    expect(screen.getByText('3 進行中')).toBeInTheDocument();
    expect(screen.getByText('1 暫緩')).toBeInTheDocument();
  });

  it('renders in project mode with stats', () => {
    renderWithAntd(
      <WorkRecordStatsCard
        mode="project"
        stats={baseStats}
        dispatchCount={5}
      />,
    );
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('renders dispatch mode without optional props', () => {
    renderWithAntd(
      <WorkRecordStatsCard mode="dispatch" stats={baseStats} />,
    );
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('作業紀錄')).toBeInTheDocument();
  });

  it('shows incoming/outgoing doc counts', () => {
    renderWithAntd(
      <WorkRecordStatsCard mode="dispatch" stats={baseStats} />,
    );
    expect(screen.getByText(/來文 4/)).toBeInTheDocument();
    expect(screen.getByText(/發文 2/)).toBeInTheDocument();
  });

  it('renders project mode with workTypeStages', () => {
    renderWithAntd(
      <WorkRecordStatsCard
        mode="project"
        stats={{ ...baseStats, currentStage: '全部完成' }}
        workTypeStages={[
          {
            workType: '01.地上物查估作業',
            stage: '送件完成',
            status: 'completed',
            total: 3,
            completed: 3,
          },
        ]}
      />,
    );
    expect(screen.getByText('地上物查估作業')).toBeInTheDocument();
    expect(screen.getByText('送件完成')).toBeInTheDocument();
  });

  it('displays "作業進度" section', () => {
    renderWithAntd(
      <WorkRecordStatsCard mode="dispatch" stats={baseStats} />,
    );
    expect(screen.getByText('作業進度')).toBeInTheDocument();
  });
});

// ============================================================================
// ChainTimeline Tests
// ============================================================================

describe('ChainTimeline', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state when no records', () => {
    renderWithAntd(<ChainTimeline records={[]} />);
    expect(screen.getByText('尚無作業紀錄')).toBeInTheDocument();
  });

  it('renders timeline items for records', () => {
    const records: WorkRecord[] = [
      createMockWorkRecord({
        id: 1,
        milestone_type: 'dispatch',
        status: 'completed',
        description: 'First record description',
      }),
      createMockWorkRecord({
        id: 2,
        milestone_type: 'survey',
        status: 'in_progress',
        description: 'Second record description',
      }),
    ];

    renderWithAntd(<ChainTimeline records={records} />);
    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('#2')).toBeInTheDocument();
  });

  it('renders record with incoming document', () => {
    const records: WorkRecord[] = [
      createMockWorkRecord({
        id: 1,
        incoming_doc: {
          id: 10,
          doc_number: 'TEST-DOC-001',
          doc_date: '2026-01-10',
        },
      }),
    ];

    renderWithAntd(<ChainTimeline records={records} />);
    expect(screen.getByText('TEST-DOC-001')).toBeInTheDocument();
  });

  it('renders "待關聯公文" when no document attached', () => {
    const records: WorkRecord[] = [
      createMockWorkRecord({ id: 1 }),
    ];

    renderWithAntd(<ChainTimeline records={records} />);
    expect(screen.getByText('待關聯公文')).toBeInTheDocument();
  });

  it('renders with canEdit=true showing edit/delete buttons', () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const records: WorkRecord[] = [
      createMockWorkRecord({ id: 1 }),
    ];

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

  it('does not render edit/delete when canEdit is false', () => {
    const records: WorkRecord[] = [
      createMockWorkRecord({ id: 1 }),
    ];

    renderWithAntd(<ChainTimeline records={records} canEdit={false} />);
    expect(screen.queryByLabelText('編輯')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('刪除')).not.toBeInTheDocument();
  });
});

// ============================================================================
// workCategoryConstants Tests
// ============================================================================

describe('workCategoryConstants', () => {
  describe('MILESTONE_LABELS', () => {
    it('has labels for all known milestone types', () => {
      const knownTypes = [
        'dispatch', 'survey', 'site_inspection', 'submit_result',
        'revision', 'review_meeting', 'negotiation', 'final_approval',
        'boundary_survey', 'closed', 'other',
      ];
      for (const type of knownTypes) {
        expect(MILESTONE_LABELS[type]).toBeTruthy();
      }
    });

    it('has matching colors for all milestone types', () => {
      for (const key of Object.keys(MILESTONE_LABELS)) {
        expect(MILESTONE_COLORS[key]).toBeTruthy();
      }
    });
  });

  describe('STATUS_LABELS', () => {
    it('has labels for all known statuses', () => {
      const statuses = ['pending', 'in_progress', 'completed', 'overdue', 'on_hold'];
      for (const status of statuses) {
        expect(STATUS_LABELS[status]).toBeTruthy();
      }
    });

    it('has matching colors for all statuses', () => {
      for (const key of Object.keys(STATUS_LABELS)) {
        expect(STATUS_COLORS[key]).toBeTruthy();
      }
    });

    it('STATUS_LABELS is non-empty', () => {
      expect(Object.keys(STATUS_LABELS).length).toBeGreaterThan(0);
    });
  });

  describe('WORK_CATEGORY_GROUPS', () => {
    it('has at least 3 groups', () => {
      expect(WORK_CATEGORY_GROUPS.length).toBeGreaterThanOrEqual(3);
    });

    it('each group has a label and non-empty items', () => {
      for (const group of WORK_CATEGORY_GROUPS) {
        expect(group.group).toBeTruthy();
        expect(group.items.length).toBeGreaterThan(0);
      }
    });

    it('all items have value, label, and color', () => {
      for (const group of WORK_CATEGORY_GROUPS) {
        for (const item of group.items) {
          expect(item.value).toBeTruthy();
          expect(item.label).toBeTruthy();
          expect(item.color).toBeTruthy();
        }
      }
    });

    it('flattened lookup tables are populated', () => {
      expect(Object.keys(WORK_CATEGORY_LABELS).length).toBeGreaterThan(0);
      expect(Object.keys(WORK_CATEGORY_COLORS).length).toBeGreaterThan(0);
    });
  });

  describe('helper functions', () => {
    it('milestoneLabel returns label for known type', () => {
      expect(milestoneLabel('dispatch')).toBe('派工');
      expect(milestoneLabel('closed')).toBe('結案');
    });

    it('milestoneLabel returns raw value for unknown type', () => {
      expect(milestoneLabel('unknown_type')).toBe('unknown_type');
    });

    it('milestoneColor returns color for known type', () => {
      expect(milestoneColor('dispatch')).toBe('blue');
    });

    it('milestoneColor returns "default" for unknown type', () => {
      expect(milestoneColor('unknown_type')).toBe('default');
    });

    it('statusLabel returns label for known status', () => {
      expect(statusLabel('pending')).toBe('待處理');
      expect(statusLabel('completed')).toBe('已完成');
    });

    it('statusColor returns color for known status', () => {
      expect(statusColor('completed')).toBe('success');
    });

    it('getCategoryLabel prefers work_category over milestone_type', () => {
      const record = createMockWorkRecord({
        work_category: 'dispatch_notice',
        milestone_type: 'dispatch',
      });
      expect(getCategoryLabel(record)).toBe('派工通知');
    });

    it('getCategoryLabel falls back to milestone_type', () => {
      const record = createMockWorkRecord({
        milestone_type: 'survey',
      });
      expect(getCategoryLabel(record)).toBe('會勘');
    });

    it('getCategoryColor prefers work_category over milestone_type', () => {
      const record = createMockWorkRecord({
        work_category: 'dispatch_notice',
        milestone_type: 'dispatch',
      });
      expect(getCategoryColor(record)).toBe('blue');
    });

    it('getCategoryColor falls back to milestone_type', () => {
      const record = createMockWorkRecord({
        milestone_type: 'survey',
      });
      expect(getCategoryColor(record)).toBe('cyan');
    });
  });
});

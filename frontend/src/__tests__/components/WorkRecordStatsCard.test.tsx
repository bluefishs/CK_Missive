/**
 * WorkRecordStatsCard - Unit Tests
 *
 * Tests dispatch/project mode rendering, stats display, and conditional sections.
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

// ============================================================================
// Imports (after mocks)
// ============================================================================

import { WorkRecordStatsCard } from '../../components/taoyuan/workflow/WorkRecordStatsCard';

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

// ============================================================================
// Tests
// ============================================================================

describe('WorkRecordStatsCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dispatch mode with total and completed stats', () => {
    renderWithAntd(
      <WorkRecordStatsCard
        mode="dispatch"
        stats={baseStats}
        onHold={1}
        linkedDocCount={5}
      />,
    );
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('6 完成')).toBeInTheDocument();
    expect(screen.getByText('3 進行中')).toBeInTheDocument();
    expect(screen.getByText('1 暫緩')).toBeInTheDocument();
  });

  it('renders project mode with dispatch count', () => {
    renderWithAntd(
      <WorkRecordStatsCard
        mode="project"
        stats={baseStats}
        dispatchCount={5}
      />,
    );
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('派工數')).toBeInTheDocument();
  });

  it('shows incoming and outgoing doc counts', () => {
    renderWithAntd(
      <WorkRecordStatsCard mode="dispatch" stats={baseStats} />,
    );
    expect(screen.getByText(/來文 4/)).toBeInTheDocument();
    expect(screen.getByText(/發文 2/)).toBeInTheDocument();
  });

  it('renders 作業紀錄 label', () => {
    renderWithAntd(
      <WorkRecordStatsCard mode="dispatch" stats={baseStats} />,
    );
    expect(screen.getByText('作業紀錄')).toBeInTheDocument();
  });

  it('renders 作業進度 section', () => {
    renderWithAntd(
      <WorkRecordStatsCard mode="dispatch" stats={baseStats} />,
    );
    expect(screen.getByText('作業進度')).toBeInTheDocument();
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

  it('does not show onHold tag when onHold is 0', () => {
    renderWithAntd(
      <WorkRecordStatsCard
        mode="dispatch"
        stats={baseStats}
        onHold={0}
      />,
    );
    expect(screen.queryByText(/暫緩/)).not.toBeInTheDocument();
  });
});

/**
 * EnhancedCalendarView Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
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

vi.mock('../../components/calendar/EventFormModal', () => ({
  EventFormModal: () => <div data-testid="event-form-modal" />,
}));

vi.mock('../../components/calendar/ReminderSettingsModal', () => ({
  ReminderSettingsModal: () => <div data-testid="reminder-modal" />,
}));

vi.mock('../../components/calendar/views', () => ({
  CalendarHeader: ({ onViewModeChange: _onViewModeChange }: { onViewModeChange: (v: string) => void }) => (
    <div data-testid="calendar-header">Header</div>
  ),
  CalendarStatistics: () => <div data-testid="calendar-stats">Stats</div>,
  CalendarFilters: () => <div data-testid="calendar-filters" />,
  MonthView: () => <div data-testid="month-view">Month</div>,
  EventListView: () => <div data-testid="list-view">List</div>,
  TimelineView: () => <div data-testid="timeline-view">Timeline</div>,
  EventDetailModal: () => <div data-testid="event-detail-modal" />,
  EVENT_TYPE_CONFIG: {
    deadline: { name: '截止日', color: 'red' },
    meeting: { name: '會議', color: 'blue' },
  },
  QUICK_FILTER_LABELS: {
    all: '全部',
    today: '今天',
    thisWeek: '本週',
    upcoming: '即將到來',
    overdue: '已逾期',
  },
}));

// ============================================================================
// Helpers
// ============================================================================

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp><MemoryRouter>{ui}</MemoryRouter></AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

// ============================================================================
// Tests
// ============================================================================

describe('EnhancedCalendarView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing with no events', async () => {
    const { EnhancedCalendarView } = await import('../../components/calendar/EnhancedCalendarView');
    const { container } = renderWithProviders(
      <EnhancedCalendarView events={[]} />
    );
    expect(container).toBeTruthy();
  });

  it('renders without crashing with default props', async () => {
    const { EnhancedCalendarView } = await import('../../components/calendar/EnhancedCalendarView');
    const { container } = renderWithProviders(
      <EnhancedCalendarView />
    );
    expect(container).toBeTruthy();
  });

  it('renders calendar header and statistics', async () => {
    const { EnhancedCalendarView } = await import('../../components/calendar/EnhancedCalendarView');
    const { getByTestId } = renderWithProviders(
      <EnhancedCalendarView events={[]} />
    );
    expect(getByTestId('calendar-header')).toBeInTheDocument();
    expect(getByTestId('calendar-stats')).toBeInTheDocument();
  });
});

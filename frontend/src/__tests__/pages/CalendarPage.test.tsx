/**
 * CalendarPage - Comprehensive Page-Level Tests
 *
 * Tests rendering, Google Calendar integration display, responsive behavior,
 * and user interaction for the calendar management page (行事曆管理).
 *
 * @version 1.0.0
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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

const mockBulkSync = vi.fn().mockResolvedValue({ success: true, synced_count: 5, failed_count: 0 });
const mockUpdateEvent = vi.fn().mockResolvedValue({});
const mockDeleteEvent = vi.fn().mockResolvedValue({});
const mockRefetch = vi.fn();

const mockCalendarEvents = [
  {
    id: 1,
    title: '公文截止日',
    description: '桃園市政府來文需回覆',
    start_datetime: '2026-03-14T09:00:00',
    end_datetime: '2026-03-14T17:00:00',
    event_type: 'deadline',
    priority: 4,
    status: 'pending',
    document_id: 101,
    doc_number: '桃府字第1150001號',
    google_event_id: null,
    google_sync_status: null,
  },
  {
    id: 2,
    title: '專案會議',
    description: '季度檢討會議',
    start_datetime: '2026-03-14T14:00:00',
    end_datetime: '2026-03-14T15:30:00',
    event_type: 'meeting',
    priority: 2,
    status: 'pending',
    document_id: null,
    doc_number: null,
    google_event_id: 'google-event-abc',
    google_sync_status: 'synced',
  },
];

const mockCategories = [
  { value: 'deadline', label: '截止日', color: '#f5222d' },
  { value: 'meeting', label: '會議', color: '#1890ff' },
  { value: 'reminder', label: '提醒', color: '#52c41a' },
];

const mockUseCalendarPage = vi.fn(() => ({
  events: mockCalendarEvents,
  categories: mockCategories,
  googleStatus: { google_calendar_available: true },
  isLoading: false,
  updateEvent: mockUpdateEvent,
  deleteEvent: mockDeleteEvent,
  bulkSync: mockBulkSync,
  isSyncing: false,
  refetch: mockRefetch,
}));

const mockUseResponsive = vi.fn(() => ({
  isMobile: false,
  isTablet: false,
  isDesktop: true,
  responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
}));

vi.mock('../../hooks', () => ({
  useCalendarPage: () => mockUseCalendarPage(),
  useResponsive: () => mockUseResponsive(),
}));

vi.mock('../../components/calendar/EnhancedCalendarView', () => ({
  EnhancedCalendarView: (props: { loading: boolean; events: unknown[] }) => (
    <div data-testid="mock-calendar-view" data-loading={String(props.loading)}>
      Calendar ({(props.events || []).length} events)
    </div>
  ),
}));

vi.mock('../../services/authService', () => {
  const mockService = {
    isAuthenticated: vi.fn(() => true),
    getCurrentUser: vi.fn(),
    getUserInfo: vi.fn(() => ({ id: 1, username: 'test', role: 'admin' })),
    getToken: vi.fn(() => 'token'),
  };
  return { __esModule: true, default: mockService, ...mockService };
});

// ============================================================================
// Helper
// ============================================================================

function renderPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <CalendarPage />
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

let CalendarPage: React.FC;

beforeEach(async () => {
  vi.clearAllMocks();
  mockUseCalendarPage.mockReturnValue({
    events: mockCalendarEvents,
    categories: mockCategories,
    googleStatus: { google_calendar_available: true },
    isLoading: false,
    updateEvent: mockUpdateEvent,
    deleteEvent: mockDeleteEvent,
    bulkSync: mockBulkSync,
    isSyncing: false,
    refetch: mockRefetch,
  });
  mockUseResponsive.mockReturnValue({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  });
  const mod = await import('../../pages/CalendarPage');
  CalendarPage = mod.default;
});

// ============================================================================
// Tests
// ============================================================================

describe('CalendarPage', () => {
  // --- Basic Rendering ---

  it('renders page title "行事曆管理" on desktop', () => {
    renderPage();
    expect(screen.getByText('行事曆管理')).toBeInTheDocument();
  });

  it('renders shorter title "行事曆" on mobile', () => {
    mockUseResponsive.mockReturnValue({
      isMobile: true,
      isTablet: false,
      isDesktop: false,
      responsiveValue: (v: Record<string, unknown>) => v.mobile ?? v.tablet ?? v.desktop,
    });
    renderPage();
    expect(screen.getByText('行事曆')).toBeInTheDocument();
  });

  it('renders EnhancedCalendarView component', () => {
    renderPage();
    expect(screen.getByTestId('mock-calendar-view')).toBeInTheDocument();
  });

  it('passes events to calendar view', () => {
    renderPage();
    expect(screen.getByText('Calendar (2 events)')).toBeInTheDocument();
  });

  // --- Google Calendar Integration ---

  it('shows Google connection status tag when connected', () => {
    renderPage();
    expect(screen.getByText('已連接 Google')).toBeInTheDocument();
  });

  it('shows "未連接" when Google Calendar is not available', () => {
    mockUseCalendarPage.mockReturnValue({
      events: [],
      categories: mockCategories,
      googleStatus: { google_calendar_available: false },
      isLoading: false,
      updateEvent: mockUpdateEvent,
      deleteEvent: mockDeleteEvent,
      bulkSync: mockBulkSync,
      isSyncing: false,
      refetch: mockRefetch,
    });
    renderPage();
    expect(screen.getByText('未連接')).toBeInTheDocument();
  });

  it('renders sync button', () => {
    renderPage();
    expect(screen.getByText('同步')).toBeInTheDocument();
  });

  it('calls bulkSync when sync button is clicked', async () => {
    renderPage();
    const syncBtn = screen.getByText('同步').closest('button');
    expect(syncBtn).toBeTruthy();
    fireEvent.click(syncBtn!);
    await waitFor(() => {
      expect(mockBulkSync).toHaveBeenCalled();
    });
  });

  // --- Desktop Sidebar ---

  it('renders sidebar event card on desktop with date', () => {
    renderPage();
    // The sidebar card title format is "MM/DD 事件 (N)"
    // Default selectedDate is today, so sidebar shows today's events (likely 0 unless date matches)
    // Since our mock events are on 2026-03-14 and test may run on different dates,
    // we just check the sidebar card exists
    const sidebarCards = screen.getAllByText(/事件/);
    expect(sidebarCards.length).toBeGreaterThan(0);
  });

  it('shows "此日無事件" when no events for selected date', () => {
    mockUseCalendarPage.mockReturnValue({
      events: [],
      categories: mockCategories,
      googleStatus: { google_calendar_available: true },
      isLoading: false,
      updateEvent: mockUpdateEvent,
      deleteEvent: mockDeleteEvent,
      bulkSync: mockBulkSync,
      isSyncing: false,
      refetch: mockRefetch,
    });
    renderPage();
    expect(screen.getByText('此日無事件')).toBeInTheDocument();
  });

  // --- Loading State ---

  it('passes loading state to EnhancedCalendarView', () => {
    mockUseCalendarPage.mockReturnValue({
      events: [],
      categories: [],
      googleStatus: null as unknown as { google_calendar_available: boolean },
      isLoading: true,
      updateEvent: mockUpdateEvent,
      deleteEvent: mockDeleteEvent,
      bulkSync: mockBulkSync,
      isSyncing: false,
      refetch: mockRefetch,
    });
    renderPage();
    const cal = screen.getByTestId('mock-calendar-view');
    expect(cal.getAttribute('data-loading')).toBe('true');
  });

  // --- No Google Status ---

  it('does not render sync button when googleStatus is null', () => {
    mockUseCalendarPage.mockReturnValue({
      events: [],
      categories: [],
      googleStatus: null as unknown as { google_calendar_available: boolean },
      isLoading: false,
      updateEvent: mockUpdateEvent,
      deleteEvent: mockDeleteEvent,
      bulkSync: mockBulkSync,
      isSyncing: false,
      refetch: mockRefetch,
    });
    renderPage();
    expect(screen.queryByText('同步')).not.toBeInTheDocument();
  });
});

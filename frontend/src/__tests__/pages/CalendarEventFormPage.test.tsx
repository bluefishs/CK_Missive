/**
 * CalendarEventFormPage Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({}),
    useLocation: () => ({ pathname: '/calendar/event/new', search: '', state: null }),
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/client', () => ({
  apiClient: { get: vi.fn().mockResolvedValue({}), post: vi.fn().mockResolvedValue({}) },
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    CALENDAR: {
      DETAIL: vi.fn(() => '/calendar/events/1'),
      CREATE: '/calendar/events/create',
      UPDATE: vi.fn(() => '/calendar/events/1/update'),
      DELETE: vi.fn(() => '/calendar/events/1/delete'),
    },
    DOCUMENTS: {
      DETAIL: vi.fn(() => '/documents/1'),
      SEARCH: '/documents/search',
    },
  },
}));

vi.mock('../../config/queryConfig', () => ({
  queryKeys: { calendar: { all: ['calendar'] } },
}));

vi.mock('@ck-shared/ui-components', () => ({
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('../../components/calendar/form/types', () => ({
  EVENT_TYPE_OPTIONS: [{ value: 'meeting', label: '會議' }],
  PRIORITY_OPTIONS: [{ value: 'normal', label: '普通' }],
}));

vi.mock('../../api/calendarApi', () => ({
  calendarApi: {
    getById: vi.fn().mockResolvedValue(null),
    create: vi.fn().mockResolvedValue({ id: 1 }),
  },
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>{ui}</MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

describe('CalendarEventFormPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/CalendarEventFormPage');
    renderWithProviders(<mod.default />);
    // Should render a form with event fields
    expect(document.querySelector('form') || screen.queryByText(/事件|行事曆|日曆/)).not.toBeNull();
  });
});

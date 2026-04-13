/**
 * EventFormModal Smoke Test
 *
 * Note: Ant Design Form with `forceRender` requires a real FormInstance from Form.useForm().
 * We mock useEventForm to NOT return form, and instead let the real component create it
 * by NOT mocking useEventForm and instead mocking the underlying APIs.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import { createTestQueryClient } from '../../test/testUtils';

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../utils/logger', () => ({
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

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    CALENDAR: {
      EVENTS_LIST: '/calendar/events/list',
      EVENTS_CREATE: '/calendar/events/create',
      EVENTS_UPDATE: '/calendar/events/update',
    },
    DOCUMENTS_ENDPOINTS: {
      SEARCH: '/documents/search',
      LIST: '/documents/list',
    },
  },
}));

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

// Mock the form/types to provide type constants
vi.mock('../../components/calendar/form/types', () => ({
  EVENT_TYPE_OPTIONS: [
    { value: 'deadline', label: '截止日' },
    { value: 'reminder', label: '提醒' },
  ],
  PRIORITY_OPTIONS: [
    { value: 1, label: '高', color: '#f5222d' },
    { value: 3, label: '中', color: '#1890ff' },
  ],
}));

// We use a wrapper component that provides a real form instance
vi.mock('../../components/calendar/form/useEventForm', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports, @typescript-eslint/no-var-requires
  const { Form: AntForm } = require('antd');
  return {
    useEventForm: vi.fn(() => {
      // Create a store-backed form instance
      const [formInstance] = AntForm.useForm();
      return {
        form: formInstance,
        isMobile: false,
        loading: false,
        allDay: false,
        setAllDay: vi.fn(),
        documentOptions: [],
        documentSearchError: null,
        existingEventsWarning: null,
        documentSearching: false,
        searchDocuments: vi.fn(),
        handleDocumentChange: vi.fn(),
        handleSubmit: vi.fn(),
      };
    }),
  };
});

import { EventFormModal } from '../../components/calendar/EventFormModal';

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

describe('EventFormModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing (open=false)', () => {
    renderWithProviders(
      <EventFormModal
        open={false}
        mode="create"
        event={undefined}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
      />,
    );
  });

  it('renders open modal with title', () => {
    const { getByText } = renderWithProviders(
      <EventFormModal
        open={true}
        mode="create"
        event={undefined}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
      />,
    );
    expect(getByText('新增日曆事件')).toBeInTheDocument();
  });
});

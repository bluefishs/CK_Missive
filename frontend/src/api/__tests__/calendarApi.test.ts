/**
 * calendarApi 單元測試
 * calendarApi Unit Tests
 *
 * 測試行事曆 API 服務
 *
 * 執行方式:
 *   cd frontend && npx vitest run src/api/__tests__/calendarApi.test.ts
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock apiClient
vi.mock('../client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

// Mock authService
vi.mock('../../services/authService', () => ({
  authService: {
    getUserInfo: vi.fn(() => ({ id: 1, username: 'testuser' })),
  },
}));

// Mock dayjs - provide a stable date for testing
vi.mock('dayjs', () => {
  const mockDayjs = () => ({
    subtract: () => ({
      format: () => '2026-01-01',
    }),
    add: () => ({
      format: () => '2026-05-01',
    }),
  });
  mockDayjs.extend = vi.fn();
  return { default: mockDayjs };
});

// Mock endpoints
vi.mock('../endpoints', () => ({
  API_ENDPOINTS: {
    CALENDAR: {
      USER_EVENTS: '/calendar/users/calendar-events',
      EVENTS_LIST: '/calendar/events/list',
      EVENTS_CREATE: '/calendar/events',
      EVENTS_DETAIL: '/calendar/events/detail',
      EVENTS_UPDATE: '/calendar/events/update',
      EVENTS_DELETE: '/calendar/events/delete',
      EVENTS_SYNC: '/calendar/events/sync',
      EVENTS_BULK_SYNC: '/calendar/events/bulk-sync',
    },
    PUBLIC: {
      CALENDAR_STATUS: '/public/calendar-status',
    },
  },
}));

// Mock logger
vi.mock('../../utils/logger', () => ({
  logger: {
    log: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
    info: vi.fn(),
  },
}));

import { apiClient } from '../client';
import { calendarApi, DEFAULT_CATEGORIES } from '../calendarApi';
import { authService } from '../../services/authService';

// ============================================================================
// Mock 資料
// ============================================================================

const mockRawEvent = {
  id: 1,
  title: '公文截止日',
  description: '工程查估報告繳交',
  start_date: '2026-03-01T09:00:00Z',
  end_date: '2026-03-01T17:00:00Z',
  all_day: false,
  document_id: 10,
  doc_number: 'CK-114-001',
  contract_project_name: '桃園橋梁工程',
  event_type: 'deadline',
  priority: 'high',
  status: 'pending',
  location: '桃園市政府',
  google_event_id: null,
  google_sync_status: 'pending',
};

// ============================================================================
// calendarApi.getEvents 測試
// ============================================================================

describe('calendarApi.getEvents - 取得行事曆事件', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功取得事件應正確轉換格式', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      events: [mockRawEvent],
      total: 1,
    });

    const result = await calendarApi.getEvents();

    expect(apiClient.post).toHaveBeenCalledWith(
      '/calendar/users/calendar-events',
      expect.objectContaining({
        user_id: 1,
        start_date: expect.any(String),
        end_date: expect.any(String),
      })
    );
    expect(result).toHaveLength(1);
    expect(result[0]!.id).toBe(1);
    expect(result[0]!.title).toBe('公文截止日');
    expect(result[0]!.start_datetime).toBe('2026-03-01T09:00:00Z');
    expect(result[0]!.end_datetime).toBe('2026-03-01T17:00:00Z');
    expect(result[0]!.document_id).toBe(10);
    expect(result[0]!.doc_number).toBe('CK-114-001');
    expect(result[0]!.contract_project_name).toBe('桃園橋梁工程');
  });

  it('未登入使用者應使用預設 userId=1', async () => {
    vi.mocked(authService.getUserInfo).mockReturnValue(null as unknown as ReturnType<typeof authService.getUserInfo>);
    vi.mocked(apiClient.post).mockResolvedValue({ success: true, events: [], total: 0 });

    await calendarApi.getEvents();

    expect(apiClient.post).toHaveBeenCalledWith(
      '/calendar/users/calendar-events',
      expect.objectContaining({ user_id: 1 })
    );
  });

  it('API 回傳空 events 時應回傳空陣列', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true, events: [], total: 0 });

    const result = await calendarApi.getEvents();

    expect(result).toEqual([]);
  });

  it('API 回傳非標準格式（直接陣列）時應直接回傳', async () => {
    const directArray = [{ id: 1, title: '事件' }];
    vi.mocked(apiClient.post).mockResolvedValue(directArray);

    const result = await calendarApi.getEvents();

    expect(result).toEqual(directArray);
  });

  it('API 回傳 null 或不明格式時應回傳空陣列', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true });

    const result = await calendarApi.getEvents();

    expect(result).toEqual([]);
  });

  it('API 錯誤時應回傳空陣列（不拋出）', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Network Error'));

    const result = await calendarApi.getEvents();

    expect(result).toEqual([]);
  });

  it('事件缺少 all_day 和 status 時應使用預設值', async () => {
    const eventWithoutDefaults = {
      ...mockRawEvent,
      all_day: undefined,
      status: undefined,
      google_sync_status: undefined,
    };
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      events: [eventWithoutDefaults],
      total: 1,
    });

    const result = await calendarApi.getEvents();

    expect(result[0]!.all_day).toBe(false);
    expect(result[0]!.status).toBe('pending');
    expect(result[0]!.google_sync_status).toBe('pending');
  });
});

// ============================================================================
// calendarApi.getGoogleStatus 測試
// ============================================================================

describe('calendarApi.getGoogleStatus - Google Calendar 狀態', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('已配置 Google Calendar 應回傳 connected 狀態', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      google_calendar_integration: true,
      google_status: { configured: true, calendar_id: 'primary' },
      message: '已連接',
      endpoint_type: 'google',
      features: ['Google 同步', '雙向更新'],
    });

    const result = await calendarApi.getGoogleStatus();

    expect(apiClient.get).toHaveBeenCalledWith('/public/calendar-status');
    expect(result.google_calendar_available).toBe(true);
    expect(result.connection_status.status).toBe('connected');
    expect(result.connection_status.calendars).toHaveLength(1);
    expect(result.service_type).toBe('google');
    expect(result.features).toEqual(['Google 同步', '雙向更新']);
  });

  it('未配置 Google Calendar 應回傳 disconnected', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      google_calendar_integration: false,
      google_status: { configured: false },
      message: '未連接',
    });

    const result = await calendarApi.getGoogleStatus();

    expect(result.google_calendar_available).toBe(false);
    expect(result.connection_status.status).toBe('disconnected');
    expect(result.connection_status.calendars).toEqual([]);
  });

  it('API 錯誤時應回傳 error 狀態的 fallback', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error('Connection failed'));

    const result = await calendarApi.getGoogleStatus();

    expect(result.google_calendar_available).toBe(false);
    expect(result.connection_status.status).toBe('error');
    expect(result.connection_status.message).toBe('無法連接到行事曆服務');
    expect(result.supported_event_types).toHaveLength(DEFAULT_CATEGORIES.length);
    expect(result.features).toContain('基本行事曆檢視');
  });

  it('回應缺少可選欄位時應使用預設值', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({});

    const result = await calendarApi.getGoogleStatus();

    expect(result.google_calendar_available).toBe(false);
    expect(result.connection_status.message).toBe('狀態未知');
    expect(result.service_type).toBe('basic');
    expect(result.features).toEqual(['本地行事曆', '事件提醒']);
  });
});

// ============================================================================
// calendarApi.updateEvent 測試
// ============================================================================

describe('calendarApi.updateEvent - 更新事件', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功更新事件應正常完成', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true });

    await expect(
      calendarApi.updateEvent(1, { title: '更新標題', status: 'completed' })
    ).resolves.toBeUndefined();

    expect(apiClient.post).toHaveBeenCalledWith(
      '/calendar/events/update',
      expect.objectContaining({
        event_id: 1,
        title: '更新標題',
        status: 'completed',
      })
    );
  });

  it('支援 start_datetime 日期格式', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true });

    await calendarApi.updateEvent(1, {
      start_datetime: '2026-04-01T09:00:00Z',
      end_datetime: '2026-04-01T17:00:00Z',
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/calendar/events/update',
      expect.objectContaining({
        start_date: '2026-04-01T09:00:00Z',
        end_date: '2026-04-01T17:00:00Z',
      })
    );
  });

  it('支援 start_date 拖曳更新格式', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true });

    await calendarApi.updateEvent(1, {
      start_date: '2026-04-02',
      end_date: '2026-04-03',
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/calendar/events/update',
      expect.objectContaining({
        start_date: '2026-04-02',
        end_date: '2026-04-03',
      })
    );
  });

  it('後端回傳 success: false 時應拋出錯誤', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: false,
      message: '事件不存在',
    });

    await expect(calendarApi.updateEvent(999, { title: 'x' })).rejects.toThrow('事件不存在');
  });

  it('API 錯誤時應拋出錯誤', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Server Error'));

    await expect(calendarApi.updateEvent(1, {})).rejects.toThrow('Server Error');
  });
});

// ============================================================================
// calendarApi.deleteEvent 測試
// ============================================================================

describe('calendarApi.deleteEvent - 刪除事件', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功刪除事件', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true });

    await expect(calendarApi.deleteEvent(1)).resolves.toBeUndefined();

    expect(apiClient.post).toHaveBeenCalledWith(
      '/calendar/events/delete',
      { event_id: 1, confirm: true }
    );
  });

  it('後端回傳 success: false 時應拋出錯誤', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: false,
      message: '無權刪除此事件',
    });

    await expect(calendarApi.deleteEvent(1)).rejects.toThrow('無權刪除此事件');
  });

  it('後端回傳 success: false 但無 message 時應用預設訊息', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: false });

    await expect(calendarApi.deleteEvent(1)).rejects.toThrow('刪除事件失敗');
  });

  it('API 錯誤時應拋出錯誤', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Forbidden'));

    await expect(calendarApi.deleteEvent(1)).rejects.toThrow('Forbidden');
  });
});

// ============================================================================
// calendarApi.bulkSync 測試
// ============================================================================

describe('calendarApi.bulkSync - 批次同步', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功批次同步', async () => {
    const mockResponse = {
      success: true,
      message: '同步完成',
      synced_count: 5,
      failed_count: 0,
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await calendarApi.bulkSync();

    expect(apiClient.post).toHaveBeenCalledWith(
      '/calendar/events/bulk-sync',
      { sync_all_pending: true }
    );
    expect(result.synced_count).toBe(5);
    expect(result.failed_count).toBe(0);
  });

  it('部分同步失敗', async () => {
    const mockResponse = {
      success: true,
      message: '部分同步失敗',
      synced_count: 3,
      failed_count: 2,
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await calendarApi.bulkSync();

    expect(result.synced_count).toBe(3);
    expect(result.failed_count).toBe(2);
  });

  it('API 錯誤時應拋出錯誤', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Google API Error'));

    await expect(calendarApi.bulkSync()).rejects.toThrow('Google API Error');
  });
});

// ============================================================================
// calendarApi.syncEvent 測試
// ============================================================================

describe('calendarApi.syncEvent - 同步單一事件', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功同步事件', async () => {
    const mockResponse = {
      success: true,
      message: '已同步',
      google_event_id: 'google-evt-123',
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await calendarApi.syncEvent(1);

    expect(apiClient.post).toHaveBeenCalledWith(
      '/calendar/events/sync',
      { event_id: 1, force_sync: false }
    );
    expect(result.success).toBe(true);
    expect(result.google_event_id).toBe('google-evt-123');
  });

  it('強制同步模式', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true, message: '強制同步完成' });

    await calendarApi.syncEvent(1, true);

    expect(apiClient.post).toHaveBeenCalledWith(
      '/calendar/events/sync',
      { event_id: 1, force_sync: true }
    );
  });

  it('API 錯誤時應拋出錯誤', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Sync Failed'));

    await expect(calendarApi.syncEvent(1)).rejects.toThrow('Sync Failed');
  });
});

// ============================================================================
// DEFAULT_CATEGORIES 測試
// ============================================================================

describe('DEFAULT_CATEGORIES - 預設分類', () => {
  it('應包含 4 個事件分類', () => {
    expect(DEFAULT_CATEGORIES).toHaveLength(4);
  });

  it('應包含 reminder, deadline, meeting, review', () => {
    const values = DEFAULT_CATEGORIES.map(c => c.value);
    expect(values).toContain('reminder');
    expect(values).toContain('deadline');
    expect(values).toContain('meeting');
    expect(values).toContain('review');
  });

  it('每個分類應有 value, label, color', () => {
    for (const cat of DEFAULT_CATEGORIES) {
      expect(cat).toHaveProperty('value');
      expect(cat).toHaveProperty('label');
      expect(cat).toHaveProperty('color');
      expect(cat.color).toMatch(/^#[0-9a-fA-F]{6}$/);
    }
  });
});

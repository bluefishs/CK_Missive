/**
 * 行事曆整合服務測試
 * CalendarIntegrationService Tests
 *
 * 測試範圍:
 * - 單例模式 (getInstance)
 * - convertDocumentToEventData - 日期處理、事件類型判斷、優先級
 * - addDocumentToCalendar - 成功與失敗路徑
 * - batchAddDocumentsToCalendar - 部分成功追蹤
 * - removeDocumentFromCalendar - 清除行為
 * - isDocumentInCalendar - 查詢邏輯
 * - determineEventType / determinePriority / determineEventDate 輔助邏輯
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

// ---------------------------------------------------------------------------
// Mock 依賴
// ---------------------------------------------------------------------------

const mockApiClientPost = vi.fn();

vi.mock('../../api/client', () => ({
  apiClient: {
    post: (...args: unknown[]) => mockApiClientPost(...args),
  },
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    CALENDAR: {
      EVENTS_CREATE: '/calendar/events',
      EVENTS_LIST: '/calendar/events/list',
      EVENTS_DELETE: '/calendar/events/delete',
    },
  },
}));

vi.mock('../../utils/logger', () => ({
  logger: {
    error: vi.fn(),
    warn: vi.fn(),
    log: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
  },
}));

// ---------------------------------------------------------------------------
// 輔助：建立測試用公文物件
// ---------------------------------------------------------------------------

interface TestDocumentFields {
  id?: number;
  doc_number?: string;
  subject?: string;
  doc_type?: string;
  content?: string;
  sender?: string;
  receiver?: string;
  send_date?: string;
  receive_date?: string;
  doc_date?: string;
  priority_level?: string;
  contract_case?: string;
  assignee?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

function makeDocument(overrides: TestDocumentFields = {}) {
  return {
    id: 1,
    doc_number: 'A-2026-001',
    subject: '測試公文主旨',
    doc_type: '收文',
    content: '',
    sender: '台北市政府',
    receiver: '',
    send_date: '',
    receive_date: '2026-03-01',
    doc_date: '2026-02-28',
    priority_level: '',
    contract_case: '',
    assignee: '',
    notes: '',
    created_at: '2026-02-27T00:00:00Z',
    updated_at: '2026-02-27T00:00:00Z',
    ...overrides,
  } as import('../../types').Document;
}

// ---------------------------------------------------------------------------
// 測試
// ---------------------------------------------------------------------------

describe('CalendarIntegrationService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // =========================================================================
  // 單例模式
  // =========================================================================

  describe('單例模式', () => {
    it('匯出的 calendarIntegrationService 應該是有效的實例', async () => {
      const { calendarIntegrationService } = await import('../calendarIntegrationService');
      expect(calendarIntegrationService).toBeDefined();
      expect(typeof calendarIntegrationService.addDocumentToCalendar).toBe('function');
    });

    it('default export 與 named export 應該是同一個實例', async () => {
      const mod = await import('../calendarIntegrationService');
      expect(mod.default).toBe(mod.calendarIntegrationService);
    });
  });

  // =========================================================================
  // addDocumentToCalendar (間接測試 convertDocumentToEventData)
  // =========================================================================

  describe('addDocumentToCalendar', () => {
    it('成功時應回傳 success=true 與事件 ID', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost.mockResolvedValueOnce({
        message: '已新增',
        event_id: 99,
        google_event_id: 'goog-123',
      });

      const doc = makeDocument();
      const result = await service.addDocumentToCalendar(doc);

      expect(result.success).toBe(true);
      expect(result.local_event_id).toBe(99);
      expect(result.google_event_id).toBe('goog-123');
      expect(result.message).toBe('已新增');
    });

    it('API 回傳 id 而非 event_id 時應正確取得', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost.mockResolvedValueOnce({ id: 55 });

      const result = await service.addDocumentToCalendar(makeDocument());

      expect(result.success).toBe(true);
      expect(result.local_event_id).toBe(55);
    });

    it('API 無 message 時應產生預設成功訊息', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost.mockResolvedValueOnce({});

      const doc = makeDocument({ doc_number: 'B-001' });
      const result = await service.addDocumentToCalendar(doc);

      expect(result.success).toBe(true);
      expect(result.message).toContain('B-001');
      expect(result.message).toContain('成功添加到行事曆');
    });

    it('API 失敗時應回傳 success=false 與錯誤訊息', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost.mockRejectedValueOnce(new Error('伺服器錯誤'));

      const result = await service.addDocumentToCalendar(makeDocument());

      expect(result.success).toBe(false);
      expect(result.message).toBe('伺服器錯誤');
    });

    it('非 Error 類型的失敗應使用預設訊息', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost.mockRejectedValueOnce('unknown error');

      const result = await service.addDocumentToCalendar(makeDocument());

      expect(result.success).toBe(false);
      expect(result.message).toBe('新增至日曆失敗');
    });

    it('請求 body 應包含 document_id 和事件資料', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost.mockResolvedValueOnce({ event_id: 1 });

      await service.addDocumentToCalendar(
        makeDocument({ id: 42, subject: '重要公文' })
      );

      const [endpoint, body] = mockApiClientPost.mock.calls[0];
      expect(endpoint).toBe('/calendar/events');
      expect(body.document_id).toBe(42);
      expect(body.title).toContain('重要公文');
      expect(body.all_day).toBe(true);
      expect(body.reminder_enabled).toBe(true);
    });
  });

  // =========================================================================
  // determineEventType (透過 addDocumentToCalendar 間接測試)
  // =========================================================================

  describe('事件類型判斷 (determineEventType)', () => {
    async function getEventTypeForDoc(overrides: TestDocumentFields): Promise<string> {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );
      mockApiClientPost.mockResolvedValueOnce({ event_id: 1 });
      await service.addDocumentToCalendar(makeDocument(overrides));
      return mockApiClientPost.mock.calls[mockApiClientPost.mock.calls.length - 1][1]
        .event_type;
    }

    it('doc_type 含「會議」時應判定為 meeting', async () => {
      const type = await getEventTypeForDoc({ doc_type: '開會通知單' });
      expect(type).toBe('meeting');
    });

    it('subject 含「會議」時應判定為 meeting', async () => {
      const type = await getEventTypeForDoc({ subject: '年度會議通知' });
      expect(type).toBe('meeting');
    });

    it('content 含「審查」時應判定為 review', async () => {
      const type = await getEventTypeForDoc({ content: '本案須進行審查作業' });
      expect(type).toBe('review');
    });

    it('subject 含「截止」時應判定為 deadline', async () => {
      const type = await getEventTypeForDoc({ subject: '申請截止通知' });
      expect(type).toBe('deadline');
    });

    it('無匹配關鍵字時應預設為 reminder', async () => {
      const type = await getEventTypeForDoc({
        doc_type: '收文',
        subject: '一般通知',
        content: '無特殊內容',
      });
      expect(type).toBe('reminder');
    });
  });

  // =========================================================================
  // determinePriority (透過 addDocumentToCalendar 間接測試)
  // =========================================================================

  describe('優先級判斷 (determinePriority)', () => {
    async function getPriorityForDoc(overrides: TestDocumentFields): Promise<number> {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );
      mockApiClientPost.mockResolvedValueOnce({ event_id: 1 });
      await service.addDocumentToCalendar(makeDocument(overrides));
      return mockApiClientPost.mock.calls[mockApiClientPost.mock.calls.length - 1][1]
        .priority;
    }

    it('priority_level 為有效數字時應直接使用', async () => {
      const priority = await getPriorityForDoc({ priority_level: '2' });
      expect(priority).toBe(2);
    });

    it('doc_type 含「急件」時應回傳最高優先級 1', async () => {
      const priority = await getPriorityForDoc({ doc_type: '急件' });
      expect(priority).toBe(1);
    });

    it('doc_type 含「會議」時應回傳優先級 2', async () => {
      const priority = await getPriorityForDoc({ doc_type: '會議通知' });
      expect(priority).toBe(2);
    });

    it('一般公文應回傳預設優先級 3', async () => {
      const priority = await getPriorityForDoc({ doc_type: '收文' });
      expect(priority).toBe(3);
    });
  });

  // =========================================================================
  // determineEventDate (透過 addDocumentToCalendar 間接測試)
  // =========================================================================

  describe('事件日期判斷 (determineEventDate)', () => {
    async function getDateForDoc(overrides: TestDocumentFields): Promise<string> {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );
      mockApiClientPost.mockResolvedValueOnce({ event_id: 1 });
      await service.addDocumentToCalendar(makeDocument(overrides));
      return mockApiClientPost.mock.calls[mockApiClientPost.mock.calls.length - 1][1]
        .start_date;
    }

    it('有 send_date 時應優先使用', async () => {
      const date = await getDateForDoc({
        send_date: '2026-04-15',
        receive_date: '2026-04-10',
        doc_date: '2026-04-01',
      });
      expect(date).toContain('2026-04-15');
    });

    it('無 send_date 時應使用 receive_date', async () => {
      const date = await getDateForDoc({
        send_date: '',
        receive_date: '2026-05-20',
        doc_date: '2026-05-01',
      });
      expect(date).toContain('2026-05-20');
    });

    it('無 send_date 和 receive_date 時應使用 doc_date', async () => {
      const date = await getDateForDoc({
        send_date: '',
        receive_date: '',
        doc_date: '2026-06-30',
      });
      expect(date).toContain('2026-06-30');
    });

    it('所有日期皆空時應使用當前日期', async () => {
      const date = await getDateForDoc({
        send_date: '',
        receive_date: '',
        doc_date: '',
      });
      // 應為 ISO 格式字串，且年份為當前年
      expect(date).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    });
  });

  // =========================================================================
  // batchAddDocumentsToCalendar
  // =========================================================================

  describe('batchAddDocumentsToCalendar', () => {
    it('全部成功時應回傳正確計數與摘要', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost
        .mockResolvedValueOnce({ event_id: 1 })
        .mockResolvedValueOnce({ event_id: 2 });

      const docs = [makeDocument({ id: 1 }), makeDocument({ id: 2 })];
      const result = await service.batchAddDocumentsToCalendar(docs);

      expect(result.successCount).toBe(2);
      expect(result.failedCount).toBe(0);
      expect(result.results).toHaveLength(2);
      expect(result.summaryMessage).toContain('成功將 2 個公文加入日曆');
    });

    it('部分失敗時應追蹤成功與失敗數', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost
        .mockResolvedValueOnce({ event_id: 1 })
        .mockRejectedValueOnce(new Error('失敗'));

      const docs = [
        makeDocument({ id: 1, doc_number: 'OK-001' }),
        makeDocument({ id: 2, doc_number: 'FAIL-001' }),
      ];
      const result = await service.batchAddDocumentsToCalendar(docs);

      expect(result.successCount).toBe(1);
      expect(result.failedCount).toBe(1);
      expect(result.summaryMessage).toContain('成功將 1 個公文加入日曆');
      expect(result.summaryMessage).toContain('1 個失敗');
    });

    it('全部失敗時摘要應只顯示失敗數', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost
        .mockRejectedValueOnce(new Error('err1'))
        .mockRejectedValueOnce(new Error('err2'));

      const docs = [makeDocument({ id: 1 }), makeDocument({ id: 2 })];
      const result = await service.batchAddDocumentsToCalendar(docs);

      expect(result.successCount).toBe(0);
      expect(result.failedCount).toBe(2);
      expect(result.summaryMessage).toContain('2 個公文加入日曆失敗');
    });

    it('空陣列時應回傳零計數與空摘要', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      const result = await service.batchAddDocumentsToCalendar([]);

      expect(result.successCount).toBe(0);
      expect(result.failedCount).toBe(0);
      expect(result.summaryMessage).toBe('');
    });
  });

  // =========================================================================
  // isDocumentInCalendar
  // =========================================================================

  describe('isDocumentInCalendar', () => {
    it('有關聯事件時應回傳 true', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost.mockResolvedValueOnce({ success: true, total: 3 });

      const result = await service.isDocumentInCalendar(42);

      expect(result).toBe(true);
      expect(mockApiClientPost).toHaveBeenCalledWith(
        '/calendar/events/list',
        { document_id: 42, page: 1, page_size: 1 }
      );
    });

    it('無關聯事件時應回傳 false', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost.mockResolvedValueOnce({ success: true, total: 0 });

      const result = await service.isDocumentInCalendar(99);
      expect(result).toBe(false);
    });

    it('API 失敗時應回傳 false', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost.mockRejectedValueOnce(new Error('timeout'));

      const result = await service.isDocumentInCalendar(1);
      expect(result).toBe(false);
    });
  });

  // =========================================================================
  // removeDocumentFromCalendar
  // =========================================================================

  describe('removeDocumentFromCalendar', () => {
    it('有關聯事件時應逐一刪除並回傳成功', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      // 列出事件
      mockApiClientPost.mockResolvedValueOnce({
        events: [{ id: 10 }, { id: 20 }],
      });
      // 刪除事件 10
      mockApiClientPost.mockResolvedValueOnce({});
      // 刪除事件 20
      mockApiClientPost.mockResolvedValueOnce({});

      const result = await service.removeDocumentFromCalendar(5);

      expect(result.success).toBe(true);
      expect(result.message).toContain('2 個相關事件');

      // 檢查刪除呼叫的參數
      expect(mockApiClientPost).toHaveBeenCalledWith(
        '/calendar/events/delete',
        { event_id: 10, confirm: true }
      );
      expect(mockApiClientPost).toHaveBeenCalledWith(
        '/calendar/events/delete',
        { event_id: 20, confirm: true }
      );
    });

    it('無關聯事件時應回傳成功但顯示無事件訊息', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost.mockResolvedValueOnce({ events: [] });

      const result = await service.removeDocumentFromCalendar(7);

      expect(result.success).toBe(true);
      expect(result.message).toContain('沒有相關的日曆事件');
    });

    it('events 為 undefined 時應當作空陣列處理', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost.mockResolvedValueOnce({});

      const result = await service.removeDocumentFromCalendar(8);

      expect(result.success).toBe(true);
      expect(result.message).toContain('沒有相關的日曆事件');
    });

    it('部分刪除失敗時仍應回傳已刪除數量', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost.mockResolvedValueOnce({
        events: [{ id: 10 }, { id: 20 }, { id: 30 }],
      });
      // 10 成功, 20 失敗, 30 成功
      mockApiClientPost.mockResolvedValueOnce({});
      mockApiClientPost.mockRejectedValueOnce(new Error('delete fail'));
      mockApiClientPost.mockResolvedValueOnce({});

      const result = await service.removeDocumentFromCalendar(9);

      expect(result.success).toBe(true);
      expect(result.message).toContain('2 個相關事件');
    });

    it('列表 API 失敗時應回傳失敗', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );

      mockApiClientPost.mockRejectedValueOnce(new Error('list failed'));

      const result = await service.removeDocumentFromCalendar(10);

      expect(result.success).toBe(false);
      expect(result.message).toBe('從日曆移除事件失敗');
    });
  });

  // =========================================================================
  // 事件描述構建 (buildEventDescription, 透過 addDocumentToCalendar 間接測試)
  // =========================================================================

  describe('事件描述構建 (buildEventDescription)', () => {
    it('描述應包含字號、主旨、發文單位', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );
      mockApiClientPost.mockResolvedValueOnce({ event_id: 1 });

      await service.addDocumentToCalendar(
        makeDocument({
          doc_number: 'X-2026-100',
          subject: '工程驗收通知',
          sender: '桃園市政府',
        })
      );

      const description =
        mockApiClientPost.mock.calls[0][1].description as string;
      expect(description).toContain('X-2026-100');
      expect(description).toContain('工程驗收通知');
      expect(description).toContain('桃園市政府');
    });

    it('有受文者、案件、業務同仁、備註時都應出現在描述中', async () => {
      const { calendarIntegrationService: service } = await import(
        '../calendarIntegrationService'
      );
      mockApiClientPost.mockResolvedValueOnce({ event_id: 1 });

      await service.addDocumentToCalendar(
        makeDocument({
          receiver: '乾坤工程',
          contract_case: 'CK-2026-A',
          assignee: '王小明',
          notes: '請儘速回覆',
        })
      );

      const description =
        mockApiClientPost.mock.calls[0][1].description as string;
      expect(description).toContain('乾坤工程');
      expect(description).toContain('CK-2026-A');
      expect(description).toContain('王小明');
      expect(description).toContain('請儘速回覆');
    });
  });
});

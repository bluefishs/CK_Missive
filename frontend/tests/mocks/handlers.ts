/**
 * MSW API Mock Handlers
 * API 請求模擬處理器
 *
 * 用於測試時模擬後端 API 回應
 */
import { http, HttpResponse } from 'msw';

const API_BASE = 'http://localhost:8001/api';

export const handlers = [
  // 公文列表
  http.post(`${API_BASE}/documents-enhanced/list`, () => {
    return HttpResponse.json({
      success: true,
      items: [
        {
          id: 1,
          doc_number: 'TEST-2026-001',
          subject: '測試公文一',
          doc_type: '收文',
          sender: '測試發文單位',
          receiver: '乾坤測繪有限公司',
          status: '已處理',
          created_at: '2026-01-08T10:00:00',
        },
        {
          id: 2,
          doc_number: 'TEST-2026-002',
          subject: '測試公文二',
          doc_type: '發文',
          sender: '乾坤測繪有限公司',
          receiver: '測試受文單位',
          status: '待處理',
          created_at: '2026-01-08T11:00:00',
        },
      ],
      total: 2,
      page: 1,
      limit: 10,
      total_pages: 1,
    });
  }),

  // 行事曆事件列表
  http.post(`${API_BASE}/calendar/events/list`, () => {
    return HttpResponse.json({
      success: true,
      items: [
        {
          id: 1,
          title: '測試事件',
          start_date: '2026-01-08T10:00:00',
          end_date: '2026-01-08T11:00:00',
          event_type: 'meeting',
          all_day: false,
        },
      ],
      total: 1,
    });
  }),

  // 機關下拉選單
  http.post(`${API_BASE}/agencies/dropdown`, () => {
    return HttpResponse.json({
      success: true,
      items: [
        { id: 1, agency_name: '測試機關一' },
        { id: 2, agency_name: '測試機關二' },
      ],
    });
  }),

  // 案件下拉選單
  http.post(`${API_BASE}/projects/dropdown`, () => {
    return HttpResponse.json({
      success: true,
      items: [
        { id: 1, project_name: '測試案件一', project_code: 'P-001' },
        { id: 2, project_name: '測試案件二', project_code: 'P-002' },
      ],
    });
  }),

  // 當前使用者
  http.get(`${API_BASE}/users/me`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        is_active: true,
        is_admin: false,
        role: 'user',
      },
    });
  }),
];

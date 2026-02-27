/**
 * API 端點定義測試
 * API Endpoints Definition Tests
 *
 * 驗證 API_ENDPOINTS 作為單一真實來源 (SSOT) 的完整性與正確性
 *
 * 執行方式:
 *   cd frontend && npx vitest run src/api/__tests__/endpoints.test.ts
 */
import { describe, it, expect } from 'vitest';
import {
  API_ENDPOINTS,
  DASHBOARD_ENDPOINTS,
  DOCUMENTS_ENDPOINTS,
  PROJECTS_ENDPOINTS,
  AGENCIES_ENDPOINTS,
  VENDORS_ENDPOINTS,
  CALENDAR_ENDPOINTS,
  SYSTEM_NOTIFICATIONS_ENDPOINTS,
  PROJECT_NOTIFICATIONS_ENDPOINTS,
  FILES_ENDPOINTS,
  USERS_ENDPOINTS,
  AUTH_ENDPOINTS,
  ADMIN_USER_MANAGEMENT_ENDPOINTS,
  CERTIFICATIONS_ENDPOINTS,
  PROJECT_VENDORS_ENDPOINTS,
  PROJECT_STAFF_ENDPOINTS,
  PROJECT_AGENCY_CONTACTS_ENDPOINTS,
  REMINDER_MANAGEMENT_ENDPOINTS,
  CSV_IMPORT_ENDPOINTS,
  PUBLIC_ENDPOINTS,
  SYSTEM_ENDPOINTS,
  ADMIN_DATABASE_ENDPOINTS,
  BACKUP_ENDPOINTS,
  TAOYUAN_DISPATCH_ENDPOINTS,
  AI_ENDPOINTS,
  DEPLOYMENT_ENDPOINTS,
} from '../endpoints';

// ============================================================================
// 輔助函數
// ============================================================================

/**
 * 遞迴收集端點物件中所有靜態字串值（跳過函數型端點）
 */
function collectStaticEndpoints(obj: Record<string, unknown>, prefix = ''): { path: string; value: string }[] {
  const results: { path: string; value: string }[] = [];
  for (const [key, value] of Object.entries(obj)) {
    const fullPath = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'string') {
      results.push({ path: fullPath, value });
    } else if (typeof value === 'object' && value !== null && typeof value !== 'function') {
      results.push(...collectStaticEndpoints(value as Record<string, unknown>, fullPath));
    }
  }
  return results;
}

/**
 * 遞迴收集端點物件中所有值（包括呼叫函數型端點取得的字串值）
 */
function collectAllEndpointValues(obj: Record<string, unknown>, prefix = ''): { path: string; value: string }[] {
  const results: { path: string; value: string }[] = [];
  for (const [key, value] of Object.entries(obj)) {
    const fullPath = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'string') {
      results.push({ path: fullPath, value });
    } else if (typeof value === 'function') {
      // 使用測試 ID 呼叫函數以取得路徑模式
      try {
        const fnResult = (value as (...args: number[]) => string)(999, 888);
        if (typeof fnResult === 'string') {
          results.push({ path: fullPath, value: fnResult });
        }
      } catch {
        // 函數可能需要不同參數，忽略錯誤
      }
    } else if (typeof value === 'object' && value !== null) {
      results.push(...collectAllEndpointValues(value as Record<string, unknown>, fullPath));
    }
  }
  return results;
}

// ============================================================================
// API_ENDPOINTS 結構完整性
// ============================================================================

describe('API_ENDPOINTS 結構完整性', () => {
  it('應該匯出 API_ENDPOINTS 物件', () => {
    expect(API_ENDPOINTS).toBeDefined();
    expect(typeof API_ENDPOINTS).toBe('object');
  });

  it('應該包含所有頂層端點群組', () => {
    const expectedGroups = [
      'DASHBOARD',
      'DOCUMENTS',
      'PROJECTS',
      'AGENCIES',
      'VENDORS',
      'CALENDAR',
      'SYSTEM_NOTIFICATIONS',
      'PROJECT_NOTIFICATIONS',
      'FILES',
      'USERS',
      'AUTH',
      'ADMIN_USER_MANAGEMENT',
      'CERTIFICATIONS',
      'PROJECT_VENDORS',
      'PROJECT_STAFF',
      'PROJECT_AGENCY_CONTACTS',
      'REMINDER_MANAGEMENT',
      'CSV_IMPORT',
      'PUBLIC',
      'SYSTEM',
      'ADMIN_DATABASE',
      'BACKUP',
      'AI',
      'DEPLOYMENT',
      'TAOYUAN_DISPATCH',
    ];

    for (const group of expectedGroups) {
      expect(API_ENDPOINTS).toHaveProperty(group);
    }
  });

  it('應該正確引用各個獨立匯出的端點物件', () => {
    expect(API_ENDPOINTS.DASHBOARD).toBe(DASHBOARD_ENDPOINTS);
    expect(API_ENDPOINTS.DOCUMENTS).toBe(DOCUMENTS_ENDPOINTS);
    expect(API_ENDPOINTS.PROJECTS).toBe(PROJECTS_ENDPOINTS);
    expect(API_ENDPOINTS.AGENCIES).toBe(AGENCIES_ENDPOINTS);
    expect(API_ENDPOINTS.VENDORS).toBe(VENDORS_ENDPOINTS);
    expect(API_ENDPOINTS.CALENDAR).toBe(CALENDAR_ENDPOINTS);
    expect(API_ENDPOINTS.SYSTEM_NOTIFICATIONS).toBe(SYSTEM_NOTIFICATIONS_ENDPOINTS);
    expect(API_ENDPOINTS.PROJECT_NOTIFICATIONS).toBe(PROJECT_NOTIFICATIONS_ENDPOINTS);
    expect(API_ENDPOINTS.FILES).toBe(FILES_ENDPOINTS);
    expect(API_ENDPOINTS.USERS).toBe(USERS_ENDPOINTS);
    expect(API_ENDPOINTS.AUTH).toBe(AUTH_ENDPOINTS);
    expect(API_ENDPOINTS.ADMIN_USER_MANAGEMENT).toBe(ADMIN_USER_MANAGEMENT_ENDPOINTS);
    expect(API_ENDPOINTS.CERTIFICATIONS).toBe(CERTIFICATIONS_ENDPOINTS);
    expect(API_ENDPOINTS.PROJECT_VENDORS).toBe(PROJECT_VENDORS_ENDPOINTS);
    expect(API_ENDPOINTS.PROJECT_STAFF).toBe(PROJECT_STAFF_ENDPOINTS);
    expect(API_ENDPOINTS.PROJECT_AGENCY_CONTACTS).toBe(PROJECT_AGENCY_CONTACTS_ENDPOINTS);
    expect(API_ENDPOINTS.REMINDER_MANAGEMENT).toBe(REMINDER_MANAGEMENT_ENDPOINTS);
    expect(API_ENDPOINTS.CSV_IMPORT).toBe(CSV_IMPORT_ENDPOINTS);
    expect(API_ENDPOINTS.PUBLIC).toBe(PUBLIC_ENDPOINTS);
    expect(API_ENDPOINTS.SYSTEM).toBe(SYSTEM_ENDPOINTS);
    expect(API_ENDPOINTS.ADMIN_DATABASE).toBe(ADMIN_DATABASE_ENDPOINTS);
    expect(API_ENDPOINTS.BACKUP).toBe(BACKUP_ENDPOINTS);
    expect(API_ENDPOINTS.AI).toBe(AI_ENDPOINTS);
    expect(API_ENDPOINTS.DEPLOYMENT).toBe(DEPLOYMENT_ENDPOINTS);
    expect(API_ENDPOINTS.TAOYUAN_DISPATCH).toBe(TAOYUAN_DISPATCH_ENDPOINTS);
  });

  it('頂層群組數量應為 25 個', () => {
    const groupCount = Object.keys(API_ENDPOINTS).length;
    expect(groupCount).toBe(25);
  });
});

// ============================================================================
// 端點值格式驗證
// ============================================================================

describe('端點值格式驗證', () => {
  const allStaticEndpoints = collectStaticEndpoints(API_ENDPOINTS);

  it('所有靜態端點值應為非空字串', () => {
    for (const { path, value } of allStaticEndpoints) {
      expect(value, `端點 ${path} 不應為空`).not.toBe('');
      expect(typeof value, `端點 ${path} 應為 string`).toBe('string');
    }
  });

  it('所有靜態端點值應以 / 開頭', () => {
    for (const { path, value } of allStaticEndpoints) {
      expect(value, `端點 ${path} (值: "${value}") 應以 / 開頭`).toMatch(/^\//);
    }
  });

  it('所有靜態端點值不應以 / 結尾（除根路徑外）', () => {
    for (const { path, value } of allStaticEndpoints) {
      if (value !== '/') {
        expect(value, `端點 ${path} (值: "${value}") 不應以 / 結尾`).not.toMatch(/\/$/);
      }
    }
  });

  it('所有靜態端點值不應包含雙斜線', () => {
    for (const { path, value } of allStaticEndpoints) {
      expect(value, `端點 ${path} (值: "${value}") 不應包含 //`).not.toContain('//');
    }
  });

  it('所有動態端點函數應回傳以 / 開頭的字串', () => {
    const allEndpoints = collectAllEndpointValues(API_ENDPOINTS);
    for (const { path, value } of allEndpoints) {
      expect(value, `端點 ${path} (值: "${value}") 應以 / 開頭`).toMatch(/^\//);
    }
  });

  it('應有超過 100 個靜態端點定義', () => {
    expect(allStaticEndpoints.length).toBeGreaterThan(100);
  });
});

// ============================================================================
// 端點唯一性驗證
// ============================================================================

describe('端點唯一性驗證', () => {
  it('所有靜態端點路徑不應重複', () => {
    const allStaticEndpoints = collectStaticEndpoints(API_ENDPOINTS);
    const values = allStaticEndpoints.map(e => e.value);
    const uniqueValues = new Set(values);

    if (uniqueValues.size !== values.length) {
      // 找出重複項並報告
      const duplicates: Record<string, string[]> = {};
      for (const { path, value } of allStaticEndpoints) {
        if (!duplicates[value]) duplicates[value] = [];
        duplicates[value].push(path);
      }
      const dupes = Object.entries(duplicates)
        .filter(([, paths]) => paths.length > 1)
        .map(([value, paths]) => `"${value}" 被 ${paths.join(', ')} 使用`);

      expect.fail(`發現重複端點: ${dupes.join('; ')}`);
    }
  });
});

// ============================================================================
// 核心功能模組端點
// ============================================================================

describe('DASHBOARD_ENDPOINTS', () => {
  it('應該包含儀表板統計與摘要端點', () => {
    expect(DASHBOARD_ENDPOINTS.STATS).toBe('/dashboard/stats');
    expect(DASHBOARD_ENDPOINTS.SUMMARY).toBe('/dashboard/summary');
  });
});

describe('DOCUMENTS_ENDPOINTS', () => {
  it('應該包含公文 CRUD 靜態端點', () => {
    expect(DOCUMENTS_ENDPOINTS.LIST).toBe('/documents-enhanced/list');
    expect(DOCUMENTS_ENDPOINTS.CREATE).toBe('/documents-enhanced/create');
    expect(DOCUMENTS_ENDPOINTS.STATISTICS).toBe('/documents-enhanced/statistics');
  });

  it('動態端點應正確產生路徑', () => {
    expect(DOCUMENTS_ENDPOINTS.DETAIL(1)).toBe('/documents-enhanced/1/detail');
    expect(DOCUMENTS_ENDPOINTS.UPDATE(42)).toBe('/documents-enhanced/42/update');
    expect(DOCUMENTS_ENDPOINTS.DELETE(99)).toBe('/documents-enhanced/99/delete');
    expect(DOCUMENTS_ENDPOINTS.AUDIT_HISTORY(7)).toBe('/documents-enhanced/7/audit-history');
  });

  it('應該包含匯入匯出端點', () => {
    expect(DOCUMENTS_ENDPOINTS.EXPORT).toBe('/documents-enhanced/export');
    expect(DOCUMENTS_ENDPOINTS.EXPORT_EXCEL).toBe('/documents-enhanced/export/excel');
    expect(DOCUMENTS_ENDPOINTS.IMPORT_EXCEL_PREVIEW).toBe('/documents-enhanced/import/excel/preview');
    expect(DOCUMENTS_ENDPOINTS.IMPORT_EXCEL).toBe('/documents-enhanced/import/excel');
    expect(DOCUMENTS_ENDPOINTS.IMPORT_EXCEL_TEMPLATE).toBe('/documents-enhanced/import/excel/template');
  });

  it('應該包含下一個發文字號端點', () => {
    expect(DOCUMENTS_ENDPOINTS.NEXT_SEND_NUMBER).toBe('/documents-enhanced/next-send-number');
  });

  it('所有端點路徑應包含 documents', () => {
    const endpoints = collectAllEndpointValues(DOCUMENTS_ENDPOINTS);
    for (const { path, value } of endpoints) {
      expect(value, `DOCUMENTS.${path} 應包含 "documents"`).toContain('documents');
    }
  });
});

describe('PROJECTS_ENDPOINTS', () => {
  it('應該包含專案 CRUD 端點', () => {
    expect(PROJECTS_ENDPOINTS.LIST).toBe('/projects/list');
    expect(PROJECTS_ENDPOINTS.CREATE).toBe('/projects');
    expect(PROJECTS_ENDPOINTS.STATISTICS).toBe('/projects/statistics');
  });

  it('動態端點應正確產生路徑', () => {
    expect(PROJECTS_ENDPOINTS.DETAIL(5)).toBe('/projects/5/detail');
    expect(PROJECTS_ENDPOINTS.UPDATE(10)).toBe('/projects/10/update');
    expect(PROJECTS_ENDPOINTS.DELETE(20)).toBe('/projects/20/delete');
  });

  it('所有端點路徑應包含 projects', () => {
    const endpoints = collectAllEndpointValues(PROJECTS_ENDPOINTS);
    for (const { value } of endpoints) {
      expect(value).toContain('projects');
    }
  });
});

describe('AGENCIES_ENDPOINTS', () => {
  it('應該包含機關 CRUD 端點', () => {
    expect(AGENCIES_ENDPOINTS.LIST).toBe('/agencies/list');
    expect(AGENCIES_ENDPOINTS.CREATE).toBe('/agencies');
    expect(AGENCIES_ENDPOINTS.STATISTICS).toBe('/agencies/statistics');
  });

  it('動態端點應正確產生路徑', () => {
    expect(AGENCIES_ENDPOINTS.DETAIL(3)).toBe('/agencies/3/detail');
    expect(AGENCIES_ENDPOINTS.UPDATE(3)).toBe('/agencies/3/update');
    expect(AGENCIES_ENDPOINTS.DELETE(3)).toBe('/agencies/3/delete');
  });
});

describe('VENDORS_ENDPOINTS', () => {
  it('應該包含廠商 CRUD 端點', () => {
    expect(VENDORS_ENDPOINTS.LIST).toBe('/vendors/list');
    expect(VENDORS_ENDPOINTS.CREATE).toBe('/vendors');
    expect(VENDORS_ENDPOINTS.STATISTICS).toBe('/vendors/statistics');
  });

  it('動態端點應正確產生路徑', () => {
    expect(VENDORS_ENDPOINTS.DETAIL(7)).toBe('/vendors/7/detail');
    expect(VENDORS_ENDPOINTS.UPDATE(7)).toBe('/vendors/7/update');
    expect(VENDORS_ENDPOINTS.DELETE(7)).toBe('/vendors/7/delete');
  });
});

// ============================================================================
// 行事曆模組端點
// ============================================================================

describe('CALENDAR_ENDPOINTS', () => {
  it('應該包含行事曆靜態端點', () => {
    expect(CALENDAR_ENDPOINTS.USER_EVENTS).toBe('/calendar/users/calendar-events');
    expect(CALENDAR_ENDPOINTS.EVENTS_LIST).toBe('/calendar/events/list');
    expect(CALENDAR_ENDPOINTS.EVENTS_CREATE).toBe('/calendar/events');
    expect(CALENDAR_ENDPOINTS.EVENTS_DETAIL).toBe('/calendar/events/detail');
    expect(CALENDAR_ENDPOINTS.EVENTS_UPDATE).toBe('/calendar/events/update');
    expect(CALENDAR_ENDPOINTS.EVENTS_DELETE).toBe('/calendar/events/delete');
    expect(CALENDAR_ENDPOINTS.EVENTS_SYNC).toBe('/calendar/events/sync');
    expect(CALENDAR_ENDPOINTS.EVENTS_BULK_SYNC).toBe('/calendar/events/bulk-sync');
    expect(CALENDAR_ENDPOINTS.EVENTS_CHECK_DOCUMENT).toBe('/calendar/events/check-document');
    expect(CALENDAR_ENDPOINTS.EVENTS_CREATE_WITH_REMINDERS).toBe('/calendar/events/create-with-reminders');
  });

  it('動態端點應正確產生路徑', () => {
    expect(CALENDAR_ENDPOINTS.DOCUMENT_EVENTS(100)).toBe('/calendar/document/100/events');
    expect(CALENDAR_ENDPOINTS.DOCUMENT_CREATE_EVENT(50)).toBe('/calendar/document/50/create-event');
  });

  it('所有端點路徑應包含 calendar', () => {
    const endpoints = collectAllEndpointValues(CALENDAR_ENDPOINTS);
    for (const { value } of endpoints) {
      expect(value).toContain('calendar');
    }
  });
});

// ============================================================================
// 通知模組端點
// ============================================================================

describe('SYSTEM_NOTIFICATIONS_ENDPOINTS', () => {
  it('應該包含系統通知端點', () => {
    expect(SYSTEM_NOTIFICATIONS_ENDPOINTS.LIST).toBe('/system-notifications/list');
    expect(SYSTEM_NOTIFICATIONS_ENDPOINTS.UNREAD_COUNT).toBe('/system-notifications/unread-count');
    expect(SYSTEM_NOTIFICATIONS_ENDPOINTS.MARK_READ).toBe('/system-notifications/mark-read');
    expect(SYSTEM_NOTIFICATIONS_ENDPOINTS.MARK_ALL_READ).toBe('/system-notifications/mark-all-read');
  });
});

describe('PROJECT_NOTIFICATIONS_ENDPOINTS', () => {
  it('應該包含專案通知端點', () => {
    expect(PROJECT_NOTIFICATIONS_ENDPOINTS.LIST).toBe('/project-notifications/list');
    expect(PROJECT_NOTIFICATIONS_ENDPOINTS.CREATE).toBe('/project-notifications');
  });
});

// ============================================================================
// 檔案管理端點
// ============================================================================

describe('FILES_ENDPOINTS', () => {
  it('應該包含檔案管理靜態端點', () => {
    expect(FILES_ENDPOINTS.STORAGE_INFO).toBe('/files/storage-info');
    expect(FILES_ENDPOINTS.CHECK_NETWORK).toBe('/files/check-network');
  });

  it('動態端點應正確產生路徑', () => {
    expect(FILES_ENDPOINTS.UPLOAD(10)).toBe('/files/upload?document_id=10');
    expect(FILES_ENDPOINTS.DOCUMENT_ATTACHMENTS(5)).toBe('/files/document/5');
    expect(FILES_ENDPOINTS.DOWNLOAD(20)).toBe('/files/20/download');
    expect(FILES_ENDPOINTS.DELETE(30)).toBe('/files/30/delete');
    expect(FILES_ENDPOINTS.VERIFY(40)).toBe('/files/verify/40');
  });
});

// ============================================================================
// 使用者與權限管理端點
// ============================================================================

describe('USERS_ENDPOINTS', () => {
  it('應該包含使用者 CRUD 端點', () => {
    expect(USERS_ENDPOINTS.LIST).toBe('/users/list');
    expect(USERS_ENDPOINTS.CREATE).toBe('/users');
  });

  it('動態端點應正確產生路徑', () => {
    expect(USERS_ENDPOINTS.DETAIL(1)).toBe('/users/1/detail');
    expect(USERS_ENDPOINTS.UPDATE(2)).toBe('/users/2/update');
    expect(USERS_ENDPOINTS.DELETE(3)).toBe('/users/3/delete');
    expect(USERS_ENDPOINTS.STATUS(4)).toBe('/users/4/status');
  });
});

describe('AUTH_ENDPOINTS', () => {
  it('應該包含基本認證端點', () => {
    expect(AUTH_ENDPOINTS.LOGIN).toBe('/auth/login');
    expect(AUTH_ENDPOINTS.LOGOUT).toBe('/auth/logout');
    expect(AUTH_ENDPOINTS.REFRESH).toBe('/auth/refresh');
    expect(AUTH_ENDPOINTS.ME).toBe('/auth/me');
  });

  it('應該包含密碼管理端點', () => {
    expect(AUTH_ENDPOINTS.PASSWORD_CHANGE).toBe('/auth/password/change');
    expect(AUTH_ENDPOINTS.PASSWORD_RESET).toBe('/auth/password-reset');
    expect(AUTH_ENDPOINTS.PASSWORD_RESET_CONFIRM).toBe('/auth/password-reset-confirm');
  });

  it('應該包含 MFA 端點', () => {
    expect(AUTH_ENDPOINTS.MFA_SETUP).toBe('/auth/mfa/setup');
    expect(AUTH_ENDPOINTS.MFA_VERIFY).toBe('/auth/mfa/verify');
    expect(AUTH_ENDPOINTS.MFA_DISABLE).toBe('/auth/mfa/disable');
    expect(AUTH_ENDPOINTS.MFA_VALIDATE).toBe('/auth/mfa/validate');
    expect(AUTH_ENDPOINTS.MFA_STATUS).toBe('/auth/mfa/status');
  });

  it('應該包含 Session 管理端點', () => {
    expect(AUTH_ENDPOINTS.SESSIONS).toBe('/auth/sessions');
    expect(AUTH_ENDPOINTS.SESSION_REVOKE).toBe('/auth/sessions/revoke');
    expect(AUTH_ENDPOINTS.SESSION_REVOKE_ALL).toBe('/auth/sessions/revoke-all');
  });

  it('所有端點路徑應包含 auth', () => {
    const endpoints = collectAllEndpointValues(AUTH_ENDPOINTS);
    for (const { value } of endpoints) {
      expect(value).toContain('auth');
    }
  });
});

describe('ADMIN_USER_MANAGEMENT_ENDPOINTS', () => {
  it('應該包含管理員使用者管理靜態端點', () => {
    expect(ADMIN_USER_MANAGEMENT_ENDPOINTS.USERS_LIST).toBe('/admin/user-management/users/list');
    expect(ADMIN_USER_MANAGEMENT_ENDPOINTS.USERS_CREATE).toBe('/admin/user-management/users');
    expect(ADMIN_USER_MANAGEMENT_ENDPOINTS.PERMISSIONS_AVAILABLE).toBe('/admin/user-management/permissions/available');
  });

  it('動態端點應正確產生路徑', () => {
    expect(ADMIN_USER_MANAGEMENT_ENDPOINTS.USERS_DETAIL(5)).toBe('/admin/user-management/users/5/detail');
    expect(ADMIN_USER_MANAGEMENT_ENDPOINTS.USERS_UPDATE(5)).toBe('/admin/user-management/users/5/update');
    expect(ADMIN_USER_MANAGEMENT_ENDPOINTS.USERS_DELETE(5)).toBe('/admin/user-management/users/5/delete');
    expect(ADMIN_USER_MANAGEMENT_ENDPOINTS.USERS_PERMISSIONS_DETAIL(5)).toBe('/admin/user-management/users/5/permissions/detail');
    expect(ADMIN_USER_MANAGEMENT_ENDPOINTS.USERS_PERMISSIONS_UPDATE(5)).toBe('/admin/user-management/users/5/permissions/update');
    expect(ADMIN_USER_MANAGEMENT_ENDPOINTS.USERS_SESSIONS_LIST(5)).toBe('/admin/user-management/users/5/sessions/list');
    expect(ADMIN_USER_MANAGEMENT_ENDPOINTS.SESSIONS_REVOKE(10)).toBe('/admin/user-management/sessions/10/revoke');
  });
});

describe('CERTIFICATIONS_ENDPOINTS', () => {
  it('應該包含證照管理靜態端點', () => {
    expect(CERTIFICATIONS_ENDPOINTS.CREATE).toBe('/certifications/create');
  });

  it('動態端點應正確產生路徑', () => {
    expect(CERTIFICATIONS_ENDPOINTS.USER_LIST(1)).toBe('/certifications/user/1/list');
    expect(CERTIFICATIONS_ENDPOINTS.DETAIL(2)).toBe('/certifications/2/detail');
    expect(CERTIFICATIONS_ENDPOINTS.UPDATE(3)).toBe('/certifications/3/update');
    expect(CERTIFICATIONS_ENDPOINTS.DELETE(4)).toBe('/certifications/4/delete');
    expect(CERTIFICATIONS_ENDPOINTS.STATS(5)).toBe('/certifications/stats/5');
    expect(CERTIFICATIONS_ENDPOINTS.UPLOAD_ATTACHMENT(6)).toBe('/certifications/6/upload-attachment');
    expect(CERTIFICATIONS_ENDPOINTS.DOWNLOAD_ATTACHMENT(7)).toBe('/certifications/7/download-attachment');
    expect(CERTIFICATIONS_ENDPOINTS.DELETE_ATTACHMENT(8)).toBe('/certifications/8/delete-attachment');
  });
});

// ============================================================================
// 關聯模組端點
// ============================================================================

describe('PROJECT_VENDORS_ENDPOINTS', () => {
  it('應該包含案件廠商關聯端點', () => {
    expect(PROJECT_VENDORS_ENDPOINTS.LIST).toBe('/project-vendors/list');
    expect(PROJECT_VENDORS_ENDPOINTS.CREATE).toBe('/project-vendors');
  });

  it('動態端點應正確產生路徑（單參數）', () => {
    expect(PROJECT_VENDORS_ENDPOINTS.PROJECT_LIST(10)).toBe('/project-vendors/project/10/list');
  });

  it('動態端點應正確產生路徑（雙參數）', () => {
    expect(PROJECT_VENDORS_ENDPOINTS.UPDATE(10, 20)).toBe('/project-vendors/project/10/vendor/20/update');
    expect(PROJECT_VENDORS_ENDPOINTS.DELETE(10, 20)).toBe('/project-vendors/project/10/vendor/20/delete');
  });
});

describe('PROJECT_STAFF_ENDPOINTS', () => {
  it('應該包含案件承辦同仁端點', () => {
    expect(PROJECT_STAFF_ENDPOINTS.LIST).toBe('/project-staff/list');
    expect(PROJECT_STAFF_ENDPOINTS.CREATE).toBe('/project-staff');
    expect(PROJECT_STAFF_ENDPOINTS.DELETE(5)).toBe('/project-staff/5/delete');
  });
});

describe('PROJECT_AGENCY_CONTACTS_ENDPOINTS', () => {
  it('應該包含專案機關承辦端點', () => {
    expect(PROJECT_AGENCY_CONTACTS_ENDPOINTS.LIST).toBe('/project-agency-contacts/list');
    expect(PROJECT_AGENCY_CONTACTS_ENDPOINTS.DETAIL).toBe('/project-agency-contacts/detail');
    expect(PROJECT_AGENCY_CONTACTS_ENDPOINTS.CREATE).toBe('/project-agency-contacts/create');
    expect(PROJECT_AGENCY_CONTACTS_ENDPOINTS.UPDATE).toBe('/project-agency-contacts/update');
    expect(PROJECT_AGENCY_CONTACTS_ENDPOINTS.DELETE).toBe('/project-agency-contacts/delete');
  });
});

// ============================================================================
// 系統管理端點
// ============================================================================

describe('REMINDER_MANAGEMENT_ENDPOINTS', () => {
  it('應該包含提醒管理端點', () => {
    expect(REMINDER_MANAGEMENT_ENDPOINTS.LIST).toBe('/reminder-management/list');
    expect(REMINDER_MANAGEMENT_ENDPOINTS.CREATE).toBe('/reminder-management');
    expect(REMINDER_MANAGEMENT_ENDPOINTS.UPDATE(1)).toBe('/reminder-management/1/update');
    expect(REMINDER_MANAGEMENT_ENDPOINTS.DELETE(2)).toBe('/reminder-management/2/delete');
  });
});

describe('CSV_IMPORT_ENDPOINTS', () => {
  it('應該包含 CSV 匯入端點', () => {
    expect(CSV_IMPORT_ENDPOINTS.UPLOAD_AND_IMPORT).toBe('/csv-import/upload-and-import');
    expect(CSV_IMPORT_ENDPOINTS.VALIDATE).toBe('/csv-import/validate');
    expect(CSV_IMPORT_ENDPOINTS.HISTORY).toBe('/csv-import/history');
  });
});

describe('PUBLIC_ENDPOINTS', () => {
  it('應該包含公開端點', () => {
    expect(PUBLIC_ENDPOINTS.CALENDAR_STATUS).toBe('/public/calendar-status');
    expect(PUBLIC_ENDPOINTS.HEALTH).toBe('/public/health');
  });
});

describe('SYSTEM_ENDPOINTS', () => {
  it('應該包含系統監控端點', () => {
    expect(SYSTEM_ENDPOINTS.STATUS).toBe('/system/status');
    expect(SYSTEM_ENDPOINTS.METRICS).toBe('/system/metrics');
    expect(SYSTEM_ENDPOINTS.HEALTH_SUMMARY).toBe('/health/summary');
  });
});

describe('ADMIN_DATABASE_ENDPOINTS', () => {
  it('應該包含管理員資料庫端點', () => {
    expect(ADMIN_DATABASE_ENDPOINTS.INFO).toBe('/admin/database/info');
    expect(ADMIN_DATABASE_ENDPOINTS.QUERY).toBe('/admin/database/query');
    expect(ADMIN_DATABASE_ENDPOINTS.HEALTH).toBe('/admin/database/health');
    expect(ADMIN_DATABASE_ENDPOINTS.INTEGRITY).toBe('/admin/database/integrity');
  });

  it('TABLE 動態端點應接受資料表名稱', () => {
    expect(ADMIN_DATABASE_ENDPOINTS.TABLE('official_documents')).toBe('/admin/database/table/official_documents');
    expect(ADMIN_DATABASE_ENDPOINTS.TABLE('users')).toBe('/admin/database/table/users');
  });
});

describe('BACKUP_ENDPOINTS', () => {
  it('應該包含備份基本端點', () => {
    expect(BACKUP_ENDPOINTS.CREATE).toBe('/backup/create');
    expect(BACKUP_ENDPOINTS.LIST).toBe('/backup/list');
    expect(BACKUP_ENDPOINTS.DELETE).toBe('/backup/delete');
    expect(BACKUP_ENDPOINTS.RESTORE).toBe('/backup/restore');
    expect(BACKUP_ENDPOINTS.CONFIG).toBe('/backup/config');
    expect(BACKUP_ENDPOINTS.STATUS).toBe('/backup/status');
  });

  it('應該包含異地備份端點', () => {
    expect(BACKUP_ENDPOINTS.REMOTE_CONFIG).toBe('/backup/remote-config');
    expect(BACKUP_ENDPOINTS.REMOTE_CONFIG_UPDATE).toBe('/backup/remote-config/update');
    expect(BACKUP_ENDPOINTS.REMOTE_SYNC).toBe('/backup/remote-sync');
  });

  it('應該包含排程器控制端點', () => {
    expect(BACKUP_ENDPOINTS.SCHEDULER_STATUS).toBe('/backup/scheduler/status');
    expect(BACKUP_ENDPOINTS.SCHEDULER_START).toBe('/backup/scheduler/start');
    expect(BACKUP_ENDPOINTS.SCHEDULER_STOP).toBe('/backup/scheduler/stop');
  });

  it('應該包含環境狀態與清理端點', () => {
    expect(BACKUP_ENDPOINTS.ENVIRONMENT_STATUS).toBe('/backup/environment-status');
    expect(BACKUP_ENDPOINTS.CLEANUP).toBe('/backup/cleanup');
  });
});

// ============================================================================
// 桃園派工管理端點
// ============================================================================

describe('TAOYUAN_DISPATCH_ENDPOINTS', () => {
  it('應該包含工程管理靜態端點', () => {
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PROJECTS_LIST).toBe('/taoyuan-dispatch/projects/list');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PROJECTS_CREATE).toBe('/taoyuan-dispatch/projects/create');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PROJECTS_IMPORT).toBe('/taoyuan-dispatch/projects/import');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PROJECTS_IMPORT_TEMPLATE).toBe('/taoyuan-dispatch/projects/import-template');
  });

  it('工程動態端點應正確產生路徑', () => {
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PROJECTS_DETAIL(1)).toBe('/taoyuan-dispatch/projects/1/detail');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PROJECTS_UPDATE(2)).toBe('/taoyuan-dispatch/projects/2/update');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PROJECTS_DELETE(3)).toBe('/taoyuan-dispatch/projects/3/delete');
  });

  it('應該包含派工單靜態端點', () => {
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_ORDERS_LIST).toBe('/taoyuan-dispatch/dispatch/list');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_NEXT_NO).toBe('/taoyuan-dispatch/dispatch/next-dispatch-no');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_ORDERS_CREATE).toBe('/taoyuan-dispatch/dispatch/create');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_IMPORT).toBe('/taoyuan-dispatch/dispatch/import');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_IMPORT_TEMPLATE).toBe('/taoyuan-dispatch/dispatch/import-template');
  });

  it('派工單動態端點應正確產生路徑', () => {
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_ORDERS_DETAIL(10)).toBe('/taoyuan-dispatch/dispatch/10/detail');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_ORDERS_UPDATE(10)).toBe('/taoyuan-dispatch/dispatch/10/update');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_ORDERS_DELETE(10)).toBe('/taoyuan-dispatch/dispatch/10/delete');
  });

  it('派工單公文關聯動態端點應正確產生路徑', () => {
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_LINK_DOCUMENT(5)).toBe('/taoyuan-dispatch/dispatch/5/link-document');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_UNLINK_DOCUMENT(5, 10)).toBe('/taoyuan-dispatch/dispatch/5/unlink-document/10');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_DOCUMENTS(5)).toBe('/taoyuan-dispatch/dispatch/5/documents');
  });

  it('應該包含匯出端點', () => {
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_EXPORT_EXCEL).toBe('/taoyuan-dispatch/dispatch/export/excel');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_EXPORT_ASYNC).toBe('/taoyuan-dispatch/dispatch/export/excel/async');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_EXPORT_PROGRESS).toBe('/taoyuan-dispatch/dispatch/export/excel/progress');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_EXPORT_DOWNLOAD).toBe('/taoyuan-dispatch/dispatch/export/excel/download');
  });

  it('應該包含公文歷程匹配端點', () => {
    expect(TAOYUAN_DISPATCH_ENDPOINTS.MATCH_DOCUMENTS).toBe('/taoyuan-dispatch/dispatch/match-documents');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_DETAIL_WITH_HISTORY(3)).toBe('/taoyuan-dispatch/dispatch/3/detail-with-history');
  });

  it('以公文為主體的關聯 API 應正確產生路徑', () => {
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DOCUMENT_DISPATCH_LINKS(1)).toBe('/taoyuan-dispatch/document/1/dispatch-links');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DOCUMENT_LINK_DISPATCH(2)).toBe('/taoyuan-dispatch/document/2/link-dispatch');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DOCUMENT_UNLINK_DISPATCH(3, 4)).toBe('/taoyuan-dispatch/document/3/unlink-dispatch/4');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DOCUMENTS_BATCH_DISPATCH_LINKS).toBe('/taoyuan-dispatch/documents/batch-dispatch-links');
  });

  it('以工程為主體的關聯 API 應正確產生路徑', () => {
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PROJECT_DISPATCH_LINKS(1)).toBe('/taoyuan-dispatch/project/1/dispatch-links');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PROJECT_LINK_DISPATCH(2)).toBe('/taoyuan-dispatch/project/2/link-dispatch');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PROJECT_UNLINK_DISPATCH(3, 4)).toBe('/taoyuan-dispatch/project/3/unlink-dispatch/4');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PROJECTS_BATCH_DISPATCH_LINKS).toBe('/taoyuan-dispatch/projects/batch-dispatch-links');
  });

  it('公文-工程直接關聯 API 應正確產生路徑', () => {
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DOCUMENT_PROJECT_LINKS(1)).toBe('/taoyuan-dispatch/document/1/project-links');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DOCUMENT_LINK_PROJECT(2)).toBe('/taoyuan-dispatch/document/2/link-project');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DOCUMENT_UNLINK_PROJECT(3, 4)).toBe('/taoyuan-dispatch/document/3/unlink-project/4');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DOCUMENTS_BATCH_PROJECT_LINKS).toBe('/taoyuan-dispatch/documents/batch-project-links');
  });

  it('應該包含契金管控端點', () => {
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PAYMENTS_LIST).toBe('/taoyuan-dispatch/payments/list');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PAYMENTS_CREATE).toBe('/taoyuan-dispatch/payments/create');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PAYMENTS_UPDATE(1)).toBe('/taoyuan-dispatch/payments/1/update');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PAYMENTS_DELETE(2)).toBe('/taoyuan-dispatch/payments/2/delete');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.PAYMENTS_CONTROL).toBe('/taoyuan-dispatch/payments/control');
  });

  it('應該包含作業歷程端點', () => {
    expect(TAOYUAN_DISPATCH_ENDPOINTS.WORKFLOW_LIST).toBe('/taoyuan-dispatch/workflow/list');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.WORKFLOW_BY_PROJECT).toBe('/taoyuan-dispatch/workflow/by-project');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.WORKFLOW_CREATE).toBe('/taoyuan-dispatch/workflow/create');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.WORKFLOW_BATCH_UPDATE).toBe('/taoyuan-dispatch/workflow/batch-update');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.WORKFLOW_DETAIL(1)).toBe('/taoyuan-dispatch/workflow/1');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.WORKFLOW_UPDATE(2)).toBe('/taoyuan-dispatch/workflow/2/update');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.WORKFLOW_DELETE(3)).toBe('/taoyuan-dispatch/workflow/3/delete');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.WORKFLOW_SUMMARY(4)).toBe('/taoyuan-dispatch/workflow/summary/4');
  });

  it('應該包含附件管理端點', () => {
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_ATTACHMENTS_UPLOAD(1)).toBe('/taoyuan-dispatch/dispatch/1/attachments/upload');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_ATTACHMENTS_LIST(2)).toBe('/taoyuan-dispatch/dispatch/2/attachments/list');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_ATTACHMENT_DOWNLOAD(3)).toBe('/taoyuan-dispatch/dispatch/attachments/3/download');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_ATTACHMENT_DELETE(4)).toBe('/taoyuan-dispatch/dispatch/attachments/4/delete');
    expect(TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_ATTACHMENT_VERIFY(5)).toBe('/taoyuan-dispatch/dispatch/attachments/5/verify');
  });

  it('所有端點路徑應包含 taoyuan-dispatch', () => {
    const endpoints = collectAllEndpointValues(TAOYUAN_DISPATCH_ENDPOINTS);
    for (const { value } of endpoints) {
      expect(value).toContain('taoyuan-dispatch');
    }
  });
});

// ============================================================================
// AI 服務端點
// ============================================================================

describe('AI_ENDPOINTS', () => {
  it('應該包含公文 AI 端點', () => {
    expect(AI_ENDPOINTS.SUMMARY).toBe('/ai/document/summary');
    expect(AI_ENDPOINTS.SUMMARY_STREAM).toBe('/ai/document/summary/stream');
    expect(AI_ENDPOINTS.CLASSIFY).toBe('/ai/document/classify');
    expect(AI_ENDPOINTS.KEYWORDS).toBe('/ai/document/keywords');
    expect(AI_ENDPOINTS.NATURAL_SEARCH).toBe('/ai/document/natural-search');
    expect(AI_ENDPOINTS.PARSE_INTENT).toBe('/ai/document/parse-intent');
  });

  it('應該包含 AI 配置與統計端點', () => {
    expect(AI_ENDPOINTS.HEALTH).toBe('/ai/health');
    expect(AI_ENDPOINTS.CONFIG).toBe('/ai/config');
    expect(AI_ENDPOINTS.STATS).toBe('/ai/stats');
    expect(AI_ENDPOINTS.STATS_RESET).toBe('/ai/stats/reset');
  });

  it('應該包含同義詞管理端點', () => {
    expect(AI_ENDPOINTS.SYNONYMS_LIST).toBe('/ai/synonyms/list');
    expect(AI_ENDPOINTS.SYNONYMS_CREATE).toBe('/ai/synonyms/create');
    expect(AI_ENDPOINTS.SYNONYMS_UPDATE).toBe('/ai/synonyms/update');
    expect(AI_ENDPOINTS.SYNONYMS_DELETE).toBe('/ai/synonyms/delete');
    expect(AI_ENDPOINTS.SYNONYMS_RELOAD).toBe('/ai/synonyms/reload');
  });

  it('應該包含 Prompt 管理端點', () => {
    expect(AI_ENDPOINTS.PROMPTS_LIST).toBe('/ai/prompts/list');
    expect(AI_ENDPOINTS.PROMPTS_CREATE).toBe('/ai/prompts/create');
    expect(AI_ENDPOINTS.PROMPTS_ACTIVATE).toBe('/ai/prompts/activate');
    expect(AI_ENDPOINTS.PROMPTS_COMPARE).toBe('/ai/prompts/compare');
  });

  it('應該包含搜尋歷史端點', () => {
    expect(AI_ENDPOINTS.SEARCH_HISTORY_LIST).toBe('/ai/search-history/list');
    expect(AI_ENDPOINTS.SEARCH_HISTORY_STATS).toBe('/ai/search-history/stats');
    expect(AI_ENDPOINTS.SEARCH_HISTORY_CLEAR).toBe('/ai/search-history/clear');
    expect(AI_ENDPOINTS.SEARCH_HISTORY_FEEDBACK).toBe('/ai/search-history/feedback');
    expect(AI_ENDPOINTS.SEARCH_HISTORY_SUGGESTIONS).toBe('/ai/search-history/suggestions');
  });

  it('應該包含知識圖譜端點', () => {
    expect(AI_ENDPOINTS.GRAPH_ENTITY_SEARCH).toBe('/ai/graph/entity/search');
    expect(AI_ENDPOINTS.GRAPH_ENTITY_NEIGHBORS).toBe('/ai/graph/entity/neighbors');
    expect(AI_ENDPOINTS.GRAPH_ENTITY_DETAIL).toBe('/ai/graph/entity/detail');
    expect(AI_ENDPOINTS.GRAPH_SHORTEST_PATH).toBe('/ai/graph/entity/shortest-path');
    expect(AI_ENDPOINTS.GRAPH_ENTITY_TIMELINE).toBe('/ai/graph/entity/timeline');
    expect(AI_ENDPOINTS.GRAPH_ENTITY_TOP).toBe('/ai/graph/entity/top');
    expect(AI_ENDPOINTS.GRAPH_STATS).toBe('/ai/graph/stats');
    expect(AI_ENDPOINTS.GRAPH_INGEST).toBe('/ai/graph/ingest');
    expect(AI_ENDPOINTS.GRAPH_MERGE_ENTITIES).toBe('/ai/graph/admin/merge-entities');
  });

  it('應該包含 Embedding 端點', () => {
    expect(AI_ENDPOINTS.EMBEDDING_STATS).toBe('/ai/embedding/stats');
    expect(AI_ENDPOINTS.EMBEDDING_BATCH).toBe('/ai/embedding/batch');
    expect(AI_ENDPOINTS.SEMANTIC_SIMILAR).toBe('/ai/document/semantic-similar');
  });

  it('應該包含 NER 實體提取端點', () => {
    expect(AI_ENDPOINTS.ENTITY_EXTRACT).toBe('/ai/entity/extract');
    expect(AI_ENDPOINTS.ENTITY_BATCH).toBe('/ai/entity/batch');
    expect(AI_ENDPOINTS.ENTITY_STATS).toBe('/ai/entity/stats');
  });

  it('應該包含 RAG 問答端點', () => {
    expect(AI_ENDPOINTS.RAG_QUERY).toBe('/ai/rag/query');
    expect(AI_ENDPOINTS.RAG_QUERY_STREAM).toBe('/ai/rag/query/stream');
  });

  it('應該包含 Agentic 問答端點', () => {
    expect(AI_ENDPOINTS.AGENT_QUERY_STREAM).toBe('/ai/agent/query/stream');
  });

  it('應該包含 Ollama 管理端點', () => {
    expect(AI_ENDPOINTS.OLLAMA_STATUS).toBe('/ai/ollama/status');
    expect(AI_ENDPOINTS.OLLAMA_ENSURE_MODELS).toBe('/ai/ollama/ensure-models');
    expect(AI_ENDPOINTS.OLLAMA_WARMUP).toBe('/ai/ollama/warmup');
  });

  it('所有端點路徑應包含 /ai/', () => {
    const endpoints = collectAllEndpointValues(AI_ENDPOINTS);
    for (const { value } of endpoints) {
      expect(value).toContain('/ai/');
    }
  });
});

// ============================================================================
// 部署管理端點
// ============================================================================

describe('DEPLOYMENT_ENDPOINTS', () => {
  it('應該包含部署管理端點', () => {
    expect(DEPLOYMENT_ENDPOINTS.STATUS).toBe('/deploy/status');
    expect(DEPLOYMENT_ENDPOINTS.HISTORY).toBe('/deploy/history');
    expect(DEPLOYMENT_ENDPOINTS.TRIGGER).toBe('/deploy/trigger');
    expect(DEPLOYMENT_ENDPOINTS.ROLLBACK).toBe('/deploy/rollback');
    expect(DEPLOYMENT_ENDPOINTS.CONFIG).toBe('/deploy/config');
  });

  it('LOGS 動態端點應正確產生路徑', () => {
    expect(DEPLOYMENT_ENDPOINTS.LOGS(123)).toBe('/deploy/logs/123');
  });
});

/**
 * 案件功能模組配置測試 (v2.0.0 API 驅動)
 */
import { describe, it, expect, beforeEach } from 'vitest';
import {
  COMMON_DOCUMENT_TABS,
  hasProjectFeature,
  getDocumentTabs,
  shouldShowTab,
  getRegisteredProjectIds,
  isRegisteredProject,
  setDispatchProjectIds,
  getDispatchProjectIds,
} from '../projectModules';

// 測試前初始化派工案件 ID
beforeEach(() => {
  setDispatchProjectIds([21, 4, 13]);
});

// ============================================================================
// COMMON_DOCUMENT_TABS
// ============================================================================

describe('COMMON_DOCUMENT_TABS', () => {
  it('應包含四個通用 Tab', () => {
    expect(COMMON_DOCUMENT_TABS).toContain('info');
    expect(COMMON_DOCUMENT_TABS).toContain('date-status');
    expect(COMMON_DOCUMENT_TABS).toContain('case-staff');
    expect(COMMON_DOCUMENT_TABS).toContain('attachments');
  });

  it('不應包含專屬 Tab', () => {
    expect(COMMON_DOCUMENT_TABS).not.toContain('dispatch');
    expect(COMMON_DOCUMENT_TABS).not.toContain('project-link');
  });
});

// ============================================================================
// setDispatchProjectIds / getDispatchProjectIds
// ============================================================================

describe('派工案件 ID 快取', () => {
  it('設定後應可取回', () => {
    setDispatchProjectIds([10, 20, 30]);
    const ids = getDispatchProjectIds();
    expect(ids).toContain(10);
    expect(ids).toContain(20);
    expect(ids).toContain(30);
  });

  it('空陣列應清除快取', () => {
    setDispatchProjectIds([]);
    expect(getDispatchProjectIds()).toHaveLength(0);
  });
});

// ============================================================================
// hasProjectFeature
// ============================================================================

describe('hasProjectFeature', () => {
  it('已啟用的案件應具備 dispatch-management 功能', () => {
    expect(hasProjectFeature(21, 'dispatch-management')).toBe(true);
    expect(hasProjectFeature(4, 'dispatch-management')).toBe(true);
    expect(hasProjectFeature(13, 'dispatch-management')).toBe(true);
  });

  it('未啟用的案件應回傳 false', () => {
    expect(hasProjectFeature(99999, 'dispatch-management')).toBe(false);
  });

  it('null/undefined 應回傳 false', () => {
    expect(hasProjectFeature(null, 'dispatch-management')).toBe(false);
    expect(hasProjectFeature(undefined, 'dispatch-management')).toBe(false);
  });
});

// ============================================================================
// getDocumentTabs
// ============================================================================

describe('getDocumentTabs', () => {
  it('已啟用案件應包含通用 + 專屬 Tab', () => {
    const tabs = getDocumentTabs(21);
    expect(tabs).toContain('info');
    expect(tabs).toContain('dispatch');
    expect(tabs).toContain('project-link');
  });

  it('未啟用案件應只回傳通用 Tab', () => {
    const tabs = getDocumentTabs(99999);
    expect(tabs).toEqual(COMMON_DOCUMENT_TABS);
  });

  it('null 應只回傳通用 Tab', () => {
    expect(getDocumentTabs(null)).toEqual(COMMON_DOCUMENT_TABS);
  });

  it('回傳的陣列應為新實例', () => {
    const tabs = getDocumentTabs(null);
    tabs.push('dispatch');
    expect(COMMON_DOCUMENT_TABS).not.toContain('dispatch');
  });
});

// ============================================================================
// shouldShowTab
// ============================================================================

describe('shouldShowTab', () => {
  it('通用 Tab 不論案件都應顯示', () => {
    for (const tab of COMMON_DOCUMENT_TABS) {
      expect(shouldShowTab(null, tab)).toBe(true);
      expect(shouldShowTab(99999, tab)).toBe(true);
      expect(shouldShowTab(21, tab)).toBe(true);
    }
  });

  it('已啟用案件應顯示 dispatch Tab', () => {
    expect(shouldShowTab(21, 'dispatch')).toBe(true);
    expect(shouldShowTab(4, 'dispatch')).toBe(true);
  });

  it('未啟用案件不應顯示專屬 Tab', () => {
    expect(shouldShowTab(99999, 'dispatch')).toBe(false);
    expect(shouldShowTab(null, 'dispatch')).toBe(false);
  });
});

// ============================================================================
// getRegisteredProjectIds / isRegisteredProject
// ============================================================================

describe('getRegisteredProjectIds', () => {
  it('應回傳已設定的案件 ID', () => {
    const ids = getRegisteredProjectIds();
    expect(ids).toContain(21);
    expect(ids).toContain(4);
    expect(ids).toContain(13);
  });
});

describe('isRegisteredProject', () => {
  it('已啟用的案件應為 true', () => {
    expect(isRegisteredProject(21)).toBe(true);
    expect(isRegisteredProject(4)).toBe(true);
  });

  it('未啟用的案件應為 false', () => {
    expect(isRegisteredProject(99999)).toBe(false);
  });

  it('null/undefined/0 應為 false', () => {
    expect(isRegisteredProject(null)).toBe(false);
    expect(isRegisteredProject(undefined)).toBe(false);
    expect(isRegisteredProject(0)).toBe(false);
  });
});

/**
 * 案件功能模組配置測試
 * Project Modules Config Tests
 */
import { describe, it, expect } from 'vitest';
import {
  COMMON_DOCUMENT_TABS,
  PROJECT_MODULE_REGISTRY,
  getProjectModuleConfig,
  hasProjectFeature,
  getDocumentTabs,
  shouldShowTab,
  getRegisteredProjectIds,
  isRegisteredProject,
} from '../projectModules';
import type {
  DocumentTabKey,
  FeatureKey,
  ProjectModuleConfig,
} from '../projectModules';
import { TAOYUAN_CONTRACT } from '../../constants/taoyuanOptions';

// ============================================================================
// COMMON_DOCUMENT_TABS
// ============================================================================

describe('COMMON_DOCUMENT_TABS', () => {
  it('應為非空陣列', () => {
    expect(Array.isArray(COMMON_DOCUMENT_TABS)).toBe(true);
    expect(COMMON_DOCUMENT_TABS.length).toBeGreaterThan(0);
  });

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
// PROJECT_MODULE_REGISTRY
// ============================================================================

describe('PROJECT_MODULE_REGISTRY', () => {
  it('應為非空物件', () => {
    expect(typeof PROJECT_MODULE_REGISTRY).toBe('object');
    expect(Object.keys(PROJECT_MODULE_REGISTRY).length).toBeGreaterThan(0);
  });

  it('應包含桃園案件', () => {
    const taoyuanConfig = PROJECT_MODULE_REGISTRY[TAOYUAN_CONTRACT.PROJECT_ID];
    expect(taoyuanConfig).toBeDefined();
  });

  describe('桃園案件配置', () => {
    const config = PROJECT_MODULE_REGISTRY[TAOYUAN_CONTRACT.PROJECT_ID]!;

    it('projectId 應與 TAOYUAN_CONTRACT.PROJECT_ID 一致', () => {
      expect(config.projectId).toBe(TAOYUAN_CONTRACT.PROJECT_ID);
    });

    it('projectCode 應與 TAOYUAN_CONTRACT.CODE 一致', () => {
      expect(config.projectCode).toBe(TAOYUAN_CONTRACT.CODE);
    });

    it('projectName 應與 TAOYUAN_CONTRACT.NAME 一致', () => {
      expect(config.projectName).toBe(TAOYUAN_CONTRACT.NAME);
    });

    it('documentTabs 應包含 dispatch 和 project-link', () => {
      expect(config.documentTabs).toContain('dispatch');
      expect(config.documentTabs).toContain('project-link');
    });

    it('features 應包含所有桃園專屬功能', () => {
      expect(config.features).toContain('dispatch-management');
      expect(config.features).toContain('project-linking');
      expect(config.features).toContain('taoyuan-projects');
      expect(config.features).toContain('document-preview');
    });

    it('應有 description 說明', () => {
      expect(typeof config.description).toBe('string');
      expect(config.description!.length).toBeGreaterThan(0);
    });
  });

  it('每個配置應具備必要屬性', () => {
    for (const config of Object.values(PROJECT_MODULE_REGISTRY)) {
      expect(typeof config.projectId).toBe('number');
      expect(typeof config.projectCode).toBe('string');
      expect(typeof config.projectName).toBe('string');
      expect(Array.isArray(config.documentTabs)).toBe(true);
      expect(Array.isArray(config.features)).toBe(true);
    }
  });
});

// ============================================================================
// getProjectModuleConfig
// ============================================================================

describe('getProjectModuleConfig', () => {
  it('有效 projectId 應回傳配置', () => {
    const config = getProjectModuleConfig(TAOYUAN_CONTRACT.PROJECT_ID);
    expect(config).not.toBeNull();
    expect(config!.projectId).toBe(TAOYUAN_CONTRACT.PROJECT_ID);
  });

  it('不存在的 projectId 應回傳 null', () => {
    expect(getProjectModuleConfig(99999)).toBeNull();
  });

  it('null 應回傳 null', () => {
    expect(getProjectModuleConfig(null)).toBeNull();
  });

  it('undefined 應回傳 null', () => {
    expect(getProjectModuleConfig(undefined)).toBeNull();
  });

  it('0 應回傳 null (falsy)', () => {
    expect(getProjectModuleConfig(0)).toBeNull();
  });
});

// ============================================================================
// hasProjectFeature
// ============================================================================

describe('hasProjectFeature', () => {
  it('桃園案件應具備 dispatch-management 功能', () => {
    expect(hasProjectFeature(TAOYUAN_CONTRACT.PROJECT_ID, 'dispatch-management')).toBe(true);
  });

  it('桃園案件應具備 document-preview 功能', () => {
    expect(hasProjectFeature(TAOYUAN_CONTRACT.PROJECT_ID, 'document-preview')).toBe(true);
  });

  it('不存在的案件應回傳 false', () => {
    expect(hasProjectFeature(99999, 'dispatch-management')).toBe(false);
  });

  it('null projectId 應回傳 false', () => {
    expect(hasProjectFeature(null, 'dispatch-management')).toBe(false);
  });

  it('undefined projectId 應回傳 false', () => {
    expect(hasProjectFeature(undefined, 'dispatch-management')).toBe(false);
  });
});

// ============================================================================
// getDocumentTabs
// ============================================================================

describe('getDocumentTabs', () => {
  it('桃園案件應包含通用 + 專屬 Tab', () => {
    const tabs = getDocumentTabs(TAOYUAN_CONTRACT.PROJECT_ID);
    // 通用
    expect(tabs).toContain('info');
    expect(tabs).toContain('date-status');
    expect(tabs).toContain('case-staff');
    expect(tabs).toContain('attachments');
    // 專屬
    expect(tabs).toContain('dispatch');
    expect(tabs).toContain('project-link');
  });

  it('不存在的案件應只回傳通用 Tab', () => {
    const tabs = getDocumentTabs(99999);
    expect(tabs).toEqual(COMMON_DOCUMENT_TABS);
  });

  it('null 應只回傳通用 Tab', () => {
    const tabs = getDocumentTabs(null);
    expect(tabs).toEqual(COMMON_DOCUMENT_TABS);
  });

  it('回傳的陣列應為新實例（不應修改原始常數）', () => {
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
      expect(shouldShowTab(TAOYUAN_CONTRACT.PROJECT_ID, tab)).toBe(true);
    }
  });

  it('桃園案件應顯示 dispatch Tab', () => {
    expect(shouldShowTab(TAOYUAN_CONTRACT.PROJECT_ID, 'dispatch')).toBe(true);
  });

  it('桃園案件應顯示 project-link Tab', () => {
    expect(shouldShowTab(TAOYUAN_CONTRACT.PROJECT_ID, 'project-link')).toBe(true);
  });

  it('不存在的案件不應顯示專屬 Tab', () => {
    expect(shouldShowTab(99999, 'dispatch')).toBe(false);
    expect(shouldShowTab(null, 'dispatch')).toBe(false);
  });
});

// ============================================================================
// getRegisteredProjectIds
// ============================================================================

describe('getRegisteredProjectIds', () => {
  it('應回傳數字陣列', () => {
    const ids = getRegisteredProjectIds();
    expect(Array.isArray(ids)).toBe(true);
    for (const id of ids) {
      expect(typeof id).toBe('number');
      expect(Number.isFinite(id)).toBe(true);
    }
  });

  it('應包含桃園案件 ID', () => {
    const ids = getRegisteredProjectIds();
    expect(ids).toContain(TAOYUAN_CONTRACT.PROJECT_ID);
  });
});

// ============================================================================
// isRegisteredProject
// ============================================================================

describe('isRegisteredProject', () => {
  it('桃園案件 ID 應為已註冊', () => {
    expect(isRegisteredProject(TAOYUAN_CONTRACT.PROJECT_ID)).toBe(true);
  });

  it('不存在的 ID 應為未註冊', () => {
    expect(isRegisteredProject(99999)).toBe(false);
  });

  it('null 應為未註冊', () => {
    expect(isRegisteredProject(null)).toBe(false);
  });

  it('undefined 應為未註冊', () => {
    expect(isRegisteredProject(undefined)).toBe(false);
  });

  it('0 應為未註冊 (falsy)', () => {
    expect(isRegisteredProject(0)).toBe(false);
  });
});

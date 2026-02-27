/**
 * 知識圖譜節點配置測試
 * Graph Node Config Tests
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  GRAPH_NODE_CONFIG,
  DEFAULT_NODE_CONFIG,
  KNOWN_NODE_TYPES,
  CANONICAL_ENTITY_TYPES,
  getNodeConfig,
  getUserOverrides,
  saveUserOverrides,
  resetUserOverrides,
  getMergedNodeConfig,
  getAllMergedConfigs,
} from '../graphNodeConfig';

// ============================================================================
// GRAPH_NODE_CONFIG structure
// ============================================================================

describe('GRAPH_NODE_CONFIG', () => {
  const expectedTypes = [
    'document', 'project', 'agency', 'dispatch', 'typroject',
    'org', 'person', 'ner_project', 'location', 'date', 'topic',
  ];

  it('應該包含所有預期的節點類型', () => {
    for (const type of expectedTypes) {
      expect(GRAPH_NODE_CONFIG).toHaveProperty(type);
    }
  });

  it('每個節點配置應包含完整欄位', () => {
    for (const [type, config] of Object.entries(GRAPH_NODE_CONFIG)) {
      expect(config).toHaveProperty('color');
      expect(config).toHaveProperty('radius');
      expect(config).toHaveProperty('label');
      expect(config).toHaveProperty('detailable');
      expect(config).toHaveProperty('description');
      // Validate types
      expect(typeof config.color).toBe('string');
      expect(typeof config.radius).toBe('number');
      expect(typeof config.label).toBe('string');
      expect(typeof config.detailable).toBe('boolean');
      expect(typeof config.description).toBe('string');
      // Color should be hex
      expect(config.color).toMatch(/^#[0-9a-fA-F]{6}$/);
      // Radius should be positive
      expect(config.radius).toBeGreaterThan(0);
      // Label and description should be non-empty
      expect(config.label.length).toBeGreaterThan(0);
      expect(config.description.length).toBeGreaterThan(0);
    }
  });

  it('業務實體類型 detailable 應為 false', () => {
    const businessTypes = ['document', 'project', 'agency', 'dispatch', 'typroject'];
    for (const type of businessTypes) {
      expect(GRAPH_NODE_CONFIG[type]!.detailable).toBe(false);
    }
  });

  it('NER 提取實體類型 detailable 應為 true', () => {
    const nerTypes = ['org', 'person', 'ner_project', 'location', 'date', 'topic'];
    for (const type of nerTypes) {
      expect(GRAPH_NODE_CONFIG[type]!.detailable).toBe(true);
    }
  });
});

// ============================================================================
// DEFAULT_NODE_CONFIG
// ============================================================================

describe('DEFAULT_NODE_CONFIG', () => {
  it('應有灰色 fallback 顏色', () => {
    expect(DEFAULT_NODE_CONFIG.color).toBe('#999999');
  });

  it('應有預設半徑 5', () => {
    expect(DEFAULT_NODE_CONFIG.radius).toBe(5);
  });

  it('label 應為未知', () => {
    expect(DEFAULT_NODE_CONFIG.label).toBe('未知');
  });

  it('detailable 應為 false', () => {
    expect(DEFAULT_NODE_CONFIG.detailable).toBe(false);
  });
});

// ============================================================================
// KNOWN_NODE_TYPES
// ============================================================================

describe('KNOWN_NODE_TYPES', () => {
  it('應該是字串陣列', () => {
    expect(Array.isArray(KNOWN_NODE_TYPES)).toBe(true);
    for (const t of KNOWN_NODE_TYPES) {
      expect(typeof t).toBe('string');
    }
  });

  it('數量應與 GRAPH_NODE_CONFIG keys 一致', () => {
    expect(KNOWN_NODE_TYPES.length).toBe(Object.keys(GRAPH_NODE_CONFIG).length);
  });

  it('應包含 document 和 org', () => {
    expect(KNOWN_NODE_TYPES).toContain('document');
    expect(KNOWN_NODE_TYPES).toContain('org');
  });
});

// ============================================================================
// CANONICAL_ENTITY_TYPES
// ============================================================================

describe('CANONICAL_ENTITY_TYPES', () => {
  it('應該是 Set', () => {
    expect(CANONICAL_ENTITY_TYPES).toBeInstanceOf(Set);
  });

  it('應只包含 detailable 為 true 的類型', () => {
    const expected = ['org', 'person', 'ner_project', 'location', 'date', 'topic'];
    expect(CANONICAL_ENTITY_TYPES.size).toBe(expected.length);
    for (const type of expected) {
      expect(CANONICAL_ENTITY_TYPES.has(type)).toBe(true);
    }
  });

  it('不應包含業務實體類型', () => {
    expect(CANONICAL_ENTITY_TYPES.has('document')).toBe(false);
    expect(CANONICAL_ENTITY_TYPES.has('project')).toBe(false);
    expect(CANONICAL_ENTITY_TYPES.has('agency')).toBe(false);
  });
});

// ============================================================================
// getNodeConfig
// ============================================================================

describe('getNodeConfig', () => {
  it('已知類型應回傳對應配置', () => {
    const config = getNodeConfig('document');
    expect(config.color).toBe('#1890ff');
    expect(config.label).toBe('公文');
  });

  it('未知類型應回傳 DEFAULT_NODE_CONFIG', () => {
    const config = getNodeConfig('unknown_type');
    expect(config).toEqual(DEFAULT_NODE_CONFIG);
  });

  it('空字串應回傳 DEFAULT_NODE_CONFIG', () => {
    const config = getNodeConfig('');
    expect(config).toEqual(DEFAULT_NODE_CONFIG);
  });
});

// ============================================================================
// localStorage 覆蓋機制
// ============================================================================

describe('localStorage override mechanism', () => {
  const STORAGE_KEY = 'kg_node_config_overrides';

  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe('getUserOverrides', () => {
    it('無覆蓋時應回傳空物件', () => {
      expect(getUserOverrides()).toEqual({});
    });

    it('應正確讀取已儲存的覆蓋', () => {
      const overrides = { document: { color: '#ff0000' } };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides));
      expect(getUserOverrides()).toEqual(overrides);
    });

    it('localStorage 含無效 JSON 時應回傳空物件', () => {
      localStorage.setItem(STORAGE_KEY, 'invalid-json');
      expect(getUserOverrides()).toEqual({});
    });
  });

  describe('saveUserOverrides', () => {
    it('應將覆蓋寫入 localStorage', () => {
      const overrides = { org: { color: '#00ff00', label: '測試組織' } };
      saveUserOverrides(overrides);
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
      expect(stored).toEqual(overrides);
    });

    it('空覆蓋應移除 localStorage 項目', () => {
      localStorage.setItem(STORAGE_KEY, '{"doc":{}}');
      saveUserOverrides({});
      expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    });

    it('應清除值為空物件的 entry', () => {
      saveUserOverrides({ document: {}, org: { color: '#abc123' } });
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
      expect(stored).not.toHaveProperty('document');
      expect(stored).toHaveProperty('org');
    });
  });

  describe('resetUserOverrides', () => {
    it('應移除 localStorage 中的覆蓋設定', () => {
      localStorage.setItem(STORAGE_KEY, '{"document":{"color":"#ff0000"}}');
      resetUserOverrides();
      expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    });
  });
});

// ============================================================================
// getMergedNodeConfig
// ============================================================================

describe('getMergedNodeConfig', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('無覆蓋時應回傳內建配置加 visible: true', () => {
    const merged = getMergedNodeConfig('document');
    expect(merged.color).toBe('#1890ff');
    expect(merged.label).toBe('公文');
    expect(merged.visible).toBe(true);
  });

  it('有覆蓋時應優先使用覆蓋值', () => {
    const overrides = { document: { color: '#ff0000', label: '自訂公文' } };
    localStorage.setItem('kg_node_config_overrides', JSON.stringify(overrides));

    const merged = getMergedNodeConfig('document');
    expect(merged.color).toBe('#ff0000');
    expect(merged.label).toBe('自訂公文');
    // radius 和 detailable 不可覆蓋，保持原值
    expect(merged.radius).toBe(GRAPH_NODE_CONFIG['document']!.radius);
    expect(merged.detailable).toBe(false);
  });

  it('visible 覆蓋為 false 時應正確反映', () => {
    const overrides = { org: { visible: false } };
    localStorage.setItem('kg_node_config_overrides', JSON.stringify(overrides));

    const merged = getMergedNodeConfig('org');
    expect(merged.visible).toBe(false);
  });

  it('未知類型應使用 DEFAULT_NODE_CONFIG', () => {
    const merged = getMergedNodeConfig('nonexistent');
    expect(merged.color).toBe('#999999');
    expect(merged.label).toBe('未知');
    expect(merged.visible).toBe(true);
  });
});

// ============================================================================
// getAllMergedConfigs
// ============================================================================

describe('getAllMergedConfigs', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('應回傳所有已知類型的合併配置', () => {
    const all = getAllMergedConfigs();
    const types = Object.keys(all);

    expect(types.length).toBe(Object.keys(GRAPH_NODE_CONFIG).length);
    for (const type of KNOWN_NODE_TYPES) {
      expect(all).toHaveProperty(type);
      expect(all[type]).toHaveProperty('visible');
    }
  });

  it('無覆蓋時所有類型 visible 應為 true', () => {
    const all = getAllMergedConfigs();
    for (const config of Object.values(all)) {
      expect(config.visible).toBe(true);
    }
  });

  it('應正確合併部分覆蓋', () => {
    const overrides = {
      document: { color: '#000000' },
      org: { visible: false },
    };
    localStorage.setItem('kg_node_config_overrides', JSON.stringify(overrides));

    const all = getAllMergedConfigs();
    expect(all['document']!.color).toBe('#000000');
    expect(all['document']!.visible).toBe(true);
    expect(all['org']!.visible).toBe(false);
    // 未覆蓋的類型應保持原樣
    expect(all['project']!.color).toBe('#52c41a');
    expect(all['project']!.visible).toBe(true);
  });
});

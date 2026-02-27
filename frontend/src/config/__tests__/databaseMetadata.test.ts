/**
 * 資料庫元數據配置測試
 * Database Metadata Config Tests
 */
import { describe, it, expect } from 'vitest';
import {
  getCategoryDisplayName,
  getCategoryColor,
  databaseMetadata,
} from '../databaseMetadata';

// ============================================================================
// getCategoryDisplayName
// ============================================================================

describe('getCategoryDisplayName', () => {
  const expectedMappings: Record<string, string> = {
    core: '核心業務',
    business: '業務管理',
    auth: '身份驗證',
    system: '系統配置',
    integration: '整合服務',
    reference: '參考資料',
    relation: '關聯表',
  };

  it.each(Object.entries(expectedMappings))(
    '分類 "%s" 應回傳 "%s"',
    (category, expectedName) => {
      expect(getCategoryDisplayName(category)).toBe(expectedName);
    }
  );

  it('未知分類應回傳原始字串', () => {
    expect(getCategoryDisplayName('unknown')).toBe('unknown');
    expect(getCategoryDisplayName('foo_bar')).toBe('foo_bar');
  });

  it('空字串應回傳空字串', () => {
    expect(getCategoryDisplayName('')).toBe('');
  });
});

// ============================================================================
// getCategoryColor
// ============================================================================

describe('getCategoryColor', () => {
  const expectedColors: Record<string, string> = {
    core: '#1976d2',
    business: '#52c41a',
    auth: '#fa8c16',
    system: '#722ed1',
    integration: '#13c2c2',
    reference: '#eb2f96',
    relation: '#666666',
  };

  it.each(Object.entries(expectedColors))(
    '分類 "%s" 應回傳顏色 "%s"',
    (category, expectedColor) => {
      expect(getCategoryColor(category)).toBe(expectedColor);
    }
  );

  it('未知分類應回傳灰色 fallback (#999999)', () => {
    expect(getCategoryColor('unknown')).toBe('#999999');
    expect(getCategoryColor('')).toBe('#999999');
  });

  it('所有顏色應為有效的 hex 格式', () => {
    for (const color of Object.values(expectedColors)) {
      expect(color).toMatch(/^#[0-9a-fA-F]{6}$/);
    }
  });
});

// ============================================================================
// databaseMetadata structure
// ============================================================================

describe('databaseMetadata', () => {
  it('應包含 table_metadata 和 categories 頂層屬性', () => {
    expect(databaseMetadata).toHaveProperty('table_metadata');
    expect(databaseMetadata).toHaveProperty('categories');
  });

  describe('table_metadata', () => {
    const expectedTables = [
      'alembic_version',
      'users',
      'user_sessions',
      'documents',
      'contract_projects',
      'partner_vendors',
      'project_vendor_association',
      'government_agencies',
      'calendar_events',
      'calendar_sync_logs',
      'cases',
      'doc_number_sequences',
      'site_configurations',
      'site_navigation_items',
    ];

    it('應包含所有預期的資料表', () => {
      for (const table of expectedTables) {
        expect(databaseMetadata.table_metadata).toHaveProperty(table);
      }
    });

    it('每個資料表應有必要的基本欄位', () => {
      for (const [tableName, meta] of Object.entries(databaseMetadata.table_metadata)) {
        expect(meta).toHaveProperty('chinese_name');
        expect(meta).toHaveProperty('description');
        expect(meta).toHaveProperty('category');
        expect(meta).toHaveProperty('frontend_pages');
        expect(meta).toHaveProperty('primary_key');
        expect(meta).toHaveProperty('relationships');
        // Type checks
        expect(typeof meta.chinese_name).toBe('string');
        expect(typeof meta.description).toBe('string');
        expect(typeof meta.category).toBe('string');
        expect(Array.isArray(meta.frontend_pages)).toBe(true);
        expect(typeof meta.primary_key).toBe('string');
        expect(Array.isArray(meta.relationships)).toBe(true);
      }
    });

    it('documents 表應有 columns 定義', () => {
      const docs = databaseMetadata.table_metadata['documents']!;
      expect(docs.columns).toBeDefined();
      expect(docs.columns).toHaveProperty('id');
      expect(docs.columns).toHaveProperty('doc_number');
      expect(docs.columns).toHaveProperty('subject');
    });

    it('users 表應有 columns 定義', () => {
      const users = databaseMetadata.table_metadata['users']!;
      expect(users.columns).toBeDefined();
      expect(users.columns).toHaveProperty('id');
      expect(users.columns).toHaveProperty('username');
      expect(users.columns).toHaveProperty('email');
    });

    it('有 columns 的表每個 column 應有 chinese_name, type, description', () => {
      for (const meta of Object.values(databaseMetadata.table_metadata)) {
        if (meta.columns) {
          for (const [colName, col] of Object.entries(meta.columns)) {
            expect(typeof col.chinese_name).toBe('string');
            expect(typeof col.type).toBe('string');
            expect(typeof col.description).toBe('string');
          }
        }
      }
    });

    it('relationship 應有正確的結構', () => {
      for (const meta of Object.values(databaseMetadata.table_metadata)) {
        for (const rel of meta.relationships) {
          expect(typeof rel.table).toBe('string');
          expect(['one_to_many', 'many_to_one', 'many_to_many']).toContain(rel.type);
          expect(typeof rel.foreign_key).toBe('string');
          expect(typeof rel.description).toBe('string');
        }
      }
    });
  });

  describe('categories', () => {
    const expectedCategories = [
      'core', 'business', 'auth', 'system', 'integration', 'reference', 'relation',
    ];

    it('應包含所有預期的分類', () => {
      for (const cat of expectedCategories) {
        expect(databaseMetadata.categories).toHaveProperty(cat);
      }
    });

    it('每個分類應有 chinese_name, description, color, icon', () => {
      for (const [catName, info] of Object.entries(databaseMetadata.categories)) {
        expect(typeof info.chinese_name).toBe('string');
        expect(typeof info.description).toBe('string');
        expect(typeof info.color).toBe('string');
        expect(typeof info.icon).toBe('string');
        expect(info.color).toMatch(/^#[0-9a-fA-F]{6}$/);
      }
    });

    it('categories 中的顏色應與 getCategoryColor 一致', () => {
      for (const [catName, info] of Object.entries(databaseMetadata.categories)) {
        expect(getCategoryColor(catName)).toBe(info.color);
      }
    });

    it('每個資料表的 category 應在 categories 中存在', () => {
      const validCategories = new Set(Object.keys(databaseMetadata.categories));
      for (const [tableName, meta] of Object.entries(databaseMetadata.table_metadata)) {
        expect(validCategories.has(meta.category)).toBe(true);
      }
    });
  });
});

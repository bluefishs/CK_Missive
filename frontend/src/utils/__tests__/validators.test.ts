/**
 * validators 工具函數單元測試
 *
 * 測試 DocumentValidators, StringCleaners, AgencyNameParser, DateParsers,
 * FormRules, ApiResponseValidators
 *
 * 執行方式:
 *   cd frontend && npm run test -- validators
 */
import { describe, it, expect, vi } from 'vitest';

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

import {
  DocumentValidators,
  StringCleaners,
  AgencyNameParser,
  DateParsers,
  FormRules,
  ApiResponseValidators,
  VALID_DOC_TYPES,
  VALID_CATEGORIES,
  VALID_STATUSES,
} from '../validators';

// ============================================================================
// DocumentValidators
// ============================================================================

describe('DocumentValidators', () => {
  describe('validateDocType', () => {
    it('returns valid doc type as-is', () => {
      expect(DocumentValidators.validateDocType('函')).toBe('函');
      expect(DocumentValidators.validateDocType('書函')).toBe('書函');
    });

    it('returns default when value is null/undefined (autoFix=true)', () => {
      expect(DocumentValidators.validateDocType(null)).toBe('函');
      expect(DocumentValidators.validateDocType(undefined)).toBe('函');
    });

    it('returns default for invalid value with autoFix', () => {
      expect(DocumentValidators.validateDocType('invalid')).toBe('函');
    });

    it('throws for invalid value without autoFix', () => {
      expect(() => DocumentValidators.validateDocType('invalid', false)).toThrow('無效的公文類型');
    });
  });

  describe('validateCategory', () => {
    it('accepts valid categories', () => {
      expect(DocumentValidators.validateCategory('收文')).toBe('收文');
      expect(DocumentValidators.validateCategory('發文')).toBe('發文');
    });

    it('throws for null/empty', () => {
      expect(() => DocumentValidators.validateCategory(null)).toThrow('類別不可為空');
    });

    it('throws for invalid category', () => {
      expect(() => DocumentValidators.validateCategory('invalid')).toThrow('無效的類別');
    });
  });

  describe('validateStatus', () => {
    it('accepts valid statuses', () => {
      expect(DocumentValidators.validateStatus('active')).toBe('active');
      expect(DocumentValidators.validateStatus('已完成')).toBe('已完成');
    });

    it('returns default for null', () => {
      expect(DocumentValidators.validateStatus(null)).toBe('active');
    });

    it('returns default for invalid status', () => {
      expect(DocumentValidators.validateStatus('unknown')).toBe('active');
    });
  });

  describe('type guard functions', () => {
    it('isValidDocType returns true for valid types', () => {
      expect(DocumentValidators.isValidDocType('函')).toBe(true);
      expect(DocumentValidators.isValidDocType('invalid')).toBe(false);
    });

    it('isValidCategory returns true for valid categories', () => {
      expect(DocumentValidators.isValidCategory('收文')).toBe(true);
      expect(DocumentValidators.isValidCategory('unknown')).toBe(false);
    });

    it('isValidStatus returns true for valid statuses', () => {
      expect(DocumentValidators.isValidStatus('active')).toBe(true);
      expect(DocumentValidators.isValidStatus('unknown')).toBe(false);
    });
  });
});

describe('constants', () => {
  it('VALID_DOC_TYPES includes expected types', () => {
    expect(VALID_DOC_TYPES).toContain('函');
    expect(VALID_DOC_TYPES).toContain('公告');
  });

  it('VALID_CATEGORIES includes receive and send', () => {
    expect(VALID_CATEGORIES).toContain('收文');
    expect(VALID_CATEGORIES).toContain('發文');
  });

  it('VALID_STATUSES includes expected statuses', () => {
    expect(VALID_STATUSES).toContain('active');
    expect(VALID_STATUSES).toContain('已完成');
  });
});

// ============================================================================
// StringCleaners
// ============================================================================

describe('StringCleaners', () => {
  describe('cleanString', () => {
    it('returns null for null/undefined', () => {
      expect(StringCleaners.cleanString(null)).toBeNull();
      expect(StringCleaners.cleanString(undefined)).toBeNull();
    });

    it('returns null for invalid string values', () => {
      expect(StringCleaners.cleanString('none')).toBeNull();
      expect(StringCleaners.cleanString('null')).toBeNull();
      expect(StringCleaners.cleanString('undefined')).toBeNull();
      expect(StringCleaners.cleanString('')).toBeNull();
    });

    it('trims whitespace from valid strings', () => {
      expect(StringCleaners.cleanString('  hello  ')).toBe('hello');
    });

    it('converts non-string values to string', () => {
      expect(StringCleaners.cleanString(123)).toBe('123');
    });
  });

  describe('cleanAgencyName', () => {
    it('returns null for empty input', () => {
      expect(StringCleaners.cleanAgencyName(null)).toBeNull();
      expect(StringCleaners.cleanAgencyName('')).toBeNull();
    });

    it('removes code suffix in parentheses', () => {
      expect(StringCleaners.cleanAgencyName('桃園市政府(10002)')).toBe('桃園市政府');
    });

    it('removes leading numeric code', () => {
      expect(StringCleaners.cleanAgencyName('10002 桃園市政府')).toBe('桃園市政府');
    });
  });

  describe('cleanAndTruncate', () => {
    it('returns null for invalid input', () => {
      expect(StringCleaners.cleanAndTruncate(null, 10)).toBeNull();
    });

    it('returns string as-is when within limit', () => {
      expect(StringCleaners.cleanAndTruncate('short', 10)).toBe('short');
    });

    it('truncates long strings with ellipsis', () => {
      const result = StringCleaners.cleanAndTruncate('a very long string indeed', 10);
      // substring(0, 7) + '...' = 'a very ...'
      expect(result).toBe('a very ...');
      expect(result!.length).toBe(10);
    });
  });
});

// ============================================================================
// AgencyNameParser
// ============================================================================

describe('AgencyNameParser', () => {
  describe('parse', () => {
    it('returns empty array for null/empty', () => {
      expect(AgencyNameParser.parse(null)).toEqual([]);
      expect(AgencyNameParser.parse('')).toEqual([]);
    });

    it('parses plain name without code', () => {
      const result = AgencyNameParser.parse('桃園市政府');
      expect(result).toHaveLength(1);
      expect(result[0]!.name).toBe('桃園市政府');
      expect(result[0]!.code).toBeNull();
    });

    it('parses multiple agencies separated by pipe', () => {
      const result = AgencyNameParser.parse('桃園市政府 | 新竹市政府');
      expect(result).toHaveLength(2);
    });
  });

  describe('extractNames', () => {
    it('returns name list from text', () => {
      const names = AgencyNameParser.extractNames('桃園市政府 | 新竹市政府');
      expect(names).toHaveLength(2);
      expect(names).toContain('桃園市政府');
      expect(names).toContain('新竹市政府');
    });
  });
});

// ============================================================================
// DateParsers
// ============================================================================

describe('DateParsers', () => {
  describe('parseDate', () => {
    it('returns null for falsy values', () => {
      expect(DateParsers.parseDate(null)).toBeNull();
      expect(DateParsers.parseDate(undefined)).toBeNull();
      expect(DateParsers.parseDate('')).toBeNull();
    });

    it('parses ISO date string', () => {
      const result = DateParsers.parseDate('2026-01-15');
      expect(result).toBeInstanceOf(Date);
      expect(result!.getFullYear()).toBe(2026);
    });

    it('parses ROC date format', () => {
      const result = DateParsers.parseDate('中華民國114年1月8日');
      expect(result).toBeInstanceOf(Date);
      expect(result!.getFullYear()).toBe(2025);
      expect(result!.getMonth()).toBe(0); // January
      expect(result!.getDate()).toBe(8);
    });

    it('returns Date object as-is', () => {
      const date = new Date(2026, 0, 1);
      expect(DateParsers.parseDate(date)).toBe(date);
    });
  });

  describe('toRocDateString', () => {
    it('returns empty string for null', () => {
      expect(DateParsers.toRocDateString(null)).toBe('');
    });

    it('converts date to ROC format', () => {
      const date = new Date(2026, 0, 15);
      expect(DateParsers.toRocDateString(date)).toBe('115年1月15日');
    });
  });

  describe('toFullRocDateString', () => {
    it('returns empty string for null', () => {
      expect(DateParsers.toFullRocDateString(null)).toBe('');
    });

    it('includes prefix', () => {
      const date = new Date(2026, 0, 15);
      expect(DateParsers.toFullRocDateString(date)).toBe('中華民國115年1月15日');
    });
  });
});

// ============================================================================
// FormRules
// ============================================================================

describe('FormRules', () => {
  it('required returns rule object', () => {
    const rule = FormRules.required('必填');
    expect(rule.required).toBe(true);
    expect(rule.message).toBe('必填');
  });

  it('maxLength returns rule with max', () => {
    const rule = FormRules.maxLength(100);
    expect(rule.max).toBe(100);
  });

  it('email returns type email rule', () => {
    const rule = FormRules.email();
    expect(rule.type).toBe('email');
  });

  it('taxId returns 8-digit pattern', () => {
    const rule = FormRules.taxId();
    expect(rule.pattern).toBeInstanceOf(RegExp);
    expect(rule.pattern.test('12345678')).toBe(true);
    expect(rule.pattern.test('1234')).toBe(false);
  });
});

// ============================================================================
// ApiResponseValidators
// ============================================================================

describe('ApiResponseValidators', () => {
  describe('isValidId', () => {
    it('returns true for positive integers', () => {
      expect(ApiResponseValidators.isValidId(1)).toBe(true);
      expect(ApiResponseValidators.isValidId(100)).toBe(true);
    });

    it('returns false for invalid values', () => {
      expect(ApiResponseValidators.isValidId(0)).toBe(false);
      expect(ApiResponseValidators.isValidId(-1)).toBe(false);
      expect(ApiResponseValidators.isValidId(null)).toBe(false);
      expect(ApiResponseValidators.isValidId(undefined)).toBe(false);
      expect(ApiResponseValidators.isValidId(1.5)).toBe(false);
    });
  });

  describe('isValidLinkType', () => {
    it('accepts valid link types', () => {
      expect(ApiResponseValidators.isValidLinkType('agency_incoming')).toBe(true);
      expect(ApiResponseValidators.isValidLinkType('company_outgoing')).toBe(true);
    });

    it('rejects invalid link types', () => {
      expect(ApiResponseValidators.isValidLinkType('unknown')).toBe(false);
      expect(ApiResponseValidators.isValidLinkType(null)).toBe(false);
    });
  });

  describe('validateBaseLink', () => {
    it('validates valid base link data', () => {
      const result = ApiResponseValidators.validateBaseLink({ link_id: 1 });
      expect(result.isValid).toBe(true);
      expect(result.data!.link_id).toBe(1);
    });

    it('rejects invalid base link data', () => {
      const result = ApiResponseValidators.validateBaseLink({ link_id: null });
      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it('rejects non-object data', () => {
      const result = ApiResponseValidators.validateBaseLink(null);
      expect(result.isValid).toBe(false);
    });
  });

  describe('validateDispatchLinkArray', () => {
    it('validates array of dispatch links', () => {
      const result = ApiResponseValidators.validateDispatchLinkArray([
        { link_id: 1, dispatch_order_id: 10, dispatch_no: 'D-001' },
        { link_id: 2, dispatch_order_id: 20, dispatch_no: 'D-002' },
      ]);
      expect(result.validData).toHaveLength(2);
      expect(result.invalidCount).toBe(0);
    });

    it('returns error for non-array input', () => {
      const result = ApiResponseValidators.validateDispatchLinkArray('not an array');
      expect(result.validData).toEqual([]);
      expect(result.errors).toContain('資料不是陣列格式');
    });
  });

  describe('safeGetLinkId', () => {
    it('returns link_id from valid data', () => {
      expect(ApiResponseValidators.safeGetLinkId({ link_id: 42 })).toBe(42);
    });

    it('returns null for missing data', () => {
      expect(ApiResponseValidators.safeGetLinkId(null)).toBeNull();
      expect(ApiResponseValidators.safeGetLinkId(undefined)).toBeNull();
    });
  });
});

/**
 * validators.ts 單元測試
 *
 * 測試公文驗證器、字串清理工具、機關名稱解析器、日期解析工具
 *
 * @version 1.0.0
 * @date 2026-02-06
 */
import { describe, it, expect, vi } from 'vitest';

// Mock logger
vi.mock('../../services/logger', () => ({
  logger: {
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    log: vi.fn(),
    debug: vi.fn(),
  },
}));

import {
  DocumentValidators,
  StringCleaners,
  AgencyNameParser,
  DateParsers,
  ApiResponseValidators,
  VALID_DOC_TYPES,
  VALID_CATEGORIES,
  VALID_STATUSES,
} from '../../utils/validators';

// =============================================================================
// DocumentValidators
// =============================================================================

describe('DocumentValidators', () => {
  describe('validateDocType', () => {
    it('有效公文類型應直接返回', () => {
      expect(DocumentValidators.validateDocType('函')).toBe('函');
      expect(DocumentValidators.validateDocType('公告')).toBe('公告');
      expect(DocumentValidators.validateDocType('書函')).toBe('書函');
    });

    it('null/undefined 值且 autoFix=true 應返回預設值「函」', () => {
      expect(DocumentValidators.validateDocType(null)).toBe('函');
      expect(DocumentValidators.validateDocType(undefined)).toBe('函');
      expect(DocumentValidators.validateDocType('')).toBe('函');
    });

    it('null/undefined 值且 autoFix=false 應返回空字串', () => {
      expect(DocumentValidators.validateDocType(null, false)).toBe('');
      expect(DocumentValidators.validateDocType(undefined, false)).toBe('');
    });

    it('無效類型且 autoFix=true 應返回預設值「函」', () => {
      expect(DocumentValidators.validateDocType('無效類型')).toBe('函');
    });

    it('無效類型且 autoFix=false 應拋出錯誤', () => {
      expect(() => DocumentValidators.validateDocType('無效類型', false)).toThrow('無效的公文類型');
    });

    it('應去除前後空白', () => {
      expect(DocumentValidators.validateDocType('  函  ')).toBe('函');
    });
  });

  describe('validateCategory', () => {
    it('有效類別應返回', () => {
      expect(DocumentValidators.validateCategory('收文')).toBe('收文');
      expect(DocumentValidators.validateCategory('發文')).toBe('發文');
    });

    it('空值應拋出錯誤', () => {
      expect(() => DocumentValidators.validateCategory(null)).toThrow('類別不可為空');
      expect(() => DocumentValidators.validateCategory(undefined)).toThrow('類別不可為空');
      expect(() => DocumentValidators.validateCategory('')).toThrow('類別不可為空');
    });

    it('無效類別應拋出錯誤', () => {
      expect(() => DocumentValidators.validateCategory('退文')).toThrow('無效的類別');
    });
  });

  describe('validateStatus', () => {
    it('有效狀態應返回', () => {
      expect(DocumentValidators.validateStatus('待處理')).toBe('待處理');
      expect(DocumentValidators.validateStatus('已完成')).toBe('已完成');
      expect(DocumentValidators.validateStatus('active')).toBe('active');
    });

    it('空值應返回預設值', () => {
      expect(DocumentValidators.validateStatus(null)).toBe('active');
      expect(DocumentValidators.validateStatus(undefined)).toBe('active');
    });

    it('空值搭配自訂預設值應返回自訂值', () => {
      expect(DocumentValidators.validateStatus(null, '待處理')).toBe('待處理');
    });

    it('無效狀態應返回預設值', () => {
      expect(DocumentValidators.validateStatus('invalid')).toBe('active');
    });
  });

  describe('isValidDocType', () => {
    it('有效類型返回 true', () => {
      VALID_DOC_TYPES.forEach((t) => {
        expect(DocumentValidators.isValidDocType(t)).toBe(true);
      });
    });

    it('無效類型返回 false', () => {
      expect(DocumentValidators.isValidDocType('隨便')).toBe(false);
    });
  });

  describe('isValidCategory', () => {
    it('有效類別返回 true', () => {
      VALID_CATEGORIES.forEach((c) => {
        expect(DocumentValidators.isValidCategory(c)).toBe(true);
      });
    });

    it('無效類別返回 false', () => {
      expect(DocumentValidators.isValidCategory('退文')).toBe(false);
    });
  });

  describe('isValidStatus', () => {
    it('有效狀態返回 true', () => {
      VALID_STATUSES.forEach((s) => {
        expect(DocumentValidators.isValidStatus(s)).toBe(true);
      });
    });

    it('無效狀態返回 false', () => {
      expect(DocumentValidators.isValidStatus('unknown')).toBe(false);
    });
  });
});

// =============================================================================
// StringCleaners
// =============================================================================

describe('StringCleaners', () => {
  describe('cleanString', () => {
    it('正常字串應返回去除空白後的結果', () => {
      expect(StringCleaners.cleanString('  hello  ')).toBe('hello');
    });

    it('null/undefined 應返回 null', () => {
      expect(StringCleaners.cleanString(null)).toBeNull();
      expect(StringCleaners.cleanString(undefined)).toBeNull();
    });

    it('特殊無效值應返回 null', () => {
      expect(StringCleaners.cleanString('none')).toBeNull();
      expect(StringCleaners.cleanString('None')).toBeNull();
      expect(StringCleaners.cleanString('null')).toBeNull();
      expect(StringCleaners.cleanString('undefined')).toBeNull();
      expect(StringCleaners.cleanString('NaN')).toBeNull();
      expect(StringCleaners.cleanString('')).toBeNull();
    });

    it('數字應轉為字串', () => {
      expect(StringCleaners.cleanString(123)).toBe('123');
      expect(StringCleaners.cleanString(0)).toBe('0');
    });
  });

  describe('cleanAgencyName', () => {
    it('純名稱應返回原值', () => {
      expect(StringCleaners.cleanAgencyName('桃園市政府')).toBe('桃園市政府');
    });

    it('應移除括號內的代碼', () => {
      expect(StringCleaners.cleanAgencyName('桃園市政府(10002)')).toBe('桃園市政府');
      expect(StringCleaners.cleanAgencyName('桃園市政府 (10002)')).toBe('桃園市政府');
    });

    it('應移除開頭的數字代碼', () => {
      expect(StringCleaners.cleanAgencyName('10002 桃園市政府')).toBe('桃園市政府');
    });

    it('null/undefined 應返回 null', () => {
      expect(StringCleaners.cleanAgencyName(null)).toBeNull();
      expect(StringCleaners.cleanAgencyName(undefined)).toBeNull();
    });

    it('空字串應返回 null', () => {
      expect(StringCleaners.cleanAgencyName('')).toBeNull();
    });
  });

  describe('cleanAndTruncate', () => {
    it('短字串不應截斷', () => {
      expect(StringCleaners.cleanAndTruncate('hello', 10)).toBe('hello');
    });

    it('長字串應截斷並加省略號', () => {
      expect(StringCleaners.cleanAndTruncate('這是一段很長的文字內容', 8)).toBe('這是一段很...');
    });

    it('剛好等於最大長度不應截斷', () => {
      expect(StringCleaners.cleanAndTruncate('12345', 5)).toBe('12345');
    });

    it('null 值應返回 null', () => {
      expect(StringCleaners.cleanAndTruncate(null, 10)).toBeNull();
    });

    it('無效值應返回 null', () => {
      expect(StringCleaners.cleanAndTruncate('none', 10)).toBeNull();
    });
  });
});

// =============================================================================
// AgencyNameParser
// =============================================================================

describe('AgencyNameParser', () => {
  describe('parse', () => {
    it('純名稱應解析為 code=null', () => {
      const result = AgencyNameParser.parse('桃園市政府');
      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({ code: null, name: '桃園市政府' });
    });

    it('代碼+括號+名稱格式應正確解析', () => {
      const result = AgencyNameParser.parse('A10002 (桃園市政府)');
      expect(result).toHaveLength(1);
      expect(result[0]?.code).toBe('A10002');
      expect(result[0]?.name).toBe('桃園市政府');
    });

    it('代碼+空格+名稱格式應正確解析', () => {
      const result = AgencyNameParser.parse('A10002 桃園市政府');
      expect(result).toHaveLength(1);
      expect(result[0]?.code).toBe('A10002');
      expect(result[0]?.name).toBe('桃園市政府');
    });

    it('以 | 分隔的多個機關應全部解析', () => {
      const result = AgencyNameParser.parse('桃園市政府 | 新竹縣政府');
      expect(result).toHaveLength(2);
      expect(result[0]?.name).toBe('桃園市政府');
      expect(result[1]?.name).toBe('新竹縣政府');
    });

    it('空值/null/undefined 應返回空陣列', () => {
      expect(AgencyNameParser.parse(null)).toEqual([]);
      expect(AgencyNameParser.parse(undefined)).toEqual([]);
      expect(AgencyNameParser.parse('')).toEqual([]);
      expect(AgencyNameParser.parse('  ')).toEqual([]);
    });
  });

  describe('extractNames', () => {
    it('應提取所有機關名稱', () => {
      const names = AgencyNameParser.extractNames('桃園市政府 | 新竹縣政府');
      expect(names).toEqual(['桃園市政府', '新竹縣政府']);
    });

    it('空值應返回空陣列', () => {
      expect(AgencyNameParser.extractNames(null)).toEqual([]);
    });
  });

  describe('extractCodes', () => {
    it('應提取機關代碼（排除 null）', () => {
      const codes = AgencyNameParser.extractCodes('A10002 (桃園市政府) | 新竹縣政府');
      expect(codes).toEqual(['A10002']);
    });

    it('無代碼時返回空陣列', () => {
      expect(AgencyNameParser.extractCodes('桃園市政府')).toEqual([]);
    });
  });
});

// =============================================================================
// DateParsers
// =============================================================================

describe('DateParsers', () => {
  describe('parseDate', () => {
    it('標準 ISO 日期字串應正確解析', () => {
      const result = DateParsers.parseDate('2026-01-15');
      expect(result).toBeInstanceOf(Date);
      expect(result?.getFullYear()).toBe(2026);
      expect(result?.getMonth()).toBe(0); // January = 0
      expect(result?.getDate()).toBe(15);
    });

    it('Date 物件應直接返回', () => {
      const date = new Date(2026, 0, 15);
      expect(DateParsers.parseDate(date)).toBe(date);
    });

    it('無效 Date 物件應返回 null', () => {
      expect(DateParsers.parseDate(new Date('invalid'))).toBeNull();
    });

    it('null/undefined 應返回 null', () => {
      expect(DateParsers.parseDate(null)).toBeNull();
      expect(DateParsers.parseDate(undefined)).toBeNull();
    });

    it('特殊無效字串應返回 null', () => {
      expect(DateParsers.parseDate('none')).toBeNull();
      expect(DateParsers.parseDate('null')).toBeNull();
      expect(DateParsers.parseDate('')).toBeNull();
    });

    it('民國日期「中華民國114年1月8日」應正確解析', () => {
      const result = DateParsers.parseDate('中華民國114年1月8日');
      expect(result).toBeInstanceOf(Date);
      expect(result?.getFullYear()).toBe(2025);
      expect(result?.getMonth()).toBe(0);
      expect(result?.getDate()).toBe(8);
    });

    it('民國日期「民國115年2月6日」應正確解析', () => {
      const result = DateParsers.parseDate('民國115年2月6日');
      expect(result).toBeInstanceOf(Date);
      expect(result?.getFullYear()).toBe(2026);
      expect(result?.getMonth()).toBe(1);
      expect(result?.getDate()).toBe(6);
    });

    it('簡化民國格式「115年2月6日」應正確解析', () => {
      const result = DateParsers.parseDate('115年2月6日');
      expect(result).toBeInstanceOf(Date);
      expect(result?.getFullYear()).toBe(2026);
    });
  });

  describe('toRocDateString', () => {
    it('應轉換為民國日期格式', () => {
      const date = new Date(2026, 0, 21); // 2026-01-21
      expect(DateParsers.toRocDateString(date)).toBe('115年1月21日');
    });

    it('null 應返回空字串', () => {
      expect(DateParsers.toRocDateString(null)).toBe('');
      expect(DateParsers.toRocDateString(undefined)).toBe('');
    });
  });

  describe('toFullRocDateString', () => {
    it('應轉換為完整民國日期格式', () => {
      const date = new Date(2026, 0, 21);
      expect(DateParsers.toFullRocDateString(date)).toBe('中華民國115年1月21日');
    });

    it('null 應返回空字串', () => {
      expect(DateParsers.toFullRocDateString(null)).toBe('');
    });
  });
});

// =============================================================================
// ApiResponseValidators
// =============================================================================

describe('ApiResponseValidators', () => {
  describe('isValidId', () => {
    it('正整數應返回 true', () => {
      expect(ApiResponseValidators.isValidId(1)).toBe(true);
      expect(ApiResponseValidators.isValidId(999)).toBe(true);
    });

    it('零和負數應返回 false', () => {
      expect(ApiResponseValidators.isValidId(0)).toBe(false);
      expect(ApiResponseValidators.isValidId(-1)).toBe(false);
    });

    it('null/undefined 應返回 false', () => {
      expect(ApiResponseValidators.isValidId(null)).toBe(false);
      expect(ApiResponseValidators.isValidId(undefined)).toBe(false);
    });

    it('浮點數應返回 false', () => {
      expect(ApiResponseValidators.isValidId(1.5)).toBe(false);
    });

    it('可轉為正整數的字串應返回 true', () => {
      expect(ApiResponseValidators.isValidId('5')).toBe(true);
    });
  });

  describe('isValidLinkType', () => {
    it('有效類型應返回 true', () => {
      expect(ApiResponseValidators.isValidLinkType('agency_incoming')).toBe(true);
      expect(ApiResponseValidators.isValidLinkType('company_outgoing')).toBe(true);
    });

    it('無效類型應返回 false', () => {
      expect(ApiResponseValidators.isValidLinkType('invalid')).toBe(false);
      expect(ApiResponseValidators.isValidLinkType(null)).toBe(false);
      expect(ApiResponseValidators.isValidLinkType(123)).toBe(false);
    });
  });

  describe('validateBaseLink', () => {
    it('有效資料應通過驗證', () => {
      const result = ApiResponseValidators.validateBaseLink({
        link_id: 1,
        link_type: 'agency_incoming',
        created_at: '2026-01-01',
      });
      expect(result.isValid).toBe(true);
      expect(result.data?.link_id).toBe(1);
    });

    it('缺少 link_id 應驗證失敗', () => {
      const result = ApiResponseValidators.validateBaseLink({ link_type: 'agency_incoming' });
      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it('null 輸入應驗證失敗', () => {
      const result = ApiResponseValidators.validateBaseLink(null);
      expect(result.isValid).toBe(false);
    });

    it('無效 link_type 應產生警告但不失敗', () => {
      const result = ApiResponseValidators.validateBaseLink({
        link_id: 1,
        link_type: 'invalid_type',
      });
      expect(result.isValid).toBe(true);
      expect(result.warnings.length).toBeGreaterThan(0);
    });
  });

  describe('validateDispatchLink', () => {
    it('有效派工關聯應通過驗證', () => {
      const result = ApiResponseValidators.validateDispatchLink({
        link_id: 1,
        dispatch_order_id: 100,
        dispatch_no: 'D-001',
      });
      expect(result.isValid).toBe(true);
      expect(result.data?.dispatch_order_id).toBe(100);
    });

    it('缺少 dispatch_order_id 應驗證失敗', () => {
      const result = ApiResponseValidators.validateDispatchLink({
        link_id: 1,
        dispatch_no: 'D-001',
      });
      expect(result.isValid).toBe(false);
    });
  });

  describe('validateDispatchLinkArray', () => {
    it('有效陣列應全部通過', () => {
      const result = ApiResponseValidators.validateDispatchLinkArray([
        { link_id: 1, dispatch_order_id: 100, dispatch_no: 'D-001' },
        { link_id: 2, dispatch_order_id: 200, dispatch_no: 'D-002' },
      ]);
      expect(result.validData).toHaveLength(2);
      expect(result.invalidCount).toBe(0);
    });

    it('混合有效/無效資料應正確分類', () => {
      const result = ApiResponseValidators.validateDispatchLinkArray([
        { link_id: 1, dispatch_order_id: 100, dispatch_no: 'D-001' },
        { link_id: null, dispatch_order_id: null },
      ]);
      expect(result.validData).toHaveLength(1);
      expect(result.invalidCount).toBe(1);
    });

    it('非陣列輸入應返回錯誤', () => {
      const result = ApiResponseValidators.validateDispatchLinkArray('not an array');
      expect(result.validData).toHaveLength(0);
      expect(result.errors).toHaveLength(1);
    });
  });

  describe('safeGetLinkId', () => {
    it('有效 link_id 應返回數字', () => {
      expect(ApiResponseValidators.safeGetLinkId({ link_id: 42 })).toBe(42);
    });

    it('null 資料應返回 null', () => {
      expect(ApiResponseValidators.safeGetLinkId(null)).toBeNull();
      expect(ApiResponseValidators.safeGetLinkId(undefined)).toBeNull();
    });

    it('無效 link_id 應返回 null', () => {
      expect(ApiResponseValidators.safeGetLinkId({ link_id: -1 })).toBeNull();
      expect(ApiResponseValidators.safeGetLinkId({ link_id: null })).toBeNull();
    });

    it('自訂 idField 應正確取值', () => {
      expect(ApiResponseValidators.safeGetLinkId({ custom_id: 99 }, 'custom_id')).toBe(99);
    });
  });
});

/**
 * 機關名稱處理工具函數
 *
 * 功能：
 * - 標準化機關名稱（移除編碼前綴）
 * - 分割多機關字串
 * - 格式化顯示
 *
 * @version 1.0.0
 * @date 2026-02-02
 */

/**
 * 標準化名稱（去除空白、統一全形半形括號）
 */
export const normalizeName = (name: string | null | undefined): string => {
  if (!name) return '';
  return name
    .trim()
    .replace(/\s+/g, '')  // 移除所有空白
    .replace(/　/g, '')    // 移除全形空白
    .replace(/（/g, '(')   // 統一括號
    .replace(/）/g, ')');
};

/**
 * 從機關字串中提取純名稱（移除編碼前綴）
 *
 * @example
 * extractAgencyName('376480000A (南投縣政府)') // '南投縣政府'
 * extractAgencyName('內政部國土管理署') // '內政部國土管理署'
 */
export const extractAgencyName = (agency: string): string => {
  if (!agency) return '';
  const trimmed = agency.trim();

  // 嘗試匹配括號內的名稱 (如 "376480000A (南投縣政府)")
  const match = trimmed.match(/\(([^)]+)\)/);
  if (match && match[1]) {
    return match[1];
  }

  return trimmed;
};

/**
 * 格式化機關名稱顯示（處理多單位分隔）
 *
 * @example
 * formatAgencyDisplay('376480000A (南投縣政府) | A01020100G (內政部國土管理署城鄉發展分署)')
 * // '南投縣政府、內政部國土管理署城鄉發展分署'
 */
export const formatAgencyDisplay = (value: string | null | undefined): string => {
  if (!value) return '-';

  const agencies = value.split(' | ').map((agency) => {
    const trimmed = agency.trim();
    const match = trimmed.match(/\(([^)]+)\)/);
    if (match && match[1]) {
      return match[1];
    }
    return trimmed;
  });

  return agencies.join('、');
};

/**
 * 從機關字串中提取機關列表（用於統計分析）
 *
 * @example
 * extractAgencyList('376480000A (南投縣政府) | A01020100G (內政部)')
 * // ['南投縣政府', '內政部']
 */
export const extractAgencyList = (value: string | null | undefined): string[] => {
  if (!value) return [];

  const agencies = value.split(/\s*\|\s*/);
  const result: string[] = [];

  for (const agency of agencies) {
    const name = extractAgencyName(agency);
    if (name) {
      const normalized = normalizeName(name);
      if (normalized && normalized !== '未指定') {
        result.push(normalized);
      }
    }
  }

  return result;
};

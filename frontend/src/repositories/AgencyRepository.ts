/**
 * 機關 Repository - 機關資料存取層
 *
 * @version 1.0.0
 * @date 2026-01-21
 */

import { BaseRepository } from './BaseRepository';
import { AGENCIES_ENDPOINTS } from '../api/endpoints';
import type { Agency, AgencyCreate, AgencyUpdate } from '../types/api';

/**
 * 機關統計資料
 */
export interface AgencyStatistics {
  total_agencies: number;
  categories: Array<{
    category: string;
    count: number;
    percentage: number;
  }>;
}

/**
 * 機關 Repository
 *
 * @example
 * ```typescript
 * const agencies = await agencyRepository.list({ search: '市政府' });
 * const agency = await agencyRepository.getById(1);
 * const stats = await agencyRepository.getStatistics();
 * ```
 */
export class AgencyRepository extends BaseRepository<Agency, AgencyCreate, AgencyUpdate> {
  protected endpoints = AGENCIES_ENDPOINTS;

  /**
   * 取得機關統計
   */
  async getStatistics(): Promise<AgencyStatistics> {
    return this.post<AgencyStatistics>(this.endpoints.STATISTICS, {});
  }

  /**
   * 依名稱查詢
   */
  async getByName(name: string): Promise<Agency | null> {
    try {
      const response = await this.list({ search: name, limit: 1 });
      const match = response.items?.find(a => a.agency_name === name);
      return match || null;
    } catch {
      return null;
    }
  }

  /**
   * 建議機關（模糊搜尋）
   */
  async suggest(text: string, limit: number = 5): Promise<Agency[]> {
    if (!text || text.length < 2) return [];
    const response = await this.list({ search: text, limit });
    return response.items || [];
  }
}

// 匯出單例
export const agencyRepository = new AgencyRepository();
export default agencyRepository;

/**
 * 廠商 Repository - 廠商資料存取層
 *
 * @version 1.0.0
 * @date 2026-01-21
 */

import { BaseRepository } from './BaseRepository';
import { VENDORS_ENDPOINTS } from '../api/endpoints';
import type { Vendor, VendorCreate, VendorUpdate } from '../types/api';

/**
 * 廠商統計資料
 */
export interface VendorStatistics {
  total_vendors: number;
  business_types: Array<{
    business_type: string;
    count: number;
  }>;
  average_rating: number;
}

/**
 * 廠商 Repository
 *
 * @example
 * ```typescript
 * const vendors = await vendorRepository.list({ search: 'ABC' });
 * const vendor = await vendorRepository.getById(1);
 * const stats = await vendorRepository.getStatistics();
 * ```
 */
export class VendorRepository extends BaseRepository<Vendor, VendorCreate, VendorUpdate> {
  protected endpoints = VENDORS_ENDPOINTS;

  /**
   * 取得廠商統計
   */
  async getStatistics(): Promise<VendorStatistics> {
    return this.post<VendorStatistics>(this.endpoints.STATISTICS, {});
  }

  /**
   * 依統一編號查詢
   */
  async getByCode(code: string): Promise<Vendor | null> {
    try {
      const response = await this.list({ search: code, limit: 1 });
      const match = response.items?.find(v => v.vendor_code === code);
      return match || null;
    } catch {
      return null;
    }
  }
}

// 匯出單例
export const vendorRepository = new VendorRepository();
export default vendorRepository;

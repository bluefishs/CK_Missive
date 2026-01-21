/**
 * Repository 基類 - 提供統一的資料存取抽象
 *
 * Repository 層的職責：
 * - 封裝 API 呼叫邏輯
 * - 提供型別安全的資料存取介面
 * - 集中處理請求/回應轉換
 * - 便於 Mock 測試
 *
 * @version 1.0.0
 * @date 2026-01-21
 */

import { apiClient } from '../api/client';

/**
 * 分頁參數介面
 */
export interface PaginationParams {
  page?: number;
  limit?: number;
}

/**
 * 列表查詢參數介面
 */
export interface ListParams extends PaginationParams {
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

/**
 * 分頁回應介面
 */
export interface ListResponse<T> {
  items: T[];
  total: number;
  page?: number;
  limit?: number;
  total_pages?: number;
}

/**
 * Repository 基類
 *
 * @template T - 實體型別
 * @template C - 建立型別
 * @template U - 更新型別
 *
 * @example
 * ```typescript
 * class VendorRepository extends BaseRepository<Vendor, VendorCreate, VendorUpdate> {
 *   protected endpoints = VENDORS_ENDPOINTS;
 *
 *   async getStatistics(): Promise<VendorStatistics> {
 *     return this.post(this.endpoints.STATISTICS, {});
 *   }
 * }
 * ```
 */
export abstract class BaseRepository<T, C, U> {
  /**
   * 端點定義 - 子類別必須覆寫
   */
  protected abstract endpoints: {
    LIST: string;
    CREATE: string;
    DETAIL: (id: number) => string;
    UPDATE: (id: number) => string;
    DELETE: (id: number) => string;
  };

  /**
   * 發送 POST 請求
   */
  protected async post<R>(endpoint: string, data: unknown): Promise<R> {
    return apiClient.post<R>(endpoint, data);
  }

  /**
   * 取得列表
   */
  async list(params: ListParams = {}): Promise<ListResponse<T>> {
    return this.post<ListResponse<T>>(this.endpoints.LIST, params);
  }

  /**
   * 取得單筆資料
   */
  async getById(id: number): Promise<T> {
    return this.post<T>(this.endpoints.DETAIL(id), {});
  }

  /**
   * 建立資料
   */
  async create(data: C): Promise<T> {
    return this.post<T>(this.endpoints.CREATE, data);
  }

  /**
   * 更新資料
   */
  async update(id: number, data: U): Promise<T> {
    return this.post<T>(this.endpoints.UPDATE(id), data);
  }

  /**
   * 刪除資料
   */
  async delete(id: number): Promise<boolean> {
    const response = await this.post<{ success: boolean }>(
      this.endpoints.DELETE(id),
      {}
    );
    return response.success;
  }
}

export default BaseRepository;

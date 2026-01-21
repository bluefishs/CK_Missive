/**
 * Repository 層統一匯出
 *
 * Repository 負責資料存取抽象，介於 API 和 Hooks 之間。
 *
 * 架構：
 * ```
 * Components/Pages
 *       ↓
 *    Hooks (React Query + Zustand)
 *       ↓
 *  Repositories (資料存取抽象)
 *       ↓
 *    API Client (HTTP 請求)
 * ```
 *
 * @version 1.0.0
 * @date 2026-01-21
 */

// 基類
export { BaseRepository } from './BaseRepository';
export type { PaginationParams, ListParams } from './BaseRepository';

// 實體 Repositories
export { VendorRepository, vendorRepository } from './VendorRepository';
export type { VendorStatistics } from './VendorRepository';

export { AgencyRepository, agencyRepository } from './AgencyRepository';
export type { AgencyStatistics } from './AgencyRepository';

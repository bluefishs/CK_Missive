/** api-entity — 廠商/機關型別 */

// ============================================================================
// 廠商 (Vendor) 相關型別
// ============================================================================

/** 廠商業務類型 */
export type VendorBusinessType =
  | '測量業務'
  | '系統業務'
  | '查估業務'
  | '其他類別';

/** 廠商基礎介面 */
export interface Vendor {
  id: number;
  vendor_name: string;
  vendor_code?: string;
  vendor_type?: 'subcontractor' | 'client';
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  tax_id?: string;
  business_type?: string;
  rating?: number;
  notes?: string;
  created_at: string;
  updated_at: string;
}

/** 廠商建立請求 */
export interface VendorCreate {
  vendor_name: string;
  vendor_code?: string;
  vendor_type?: 'subcontractor' | 'client';
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  business_type?: string;
  rating?: number;
  notes?: string;
}

/** 廠商更新請求 */
export type VendorUpdate = Partial<VendorCreate>;

/** 廠商選項（下拉選單用） */
export interface VendorOption {
  id: number;
  vendor_name: string;
  vendor_code?: string;
}

// ============================================================================
// 機關 (Agency) 相關型別
// ============================================================================

/** 機關類型 */
export type AgencyType = '中央機關' | '地方機關' | '民間單位' | '其他';

/** 機關基礎介面 */
export interface Agency {
  id: number;
  agency_name: string;
  agency_short_name?: string;
  agency_code?: string;
  agency_type?: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  notes?: string;
  source?: 'manual' | 'auto' | 'import';
  created_at: string;
  updated_at: string;
}

/** 機關建立請求 */
export interface AgencyCreate {
  agency_name: string;
  agency_short_name?: string;
  agency_code?: string;
  agency_type?: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  notes?: string;
}

/** 機關更新請求 */
export type AgencyUpdate = Partial<AgencyCreate>;

/** 機關選項（下拉選單用） */
export interface AgencyOption {
  id: number;
  agency_name: string;
  agency_short_name?: string;
  agency_code?: string;
}

/** 機關（含統計資料） */
export interface AgencyWithStats extends Agency {
  document_count: number;
  sent_count: number;
  received_count: number;
  last_activity: string | null;
  primary_type: 'sender' | 'receiver' | 'both' | 'unknown';
  category?: string;
  original_names?: string[];
}

/** 機關分類統計 */
export interface CategoryStat {
  category: string;
  count: number;
  percentage: number;
}

/** 機關資料品質統計 */
export interface AgencyDataQuality {
  missing_agency_code: number;
  missing_by_source: Record<string, number>;
}

/** 機關統計資料 */
export interface AgencyStatistics {
  total_agencies: number;
  categories: CategoryStat[];
  data_quality?: AgencyDataQuality | null;
}

// ============================================================================
// 統計型別
// ============================================================================

/** 廠商統計資料 */
export interface VendorStatistics {
  total_vendors: number;
  business_types: Array<{
    business_type: string;
    count: number;
  }>;
  average_rating: number;
}

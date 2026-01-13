/**
 * 證照管理 API 服務
 *
 * 用於承辦同仁證照 CRUD 操作
 */

import { apiClient } from './client';
import { PaginatedResponse } from './types';
import { API_ENDPOINTS } from './endpoints';

// ============================================================================
// 型別定義
// ============================================================================

/** 證照類型選項 */
export const CERT_TYPES = ['核發證照', '評量證書', '訓練證明'] as const;
export type CertType = typeof CERT_TYPES[number];

/** 證照狀態選項 */
export const CERT_STATUS = ['有效', '已過期', '已撤銷'] as const;
export type CertStatus = typeof CERT_STATUS[number];

/** 證照基礎介面 */
export interface Certification {
  id: number;
  user_id: number;
  cert_type: CertType;
  cert_name: string;
  issuing_authority?: string;
  cert_number?: string;
  issue_date?: string;
  expiry_date?: string;
  status: CertStatus;
  notes?: string;
  attachment_path?: string;
  created_at?: string;
  updated_at?: string;
}

/** 建立證照請求 */
export interface CertificationCreate {
  user_id: number;
  cert_type: CertType;
  cert_name: string;
  issuing_authority?: string;
  cert_number?: string;
  issue_date?: string;
  expiry_date?: string;
  status?: CertStatus;
  notes?: string;
}

/** 更新證照請求 */
export interface CertificationUpdate {
  cert_type?: CertType;
  cert_name?: string;
  issuing_authority?: string;
  cert_number?: string;
  issue_date?: string;
  expiry_date?: string;
  status?: CertStatus;
  notes?: string;
}

/** 證照列表查詢參數 */
export interface CertificationListParams {
  page?: number;
  page_size?: number;
  cert_type?: CertType;
  status?: CertStatus;
  keyword?: string;
}

/** 證照統計 */
export interface CertificationStats {
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  total: number;
}

// ============================================================================
// API 方法
// ============================================================================

/**
 * 證照 API 服務
 */
export const certificationsApi = {
  /**
   * 新增證照
   *
   * @param data 證照資料
   * @returns 新建的證照
   */
  async create(data: CertificationCreate): Promise<Certification> {
    const response = await apiClient.post<{ success: boolean; data: Certification }>(
      API_ENDPOINTS.CERTIFICATIONS.CREATE,
      data
    );
    return response.data;
  },

  /**
   * 取得使用者證照列表
   *
   * @param userId 使用者 ID
   * @param params 查詢參數
   * @returns 分頁證照列表
   */
  async getUserCertifications(
    userId: number,
    params?: CertificationListParams
  ): Promise<PaginatedResponse<Certification>> {
    const queryParams = {
      page: params?.page ?? 1,
      page_size: params?.page_size ?? 20,
      cert_type: params?.cert_type,
      status: params?.status,
      keyword: params?.keyword,
    };

    return await apiClient.postList<Certification>(
      API_ENDPOINTS.CERTIFICATIONS.USER_LIST(userId),
      queryParams
    );
  },

  /**
   * 取得證照詳情
   *
   * @param certId 證照 ID
   * @returns 證照詳情
   */
  async getDetail(certId: number): Promise<Certification> {
    const response = await apiClient.post<{ success: boolean; data: Certification }>(
      API_ENDPOINTS.CERTIFICATIONS.DETAIL(certId)
    );
    return response.data;
  },

  /**
   * 更新證照
   *
   * @param certId 證照 ID
   * @param data 更新資料
   * @returns 更新後的證照
   */
  async update(certId: number, data: CertificationUpdate): Promise<Certification> {
    const response = await apiClient.post<{ success: boolean; data: Certification }>(
      API_ENDPOINTS.CERTIFICATIONS.UPDATE(certId),
      data
    );
    return response.data;
  },

  /**
   * 刪除證照
   *
   * @param certId 證照 ID
   * @returns 刪除結果
   */
  async delete(certId: number): Promise<void> {
    await apiClient.post(API_ENDPOINTS.CERTIFICATIONS.DELETE(certId));
  },

  /**
   * 取得使用者證照統計
   *
   * @param userId 使用者 ID
   * @returns 證照統計
   */
  async getStats(userId: number): Promise<CertificationStats> {
    const response = await apiClient.post<{ success: boolean; data: CertificationStats }>(
      API_ENDPOINTS.CERTIFICATIONS.STATS(userId)
    );
    return response.data;
  },
};

// 預設匯出
export default certificationsApi;

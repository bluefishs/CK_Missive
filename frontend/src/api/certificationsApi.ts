/**
 * 證照管理 API 服務
 *
 * 用於承辦同仁證照 CRUD 操作
 *
 * @version 2.0.0
 * @date 2026-01-23
 */

import { apiClient } from './client';
import { PaginatedResponse } from './types';
import { API_ENDPOINTS } from './endpoints';

// 型別從 types/api.ts 匯入（符合 SSOT 規範）
import type {
  Certification,
  CertificationCreate,
  CertificationUpdate,
  CertificationListParams,
  CertificationStats,
} from '../types/api';

// 重新匯出型別供外部使用
export type {
  Certification,
  CertificationCreate,
  CertificationUpdate,
  CertificationListParams,
  CertificationStats,
};

// 重新匯出常數
export { CERT_TYPES, CERT_STATUS } from '../types/api';
export type { CertType, CertStatus } from '../types/api';

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

  /**
   * 上傳證照附件（含進度追蹤）
   *
   * @param certId 證照 ID
   * @param file 檔案
   * @param onProgress 進度回調 (percent: 0-100)
   * @returns 上傳結果
   */
  async uploadAttachment(
    certId: number,
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<{ cert_id: number; attachment_path: string; filename: string; file_size: number; checksum?: string }> {
    const response = await apiClient.uploadWithProgress<{
      success: boolean;
      data: { cert_id: number; attachment_path: string; filename: string; file_size: number; checksum?: string };
    }>(
      API_ENDPOINTS.CERTIFICATIONS.UPLOAD_ATTACHMENT(certId),
      file,
      'file',
      onProgress ? (percent) => onProgress(percent) : undefined
    );

    return response.data;
  },

  /**
   * 下載證照附件
   *
   * @param certId 證照 ID
   */
  async downloadAttachment(certId: number): Promise<Blob> {
    const response = await apiClient.postBlob(
      API_ENDPOINTS.CERTIFICATIONS.DOWNLOAD_ATTACHMENT(certId)
    );
    return response;
  },

  /**
   * 刪除證照附件
   *
   * @param certId 證照 ID
   */
  async deleteAttachment(certId: number): Promise<void> {
    await apiClient.post(API_ENDPOINTS.CERTIFICATIONS.DELETE_ATTACHMENT(certId));
  },
};

// 預設匯出
export default certificationsApi;

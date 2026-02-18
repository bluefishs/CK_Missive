/**
 * 桃園查估派工 - 轄管工程 API
 *
 * @version 2.0.0
 * @date 2026-01-23
 */

import { apiClient, API_BASE_URL } from '../client';
import { API_ENDPOINTS } from '../endpoints';
import type {
  TaoyuanProject,
  TaoyuanProjectCreate,
  TaoyuanProjectUpdate,
  TaoyuanProjectListQuery,
  TaoyuanProjectListResponse,
  ExcelImportResult,
} from '../../types/api';

/**
 * 轄管工程 API 服務
 */
export const taoyuanProjectsApi = {
  /**
   * 取得轄管工程列表
   */
  async getList(params?: TaoyuanProjectListQuery): Promise<TaoyuanProjectListResponse> {
    return apiClient.post<TaoyuanProjectListResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_LIST,
      params ?? {}
    );
  },

  /**
   * 建立轄管工程
   */
  async create(data: TaoyuanProjectCreate): Promise<TaoyuanProject> {
    // 後端直接返回 TaoyuanProject 物件
    return apiClient.post<TaoyuanProject>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_CREATE,
      data
    );
  },

  /**
   * 取得轄管工程詳情
   */
  async getDetail(id: number): Promise<TaoyuanProject> {
    return apiClient.post<TaoyuanProject>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_DETAIL(id),
      {}
    );
  },

  /**
   * 更新轄管工程
   */
  async update(id: number, data: TaoyuanProjectUpdate): Promise<TaoyuanProject> {
    // 後端直接返回 TaoyuanProject 物件
    return apiClient.post<TaoyuanProject>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_UPDATE(id),
      data
    );
  },

  /**
   * 刪除轄管工程
   */
  async delete(id: number): Promise<void> {
    await apiClient.post(API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_DELETE(id), {});
  },

  /**
   * Excel 匯入工程資料
   */
  async importExcel(
    file: File,
    contractProjectId: number,
    reviewYear?: number
  ): Promise<ExcelImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('contract_project_id', String(contractProjectId));
    if (reviewYear) {
      formData.append('review_year', String(reviewYear));
    }

    return apiClient.post<ExcelImportResult>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_IMPORT,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
  },

  /**
   * 下載匯入範本 (POST + blob 下載，符合資安規範)
   */
  async downloadImportTemplate(): Promise<void> {
    const url = `${API_BASE_URL}${API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_IMPORT_TEMPLATE}`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('下載範本失敗');
    }

    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = 'taoyuan_projects_import_template.xlsx';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  },
};

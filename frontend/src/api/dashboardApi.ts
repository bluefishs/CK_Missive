/**
 * 儀表板 API
 *
 * 提供儀表板統計資料與近期公文查詢
 */

import { apiClient } from './client';
import { API_ENDPOINTS } from './endpoints';
import { logger } from '../services/logger';

// 型別從 types/ 匯入 (SSOT)
import type {
  DashboardStats,
  RecentDocument,
  DashboardResponse,
  FormattedDocument,
  DocumentStats,
} from '../types/api';

// 向後相容 re-export
export type { DashboardStats, RecentDocument, DashboardResponse, FormattedDocument, DocumentStats };

// ============================================================================
// API 方法
// ============================================================================

export const dashboardApi = {
  /**
   * 取得儀表板資料 (統計 + 近期公文)
   */
  async getDashboardData(): Promise<DashboardResponse> {
    try {
      const response = await apiClient.post<DashboardResponse>(API_ENDPOINTS.DASHBOARD.STATS, {});
      return {
        stats: response?.stats || { total: 0, approved: 0, pending: 0, rejected: 0 },
        recent_documents: response?.recent_documents || [],
      };
    } catch (error) {
      logger.error('Dashboard API error:', error);
      return {
        stats: { total: 0, approved: 0, pending: 0, rejected: 0 },
        recent_documents: [],
      };
    }
  },

  /**
   * 格式化近期公文資料 (用於表格顯示)
   */
  formatRecentDocuments(documents: RecentDocument[]): FormattedDocument[] {
    return documents.map((doc, index) => ({
      key: doc.id || index,
      id: doc.doc_number || `DOC-${doc.id}`,
      title: doc.subject || '無標題',
      type: doc.doc_type || '一般公文',
      status: doc.status || '收文完成',
      agency: doc.sender || '未指定機關',
      creator: doc.creator || '系統使用者',
      createDate: doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '',
      deadline: doc.receive_date ? new Date(doc.receive_date).toLocaleDateString() : '',
    }));
  },
};

export default dashboardApi;

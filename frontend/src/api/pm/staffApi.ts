/**
 * PM 案件人員 API 服務
 */

import { apiClient } from '../client';
import type { SuccessResponse, DeleteResponse } from '../types';
import type {
  PMCaseStaff,
  PMCaseStaffCreate,
  PMCaseStaffUpdate,
} from '../../types/pm';
import { PM_ENDPOINTS } from '../endpoints';

export const pmStaffApi = {
  /** 取得案件人員列表 */
  async list(pmCaseId: number): Promise<PMCaseStaff[]> {
    const response = await apiClient.post<SuccessResponse<PMCaseStaff[]>>(
      PM_ENDPOINTS.STAFF_LIST,
      { pm_case_id: pmCaseId }
    );
    return response.data!;
  },

  /** 建立案件人員 */
  async create(data: PMCaseStaffCreate): Promise<PMCaseStaff> {
    const response = await apiClient.post<SuccessResponse<PMCaseStaff>>(
      PM_ENDPOINTS.STAFF_CREATE,
      data
    );
    return response.data!;
  },

  /** 更新案件人員 */
  async update(id: number, data: PMCaseStaffUpdate): Promise<PMCaseStaff> {
    const response = await apiClient.post<SuccessResponse<PMCaseStaff>>(
      PM_ENDPOINTS.STAFF_UPDATE,
      { id, data }
    );
    return response.data!;
  },

  /** 刪除案件人員 */
  async delete(id: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(PM_ENDPOINTS.STAFF_DELETE, { id });
  },
};

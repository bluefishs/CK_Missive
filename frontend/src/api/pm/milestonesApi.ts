/**
 * PM 里程碑 API 服務
 */

import { apiClient } from '../client';
import type { SuccessResponse, DeleteResponse } from '../types';
import type {
  PMMilestone,
  PMMilestoneCreate,
  PMMilestoneUpdate,
} from '../../types/pm';
import { PM_ENDPOINTS } from '../endpoints';

export const pmMilestonesApi = {
  /** 取得案件里程碑列表 */
  async list(pmCaseId: number): Promise<PMMilestone[]> {
    const response = await apiClient.post<SuccessResponse<PMMilestone[]>>(
      PM_ENDPOINTS.MILESTONES_LIST,
      { pm_case_id: pmCaseId }
    );
    return response.data!;
  },

  /** 建立里程碑 */
  async create(data: PMMilestoneCreate): Promise<PMMilestone> {
    const response = await apiClient.post<SuccessResponse<PMMilestone>>(
      PM_ENDPOINTS.MILESTONES_CREATE,
      data
    );
    return response.data!;
  },

  /** 更新里程碑 */
  async update(id: number, data: PMMilestoneUpdate): Promise<PMMilestone> {
    const response = await apiClient.post<SuccessResponse<PMMilestone>>(
      PM_ENDPOINTS.MILESTONES_UPDATE,
      { id, data }
    );
    return response.data!;
  },

  /** 刪除里程碑 */
  async delete(id: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(PM_ENDPOINTS.MILESTONES_DELETE, { id });
  },
};

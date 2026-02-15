/**
 * 專案機關承辦 API
 */
import { apiClient } from './client';
import { API_ENDPOINTS } from './endpoints';

// 從 types/api.ts 匯入統一的型別定義
import {
  ProjectAgencyContact,
  ProjectAgencyContactCreate,
  ProjectAgencyContactUpdate,
} from '../types/api';

// 重新匯出供外部使用
export type { ProjectAgencyContact, ProjectAgencyContactCreate, ProjectAgencyContactUpdate };

/** 專案機關承辦列表回應 */
export interface ProjectAgencyContactListResponse {
  items: ProjectAgencyContact[];
  total: number;
}

// 取得專案的機關承辦列表
export const getProjectAgencyContacts = async (
  projectId: number
): Promise<ProjectAgencyContactListResponse> => {
  return apiClient.post<ProjectAgencyContactListResponse>(
    API_ENDPOINTS.PROJECT_AGENCY_CONTACTS.LIST,
    { project_id: projectId }
  );
};

// 取得單一機關承辦資料
export const getAgencyContact = async (
  contactId: number
): Promise<ProjectAgencyContact> => {
  return apiClient.post<ProjectAgencyContact>(
    API_ENDPOINTS.PROJECT_AGENCY_CONTACTS.DETAIL,
    { contact_id: contactId }
  );
};

// 建立機關承辦
export const createAgencyContact = async (
  data: ProjectAgencyContactCreate
): Promise<ProjectAgencyContact> => {
  return apiClient.post<ProjectAgencyContact>(
    API_ENDPOINTS.PROJECT_AGENCY_CONTACTS.CREATE,
    data
  );
};

// 更新機關承辦
export const updateAgencyContact = async (
  contactId: number,
  data: ProjectAgencyContactUpdate
): Promise<ProjectAgencyContact> => {
  return apiClient.post<ProjectAgencyContact>(
    API_ENDPOINTS.PROJECT_AGENCY_CONTACTS.UPDATE,
    { contact_id: contactId, ...data }
  );
};

// 刪除機關承辦
export const deleteAgencyContact = async (
  contactId: number
): Promise<{ success: boolean; message: string }> => {
  return apiClient.post<{ success: boolean; message: string }>(
    API_ENDPOINTS.PROJECT_AGENCY_CONTACTS.DELETE,
    { contact_id: contactId }
  );
};

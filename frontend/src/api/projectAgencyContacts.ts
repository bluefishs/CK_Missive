/**
 * 專案機關承辦 API
 */
import { apiClient } from './client';

export interface ProjectAgencyContact {
  id: number;
  project_id: number;
  contact_name: string;
  position?: string;
  department?: string;
  phone?: string;
  mobile?: string;
  email?: string;
  is_primary: boolean;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectAgencyContactCreate {
  project_id: number;
  contact_name: string;
  position?: string;
  department?: string;
  phone?: string;
  mobile?: string;
  email?: string;
  is_primary?: boolean;
  notes?: string;
}

export interface ProjectAgencyContactUpdate {
  contact_name?: string;
  position?: string;
  department?: string;
  phone?: string;
  mobile?: string;
  email?: string;
  is_primary?: boolean;
  notes?: string;
}

export interface ProjectAgencyContactListResponse {
  items: ProjectAgencyContact[];
  total: number;
}

// 取得專案的機關承辦列表
export const getProjectAgencyContacts = async (
  projectId: number
): Promise<ProjectAgencyContactListResponse> => {
  return apiClient.post<ProjectAgencyContactListResponse>(
    '/project-agency-contacts/list',
    { project_id: projectId }
  );
};

// 取得單一機關承辦資料
export const getAgencyContact = async (
  contactId: number
): Promise<ProjectAgencyContact> => {
  return apiClient.post<ProjectAgencyContact>(
    '/project-agency-contacts/detail',
    { contact_id: contactId }
  );
};

// 建立機關承辦
export const createAgencyContact = async (
  data: ProjectAgencyContactCreate
): Promise<ProjectAgencyContact> => {
  return apiClient.post<ProjectAgencyContact>(
    '/project-agency-contacts/create',
    data
  );
};

// 更新機關承辦
export const updateAgencyContact = async (
  contactId: number,
  data: ProjectAgencyContactUpdate
): Promise<ProjectAgencyContact> => {
  return apiClient.post<ProjectAgencyContact>(
    '/project-agency-contacts/update',
    { contact_id: contactId, ...data }
  );
};

// 刪除機關承辦
export const deleteAgencyContact = async (
  contactId: number
): Promise<{ success: boolean; message: string }> => {
  return apiClient.post<{ success: boolean; message: string }>(
    '/project-agency-contacts/delete',
    { contact_id: contactId }
  );
};

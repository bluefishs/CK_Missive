import { apiClient } from './config';

// ========== 專案類型定義 ==========

// 後端專案回應格式
interface ProjectResponse {
  id: number;
  project_name: string;
  project_code?: string;
  year: number;
  category?: string;
  status?: string;
  client_agency?: string;
  contract_amount?: number;
  start_date?: string;
  end_date?: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

interface ProjectListResponse {
  projects: ProjectResponse[];
  total: number;
  skip: number;
  limit: number;
}

// 承辦同仁類型
export interface ProjectStaff {
  id: number;
  project_id: number;
  user_id: number;
  user_name: string;
  user_email?: string;
  department?: string;
  phone?: string;
  role?: string;
  is_primary: boolean;
  start_date?: string;
  end_date?: string;
  status?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

interface ProjectStaffListResponse {
  project_id: number;
  project_name: string;
  staff: ProjectStaff[];
  total: number;
}

// 協力廠商類型
export interface ProjectVendor {
  project_id: number;
  vendor_id: number;
  vendor_name: string;
  vendor_code?: string;
  vendor_contact_person?: string;
  vendor_phone?: string;
  vendor_business_type?: string;
  role?: string;
  contract_amount?: number;
  start_date?: string;
  end_date?: string;
  status?: string;
  created_at: string;
  updated_at: string;
}

interface ProjectVendorListResponse {
  project_id: number;
  project_name: string;
  associations: ProjectVendor[];
  total: number;
}

// ========== 專案 API ==========

export const projectsApi = {
  // 獲取專案列表
  getProjects: async (params?: {
    skip?: number;
    limit?: number;
    search?: string;
    year?: number;
    category?: string;
    status?: string;
  }): Promise<ProjectListResponse> => {
    const response = await apiClient.get('/projects', { params });
    return response as unknown as ProjectListResponse;
  },

  // 獲取單個專案
  getProject: async (projectId: number): Promise<ProjectResponse> => {
    const response = await apiClient.get(`/projects/${projectId}`);
    return response as unknown as ProjectResponse;
  },

  // 創建專案
  createProject: async (data: Partial<ProjectResponse>): Promise<ProjectResponse> => {
    const response = await apiClient.post('/projects', data);
    return response as unknown as ProjectResponse;
  },

  // 更新專案
  updateProject: async (projectId: number, data: Partial<ProjectResponse>): Promise<ProjectResponse> => {
    const response = await apiClient.put(`/projects/${projectId}`, data);
    return response as unknown as ProjectResponse;
  },

  // 刪除專案
  deleteProject: async (projectId: number): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}`);
  },

  // 獲取年度選項
  getYears: async (): Promise<{ years: number[] }> => {
    const response = await apiClient.get('/projects/years');
    return response as unknown as { years: number[] };
  },

  // 獲取類別選項
  getCategories: async (): Promise<{ categories: string[] }> => {
    const response = await apiClient.get('/projects/categories');
    return response as unknown as { categories: string[] };
  },

  // 獲取狀態選項
  getStatuses: async (): Promise<{ statuses: string[] }> => {
    const response = await apiClient.get('/projects/statuses');
    return response as unknown as { statuses: string[] };
  },

  // 獲取統計資料
  getStatistics: async (): Promise<any> => {
    const response = await apiClient.get('/projects/statistics');
    return response;
  },
};

// ========== 承辦同仁 API ==========

export const projectStaffApi = {
  // 獲取專案的所有承辦同仁
  getProjectStaff: async (projectId: number): Promise<ProjectStaffListResponse> => {
    const response = await apiClient.get(`/project-staff/project/${projectId}`);
    return response as unknown as ProjectStaffListResponse;
  },

  // 新增承辦同仁
  addStaff: async (data: {
    project_id: number;
    user_id: number;
    role?: string;
    is_primary?: boolean;
    start_date?: string;
    end_date?: string;
    status?: string;
    notes?: string;
  }): Promise<{ message: string; project_id: number; user_id: number }> => {
    const response = await apiClient.post('/project-staff', data);
    return response as unknown as { message: string; project_id: number; user_id: number };
  },

  // 更新承辦同仁
  updateStaff: async (
    projectId: number,
    userId: number,
    data: {
      role?: string;
      is_primary?: boolean;
      start_date?: string;
      end_date?: string;
      status?: string;
      notes?: string;
    }
  ): Promise<{ message: string; project_id: number; user_id: number }> => {
    const response = await apiClient.put(`/project-staff/project/${projectId}/user/${userId}`, data);
    return response as unknown as { message: string; project_id: number; user_id: number };
  },

  // 刪除承辦同仁
  deleteStaff: async (projectId: number, userId: number): Promise<{ message: string }> => {
    const response = await apiClient.delete(`/project-staff/project/${projectId}/user/${userId}`);
    return response as unknown as { message: string };
  },

  // 獲取所有承辦同仁關聯
  getAllAssignments: async (params?: {
    skip?: number;
    limit?: number;
    project_id?: number;
    user_id?: number;
    status?: string;
  }): Promise<{ assignments: any[]; total: number; skip: number; limit: number }> => {
    const response = await apiClient.get('/project-staff', { params });
    return response as unknown as { assignments: any[]; total: number; skip: number; limit: number };
  },
};

// ========== 協力廠商 API ==========

export const projectVendorsApi = {
  // 獲取專案的所有協力廠商
  getProjectVendors: async (projectId: number): Promise<ProjectVendorListResponse> => {
    const response = await apiClient.get(`/project-vendors/project/${projectId}`);
    return response as unknown as ProjectVendorListResponse;
  },

  // 新增協力廠商
  addVendor: async (data: {
    project_id: number;
    vendor_id: number;
    role?: string;
    contract_amount?: number;
    start_date?: string;
    end_date?: string;
    status?: string;
  }): Promise<{ message: string; project_id: number; vendor_id: number }> => {
    const response = await apiClient.post('/project-vendors', data);
    return response as unknown as { message: string; project_id: number; vendor_id: number };
  },

  // 更新協力廠商
  updateVendor: async (
    projectId: number,
    vendorId: number,
    data: {
      role?: string;
      contract_amount?: number;
      start_date?: string;
      end_date?: string;
      status?: string;
    }
  ): Promise<{ message: string; project_id: number; vendor_id: number }> => {
    const response = await apiClient.put(`/project-vendors/project/${projectId}/vendor/${vendorId}`, data);
    return response as unknown as { message: string; project_id: number; vendor_id: number };
  },

  // 刪除協力廠商
  deleteVendor: async (projectId: number, vendorId: number): Promise<{ message: string }> => {
    const response = await apiClient.delete(`/project-vendors/project/${projectId}/vendor/${vendorId}`);
    return response as unknown as { message: string };
  },

  // 獲取所有廠商關聯
  getAllAssociations: async (params?: {
    skip?: number;
    limit?: number;
    project_id?: number;
    vendor_id?: number;
    status?: string;
  }): Promise<{ associations: any[]; total: number; skip: number; limit: number }> => {
    const response = await apiClient.get('/project-vendors', { params });
    return response as unknown as { associations: any[]; total: number; skip: number; limit: number };
  },
};

// ========== 廠商列表 API (用於新增廠商時選擇) ==========

export const vendorsApi = {
  // 獲取廠商列表
  getVendors: async (params?: {
    skip?: number;
    limit?: number;
    search?: string;
  }): Promise<{ vendors: any[]; total: number }> => {
    const response = await apiClient.get('/vendors', { params });
    return response as unknown as { vendors: any[]; total: number };
  },
};

// ========== 使用者列表 API (用於新增同仁時選擇) ==========

export const usersApi = {
  // 獲取使用者列表
  getUsers: async (params?: {
    skip?: number;
    limit?: number;
    search?: string;
  }): Promise<{ users: any[]; total: number }> => {
    const response = await apiClient.get('/users', { params });
    return response as unknown as { users: any[]; total: number };
  },
};

export default projectsApi;

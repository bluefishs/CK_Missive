/**
 * 公文管理API服務
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// 創建axios實例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 請求攔截器
apiClient.interceptors.request.use(
  (config) => {
    console.log('API請求:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('API請求錯誤:', error);
    return Promise.reject(error);
  }
);

// 回應攔截器
apiClient.interceptors.response.use(
  (response) => {
    console.log('API回應:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('API回應錯誤:', error.response?.status, error.response?.data);
    return Promise.reject(error);
  }
);

// 文件相關API
export const documentAPI = {
  // 取得文件列表
  getDocuments: async (params = {}) => {
    const response = await apiClient.get('/documents-enhanced/integrated-search', { params });
    return response.data;
  },

  // 取得單一文件
  getDocument: async (id) => {
    const response = await apiClient.get(`/documents/${id}`);
    return response.data;
  },

  // 建立文件
  createDocument: async (data) => {
    const response = await apiClient.post('/documents/', data);
    return response.data;
  },

  // 更新文件
  updateDocument: async (id, data) => {
    const response = await apiClient.put(`/documents/${id}`, data);
    return response.data;
  },

  // 刪除文件
  deleteDocument: async (id) => {
    const response = await apiClient.delete(`/documents/${id}`);
    return response.data;
  },

  // 匯入CSV
  importCSV: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post('/documents/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // 取得統計資訊
  getStatistics: async () => {
    const response = await apiClient.get('/documents/stats/overview');
    return response.data;
  },

  // 匯出Excel
  exportExcel: async (filters = {}) => {
    const params = new URLSearchParams();
    Object.keys(filters).forEach(key => {
      if (filters[key] !== null && filters[key] !== undefined && filters[key] !== '') {
        params.append(key, filters[key]);
      }
    });

    const response = await apiClient.get(`/documents/export/download?${params.toString()}`, {
      responseType: 'blob',
    });

    // 處理檔案下載
    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    });
    
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `documents_export_${new Date().toISOString().slice(0,10)}.xlsx`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    return { success: true, message: '匯出成功' };
  },
};

export default apiClient;

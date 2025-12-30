import axios from 'axios';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001') + '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API請求錯誤:', error);
    return Promise.reject(error);
  }
);

export const documentService = {
  getDocuments: async (params: any = {}): Promise<any> => {
    // 使用documents-enhanced端點，它已經正常工作且支援CORS
    const response = await api.get('/documents-enhanced/integrated-search', { params });
    return response.data;
  },
  getDocument: async (id: number): Promise<any> => {
    const response = await api.get(`/documents-enhanced/${id}`);
    return response.data;
  },
};

export default api;
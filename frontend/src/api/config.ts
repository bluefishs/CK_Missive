import axios from 'axios';

// API 基本配置 - 使用 Vite 代理
// 當未設定 VITE_API_BASE_URL 時，使用相對路徑透過 Vite proxy
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api`
  : '/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 請求攔截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在這裡添加認證 token
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 響應攔截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    // 處理全局錯誤
    if (error.response?.status === 401) {
      const authDisabled = import.meta.env.VITE_AUTH_DISABLED === 'true';

      if (!authDisabled) {
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
      } else {
        console.log('🔧 Development mode: Ignoring 401 error in apiClient');
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;

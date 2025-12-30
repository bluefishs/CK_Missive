import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios';
import { apiConfig } from './apiConfig';

export class HttpError extends Error {
  public status: number;
  public data?: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'HttpError';
    this.status = status;
    this.data = data;
  }
}

class HttpClient {
  private client: AxiosInstance;

  constructor() {
    const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001') + '/api';

    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        const status = error.response?.status || 500;
        const responseData = error.response?.data as any;
        const message = responseData?.message || error.message;
        const data = error.response?.data;
        throw new HttpError(message, status, data);
      }
    );
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post(url, data, config);
    return response.data;
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete(url, config);
    return response.data;
  }
}

export const httpClient = new HttpClient();
export default httpClient;
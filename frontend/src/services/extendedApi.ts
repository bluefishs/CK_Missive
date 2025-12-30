class ExtendedApiService {
  private baseUrl: string;

  constructor(baseUrl: string = '/api/extended') {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`);
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    return response.json();
  }

  // 承攬案件API
  async getProjects() {
    return this.request('/projects');
  }

  async getProject(id: number) {
    return this.request(`/projects/${id}`);
  }

  // 公文管理API
  async getDocuments() {
    return this.request('/documents');
  }

  async getDocument(id: number) {
    return this.request(`/documents/${id}`);
  }

  // 機關單位API
  async getAgencies() {
    return this.request('/agencies');
  }

  async getAgency(id: number) {
    return this.request(`/agencies/${id}`);
  }

  // 協力廠商API
  async getVendors() {
    return this.request('/vendors');
  }

  async getVendor(id: number) {
    return this.request(`/vendors/${id}`);
  }

  // 統計API
  async getStatistics() {
    return this.request('/stats/overview');
  }
}

export const extendedApiService = new ExtendedApiService();
export default ExtendedApiService;
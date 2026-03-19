/**
 * useDropdownData Hook 單元測試
 * useDropdownData Hook Unit Tests
 *
 * 測試共用下拉選單資料 React Query Hooks
 *
 * 執行方式:
 *   cd frontend && npm run test -- useDropdownData
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import type { Project, User } from '../../types/api';

// ============================================================================
// Mock 資料工廠函數
// ============================================================================

const createMockProject = (overrides: Partial<Project> = {}): Project => ({
  id: 1,
  project_name: '測試專案',
  project_code: 'PRJ-001',
  status: 'in_progress',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

const createMockUser = (overrides: Partial<User> = {}): User => ({
  id: 1,
  username: 'testuser',
  full_name: '測試使用者',
  email: 'test@example.com',
  role: 'user',
  is_active: true,
  is_admin: false,
  created_at: '2026-01-01T00:00:00Z',
  ...overrides,
} as User);

// Mock apiClient
const mockPost = vi.fn();
vi.mock('../../api/client', () => ({
  apiClient: {
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

// Mock endpoints
vi.mock('../../api/endpoints', () => ({
  PROJECTS_ENDPOINTS: {
    LIST: '/projects/list',
  },
  USERS_ENDPOINTS: {
    LIST: '/admin/user-management/list',
  },
}));

// Mock filesApi
vi.mock('../../api/filesApi', () => ({
  filesApi: {
    getStorageInfo: vi.fn(),
  },
}));

// 引入被測試的 hooks (after mocks)
import {
  useProjectsDropdown,
  useUsersDropdown,
  useFileSettings,
} from '../../hooks/business/useDropdownData';

import { filesApi } from '../../api/filesApi';

// 建立測試用 QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

// 建立 wrapper
const createWrapper = () => {
  const queryClient = createTestQueryClient();
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  return Wrapper;
};

// ============================================================================
// useProjectsDropdown Hook 測試
// ============================================================================

describe('useProjectsDropdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return projects list on success (projects key)', async () => {
    const mockProjects = [
      createMockProject({ id: 1, project_name: '專案A' }),
      createMockProject({ id: 2, project_name: '專案B' }),
    ];

    mockPost.mockResolvedValue({ projects: mockProjects });

    const { result } = renderHook(() => useProjectsDropdown(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.projects).toHaveLength(2);
    expect(result.current.projects[0]?.project_name).toBe('專案A');
  });

  it('should return projects list on success (items key)', async () => {
    const mockProjects = [
      createMockProject({ id: 1, project_name: '專案C' }),
    ];

    mockPost.mockResolvedValue({ items: mockProjects });

    const { result } = renderHook(() => useProjectsDropdown(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.projects).toHaveLength(1);
    expect(result.current.projects[0]?.project_name).toBe('專案C');
  });

  it('should return empty array when API returns no data', async () => {
    mockPost.mockResolvedValue({});

    const { result } = renderHook(() => useProjectsDropdown(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.projects).toEqual([]);
  });

  it('should call API with page=1 and limit=100', async () => {
    mockPost.mockResolvedValue({ projects: [] });

    renderHook(() => useProjectsDropdown(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith(
        '/projects/list',
        { page: 1, limit: 100 }
      );
    });
  });

  it('should return empty array on API error', async () => {
    mockPost.mockRejectedValue(new Error('Network Error'));

    const { result } = renderHook(() => useProjectsDropdown(), {
      wrapper: createWrapper(),
    });

    // Even on error, projects should be the default empty array
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.projects).toEqual([]);
  });
});

// ============================================================================
// useUsersDropdown Hook 測試
// ============================================================================

describe('useUsersDropdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return users list on success (users key)', async () => {
    const mockUsers = [
      createMockUser({ id: 1, username: 'user1', full_name: '使用者A' }),
      createMockUser({ id: 2, username: 'user2', full_name: '使用者B' }),
    ];

    mockPost.mockResolvedValue({ users: mockUsers });

    const { result } = renderHook(() => useUsersDropdown(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.users).toHaveLength(2);
    expect(result.current.users[0]?.full_name).toBe('使用者A');
  });

  it('should return users list on success (items key)', async () => {
    const mockUsers = [
      createMockUser({ id: 1, username: 'user3', full_name: '使用者C' }),
    ];

    mockPost.mockResolvedValue({ items: mockUsers });

    const { result } = renderHook(() => useUsersDropdown(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.users).toHaveLength(1);
  });

  it('should return empty array when no data', async () => {
    mockPost.mockResolvedValue({});

    const { result } = renderHook(() => useUsersDropdown(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.users).toEqual([]);
  });

  it('should call API with page=1 and limit=100', async () => {
    mockPost.mockResolvedValue({ users: [] });

    renderHook(() => useUsersDropdown(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith(
        '/admin/user-management/list',
        { page: 1, limit: 100 }
      );
    });
  });
});

// ============================================================================
// useFileSettings Hook 測試
// ============================================================================

describe('useFileSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return file settings from API', async () => {
    vi.mocked(filesApi.getStorageInfo).mockResolvedValue({
      success: true,
      storage_path: '/uploads',
      storage_type: 'local',
      is_network_path: false,
      total_files: 10,
      total_size_mb: 50,
      allowed_extensions: ['.pdf', '.docx', '.xlsx'],
      max_file_size_mb: 100,
    } as never);

    const { result } = renderHook(() => useFileSettings(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.allowedExtensions).toEqual(['.pdf', '.docx', '.xlsx']);
    });

    expect(result.current.maxFileSizeMB).toBe(100);
  });

  it('should return default settings before API response', () => {
    // Make the API call hang forever
    vi.mocked(filesApi.getStorageInfo).mockImplementation(
      () => new Promise(() => {})
    );

    const { result } = renderHook(() => useFileSettings(), {
      wrapper: createWrapper(),
    });

    // Should return defaults while loading
    expect(result.current.allowedExtensions).toEqual(
      ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.png', '.zip']
    );
    expect(result.current.maxFileSizeMB).toBe(50);
  });

  it('should return default settings on API error', async () => {
    vi.mocked(filesApi.getStorageInfo).mockRejectedValue(new Error('API Error'));

    const { result } = renderHook(() => useFileSettings(), {
      wrapper: createWrapper(),
    });

    // Wait for the query to settle
    await waitFor(() => {
      // After error, should still return defaults
      expect(result.current.maxFileSizeMB).toBe(50);
    });

    expect(result.current.allowedExtensions).toEqual(
      ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.png', '.zip']
    );
  });
});

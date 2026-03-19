/**
 * Core Hooks - Unit Tests
 *
 * Tests: useProjectsDropdown, useUsersDropdown, useFileSettings
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { createTestQueryClient } from '../../test/testUtils';

// ============================================================================
// Hoisted mocks
// ============================================================================

const { mockApiClient, mockFilesApi } = vi.hoisted(() => ({
  mockApiClient: {
    get: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({}),
    put: vi.fn().mockResolvedValue({}),
    patch: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue({}),
  },
  mockFilesApi: {
    getStorageInfo: vi.fn().mockResolvedValue({
      allowed_extensions: ['.pdf', '.doc'],
      max_file_size_mb: 25,
    }),
  },
}));

// ============================================================================
// Mocks
// ============================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/client', () => ({
  apiClient: mockApiClient,
}));

vi.mock('../../api/filesApi', () => ({
  filesApi: mockFilesApi,
}));

import {
  useProjectsDropdown,
  useUsersDropdown,
  useFileSettings,
} from '../../hooks/business/useDropdownData';

// ============================================================================
// Helpers
// ============================================================================

function createWrapper() {
  const queryClient = createTestQueryClient();
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  return Wrapper;
}

// ============================================================================
// useProjectsDropdown Tests
// ============================================================================

describe('useProjectsDropdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns empty array initially while loading', () => {
    mockApiClient.post.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useProjectsDropdown(), {
      wrapper: createWrapper(),
    });
    expect(result.current.projects).toEqual([]);
    expect(result.current.isLoading).toBe(true);
  });

  it('returns projects from API response with projects field', async () => {
    const mockProjects = [
      { id: 1, project_name: 'Project A', project_code: 'PA' },
      { id: 2, project_name: 'Project B', project_code: 'PB' },
    ];
    mockApiClient.post.mockResolvedValue({ projects: mockProjects });

    const { result } = renderHook(() => useProjectsDropdown(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.projects).toEqual(mockProjects);
  });

  it('returns projects from API response with items field', async () => {
    const mockProjects = [{ id: 1, project_name: 'Project X' }];
    mockApiClient.post.mockResolvedValue({ items: mockProjects });

    const { result } = renderHook(() => useProjectsDropdown(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.projects).toEqual(mockProjects);
  });

  it('returns empty array when API returns no items', async () => {
    mockApiClient.post.mockResolvedValue({});

    const { result } = renderHook(() => useProjectsDropdown(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.projects).toEqual([]);
  });
});

// ============================================================================
// useUsersDropdown Tests
// ============================================================================

describe('useUsersDropdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns empty array initially while loading', () => {
    mockApiClient.post.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useUsersDropdown(), {
      wrapper: createWrapper(),
    });
    expect(result.current.users).toEqual([]);
    expect(result.current.isLoading).toBe(true);
  });

  it('returns users from API response with users field', async () => {
    const mockUsers = [
      { id: 1, username: 'user1' },
      { id: 2, username: 'user2' },
    ];
    mockApiClient.post.mockResolvedValue({ users: mockUsers });

    const { result } = renderHook(() => useUsersDropdown(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.users).toEqual(mockUsers);
  });

  it('returns users from API response with items field', async () => {
    const mockUsers = [{ id: 1, username: 'admin' }];
    mockApiClient.post.mockResolvedValue({ items: mockUsers });

    const { result } = renderHook(() => useUsersDropdown(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.users).toEqual(mockUsers);
  });
});

// ============================================================================
// useFileSettings Tests
// ============================================================================

describe('useFileSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns default file settings initially', () => {
    const { result } = renderHook(() => useFileSettings(), {
      wrapper: createWrapper(),
    });

    // Before API resolves, returns defaults
    expect(result.current.allowedExtensions).toBeDefined();
    expect(result.current.maxFileSizeMB).toBeDefined();
    expect(Array.isArray(result.current.allowedExtensions)).toBe(true);
  });

  it('returns fetched settings after API resolves', async () => {
    mockFilesApi.getStorageInfo.mockResolvedValue({
      allowed_extensions: ['.pdf', '.doc'],
      max_file_size_mb: 25,
    });

    const { result } = renderHook(() => useFileSettings(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.maxFileSizeMB).toBe(25);
    });

    expect(result.current.allowedExtensions).toEqual(['.pdf', '.doc']);
  });
});

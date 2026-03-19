/**
 * useDocumentOperations Hook Tests
 *
 * Tests for the document operations hook including:
 * - Operation mode detection (view, edit, create, copy)
 * - File validation (extension, size)
 * - Duplicate file detection
 * - File list management
 * - Critical change detection
 * - Attachment operations
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { createTestQueryClient } from '../../test/testUtils';

// ==========================================================================
// Mocks
// ==========================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/client', () => ({
  apiClient: {
    post: vi.fn().mockResolvedValue({ staff: [] }),
    get: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../../api/endpoints', () => ({
  PROJECT_STAFF_ENDPOINTS: {
    PROJECT_LIST: (id: number) => `/project-staff/project/${id}/list`,
  },
}));

const mockGetAttachments = vi.fn().mockResolvedValue([]);
const mockUploadFiles = vi.fn().mockResolvedValue({ success: true, message: '', files: [], errors: [] });
const mockDownloadAttachment = vi.fn().mockResolvedValue(undefined);
const mockDeleteAttachment = vi.fn().mockResolvedValue(undefined);
const mockGetAttachmentBlob = vi.fn().mockResolvedValue(new Blob());

vi.mock('../../api/filesApi', () => ({
  filesApi: {
    getDocumentAttachments: (...args: unknown[]) => mockGetAttachments(...args),
    uploadFiles: (...args: unknown[]) => mockUploadFiles(...args),
    downloadAttachment: (...args: unknown[]) => mockDownloadAttachment(...args),
    deleteAttachment: (...args: unknown[]) => mockDeleteAttachment(...args),
    getAttachmentBlob: (...args: unknown[]) => mockGetAttachmentBlob(...args),
    getFileSettings: vi.fn().mockResolvedValue({
      max_file_size_mb: 50,
      allowed_extensions: ['.pdf', '.doc', '.docx'],
    }),
  },
}));

vi.mock('../../hooks/business/useDropdownData', () => ({
  useProjectsDropdown: vi.fn(() => ({
    projects: [{ id: 1, project_name: 'Project 1' }],
    isLoading: false,
  })),
  useUsersDropdown: vi.fn(() => ({
    users: [{ id: 1, username: 'user1', full_name: 'User One' }],
    isLoading: false,
  })),
  useFileSettings: vi.fn(() => ({
    maxFileSizeMB: 50,
    allowedExtensions: ['.pdf', '.doc', '.docx', '.xls', '.xlsx'],
  })),
}));

// ==========================================================================
// Helpers
// ==========================================================================

function createWrapper() {
  const queryClient = createTestQueryClient();
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  return Wrapper;
}

const mockMessage = {
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
  warning: vi.fn(),
  loading: vi.fn(),
  open: vi.fn(),
  destroy: vi.fn(),
};

async function renderOperationsHook(
  operation: 'view' | 'edit' | 'create' | 'copy' = 'edit',
  document: Record<string, unknown> | null = { id: 1, doc_number: 'DOC-001', subject: 'Test' },
) {
  const mod = await import('../../components/document/operations/useDocumentOperations');
  return renderHook(
    () =>
      mod.useDocumentOperations({
        document: document as Parameters<typeof mod.useDocumentOperations>[0]['document'],
        operation,
        visible: true,
        message: mockMessage as unknown as Parameters<typeof mod.useDocumentOperations>[0]['message'],
      }),
    { wrapper: createWrapper() },
  );
}

// ==========================================================================
// Tests
// ==========================================================================

describe('useDocumentOperations', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // --- Operation mode ---

  it('identifies view mode as read-only', async () => {
    const { result } = await renderOperationsHook('view');
    expect(result.current.isReadOnly).toBe(true);
    expect(result.current.isCreate).toBe(false);
    expect(result.current.isCopy).toBe(false);
  });

  it('identifies create mode', async () => {
    const { result } = await renderOperationsHook('create', null);
    expect(result.current.isCreate).toBe(true);
    expect(result.current.isReadOnly).toBe(false);
    expect(result.current.isCopy).toBe(false);
  });

  it('identifies copy mode', async () => {
    const { result } = await renderOperationsHook('copy');
    expect(result.current.isCopy).toBe(true);
    expect(result.current.isCreate).toBe(false);
    expect(result.current.isReadOnly).toBe(false);
  });

  it('identifies edit mode (not read-only, not create, not copy)', async () => {
    const { result } = await renderOperationsHook('edit');
    expect(result.current.isReadOnly).toBe(false);
    expect(result.current.isCreate).toBe(false);
    expect(result.current.isCopy).toBe(false);
  });

  // --- File validation ---

  it('validates allowed file extensions', async () => {
    const { result } = await renderOperationsHook('edit');
    const validFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    const validation = result.current.validateFile(validFile);
    expect(validation.valid).toBe(true);
  });

  it('rejects disallowed file extensions', async () => {
    const { result } = await renderOperationsHook('edit');
    const invalidFile = new File(['content'], 'test.exe', { type: 'application/octet-stream' });
    const validation = result.current.validateFile(invalidFile);
    expect(validation.valid).toBe(false);
    expect(validation.error).toContain('.exe');
  });

  it('rejects files exceeding size limit', async () => {
    const { result } = await renderOperationsHook('edit');
    // Create a file object that reports a large size
    const largeFile = new File(['x'], 'large.pdf', { type: 'application/pdf' });
    Object.defineProperty(largeFile, 'size', { value: 100 * 1024 * 1024 }); // 100MB
    const validation = result.current.validateFile(largeFile);
    expect(validation.valid).toBe(false);
    expect(validation.error).toContain('超過限制');
  });

  // --- File list management ---

  it('handles file list changes', async () => {
    const { result } = await renderOperationsHook('edit');
    const mockFileList = [
      { uid: '1', name: 'test.pdf', status: 'done' as const },
    ];
    act(() => {
      result.current.handleFileListChange(mockFileList as Parameters<typeof result.current.handleFileListChange>[0]);
    });
    expect(result.current.fileList).toEqual(mockFileList);
  });

  it('removes a file from the list', async () => {
    const { result } = await renderOperationsHook('edit');
    const files = [
      { uid: '1', name: 'a.pdf', status: 'done' as const },
      { uid: '2', name: 'b.pdf', status: 'done' as const },
    ];
    act(() => {
      result.current.handleFileListChange(files as Parameters<typeof result.current.handleFileListChange>[0]);
    });
    act(() => {
      result.current.handleRemoveFile({ uid: '1', name: 'a.pdf' } as Parameters<typeof result.current.handleRemoveFile>[0]);
    });
    expect(result.current.fileList).toHaveLength(1);
    expect(result.current.fileList[0]?.name).toBe('b.pdf');
  });

  it('clears upload errors', async () => {
    const { result } = await renderOperationsHook('edit');
    act(() => {
      result.current.handleClearUploadErrors();
    });
    expect(result.current.uploadErrors).toEqual([]);
  });

  // --- Duplicate detection ---

  it('does not flag duplicates in create mode', async () => {
    const { result } = await renderOperationsHook('create', null);
    const file = new File(['content'], 'existing.pdf', { type: 'application/pdf' });
    const isDuplicate = result.current.handleCheckDuplicate(file);
    expect(isDuplicate).toBe(false);
  });

  // --- Critical change detection ---

  it('detects no changes when original is null', async () => {
    const { result } = await renderOperationsHook('create', null);
    const changes = result.current.detectCriticalChanges(null, { subject: 'New' });
    expect(changes).toEqual([]);
  });

  // --- Initial state ---

  it('returns projects from dropdown hook', async () => {
    const { result } = await renderOperationsHook('edit');
    expect(result.current.cases).toHaveLength(1);
    expect(result.current.cases[0]?.project_name).toBe('Project 1');
  });

  it('returns users from dropdown hook', async () => {
    const { result } = await renderOperationsHook('edit');
    expect(result.current.users).toHaveLength(1);
  });

  it('starts with empty file list', async () => {
    const { result } = await renderOperationsHook('edit');
    expect(result.current.fileList).toEqual([]);
  });

  it('starts with loading false', async () => {
    const { result } = await renderOperationsHook('edit');
    expect(result.current.loading).toBe(false);
    expect(result.current.uploading).toBe(false);
  });
});

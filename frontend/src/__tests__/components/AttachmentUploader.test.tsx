/**
 * AttachmentUploader Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../components/common/attachment/attachmentUtils', () => ({
  validateFile: vi.fn(() => ({ valid: true })),
  DEFAULT_ALLOWED_EXTENSIONS: ['.pdf', '.doc', '.docx', '.xlsx'],
  DEFAULT_MAX_FILE_SIZE_MB: 50,
  formatFileSize: vi.fn((size?: number) => size ? `${(size / 1024).toFixed(1)} KB` : '0 KB'),
}));

// ============================================================================
// Helpers
// ============================================================================

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp><MemoryRouter>{ui}</MemoryRouter></AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

// ============================================================================
// Tests
// ============================================================================

describe('AttachmentUploader', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', async () => {
    const { AttachmentUploader } = await import('../../components/common/attachment/AttachmentUploader');
    const { container } = renderWithProviders(
      <AttachmentUploader fileList={[]} setFileList={vi.fn()} />
    );
    expect(container).toBeTruthy();
  });

  it('renders upload hint text', async () => {
    const { AttachmentUploader } = await import('../../components/common/attachment/AttachmentUploader');
    renderWithProviders(
      <AttachmentUploader fileList={[]} setFileList={vi.fn()} />
    );
    expect(screen.getByText('點擊或拖拽檔案到此區域上傳')).toBeInTheDocument();
  });

  it('renders upload progress when uploading', async () => {
    const { AttachmentUploader } = await import('../../components/common/attachment/AttachmentUploader');
    renderWithProviders(
      <AttachmentUploader
        fileList={[]}
        setFileList={vi.fn()}
        uploading={true}
        uploadProgress={50}
      />
    );
    expect(screen.getByText('正在上傳檔案...')).toBeInTheDocument();
  });

  it('renders upload errors when provided', async () => {
    const { AttachmentUploader } = await import('../../components/common/attachment/AttachmentUploader');
    renderWithProviders(
      <AttachmentUploader
        fileList={[]}
        setFileList={vi.fn()}
        uploadErrors={['File too large']}
      />
    );
    expect(screen.getByText('File too large')).toBeInTheDocument();
  });
});

/**
 * DocumentImport Smoke Test
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

vi.mock('../../components/document/import/useDocumentImport', () => ({
  useDocumentImport: vi.fn(() => ({
    activeTab: 'excel',
    setActiveTab: vi.fn(),
    uploading: false,
    importing: false,
    step: 'upload',
    previewResult: null,
    importResult: null,
    handleReset: vi.fn(),
    handleClose: vi.fn(),
    handleExcelPreview: vi.fn(),
    handleExcelImport: vi.fn(),
    handleCsvUpload: vi.fn(),
    handleDownloadTemplate: vi.fn(),
  })),
}));

vi.mock('../../components/document/import/ImportPreviewCard', () => ({
  ImportPreviewCard: () => <div data-testid="import-preview">Preview</div>,
}));

vi.mock('../../components/document/import/ImportResultCard', () => ({
  ImportResultCard: () => <div data-testid="import-result">Result</div>,
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

describe('DocumentImport', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing when visible', async () => {
    const { DocumentImport } = await import('../../components/document/DocumentImport');
    const { container } = renderWithProviders(
      <DocumentImport visible={true} onClose={vi.fn()} />
    );
    expect(container).toBeTruthy();
  });

  it('renders modal title', async () => {
    const { DocumentImport } = await import('../../components/document/DocumentImport');
    renderWithProviders(
      <DocumentImport visible={true} onClose={vi.fn()} />
    );
    expect(screen.getByText('公文匯入')).toBeInTheDocument();
  });

  it('does not render content when not visible', async () => {
    const { DocumentImport } = await import('../../components/document/DocumentImport');
    renderWithProviders(
      <DocumentImport visible={false} onClose={vi.fn()} />
    );
    expect(screen.queryByText('公文匯入')).not.toBeInTheDocument();
  });
});

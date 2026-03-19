/**
 * DocumentPagination Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import { createTestQueryClient } from '../../test/testUtils';

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

import { DocumentPagination } from '../../components/document/DocumentPagination';

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>{ui}</MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

describe('DocumentPagination', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderWithProviders(
      <DocumentPagination
        page={1}
        limit={20}
        total={100}
        totalPages={5}
        onPageChange={vi.fn()}
        onLimitChange={vi.fn()}
      />,
    );
  });

  it('displays page range text', () => {
    const { getByText } = renderWithProviders(
      <DocumentPagination
        page={1}
        limit={20}
        total={100}
        totalPages={5}
        onPageChange={vi.fn()}
        onLimitChange={vi.fn()}
      />,
    );
    expect(getByText(/顯示第 1 - 20 筆/)).toBeInTheDocument();
  });

  it('displays statistics labels', () => {
    const { getByText } = renderWithProviders(
      <DocumentPagination
        page={1}
        limit={20}
        total={50}
        totalPages={3}
        onPageChange={vi.fn()}
        onLimitChange={vi.fn()}
      />,
    );
    expect(getByText('總計')).toBeInTheDocument();
    expect(getByText('收文')).toBeInTheDocument();
    expect(getByText('發文')).toBeInTheDocument();
  });
});

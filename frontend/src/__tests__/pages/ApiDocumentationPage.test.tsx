/**
 * ApiDocumentationPage Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/client', () => ({
  apiClient: { get: vi.fn().mockResolvedValue({}), post: vi.fn().mockResolvedValue({}) },
  SERVER_BASE_URL: 'http://localhost:8001',
}));

vi.mock('@ck-shared/ui-components', () => ({
  ResponsiveContent: ({ children, ...rest }: { children: React.ReactNode; [k: string]: unknown }) => <div {...rest}>{children}</div>,
}));

vi.mock('swagger-ui-react', () => ({
  default: () => <div data-testid="mock-swagger">SwaggerUI</div>,
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <React.Suspense fallback={<div>Loading...</div>}>{ui}</React.Suspense>
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

describe('ApiDocumentationPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/ApiDocumentationPage');
    renderWithProviders(<mod.default />);
    // Shows loading state or actual content
    const el = screen.queryByText('載入 API 文件中...') || screen.queryByText('API 文件');
    expect(el).not.toBeNull();
  });
});

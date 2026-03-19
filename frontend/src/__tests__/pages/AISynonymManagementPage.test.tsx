/**
 * AISynonymManagementPage Smoke Test
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

vi.mock('../../components/ai/management/SynonymManagementPanel', () => ({
  SynonymManagementContent: () => <div data-testid="mock-synonym-content">SynonymManagement</div>,
  DEFAULT_CATEGORIES: [],
  CATEGORY_COLORS: {},
}));

vi.mock('@ck-shared/ui-components', () => ({
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

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

describe('AISynonymManagementPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/AISynonymManagementPage');
    renderWithProviders(<mod.default />);
    expect(screen.getByTestId('mock-synonym-content')).toBeInTheDocument();
  });
});

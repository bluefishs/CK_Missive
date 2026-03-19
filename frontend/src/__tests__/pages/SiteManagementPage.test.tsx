/**
 * SiteManagementPage Smoke Test
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

vi.mock('../../services/secureApiService', () => ({
  secureApiService: {
    getNavigationItems: vi.fn().mockResolvedValue([]),
    createNavigationItem: vi.fn(),
    updateNavigationItem: vi.fn(),
    deleteNavigationItem: vi.fn(),
  },
}));

vi.mock('../../services/navigationService', () => ({
  navigationService: { getItems: vi.fn().mockResolvedValue([]) },
}));

vi.mock('../../hooks', () => ({
  usePermissions: vi.fn(() => ({
    hasPermission: () => true,
    permissions: ['all'],
    isAdmin: () => true,
    isSuperuser: () => false,
  })),
  useResponsive: vi.fn(() => ({
    isMobile: false, isTablet: false, isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

vi.mock('../../components/site-management/SiteConfigManagement', () => ({
  default: () => <div data-testid="mock-site-config">SiteConfig</div>,
}));

vi.mock('../../pages/SiteManagementPage.css', () => ({}));

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

describe('SiteManagementPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/SiteManagementPage');
    renderWithProviders(<mod.SiteManagementPage />);
    expect(screen.getByText(/網站管理|導覽選單管理/)).toBeInTheDocument();
  });
});

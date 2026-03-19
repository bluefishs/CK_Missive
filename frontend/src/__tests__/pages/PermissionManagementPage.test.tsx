/**
 * PermissionManagementPage Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../components/common', () => ({
  ResponsiveTable: () => <div data-testid="mock-responsive-table">Table</div>,
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('@ck-shared/ui-components', () => ({
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('../../constants/permissions', () => ({
  PERMISSION_CATEGORIES: {
    document: { name: '公文管理', permissions: ['document.read', 'document.write'] },
  },
  USER_ROLES: {
    admin: { name_zh: '管理員', description_zh: '系統管理者', default_permissions: ['all'], can_login: true },
    user: { name_zh: '一般使用者', description_zh: '一般角色', default_permissions: [], can_login: true },
  },
  groupPermissionsByCategory: vi.fn(() => ({})),
  getPermissionLabel: vi.fn((p: string) => p),
  ROLE_ICONS: {},
}));

vi.mock('../../router/types', () => ({
  ROUTES: { ROLE_PERMISSION_DETAIL: '/admin/permissions/:role' },
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

describe('PermissionManagementPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/PermissionManagementPage');
    renderWithProviders(<mod.default />);
    expect(screen.getByText(/角色權限管理|權限管理/)).toBeInTheDocument();
  });
});

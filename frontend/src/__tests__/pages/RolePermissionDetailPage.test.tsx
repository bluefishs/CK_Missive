/**
 * RolePermissionDetailPage Smoke Test
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
  return { ...actual, useNavigate: () => mockNavigate, useParams: () => ({ role: 'admin' }) };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('@ck-shared/ui-components', () => ({
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('../../components/admin/PermissionManager', () => ({
  default: () => <div data-testid="mock-permission-manager">PermissionManager</div>,
}));

vi.mock('../../constants/permissions', () => ({
  USER_ROLES: {
    admin: { name_zh: '管理員', description_zh: '系統管理者', default_permissions: ['all'], can_login: true },
    user: { name_zh: '一般使用者', description_zh: '一般角色', default_permissions: [], can_login: true },
  },
}));

vi.mock('../../router/types', () => ({
  ROUTES: { PERMISSION_MANAGEMENT: '/admin/permissions' },
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

describe('RolePermissionDetailPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/RolePermissionDetailPage');
    renderWithProviders(<mod.default />);
    expect(screen.getAllByText(/管理員|角色權限/).length).toBeGreaterThan(0);
  });
});

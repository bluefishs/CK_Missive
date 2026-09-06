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

// 2026-09-06：頁面的五支 react-query hook 沒 mock ⇒ 永遠 isLoading ⇒ 只看得到「載入中...」。
// ⚠️ 回傳物件要穩定（vi.hoisted 一次建好）：工廠每次 render 回新物件會讓依賴 data 的 useEffect 無限重跑，整支測試卡死。
const rpMocks = vi.hoisted(() => {
  const noop = () => undefined;
  const detail = { data: { role: { role: 'admin', name_zh: '管理員', permissions: [], users: [], user_count: 0, nav_items: [] }, permissions: [], users: [] }, isLoading: false, refetch: noop };
  const avail = { data: { permissions: [], unassigned: [], unassigned_count: 0 } };
  const mut = { mutateAsync: async () => undefined, isPending: false };
  const nav = { data: { tree: [] }, isLoading: false, refetch: noop };
  return { detail, avail, mut, nav };
});
vi.mock('../../hooks/system/useRolePermissions', () => ({
  useRolePermissionsDetail: () => rpMocks.detail,
  useAvailablePermissions: () => rpMocks.avail,
  useUpdateRolePermissions: () => rpMocks.mut,
  useSyncRoleUsers: () => rpMocks.mut,
  useNavTree: () => rpMocks.nav,
}));
vi.mock('../../components/admin/NavTreePermissionEditor', () => ({
  default: () => <div data-testid="mock-nav-tree-editor" />,
}));
vi.mock('../../components/admin/PermissionManager', () => ({
  default: () => <div data-testid="mock-permission-manager">PermissionManager</div>,
}));

vi.mock('../../constants/permissions', async (importOriginal) => ({
  // 2026-09-06 A111：先展開原模組再覆蓋——部分 mock 蓋掉整個 barrel 會讓後來新增的 export 全部消失
  ...(await importOriginal<Record<string, unknown>>()),
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
    expect(screen.getAllByText(/詳細權限設定/ /* 標題＝`${角色名} 詳細權限設定` */).length).toBeGreaterThan(0);
  });
});

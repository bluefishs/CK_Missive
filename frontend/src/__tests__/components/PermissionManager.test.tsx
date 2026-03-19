/**
 * PermissionManager Smoke Test
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

vi.mock('../../constants/permissions', () => ({
  PERMISSION_CATEGORIES: {
    documents: {
      name_zh: '公文管理',
      name_en: 'Documents',
      permissions: [
        { key: 'doc.read', name_zh: '檢視公文', name_en: 'View Documents', description_zh: '可檢視公文', description_en: 'Can view documents' },
        { key: 'doc.write', name_zh: '編輯公文', name_en: 'Edit Documents', description_zh: '可編輯公文', description_en: 'Can edit documents' },
      ],
    },
    admin: {
      name_zh: '系統管理',
      name_en: 'Admin',
      permissions: [
        { key: 'admin.users', name_zh: '使用者管理', name_en: 'User Management', description_zh: '管理使用者', description_en: 'Manage users' },
      ],
    },
  },
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

describe('PermissionManager', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', async () => {
    const { PermissionManager } = await import('../../components/admin/PermissionManager');
    const { container } = renderWithProviders(
      <PermissionManager />
    );
    expect(container).toBeTruthy();
  });

  it('renders permission title', async () => {
    const { PermissionManager } = await import('../../components/admin/PermissionManager');
    renderWithProviders(
      <PermissionManager />
    );
    expect(screen.getByText('權限管理')).toBeInTheDocument();
  });

  it('renders category names', async () => {
    const { PermissionManager } = await import('../../components/admin/PermissionManager');
    renderWithProviders(
      <PermissionManager />
    );
    expect(screen.getByText('公文管理')).toBeInTheDocument();
    expect(screen.getByText('系統管理')).toBeInTheDocument();
  });

  it('renders in readOnly mode without select-all buttons', async () => {
    const { PermissionManager } = await import('../../components/admin/PermissionManager');
    renderWithProviders(
      <PermissionManager readOnly={true} />
    );
    expect(screen.queryByText('全選')).not.toBeInTheDocument();
  });
});

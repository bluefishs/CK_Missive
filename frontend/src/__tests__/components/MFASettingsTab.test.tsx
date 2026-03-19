/**
 * MFASettingsTab Smoke Test
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

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({ mfa_enabled: false, backup_codes_remaining: 0 }),
    put: vi.fn().mockResolvedValue({}),
    patch: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    AUTH: {
      MFA_STATUS: '/auth/mfa/status',
      MFA_SETUP: '/auth/mfa/setup',
      MFA_VERIFY: '/auth/mfa/verify',
      MFA_DISABLE: '/auth/mfa/disable',
    },
  },
}));

import { MFASettingsTab } from '../../components/auth/MFASettingsTab';

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

describe('MFASettingsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderWithProviders(<MFASettingsTab />);
  });

  it('displays MFA heading after loading', async () => {
    const { findByText } = renderWithProviders(<MFASettingsTab />);
    expect(await findByText('雙因素認證 (MFA)')).toBeInTheDocument();
  });
});

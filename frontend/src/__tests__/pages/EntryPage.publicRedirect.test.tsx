/**
 * EntryPage 公網宣告式導向護欄 (L74 / L66 / L67)
 *
 * 鎖定 2026-06-16 SSO 真根因修（commit b2b6ae26 / 9e229a36）：
 *   EntryPage 在「公網 + sessionStore 已認證」時，必須以宣告式 <Navigate> 離開 entry
 *   到 /dashboard（不依賴會被 useEffect cleanup 中斷的 async callback imperative navigate）。
 *   反例症狀：第一次停在 entry、重整才好（last-writer-wins 競態 + 導向被守衛跳過）。
 *
 * 既有 EntryPage.test.tsx 只覆蓋 localhost imperative 路徑（env=localhost）；
 * 本檔補「公網宣告式」路徑（env=public → IS_NGROK_OR_PUBLIC=true → line 318 <Navigate>）。
 *
 * 註：真實「跨子域 ck_employee cookie SSO」需 owner 真實瀏覽器（headless 無法代行），
 *     屬 owner 複驗範疇；本檔以 sessionStore 權威狀態驅動，鎖定前端宣告式導向契約。
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/EntryPage.publicRedirect.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';

const WAIT_OPTS = { timeout: 5000 };

// ── 環境 mock：public → 模組級 ENV_TYPE 在 import 時即為 public（IS_NGROK_OR_PUBLIC=true）──
vi.mock('../../config/env', () => ({
  detectEnvironment: () => 'public',
  isAuthDisabled: () => false,
  GOOGLE_CLIENT_ID: '',
  LINE_LOGIN_CHANNEL_ID: '',
}));

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../pages/EntryPage.css', () => ({}));

// authService：ssoBridge mock 為 null（不打網路）；isAuthenticated 預設 false（改由 sessionStore 驅動）
vi.mock('../../services/authService', () => ({
  __esModule: true,
  default: {
    isAuthenticated: vi.fn(() => false),
    ssoBridge: vi.fn().mockResolvedValue(null),
    getCurrentUser: vi.fn().mockResolvedValue(null),
    getUserInfo: vi.fn(() => null),
    setUserInfo: vi.fn(),
    googleLogin: vi.fn(),
    login: vi.fn(),
  },
}));

import { useSessionStore } from '../../store/sessionStore';
import EntryPage from '../../pages/EntryPage';

function renderAtEntry() {
  return render(
    <ConfigProvider locale={zhTW}>
      <AntApp>
        <MemoryRouter initialEntries={['/entry']}>
          <Routes>
            <Route path="/entry" element={<EntryPage />} />
            <Route path="/dashboard" element={<div>DASHBOARD_MARKER</div>} />
          </Routes>
        </MemoryRouter>
      </AntApp>
    </ConfigProvider>,
  );
}

describe('EntryPage 公網宣告式導向護欄 (L74/L66)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore.setState({ status: 'resolving', user: null });
  });

  it('已認證 + 公網 → 宣告式 Navigate 到 /dashboard（不停留 entry、不迴圈）', async () => {
    useSessionStore.setState({
      status: 'authenticated',
      user: { username: 'u', full_name: 'U' } as never,
    });

    renderAtEntry();

    await waitFor(() => {
      expect(screen.getByText('DASHBOARD_MARKER')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('未認證 + 公網 → 停留 entry（不誤導向 dashboard）', async () => {
    useSessionStore.setState({ status: 'anonymous', user: null });

    renderAtEntry();

    // 停在 entry：入口標題渲染，且未跳到 dashboard
    await waitFor(() => {
      expect(screen.getByText('公文系統入口')).toBeInTheDocument();
    }, WAIT_OPTS);
    expect(screen.queryByText('DASHBOARD_MARKER')).not.toBeInTheDocument();
  });
});

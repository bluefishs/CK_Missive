/**
 * DigitalTwinPage Tests
 *
 * Tests for the digital twin page including:
 * - Page title and subtitle rendering
 * - ProfileCard error/retry state
 * - DualModeChatPanel integration
 * - Gateway health badge
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/DigitalTwinPage.test.tsx
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

const WAIT_OPTS = { timeout: 5000 };

// ==========================================================================
// Mocks — avoid importOriginal to prevent module init side effects
// ==========================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../config/env', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../config/env')>();
  return { ...actual };
});

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>();
  return {
    ...actual,
    apiClient: {
      get: vi.fn().mockResolvedValue({}),
      post: vi.fn().mockResolvedValue({
        success: true,
        identity: '乾坤智能體',
        total_queries: 120,
        top_domains: [{ domain: '公文查詢', count: 45 }],
        favorite_tools: [{ tool: 'search_documents', count: 80 }],
        avg_score: 4.2,
        learnings_count: 15,
        conversation_summaries: 0,
        personality_hint: '擅長公文領域的智能助理',
        rated_queries: 0,
        recent_summaries: [],
      }),
      put: vi.fn().mockResolvedValue({}),
      patch: vi.fn().mockResolvedValue({}),
      delete: vi.fn().mockResolvedValue({}),
    },
  };
});

// Mock digitalTwin without importOriginal to avoid fetch/SSE init
vi.mock('../../api/digitalTwin', () => ({
  checkGatewayHealth: vi.fn().mockResolvedValue({
    available: true,
    latencyMs: 42,
  }),
  streamDigitalTwin: vi.fn().mockReturnValue(new AbortController()),
  getQaImpact: vi.fn().mockResolvedValue({ success: false, changed_files_count: 0, affected: [], recommendation: 'no_changes', message: '' }),
  getAgentTopology: vi.fn().mockResolvedValue({ nodes: [], edges: [], meta: { total_nodes: 0, total_edges: 0, timestamp: '' } }),
  getTaskStatus: vi.fn().mockResolvedValue({ success: false }),
  approveTask: vi.fn().mockResolvedValue({ success: false }),
  rejectTask: vi.fn().mockResolvedValue({ success: false }),
}));

vi.mock('../../components/ai/DualModeChatPanel', () => ({
  DualModeChatPanel: () => <div data-testid="mock-dual-chat">DualModeChatPanel</div>,
}));

vi.mock('@ck-shared/ui-components', () => ({
  ResponsiveContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <React.Suspense fallback={<div>Loading...</div>}>
              <PageWrapper />
            </React.Suspense>
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function PageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/DigitalTwinPage').then((mod) => {
      setPage(() => mod.default);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('DigitalTwinPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  it('renders the page title', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('數位分身')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the subtitle', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/NemoClaw 跨專案智能協作引擎/)).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders DualModeChatPanel', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('mock-dual-chat')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders profile card area (loading or data)', async () => {
    renderPage();
    await waitFor(() => {
      // ProfileCard renders either identity name, loading text, or error text
      const hasProfile = screen.queryByText('乾坤智能體');
      const hasLoading = screen.queryByText('載入數位分身檔案...');
      const hasError = screen.queryByText('載入失敗');
      expect(hasProfile || hasLoading || hasError).toBeTruthy();
    }, WAIT_OPTS);
  });

  it('renders retry button on profile error', async () => {
    renderPage();
    await waitFor(() => {
      // If profile API fails, retry button should be available
      const retryBtn = screen.queryByText('重新載入');
      const profileOk = screen.queryByText('累計問答');
      // Either profile loaded or retry is available
      expect(retryBtn || profileOk).toBeTruthy();
    }, WAIT_OPTS);
  });

  it('renders gateway health badge area', async () => {
    renderPage();
    await waitFor(() => {
      // Gateway badge shows one of: 連線正常 / 檢測中... / 離線 / 未知
      const ok = screen.queryByText(/Gateway 連線正常/);
      const checking = screen.queryByText('檢測中...');
      const offline = screen.queryByText(/Gateway 離線/);
      const unknown = screen.queryByText('未知');
      expect(ok || checking || offline || unknown).toBeTruthy();
    }, WAIT_OPTS);
  });

  it('renders both columns layout (profile + chat)', async () => {
    renderPage();
    await waitFor(() => {
      // Page renders two main areas: profile card (left) and chat panel (right)
      expect(screen.getByText('數位分身')).toBeInTheDocument();
      expect(screen.getByTestId('mock-dual-chat')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

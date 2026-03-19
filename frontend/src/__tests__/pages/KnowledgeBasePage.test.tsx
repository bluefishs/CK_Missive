/**
 * KnowledgeBasePage Tests
 *
 * Tests for the knowledge base browser page including:
 * - Page title rendering
 * - Three tabs render (知識地圖, 架構決策 ADR, 架構圖)
 * - Tab switching
 * - Child tab component rendering
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/KnowledgeBasePage.test.tsx
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

const WAIT_OPTS = { timeout: 5000 };

// ==========================================================================
// Mocks
// ==========================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../pages/knowledgeBase/KnowledgeMapTab', () => ({
  KnowledgeMapTab: () => <div data-testid="knowledge-map-tab">KnowledgeMapContent</div>,
}));

vi.mock('../../pages/knowledgeBase/AdrTab', () => ({
  AdrTab: () => <div data-testid="adr-tab">AdrContent</div>,
}));

vi.mock('../../pages/knowledgeBase/DiagramsTab', () => ({
  DiagramsTab: () => <div data-testid="diagrams-tab">DiagramsContent</div>,
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderKnowledgeBasePage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <React.Suspense fallback={<div>Loading...</div>}>
              <KnowledgeBasePageWrapper />
            </React.Suspense>
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function KnowledgeBasePageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/KnowledgeBasePage').then((mod) => {
      setPage(() => mod.default);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('KnowledgeBasePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the page title', async () => {
    renderKnowledgeBasePage();
    await waitFor(() => {
      expect(screen.getByText('知識庫瀏覽器')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the knowledge map tab label', async () => {
    renderKnowledgeBasePage();
    await waitFor(() => {
      expect(screen.getByText('知識地圖')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the ADR tab label', async () => {
    renderKnowledgeBasePage();
    await waitFor(() => {
      expect(screen.getByText(/架構決策/)).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the diagrams tab label', async () => {
    renderKnowledgeBasePage();
    await waitFor(() => {
      expect(screen.getByText('架構圖')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders KnowledgeMapTab content by default (first tab)', async () => {
    renderKnowledgeBasePage();
    await waitFor(() => {
      expect(screen.getByTestId('knowledge-map-tab')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('switches to ADR tab when clicked', async () => {
    renderKnowledgeBasePage();
    await waitFor(() => {
      expect(screen.getByText(/架構決策/)).toBeInTheDocument();
    }, WAIT_OPTS);

    fireEvent.click(screen.getByText(/架構決策/));
    await waitFor(() => {
      expect(screen.getByTestId('adr-tab')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('switches to diagrams tab when clicked', async () => {
    renderKnowledgeBasePage();
    await waitFor(() => {
      expect(screen.getByText('架構圖')).toBeInTheDocument();
    }, WAIT_OPTS);

    fireEvent.click(screen.getByText('架構圖'));
    await waitFor(() => {
      expect(screen.getByTestId('diagrams-tab')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

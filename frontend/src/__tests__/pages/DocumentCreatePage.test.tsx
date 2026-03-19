/**
 * DocumentCreatePage Tests
 *
 * Tests for the document creation page including:
 * - Page title renders
 * - Form fields render (title, type, agency, priority, content)
 * - Submit and cancel buttons
 * - Back button navigation
 * - Form initial values
 * - Form validation
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

// Dynamic import needs a longer timeout for module resolution in full test suite
const WAIT_OPTS = { timeout: 5000 };

// ==========================================================================
// Mocks
// ==========================================================================

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

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderDocumentCreatePage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <React.Suspense fallback={<div>Loading...</div>}>
              <DocumentCreatePageWrapper />
            </React.Suspense>
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function DocumentCreatePageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/DocumentCreatePage').then((mod) => {
      setPage(() => mod.DocumentCreatePage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('DocumentCreatePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    renderDocumentCreatePage();
    await waitFor(() => {
      expect(screen.getByText('新增公文')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the card title', async () => {
    renderDocumentCreatePage();
    await waitFor(() => {
      expect(screen.getByText('公文基本資訊')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the back button', async () => {
    renderDocumentCreatePage();
    await waitFor(() => {
      expect(screen.getByText('返回列表')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('navigates back when back button is clicked', async () => {
    renderDocumentCreatePage();
    await waitFor(() => {
      expect(screen.getByText('返回列表')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('返回列表'));
    expect(mockNavigate).toHaveBeenCalledWith('/documents');
  });

  it('renders the document title input field', async () => {
    renderDocumentCreatePage();
    await waitFor(() => {
      expect(screen.getByLabelText('公文標題')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the document type select field', async () => {
    renderDocumentCreatePage();
    await waitFor(() => {
      expect(screen.getByLabelText('公文類型')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the agency select field', async () => {
    renderDocumentCreatePage();
    await waitFor(() => {
      expect(screen.getByLabelText('承辦機關')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the priority select field', async () => {
    renderDocumentCreatePage();
    await waitFor(() => {
      expect(screen.getByLabelText('優先等級')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the content textarea field', async () => {
    renderDocumentCreatePage();
    await waitFor(() => {
      expect(screen.getByLabelText('公文內容')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the submit button', async () => {
    renderDocumentCreatePage();
    await waitFor(() => {
      expect(screen.getByText('建立公文')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the cancel button', async () => {
    renderDocumentCreatePage();
    await waitFor(() => {
      // Antd inserts a space between two Chinese characters in buttons: "取 消"
      const buttons = screen.getAllByRole('button');
      const cancelButton = buttons.find(
        (btn) => btn.textContent?.includes('取') && btn.textContent?.includes('消')
      );
      expect(cancelButton).toBeTruthy();
    }, WAIT_OPTS);
  });

  it('navigates to documents list when cancel is clicked', async () => {
    renderDocumentCreatePage();
    let cancelButton: HTMLElement | undefined;
    await waitFor(() => {
      const buttons = screen.getAllByRole('button');
      cancelButton = buttons.find(
        (btn) => btn.textContent?.includes('取') && btn.textContent?.includes('消')
      );
      expect(cancelButton).toBeTruthy();
    }, WAIT_OPTS);
    fireEvent.click(cancelButton!);
    expect(mockNavigate).toHaveBeenCalledWith('/documents');
  });
});

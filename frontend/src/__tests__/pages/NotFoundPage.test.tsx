/**
 * NotFoundPage Tests
 *
 * Tests for the 404 page including:
 * - 404 status display
 * - Error message rendering
 * - Back to home button
 * - Navigation on button click
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/NotFoundPage.test.tsx
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';

const WAIT_OPTS = { timeout: 5000 };

// ==========================================================================
// Mocks
// ==========================================================================

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

// ==========================================================================
// Helpers
// ==========================================================================

function NotFoundPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/NotFoundPage').then((mod) => {
      setPage(() => mod.NotFoundPage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

function renderNotFoundPage() {
  return render(
    <ConfigProvider locale={zhTW}>
      <MemoryRouter>
        <React.Suspense fallback={<div>Loading...</div>}>
          <NotFoundPageWrapper />
        </React.Suspense>
      </MemoryRouter>
    </ConfigProvider>,
  );
}

// ==========================================================================
// Tests
// ==========================================================================

describe('NotFoundPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders 404 title', async () => {
    renderNotFoundPage();
    await waitFor(() => {
      expect(screen.getByText('404')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the error message', async () => {
    renderNotFoundPage();
    await waitFor(() => {
      expect(screen.getByText('抱歉，您要尋找的頁面不存在或已被移除。')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders back to home button', async () => {
    renderNotFoundPage();
    await waitFor(() => {
      expect(screen.getByText('回到首頁')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('navigates to dashboard when clicking back to home button', async () => {
    renderNotFoundPage();
    await waitFor(() => {
      expect(screen.getByText('回到首頁')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('回到首頁'));
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
  });
});

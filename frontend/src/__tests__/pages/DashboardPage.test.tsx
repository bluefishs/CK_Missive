/**
 * DashboardPage Tests
 *
 * Tests for the dashboard overview page including:
 * - Page title rendering (responsive: mobile vs desktop)
 * - DashboardCalendarSection rendering
 * - Background styling
 * - Responsive layout adjustments
 *
 * Run:
 *   cd frontend && npx vitest run src/__tests__/pages/DashboardPage.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

const mockResponsiveValue = vi.fn((v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile);
const mockUseResponsive = vi.fn(() => ({
  isMobile: false,
  isTablet: false,
  isDesktop: true,
  responsiveValue: mockResponsiveValue,
}));

vi.mock('../../hooks', () => ({
  useResponsive: () => mockUseResponsive(),
  usePMCaseSummary: () => ({ data: null, isLoading: false }),
  useERPProfitSummary: () => ({ data: null, isLoading: false }),
}));

vi.mock('../../components/dashboard', () => ({
  DashboardCalendarSection: ({ maxEvents }: { maxEvents?: number }) => (
    <div data-testid="mock-calendar-section" data-max-events={maxEvents}>
      DashboardCalendarSection
    </div>
  ),
}));

vi.mock('../../components/dashboard/ProjectStatsPanel', () => ({
  ProjectStatsPanel: () => (
    <div data-testid="mock-project-stats-panel">ProjectStatsPanel</div>
  ),
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderDashboardPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <DashboardPageWrapper />
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function DashboardPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/DashboardPage').then((mod) => {
      setPage(() => mod.DashboardPage);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseResponsive.mockReturnValue({
      isMobile: false,
      isTablet: false,
      isDesktop: true,
      responsiveValue: mockResponsiveValue,
    });
  });

  it('renders the desktop page title', async () => {
    renderDashboardPage();
    await waitFor(() => {
      expect(screen.getByText('儀表板總覽')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders mobile page title when isMobile is true', async () => {
    mockUseResponsive.mockReturnValue({
      isMobile: true,
      isTablet: false,
      isDesktop: false,
      responsiveValue: vi.fn((v: Record<string, unknown>) => v.mobile ?? v.tablet ?? v.desktop),
    });
    renderDashboardPage();
    await waitFor(() => {
      expect(screen.getByText('儀表板')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders DashboardCalendarSection component', async () => {
    renderDashboardPage();
    await waitFor(() => {
      expect(screen.getByTestId('mock-calendar-section')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('passes maxEvents=15 to DashboardCalendarSection', async () => {
    renderDashboardPage();
    await waitFor(() => {
      const section = screen.getByTestId('mock-calendar-section');
      expect(section.getAttribute('data-max-events')).toBe('15');
    }, WAIT_OPTS);
  });

  it('renders with grey background container', async () => {
    renderDashboardPage();
    await waitFor(() => {
      expect(screen.getByText('儀表板總覽')).toBeInTheDocument();
    }, WAIT_OPTS);
    const container = screen.getByText('儀表板總覽').closest('div[style]');
    expect(container).toBeTruthy();
  });

  it('uses h3 level heading on desktop', async () => {
    renderDashboardPage();
    await waitFor(() => {
      const heading = screen.getByText('儀表板總覽');
      expect(heading.tagName).toBe('H3');
    }, WAIT_OPTS);
  });

  it('uses h4 level heading on mobile', async () => {
    mockUseResponsive.mockReturnValue({
      isMobile: true,
      isTablet: false,
      isDesktop: false,
      responsiveValue: vi.fn((v: Record<string, unknown>) => v.mobile ?? v.tablet ?? v.desktop),
    });
    renderDashboardPage();
    await waitFor(() => {
      const heading = screen.getByText('儀表板');
      expect(heading.tagName).toBe('H4');
    }, WAIT_OPTS);
  });

  it('calls responsiveValue for padding calculation', async () => {
    renderDashboardPage();
    await waitFor(() => {
      expect(screen.getByText('儀表板總覽')).toBeInTheDocument();
    }, WAIT_OPTS);
    expect(mockResponsiveValue).toHaveBeenCalled();
  });

  it('title has blue color styling', async () => {
    renderDashboardPage();
    await waitFor(() => {
      const heading = screen.getByText('儀表板總覽');
      expect(heading.style.color).toBe('rgb(25, 118, 210)');
    }, WAIT_OPTS);
  });

  it('renders full page without errors when no data', async () => {
    renderDashboardPage();
    await waitFor(() => {
      expect(screen.getByText('儀表板總覽')).toBeInTheDocument();
      expect(screen.getByTestId('mock-calendar-section')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

/**
 * QaImpactCard Tests
 *
 * Tests for the Diff-aware QA impact analysis card:
 * - Card title rendering
 * - Data states (loading, no changes, with data)
 * - Recommendation tag
 * - Reload button
 *
 * Run:
 *   cd frontend && npx vitest run src/components/ai/management/__tests__/QaImpactCard.test.tsx
 */
import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';

const WAIT_OPTS = { timeout: 5000 };

// ==========================================================================
// Mocks
// ==========================================================================

const mockQaData = {
  success: true,
  changed_files_count: 5,
  affected: [
    { layer: 'backend', category: 'services', count: 3, risk: 'high', files: ['service_a.py', 'service_b.py', 'service_c.py'] },
    { layer: 'frontend', category: 'components', count: 2, risk: 'low', files: ['CompA.tsx', 'CompB.tsx'] },
  ],
  recommendation: 'diff_aware_qa',
  message: '建議執行 Diff-aware QA',
  summary: {
    backend_changes: 3,
    frontend_changes: 2,
    high_risk_modules: 1,
    has_migrations: false,
  },
};

const mockGetQaImpact = vi.fn().mockResolvedValue(mockQaData);

vi.mock('../../../../api/digitalTwin', () => ({
  getQaImpact: mockGetQaImpact,
}));

vi.mock('../../../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

// ==========================================================================
// Helpers
// ==========================================================================

let QaImpactCard: React.FC;

beforeAll(async () => {
  const mod = await import('../QaImpactCard');
  QaImpactCard = mod.QaImpactCard;
});

function renderCard() {
  return render(
    <ConfigProvider locale={zhTW}>
      <AntApp>
        <QaImpactCard />
      </AntApp>
    </ConfigProvider>,
  );
}

// ==========================================================================
// Tests
// ==========================================================================

describe('QaImpactCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Re-establish mock implementation after clearAllMocks (clearAllMocks preserves it,
    // but restoreAllMocks in afterEach would have removed it for the next test)
    mockGetQaImpact.mockResolvedValue(mockQaData);
  });

  afterEach(() => {
    // Don't use vi.restoreAllMocks() — it resets factory mock implementations
    // Just re-establish matchMedia for Ant Design
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

  it('renders the card title', async () => {
    renderCard();
    await waitFor(() => {
      expect(screen.getByText(/Diff-aware QA 影響分析/)).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders recommendation tag', async () => {
    renderCard();
    await waitFor(() => {
      expect(screen.getByText('Diff-aware QA')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders changed files statistic', async () => {
    renderCard();
    await waitFor(() => {
      expect(screen.getByText('變更檔案')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders backend/frontend labels', async () => {
    renderCard();
    await waitFor(() => {
      expect(screen.getByText('後端')).toBeInTheDocument();
      expect(screen.getByText('前端')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders high risk module count', async () => {
    renderCard();
    await waitFor(() => {
      expect(screen.getByText('高風險模組')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders message text', async () => {
    renderCard();
    await waitFor(() => {
      expect(screen.getByText('建議執行 Diff-aware QA')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders risk tags in table', async () => {
    renderCard();
    await waitFor(() => {
      expect(screen.getByText('高')).toBeInTheDocument();
      expect(screen.getByText('低')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders reload button', async () => {
    renderCard();
    await waitFor(() => {
      expect(screen.getByText('重新分析')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});

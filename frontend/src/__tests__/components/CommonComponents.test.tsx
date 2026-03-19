/**
 * Common Components - Smoke & Interaction Tests
 *
 * Tests: MarkdownRenderer, PageLoading, GlobalApiErrorNotifier
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { App as AntApp } from 'antd';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

// Mock MermaidBlock lazy import
vi.mock('../../components/common/MermaidBlock', () => ({
  default: ({ code }: { code: string }) => (
    <div data-testid="mermaid-block">{code}</div>
  ),
}));

import { MarkdownRenderer } from '../../components/common/MarkdownRenderer';
import { PageLoading } from '../../components/common/PageLoading';
import { apiErrorBus, ApiException } from '../../api/errors';

// Lazy-import GlobalApiErrorNotifier (needs to be after mocks)
import GlobalApiErrorNotifier from '../../components/common/GlobalApiErrorNotifier';

// ============================================================================
// MarkdownRenderer Tests
// ============================================================================

describe('MarkdownRenderer', () => {
  it('renders plain text', () => {
    render(<MarkdownRenderer content="Hello World" />);
    expect(screen.getByText('Hello World')).toBeInTheDocument();
  });

  it('renders headings', () => {
    render(<MarkdownRenderer content="## My Heading" />);
    expect(screen.getByText('My Heading')).toBeInTheDocument();
  });

  it('renders inline code', () => {
    render(<MarkdownRenderer content="Use `console.log` here" />);
    expect(screen.getByText('console.log')).toBeInTheDocument();
  });

  it('renders code blocks with language', () => {
    const content = '```javascript\nconst x = 1;\n```';
    render(<MarkdownRenderer content={content} />);
    expect(screen.getByText('const x = 1;')).toBeInTheDocument();
  });

  it('renders links with target _blank', () => {
    render(<MarkdownRenderer content="[Click](https://example.com)" />);
    const link = screen.getByText('Click');
    expect(link).toBeInTheDocument();
    expect(link.closest('a')).toHaveAttribute('target', '_blank');
  });

  it('renders GFM tables', () => {
    const content = '| A | B |\n|---|---|\n| 1 | 2 |';
    render(<MarkdownRenderer content={content} />);
    expect(screen.getByText('A')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('renders blockquotes', () => {
    render(<MarkdownRenderer content="> Important note" />);
    expect(screen.getByText('Important note')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <MarkdownRenderer content="test" className="custom-class" />
    );
    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('renders bold text', () => {
    render(<MarkdownRenderer content="**bold text**" />);
    expect(screen.getByText('bold text')).toBeInTheDocument();
  });

  it('renders unordered lists', () => {
    const { container } = render(<MarkdownRenderer content={"- item1\n- item2"} />);
    const listItems = container.querySelectorAll('li');
    expect(listItems.length).toBe(2);
  });
});

// ============================================================================
// PageLoading Tests
// ============================================================================

describe('PageLoading', () => {
  it('renders with default message', () => {
    render(<PageLoading />);
    expect(screen.getByText('載入中...')).toBeInTheDocument();
  });

  it('renders with custom message', () => {
    render(<PageLoading message="Loading data..." />);
    expect(screen.getByText('Loading data...')).toBeInTheDocument();
  });

  it('renders a spinner', () => {
    const { container } = render(<PageLoading />);
    expect(container.querySelector('.ant-spin')).toBeInTheDocument();
  });
});

// ============================================================================
// GlobalApiErrorNotifier Tests
// ============================================================================

describe('GlobalApiErrorNotifier', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithApp = () => {
    return render(
      <AntApp>
        <GlobalApiErrorNotifier />
      </AntApp>
    );
  };

  it('renders without crashing (returns null)', () => {
    const { container } = renderWithApp();
    // Component returns null, so AntApp wrapper is present but nothing else
    expect(container).toBeTruthy();
  });

  it('subscribes to apiErrorBus on mount', () => {
    const subscribeSpy = vi.spyOn(apiErrorBus, 'subscribe');
    renderWithApp();
    expect(subscribeSpy).toHaveBeenCalledTimes(1);
    subscribeSpy.mockRestore();
  });

  it('unsubscribes from apiErrorBus on unmount', () => {
    const unsubscribeFn = vi.fn();
    const subscribeSpy = vi.spyOn(apiErrorBus, 'subscribe').mockReturnValue(unsubscribeFn);
    const { unmount } = renderWithApp();
    unmount();
    expect(unsubscribeFn).toHaveBeenCalledTimes(1);
    subscribeSpy.mockRestore();
  });

  it('handles 429 error emission without throwing', () => {
    renderWithApp();
    const error = new ApiException('TOO_MANY_REQUESTS', 'Rate limited', 429);
    expect(() => {
      act(() => {
        apiErrorBus.emit(error);
      });
    }).not.toThrow();
  });

  it('handles 500 error emission without throwing', () => {
    renderWithApp();
    const error = new ApiException('INTERNAL_ERROR', 'Server error', 500);
    expect(() => {
      act(() => {
        apiErrorBus.emit(error);
      });
    }).not.toThrow();
  });

  it('handles 403 error emission without throwing', () => {
    renderWithApp();
    const error = new ApiException('FORBIDDEN', 'No permission', 403);
    expect(() => {
      act(() => {
        apiErrorBus.emit(error);
      });
    }).not.toThrow();
  });

  it('handles network error (status 0) without throwing', () => {
    renderWithApp();
    const error = new ApiException('NETWORK_ERROR', 'Network failed', 0);
    expect(() => {
      act(() => {
        apiErrorBus.emit(error);
      });
    }).not.toThrow();
  });
});

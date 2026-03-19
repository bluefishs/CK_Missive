/**
 * MarkdownRenderer Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../components/common/MermaidBlock', () => ({
  default: ({ code }: { code: string }) => (
    <div data-testid="mermaid-block">{code}</div>
  ),
}));

// ============================================================================
// Helpers
// ============================================================================

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <ConfigProvider locale={zhTW}>
      {ui}
    </ConfigProvider>,
  );
}

// ============================================================================
// Tests
// ============================================================================

describe('MarkdownRenderer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', async () => {
    const { MarkdownRenderer } = await import('../../components/common/MarkdownRenderer');
    const { container } = renderWithProviders(
      <MarkdownRenderer content="Hello World" />
    );
    expect(container).toBeTruthy();
  });

  it('renders plain text content', async () => {
    const { MarkdownRenderer } = await import('../../components/common/MarkdownRenderer');
    renderWithProviders(
      <MarkdownRenderer content="This is a test paragraph." />
    );
    expect(screen.getByText('This is a test paragraph.')).toBeInTheDocument();
  });

  it('renders heading elements', async () => {
    const { MarkdownRenderer } = await import('../../components/common/MarkdownRenderer');
    const { container } = renderWithProviders(
      <MarkdownRenderer content="## Second Level Heading" />
    );
    const heading = container.querySelector('h3'); // h2 in markdown maps to level={3}
    expect(heading).toBeInTheDocument();
  });

  it('renders inline code', async () => {
    const { MarkdownRenderer } = await import('../../components/common/MarkdownRenderer');
    renderWithProviders(
      <MarkdownRenderer content="Use `console.log` for debugging." />
    );
    expect(screen.getByText('console.log')).toBeInTheDocument();
  });

  it('renders links', async () => {
    const { MarkdownRenderer } = await import('../../components/common/MarkdownRenderer');
    renderWithProviders(
      <MarkdownRenderer content="[Click here](https://example.com)" />
    );
    const link = screen.getByText('Click here');
    expect(link).toBeInTheDocument();
    expect(link.closest('a')).toHaveAttribute('href', 'https://example.com');
  });

  it('applies custom className', async () => {
    const { MarkdownRenderer } = await import('../../components/common/MarkdownRenderer');
    const { container } = renderWithProviders(
      <MarkdownRenderer content="test" className="custom-class" />
    );
    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });
});

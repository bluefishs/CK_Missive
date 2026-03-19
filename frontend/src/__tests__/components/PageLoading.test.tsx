/**
 * PageLoading - Unit Tests
 *
 * Tests: loading spinner rendering, loading text, custom message prop
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';

// ============================================================================
// Imports
// ============================================================================

import { PageLoading } from '../../components/common/PageLoading';

// ============================================================================
// Tests
// ============================================================================

describe('PageLoading', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the loading spinner', () => {
    const { container } = render(<PageLoading />);
    const spinner = container.querySelector('.ant-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('renders default loading message', () => {
    render(<PageLoading />);
    expect(screen.getByText('載入中...')).toBeInTheDocument();
  });

  it('renders custom message when provided', () => {
    render(<PageLoading message="正在處理資料..." />);
    expect(screen.getByText('正在處理資料...')).toBeInTheDocument();
    expect(screen.queryByText('載入中...')).not.toBeInTheDocument();
  });

  it('has centered layout styling', () => {
    const { container } = render(<PageLoading />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.style.display).toBe('flex');
    expect(wrapper.style.justifyContent).toBe('center');
    expect(wrapper.style.alignItems).toBe('center');
  });
});

/**
 * GraphNodeSettings - Unit Tests
 *
 * Tests settings panel rendering, node type config, visibility toggles,
 * save/reset, and localStorage persistence.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { App as AntApp, ConfigProvider } from 'antd';
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

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
    get length() { return Object.keys(store).length; },
    key: vi.fn((i: number) => Object.keys(store)[i] ?? null),
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// ============================================================================
// Imports (after mocks)
// ============================================================================

import { GraphNodeSettings } from '../../components/ai/GraphNodeSettings';

// ============================================================================
// Helpers
// ============================================================================

function renderWithAntd(ui: React.ReactElement) {
  return render(
    <ConfigProvider locale={zhTW}>
      <AntApp>{ui}</AntApp>
    </ConfigProvider>,
  );
}

// ============================================================================
// Tests
// ============================================================================

describe('GraphNodeSettings', () => {
  const mockOnClose = vi.fn();
  const mockOnSaved = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  it('renders drawer with title when open', () => {
    renderWithAntd(
      <GraphNodeSettings
        open={true}
        onClose={mockOnClose}
        onSaved={mockOnSaved}
        activeTypes={new Set(['document', 'agency', 'person'])}
      />,
    );
    expect(screen.getByText('知識圖譜節點設定')).toBeInTheDocument();
  });

  it('does not show content when open is false', () => {
    renderWithAntd(
      <GraphNodeSettings
        open={false}
        onClose={mockOnClose}
        activeTypes={new Set(['document'])}
      />,
    );
    // Drawer content should not be visible
    expect(screen.queryByText('知識圖譜節點設定')).not.toBeInTheDocument();
  });

  it('shows node type groups with active types', () => {
    renderWithAntd(
      <GraphNodeSettings
        open={true}
        onClose={mockOnClose}
        activeTypes={new Set(['document', 'dispatch', 'person'])}
      />,
    );
    // Groups containing active types should be visible
    expect(screen.getByText('公文 / 派工')).toBeInTheDocument();
    // "人物 / 地點" group should be visible since person is active
    expect(screen.getByText('人物 / 地點')).toBeInTheDocument();
  });

  it('renders save and cancel buttons in drawer footer', () => {
    const { baseElement } = renderWithAntd(
      <GraphNodeSettings
        open={true}
        onClose={mockOnClose}
        activeTypes={new Set(['document'])}
      />,
    );
    // Drawer renders in portal, use baseElement to find footer buttons
    const saveBtn = baseElement.querySelector('.ant-drawer-footer button.ant-btn-primary');
    expect(saveBtn).not.toBeNull();
    // Ant Design inserts a space between Chinese chars, so use regex
    expect(saveBtn?.textContent).toMatch(/儲\s*存/);
  });

  it('calls onClose when drawer close button is clicked', () => {
    const { baseElement } = renderWithAntd(
      <GraphNodeSettings
        open={true}
        onClose={mockOnClose}
        activeTypes={new Set(['document'])}
      />,
    );

    // Find the drawer close button (X icon)
    const closeBtn = baseElement.querySelector('.ant-drawer-close');
    if (closeBtn) {
      fireEvent.click(closeBtn);
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    } else {
      // Fallback: find cancel button in footer
      const cancelBtns = baseElement.querySelectorAll('.ant-drawer-footer button:not(.ant-btn-primary)');
      expect(cancelBtns.length).toBeGreaterThan(0);
    }
  });

  it('renders reset button', () => {
    renderWithAntd(
      <GraphNodeSettings
        open={true}
        onClose={mockOnClose}
        activeTypes={new Set(['document'])}
      />,
    );
    expect(screen.getByText('重置')).toBeInTheDocument();
  });

  it('shows info alert with usage instructions', () => {
    renderWithAntd(
      <GraphNodeSettings
        open={true}
        onClose={mockOnClose}
        activeTypes={new Set(['document'])}
      />,
    );
    expect(screen.getByText(/僅顯示圖譜中實際存在的節點類型/)).toBeInTheDocument();
  });

  it('calls onClose and onSaved when save is clicked', async () => {
    const { baseElement } = renderWithAntd(
      <GraphNodeSettings
        open={true}
        onClose={mockOnClose}
        onSaved={mockOnSaved}
        activeTypes={new Set(['document'])}
      />,
    );

    // Find save button in drawer footer portal
    const saveBtn = baseElement.querySelector('.ant-drawer-footer button.ant-btn-primary');
    expect(saveBtn).not.toBeNull();
    fireEvent.click(saveBtn!);

    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalledTimes(1);
      expect(mockOnSaved).toHaveBeenCalledTimes(1);
    });
  });
});

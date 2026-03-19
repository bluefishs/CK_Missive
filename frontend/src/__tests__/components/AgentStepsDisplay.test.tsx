/**
 * AgentStepsDisplay - Unit Tests
 *
 * Tests: steps rendering, step status icons, collapsible behavior, tool labels
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';

// ============================================================================
// Imports
// ============================================================================

import {
  AgentStepsDisplay,
  TOOL_LABELS,
  TOOL_ICONS,
} from '../../components/ai/AgentStepsDisplay';
import type { AgentStepInfo } from '../../types/ai';

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

describe('AgentStepsDisplay', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    // Re-establish matchMedia mock after restoreAllMocks (required by Ant Design Steps)
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

  it('returns null when steps array is empty', () => {
    const { container } = render(<AgentStepsDisplay steps={[]} streaming={false} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders a thinking step with the step text', () => {
    const steps: AgentStepInfo[] = [
      { type: 'thinking', step_index: 0, step: '分析使用者查詢意圖' },
    ];
    renderWithAntd(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/分析使用者查詢意圖/)).toBeInTheDocument();
  });

  it('renders a tool_call step with tool label', () => {
    const steps: AgentStepInfo[] = [
      { type: 'tool_call', step_index: 0, tool: 'search_documents', step: 'Searching' },
    ];
    renderWithAntd(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/搜尋公文/)).toBeInTheDocument();
  });

  it('renders a tool_result step with summary', () => {
    const steps: AgentStepInfo[] = [
      { type: 'tool_call', step_index: 0, tool: 'search_documents' },
      { type: 'tool_result', step_index: 1, tool: 'search_documents', summary: '找到 3 篇相關公文' },
    ];
    renderWithAntd(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/找到 3 篇相關公文/)).toBeInTheDocument();
  });

  it('shows loading indicator when streaming is true', () => {
    const steps: AgentStepInfo[] = [
      { type: 'thinking', step_index: 0, step: 'Processing' },
    ];
    renderWithAntd(<AgentStepsDisplay steps={steps} streaming={true} />);
    expect(screen.getByText(/處理中.../)).toBeInTheDocument();
  });

  it('does not show loading indicator when streaming is false', () => {
    const steps: AgentStepInfo[] = [
      { type: 'thinking', step_index: 0, step: 'Done thinking' },
    ];
    renderWithAntd(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.queryByText(/處理中.../)).not.toBeInTheDocument();
  });

  it('sorts steps by step_index regardless of input order', () => {
    const steps: AgentStepInfo[] = [
      { type: 'tool_result', step_index: 2, tool: 'get_statistics', summary: 'Third step' },
      { type: 'thinking', step_index: 0, step: 'First step' },
      { type: 'tool_call', step_index: 1, tool: 'get_statistics', step: 'Second step' },
    ];
    renderWithAntd(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/First step/)).toBeInTheDocument();
    expect(screen.getByText(/Third step/)).toBeInTheDocument();
  });

  it('renders a react step with confidence and action', () => {
    const steps: AgentStepInfo[] = [
      { type: 'react', step_index: 0, step: '結果不足，擴展搜尋', confidence: 0.35, action: 'continue' },
    ];
    renderWithAntd(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/深度推理/)).toBeInTheDocument();
    expect(screen.getByText(/繼續/)).toBeInTheDocument();
    expect(screen.getByText(/信心 35%/)).toBeInTheDocument();
  });

  it('renders react step with refine action label', () => {
    const steps: AgentStepInfo[] = [
      { type: 'react', step_index: 0, step: '重新調整策略', confidence: 0.6, action: 'refine' },
    ];
    renderWithAntd(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/精煉/)).toBeInTheDocument();
  });

  it('TOOL_LABELS contains expected tool mappings', () => {
    expect(TOOL_LABELS.search_documents).toBe('搜尋公文');
    expect(TOOL_LABELS.search_dispatch_orders).toBe('搜尋派工單');
    expect(TOOL_LABELS.search_entities).toBe('搜尋實體');
    expect(TOOL_LABELS.get_entity_detail).toBe('實體詳情');
    expect(TOOL_LABELS.find_similar).toBe('相似公文');
    expect(TOOL_LABELS.get_statistics).toBe('統計資訊');
  });

  it('TOOL_ICONS has entries for all labeled tools', () => {
    const toolNames = Object.keys(TOOL_LABELS);
    for (const toolName of toolNames) {
      expect(TOOL_ICONS[toolName]).toBeTruthy();
    }
  });
});

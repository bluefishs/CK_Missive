/**
 * AgentStepsDisplay 元件測試
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AgentStepsDisplay, TOOL_ICONS, TOOL_LABELS } from '../AgentStepsDisplay';
import type { AgentStepInfo } from '../../../types/ai';

// ── Helpers ──
function createStep(overrides: Partial<AgentStepInfo> & { type: AgentStepInfo['type'] }): AgentStepInfo {
  const { type, ...rest } = overrides;
  return {
    step_index: 0,
    step: '測試步驟',
    type,
    ...rest,
  } as AgentStepInfo;
}

// ── Tests ──
describe('AgentStepsDisplay', () => {
  // ── 基本渲染 ──
  it('空步驟陣列返回 null', () => {
    const { container } = render(<AgentStepsDisplay steps={[]} streaming={false} />);
    expect(container.innerHTML).toBe('');
  });

  it('null/undefined 步驟返回 null', () => {
    const { container } = render(
      <AgentStepsDisplay steps={null as unknown as AgentStepInfo[]} streaming={false} />,
    );
    expect(container.innerHTML).toBe('');
  });

  // ── thinking 步驟 ──
  it('渲染 thinking 步驟', () => {
    const steps: AgentStepInfo[] = [
      createStep({ step_index: 0, type: 'thinking', step: '分析使用者意圖' }),
    ];
    render(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/分析使用者意圖/)).toBeInTheDocument();
  });

  // ── tool_call 步驟 ──
  it('渲染 tool_call 步驟（含工具標籤）', () => {
    const steps: AgentStepInfo[] = [
      createStep({ step_index: 0, type: 'tool_call', tool: 'search_documents', step: '搜尋公文' }),
    ];
    render(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/搜尋公文/)).toBeInTheDocument();
  });

  it('未知工具名稱直接顯示原始名稱', () => {
    const steps: AgentStepInfo[] = [
      createStep({ step_index: 0, type: 'tool_call', tool: 'custom_tool', step: '自訂工具' }),
    ];
    render(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/custom_tool/)).toBeInTheDocument();
  });

  // ── tool_result 步驟 ──
  it('渲染 tool_result 步驟（含摘要）', () => {
    const steps: AgentStepInfo[] = [
      createStep({ step_index: 0, type: 'tool_call', tool: 'search_documents', step: '' }),
      createStep({ step_index: 1, type: 'tool_result', tool: 'search_documents', summary: '找到 5 筆公文' }),
    ];
    render(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/找到 5 筆公文/)).toBeInTheDocument();
  });

  // ── react (深度推理) 步驟 ──
  it('渲染 react 步驟（含信心度與動作）', () => {
    const steps: AgentStepInfo[] = [
      createStep({
        step_index: 0,
        type: 'react',
        step: '判斷是否需要更多資料',
        confidence: 0.85,
        action: 'refine',
      }),
    ];
    render(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/深度推理/)).toBeInTheDocument();
    expect(screen.getByText(/精煉/)).toBeInTheDocument();
    expect(screen.getByText(/85%/)).toBeInTheDocument();
  });

  it('react 步驟 action=answer 顯示「回答」', () => {
    const steps: AgentStepInfo[] = [
      createStep({
        step_index: 0,
        type: 'react',
        step: '已有足夠資訊',
        confidence: 0.95,
        action: 'answer',
      }),
    ];
    render(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/回答/)).toBeInTheDocument();
  });

  // ── 排序 ──
  it('依 step_index 排序顯示', () => {
    const steps: AgentStepInfo[] = [
      createStep({ step_index: 2, type: 'tool_result', tool: 'search_documents', summary: '結果C' }),
      createStep({ step_index: 0, type: 'thinking', step: '步驟A' }),
      createStep({ step_index: 1, type: 'thinking', step: '步驟B' }),
    ];
    const { container } = render(<AgentStepsDisplay steps={steps} streaming={false} />);
    const texts = container.textContent || '';
    const posA = texts.indexOf('步驟A');
    const posB = texts.indexOf('步驟B');
    const posC = texts.indexOf('結果C');
    expect(posA).toBeLessThan(posB);
    expect(posB).toBeLessThan(posC);
  });

  // ── streaming 狀態 ──
  it('streaming=true 時顯示「處理中...」', () => {
    const steps: AgentStepInfo[] = [
      createStep({ step_index: 0, type: 'thinking', step: '分析中' }),
    ];
    render(<AgentStepsDisplay steps={steps} streaming={true} />);
    expect(screen.getByText(/處理中/)).toBeInTheDocument();
  });

  it('streaming=false 時不顯示「處理中...」', () => {
    const steps: AgentStepInfo[] = [
      createStep({ step_index: 0, type: 'thinking', step: '分析中' }),
    ];
    render(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.queryByText(/處理中/)).not.toBeInTheDocument();
  });

  // ── 多步驟混合 ──
  it('正確渲染混合步驟序列', () => {
    const steps: AgentStepInfo[] = [
      createStep({ step_index: 0, type: 'thinking', step: '意圖分析' }),
      createStep({ step_index: 1, type: 'tool_call', tool: 'search_documents', step: '' }),
      createStep({ step_index: 2, type: 'tool_result', tool: 'search_documents', summary: '找到 3 筆' }),
      createStep({ step_index: 3, type: 'react', step: '評估結果', confidence: 0.9, action: 'answer' }),
    ];
    render(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/意圖分析/)).toBeInTheDocument();
    expect(screen.getByText(/找到 3 筆/)).toBeInTheDocument();
    expect(screen.getByText(/深度推理/)).toBeInTheDocument();
  });
});

// ── 常數匯出 ──
describe('TOOL_ICONS & TOOL_LABELS', () => {
  it('TOOL_ICONS 包含 8 個工具', () => {
    expect(Object.keys(TOOL_ICONS)).toHaveLength(8);
  });

  it('TOOL_LABELS 包含 8 個工具標籤', () => {
    expect(Object.keys(TOOL_LABELS)).toHaveLength(8);
    expect(TOOL_LABELS.search_documents).toBe('搜尋公文');
    expect(TOOL_LABELS.get_statistics).toBe('統計資訊');
  });

  it('TOOL_ICONS 與 TOOL_LABELS 鍵集合一致', () => {
    expect(Object.keys(TOOL_ICONS).sort()).toEqual(Object.keys(TOOL_LABELS).sort());
  });
});

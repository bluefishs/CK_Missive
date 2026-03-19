/**
 * GanttTab 單元測試
 *
 * 測試 PM 案件甘特圖頁籤的三種狀態：載入中 / 無資料 / 有資料
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('../../hooks/business/usePMCases', () => ({
  usePMCaseGantt: vi.fn(),
}));

// Mock React.lazy to return a synchronous component for MermaidBlock
vi.mock('../../components/common/MermaidBlock', () => ({
  default: ({ code }: { code: string }) => <div data-testid="mermaid-block">{code}</div>,
}));

import GanttTab from '../../pages/pmCase/GanttTab';
import { usePMCaseGantt } from '../../hooks/business/usePMCases';

describe('GanttTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading spinner', () => {
    vi.mocked(usePMCaseGantt).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as unknown as ReturnType<typeof usePMCaseGantt>);

    render(<GanttTab pmCaseId={1} />);
    expect(screen.getByText('載入甘特圖...')).toBeTruthy();
  });

  it('shows empty when no data', () => {
    vi.mocked(usePMCaseGantt).mockReturnValue({
      data: null,
      isLoading: false,
    } as unknown as ReturnType<typeof usePMCaseGantt>);

    render(<GanttTab pmCaseId={1} />);
    expect(screen.getByText(/尚無里程碑資料/)).toBeTruthy();
  });

  it('renders gantt chart when data exists', () => {
    const ganttCode = 'gantt\n    title Test\n    section M\n    Task1 :done, m1, 2025-01-01, 2025-02-01';
    vi.mocked(usePMCaseGantt).mockReturnValue({
      data: ganttCode,
      isLoading: false,
    } as unknown as ReturnType<typeof usePMCaseGantt>);

    render(<GanttTab pmCaseId={1} />);
    expect(screen.getByText('里程碑甘特圖')).toBeTruthy();
  });
});

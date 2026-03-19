/**
 * CodeWikiFiltersCard 元件測試
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { CodeWikiFiltersCard } from '../CodeWikiFiltersCard';
import type { UseCodeWikiGraphReturn } from '../../../hooks/useCodeWikiGraph';

function createMockGraph(overrides: Partial<UseCodeWikiGraphReturn> = {}): UseCodeWikiGraphReturn {
  return {
    entityTypes: ['py_module', 'py_class'],
    setEntityTypes: vi.fn(),
    modulePrefix: '',
    setModulePrefix: vi.fn(),
    relTypes: [],
    setRelTypes: vi.fn(),
    loading: false,
    loadCodeWiki: vi.fn(),
    codeWikiData: null,
    filteredData: null,
    ...overrides,
  };
}

describe('CodeWikiFiltersCard', () => {
  it('渲染預設標題與載入按鈕', () => {
    render(<CodeWikiFiltersCard graph={createMockGraph()} />);
    expect(screen.getByText('代碼圖譜篩選')).toBeInTheDocument();
    expect(screen.getByText('載入代碼圖譜')).toBeInTheDocument();
  });

  it('自訂標題與按鈕文字', () => {
    render(
      <CodeWikiFiltersCard
        graph={createMockGraph()}
        title="DB 圖譜"
        loadButtonText="載入 DB 圖譜"
      />,
    );
    expect(screen.getByText('DB 圖譜')).toBeInTheDocument();
    expect(screen.getByText('載入 DB 圖譜')).toBeInTheDocument();
  });

  it('顯示實體類型與關聯類型篩選器', () => {
    render(<CodeWikiFiltersCard graph={createMockGraph()} />);
    expect(screen.getByText('實體類型')).toBeInTheDocument();
    expect(screen.getByText('關聯類型篩選')).toBeInTheDocument();
  });

  it('showModulePrefix=true 時顯示模組前綴輸入框', () => {
    render(<CodeWikiFiltersCard graph={createMockGraph()} showModulePrefix={true} />);
    expect(screen.getByText('模組前綴')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('如 app.services.ai')).toBeInTheDocument();
  });

  it('showModulePrefix=false 時隱藏模組前綴', () => {
    render(<CodeWikiFiltersCard graph={createMockGraph()} showModulePrefix={false} />);
    expect(screen.queryByText('模組前綴')).not.toBeInTheDocument();
  });

  it('entityTypes 為空時載入按鈕禁用', () => {
    render(<CodeWikiFiltersCard graph={createMockGraph({ entityTypes: [] })} />);
    const btn = screen.getByText('載入代碼圖譜').closest('button');
    expect(btn).toBeDisabled();
  });

  it('點擊載入按鈕呼叫 loadCodeWiki', async () => {
    const mockGraph = createMockGraph();
    const user = userEvent.setup();
    render(<CodeWikiFiltersCard graph={mockGraph} />);

    await user.click(screen.getByText('載入代碼圖譜'));
    expect(mockGraph.loadCodeWiki).toHaveBeenCalledTimes(1);
  });

  it('有資料時顯示節點/關聯統計', () => {
    const mockGraph = createMockGraph({
      codeWikiData: {
        nodes: [{ id: '1' }, { id: '2' }, { id: '3' }] as never[],
        edges: [{ source: '1', target: '2' }] as never[],
      },
      filteredData: {
        nodes: [{ id: '1' }, { id: '2' }, { id: '3' }] as never[],
        edges: [{ source: '1', target: '2' }] as never[],
      },
    });
    render(<CodeWikiFiltersCard graph={mockGraph} />);
    expect(screen.getByText(/3 個節點/)).toBeInTheDocument();
    expect(screen.getByText(/1 條關聯/)).toBeInTheDocument();
  });

  it('篩選中時顯示「已篩選」標籤', () => {
    const mockGraph = createMockGraph({
      relTypes: ['IMPORTS'],
      codeWikiData: {
        nodes: [{ id: '1' }] as never[],
        edges: [] as never[],
      },
      filteredData: {
        nodes: [{ id: '1' }] as never[],
        edges: [] as never[],
      },
    });
    render(<CodeWikiFiltersCard graph={mockGraph} />);
    expect(screen.getByText(/已篩選/)).toBeInTheDocument();
  });

  it('loading=true 時按鈕顯示 loading 狀態', () => {
    render(<CodeWikiFiltersCard graph={createMockGraph({ loading: true })} />);
    const btn = screen.getByText('載入代碼圖譜').closest('button');
    expect(btn?.classList.contains('ant-btn-loading') || btn?.querySelector('.ant-btn-loading-icon')).toBeTruthy();
  });
});

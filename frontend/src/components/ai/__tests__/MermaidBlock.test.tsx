/**
 * MermaidBlock + parseMermaidBlocks 單元測試
 *
 * 測試 Mermaid 圖表渲染元件與 mermaid 區塊解析函數。
 *
 * 執行方式:
 *   cd frontend && npx vitest run src/components/ai/__tests__/MermaidBlock.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Mock mermaid library (dynamic import)
// ---------------------------------------------------------------------------
const mermaidMock = {
  initialize: vi.fn(),
  render: vi.fn(),
};

vi.mock('mermaid', () => ({
  default: mermaidMock,
}));

// ---------------------------------------------------------------------------
// parseMermaidBlocks tests
// ---------------------------------------------------------------------------
import { parseMermaidBlocks } from '../MessageBubble';

describe('parseMermaidBlocks - Mermaid 區塊解析', () => {
  it('純文字（無 mermaid 區塊）應回傳 null', () => {
    const result = parseMermaidBlocks('這是一段普通文字，沒有任何圖表。');
    expect(result).toBeNull();
  });

  it('空字串應回傳 null', () => {
    const result = parseMermaidBlocks('');
    expect(result).toBeNull();
  });

  it('正確拆分包含一個 mermaid 區塊的文字', () => {
    const input = '前文\n```mermaid\ngraph TD\nA-->B\n```\n後文';
    const result = parseMermaidBlocks(input);

    expect(result).not.toBeNull();
    expect(result).toHaveLength(3);
    expect(result![0]).toEqual({ type: 'text', content: '前文\n' });
    expect(result![1]).toEqual({ type: 'mermaid', content: 'graph TD\nA-->B' });
    expect(result![2]).toEqual({ type: 'text', content: '\n後文' });
  });

  it('正確拆分包含多個 mermaid 區塊的文字', () => {
    const input = '介紹\n```mermaid\nflowchart LR\nA-->B\n```\n中間說明\n```mermaid\nerDiagram\nUSER ||--o{ ORDER : places\n```\n結尾';
    const result = parseMermaidBlocks(input);

    expect(result).not.toBeNull();
    expect(result).toHaveLength(5);
    expect(result![0]).toEqual({ type: 'text', content: '介紹\n' });
    expect(result![1]).toEqual({ type: 'mermaid', content: 'flowchart LR\nA-->B' });
    expect(result![2]).toEqual({ type: 'text', content: '\n中間說明\n' });
    expect(result![3]).toEqual({ type: 'mermaid', content: 'erDiagram\nUSER ||--o{ ORDER : places' });
    expect(result![4]).toEqual({ type: 'text', content: '\n結尾' });
  });

  it('處理空白 mermaid 區塊內容', () => {
    const input = '前文\n```mermaid\n\n```\n後文';
    const result = parseMermaidBlocks(input);

    expect(result).not.toBeNull();
    // Should have text + empty mermaid + text
    const mermaidPart = result!.find(p => p.type === 'mermaid');
    expect(mermaidPart).toBeDefined();
    expect(mermaidPart!.content).toBe('');
  });

  it('保留周圍文字', () => {
    const input = '# 標題\n\n這是分析結果：\n```mermaid\nsequenceDiagram\nA->>B: Hello\n```\n\n以上就是流程。';
    const result = parseMermaidBlocks(input);

    expect(result).not.toBeNull();
    const textParts = result!.filter(p => p.type === 'text');
    const combined = textParts.map(p => p.content).join('');
    expect(combined).toContain('# 標題');
    expect(combined).toContain('這是分析結果：');
    expect(combined).toContain('以上就是流程。');
  });

  it('僅包含 mermaid 區塊（無周圍文字）應正確解析', () => {
    const input = '```mermaid\ngraph TD\nA-->B\n```';
    const result = parseMermaidBlocks(input);

    expect(result).not.toBeNull();
    expect(result).toHaveLength(1);
    expect(result![0]).toEqual({ type: 'mermaid', content: 'graph TD\nA-->B' });
  });

  it('非 mermaid 的 code block 不應被解析', () => {
    const input = '看看這段程式碼：\n```javascript\nconsole.log("hello");\n```\n結束';
    const result = parseMermaidBlocks(input);
    expect(result).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// MermaidBlock component tests
// ---------------------------------------------------------------------------
import MermaidBlock from '../MermaidBlock';

describe('MermaidBlock - Mermaid 圖表渲染元件', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mermaidMock.render.mockResolvedValue({ svg: '<svg><text>rendered</text></svg>' });
  });

  it('接收 chart prop 並呼叫 mermaid.render', async () => {
    const chart = 'graph TD\nA-->B';
    render(<MermaidBlock chart={chart} />);

    await waitFor(() => {
      expect(mermaidMock.initialize).toHaveBeenCalledWith(
        expect.objectContaining({
          startOnLoad: false,
          securityLevel: 'strict',
        }),
      );
      expect(mermaidMock.render).toHaveBeenCalledWith(
        expect.stringContaining('mermaid-'),
        chart,
      );
    });
  });

  it('顯示縮放控制按鈕（放大、縮小、重置）', async () => {
    render(<MermaidBlock chart="graph TD\nA-->B" />);

    await waitFor(() => {
      expect(mermaidMock.render).toHaveBeenCalled();
    });

    // Buttons are identified by title attribute
    expect(screen.getByTitle('放大')).toBeInTheDocument();
    expect(screen.getByTitle('縮小')).toBeInTheDocument();
    expect(screen.getByTitle('重置視圖')).toBeInTheDocument();
  });

  it('顯示下載與複製按鈕', async () => {
    render(<MermaidBlock chart="graph TD\nA-->B" />);

    await waitFor(() => {
      expect(mermaidMock.render).toHaveBeenCalled();
    });

    expect(screen.getByTitle('下載 SVG')).toBeInTheDocument();
    expect(screen.getByTitle('複製 Mermaid 語法')).toBeInTheDocument();
  });

  it('顯示全螢幕按鈕', async () => {
    render(<MermaidBlock chart="graph TD\nA-->B" />);

    await waitFor(() => {
      expect(mermaidMock.render).toHaveBeenCalled();
    });

    expect(screen.getByTitle('全螢幕')).toBeInTheDocument();
  });

  it('顯示縮放百分比 (預設 100%)', async () => {
    render(<MermaidBlock chart="graph TD\nA-->B" />);

    await waitFor(() => {
      expect(mermaidMock.render).toHaveBeenCalled();
    });

    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('mermaid 渲染失敗時顯示錯誤狀態', async () => {
    mermaidMock.render.mockRejectedValue(new Error('Syntax error in graph'));

    render(<MermaidBlock chart="invalid mermaid syntax!!!" />);

    await waitFor(() => {
      expect(screen.getByText(/Mermaid 渲染失敗/)).toBeInTheDocument();
      expect(screen.getByText(/Syntax error in graph/)).toBeInTheDocument();
    });
  });

  it('錯誤狀態下顯示原始 chart 語法', async () => {
    const badChart = 'not-valid-diagram';
    mermaidMock.render.mockRejectedValue(new Error('Parse error'));

    render(<MermaidBlock chart={badChart} />);

    await waitFor(() => {
      expect(screen.getByText(badChart)).toBeInTheDocument();
    });
  });

  it('渲染 title 與 description', async () => {
    render(
      <MermaidBlock
        chart="graph TD\nA-->B"
        title="系統架構圖"
        description="展示系統各模組之間的關係"
      />,
    );

    await waitFor(() => {
      expect(mermaidMock.render).toHaveBeenCalled();
    });

    expect(screen.getByText('系統架構圖')).toBeInTheDocument();
    expect(screen.getByText('展示系統各模組之間的關係')).toBeInTheDocument();
  });

  it('顯示操作提示文字', async () => {
    render(<MermaidBlock chart="graph TD\nA-->B" />);

    await waitFor(() => {
      expect(mermaidMock.render).toHaveBeenCalled();
    });

    expect(screen.getByText(/Ctrl\+滾輪縮放/)).toBeInTheDocument();
  });
});

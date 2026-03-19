/**
 * MessageBubble 單元測試
 *
 * 測試訊息氣泡元件的各種渲染狀態：使用者/助理訊息、streaming、
 * metadata 標籤、回饋按鈕、來源引用、Agent 推理步驟。
 *
 * 執行方式:
 *   cd frontend && npx vitest run src/components/ai/__tests__/MessageBubble.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import type { ChatMessage, RAGSourceItem, AgentStepInfo } from '../../../types/ai';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------
vi.mock('../MermaidBlock', () => ({
  default: ({ chart }: { chart: string }) => (
    <div data-testid="mermaid-block">{chart}</div>
  ),
}));

vi.mock('../AgentStepsDisplay', () => ({
  AgentStepsDisplay: ({ steps, streaming }: { steps: AgentStepInfo[]; streaming: boolean }) => (
    <div data-testid="agent-steps-display" data-streaming={streaming}>
      {steps.length} steps
    </div>
  ),
}));

import { MessageBubble } from '../MessageBubble';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function createMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    role: 'assistant',
    content: '這是一則測試訊息',
    timestamp: new Date('2026-03-15T10:30:00'),
    ...overrides,
  };
}

function createSource(overrides: Partial<RAGSourceItem> = {}): RAGSourceItem {
  return {
    document_id: 1,
    doc_number: 'CK-2026-001',
    subject: '測試公文主旨',
    doc_type: '函',
    category: '收文',
    sender: '桃園市政府',
    receiver: '測試機關',
    doc_date: '2026-03-15',
    similarity: 0.95,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('MessageBubble - 訊息氣泡元件', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // =========================================================================
  // 使用者訊息
  // =========================================================================
  describe('使用者訊息渲染', () => {
    it('顯示使用者角色標示「您」', () => {
      render(<MessageBubble message={createMessage({ role: 'user', content: '你好' })} />);
      expect(screen.getByText(/您/)).toBeInTheDocument();
    });

    it('顯示訊息內容', () => {
      render(<MessageBubble message={createMessage({ role: 'user', content: '查詢公文' })} />);
      expect(screen.getByText('查詢公文')).toBeInTheDocument();
    });

    it('顯示格式化的時間戳', () => {
      render(
        <MessageBubble
          message={createMessage({ role: 'user', content: '你好', timestamp: new Date('2026-03-15T14:30:00') })}
        />,
      );
      // zh-TW 2-digit format: 下午02:30 or 14:30
      expect(screen.getByText(/14:30|02:30/)).toBeInTheDocument();
    });

    it('不顯示 metadata 標籤', () => {
      render(
        <MessageBubble
          message={createMessage({
            role: 'user',
            content: '查詢',
            latency_ms: 500,
            model: 'llama3',
          })}
        />,
      );
      expect(screen.queryByText(/0.5s/)).not.toBeInTheDocument();
      expect(screen.queryByText('llama3')).not.toBeInTheDocument();
    });

    it('不顯示回饋按鈕', () => {
      const onFeedback = vi.fn();
      render(
        <MessageBubble
          message={createMessage({ role: 'user', content: '查詢' })}
          onFeedback={onFeedback}
        />,
      );
      expect(screen.queryByText('回答有幫助嗎？')).not.toBeInTheDocument();
    });

    it('不顯示來源引用', () => {
      render(
        <MessageBubble
          message={createMessage({
            role: 'user',
            content: '查詢',
            sources: [createSource()],
          })}
        />,
      );
      expect(screen.queryByText(/查看.*篇來源公文/)).not.toBeInTheDocument();
    });
  });

  // =========================================================================
  // 助理訊息
  // =========================================================================
  describe('助理訊息渲染', () => {
    it('顯示預設角色名「AI 助理」', () => {
      render(<MessageBubble message={createMessage({ role: 'assistant' })} />);
      expect(screen.getByText(/AI 助理/)).toBeInTheDocument();
    });

    it('顯示自訂 agentIdentity', () => {
      render(
        <MessageBubble
          message={createMessage({ role: 'assistant', agentIdentity: '公文分析師' })}
        />,
      );
      expect(screen.getByText(/公文分析師/)).toBeInTheDocument();
    });

    it('顯示訊息內容並保留空白', () => {
      const content = '第一行\n第二行\n  縮排文字';
      render(<MessageBubble message={createMessage({ content })} />);
      expect(screen.getByText(/第一行/)).toBeInTheDocument();
      expect(screen.getByText(/第二行/)).toBeInTheDocument();
      expect(screen.getByText(/縮排文字/)).toBeInTheDocument();
    });
  });

  // =========================================================================
  // Streaming 狀態
  // =========================================================================
  describe('Streaming 狀態', () => {
    it('streaming 中顯示 loading 圖標', () => {
      const { container } = render(
        <MessageBubble message={createMessage({ streaming: true, content: '正在回答...' })} />,
      );
      // LoadingOutlined renders as an anticon-loading span
      const loadingIcon = container.querySelector('.anticon-loading');
      expect(loadingIcon).toBeInTheDocument();
    });

    it('非 streaming 時不顯示 loading 圖標', () => {
      const { container } = render(
        <MessageBubble message={createMessage({ streaming: false, content: '已完成回答' })} />,
      );
      const loadingIcon = container.querySelector('.anticon-loading');
      expect(loadingIcon).not.toBeInTheDocument();
    });

    it('streaming 時不顯示 metadata 標籤', () => {
      render(
        <MessageBubble
          message={createMessage({
            streaming: true,
            content: '回答中...',
            latency_ms: 1500,
            model: 'llama3',
          })}
        />,
      );
      expect(screen.queryByText(/1.5s/)).not.toBeInTheDocument();
      expect(screen.queryByText('llama3')).not.toBeInTheDocument();
    });

    it('streaming 時不顯示回饋按鈕', () => {
      const onFeedback = vi.fn();
      render(
        <MessageBubble
          message={createMessage({ streaming: true, content: '回答中...' })}
          onFeedback={onFeedback}
        />,
      );
      expect(screen.queryByText('回答有幫助嗎？')).not.toBeInTheDocument();
    });
  });

  // =========================================================================
  // Metadata 標籤
  // =========================================================================
  describe('Metadata 標籤', () => {
    it('顯示延遲時間 (秒)', () => {
      render(
        <MessageBubble message={createMessage({ latency_ms: 2345 })} />,
      );
      expect(screen.getByText('2.3s')).toBeInTheDocument();
    });

    it('顯示模型名稱', () => {
      render(
        <MessageBubble message={createMessage({ latency_ms: 100, model: 'llama3.1' })} />,
      );
      expect(screen.getByText('llama3.1')).toBeInTheDocument();
    });

    it('不顯示 model 為 "none" 或 "error"', () => {
      render(
        <MessageBubble message={createMessage({ latency_ms: 100, model: 'none' })} />,
      );
      expect(screen.queryByText('none')).not.toBeInTheDocument();

      const { unmount } = render(
        <MessageBubble message={createMessage({ latency_ms: 100, model: 'error' })} />,
      );
      expect(screen.queryByText('error')).not.toBeInTheDocument();
      unmount();
    });

    it('顯示引用數量', () => {
      render(
        <MessageBubble message={createMessage({ latency_ms: 100, retrieval_count: 5 })} />,
      );
      expect(screen.getByText('5 篇引用')).toBeInTheDocument();
    });

    it('引用數量為 0 時不顯示', () => {
      render(
        <MessageBubble message={createMessage({ latency_ms: 100, retrieval_count: 0 })} />,
      );
      expect(screen.queryByText(/篇引用/)).not.toBeInTheDocument();
    });

    it('顯示推理輪數', () => {
      render(
        <MessageBubble message={createMessage({ latency_ms: 100, iterations: 3 })} />,
      );
      expect(screen.getByText('3 輪推理')).toBeInTheDocument();
    });

    it('顯示工具使用數量', () => {
      render(
        <MessageBubble
          message={createMessage({
            latency_ms: 100,
            toolsUsed: ['search_documents', 'query_graph', 'get_stats'],
          })}
        />,
      );
      expect(screen.getByText('3 工具')).toBeInTheDocument();
    });

    it('沒有 latency_ms 時不顯示任何 metadata', () => {
      render(
        <MessageBubble
          message={createMessage({
            model: 'llama3',
            retrieval_count: 5,
            iterations: 2,
          })}
        />,
      );
      expect(screen.queryByText('llama3')).not.toBeInTheDocument();
      expect(screen.queryByText(/篇引用/)).not.toBeInTheDocument();
      expect(screen.queryByText(/輪推理/)).not.toBeInTheDocument();
    });
  });

  // =========================================================================
  // 回饋按鈕
  // =========================================================================
  describe('回饋按鈕', () => {
    it('助理訊息完成後顯示回饋提示', () => {
      const onFeedback = vi.fn();
      render(
        <MessageBubble
          message={createMessage({ content: '回答完畢' })}
          onFeedback={onFeedback}
        />,
      );
      expect(screen.getByText('回答有幫助嗎？')).toBeInTheDocument();
    });

    it('點擊讚顯示按鈕觸發 onFeedback(1)', () => {
      const onFeedback = vi.fn();
      render(
        <MessageBubble
          message={createMessage({ content: '回答完畢' })}
          onFeedback={onFeedback}
        />,
      );

      // Get the like button (first button after the text)
      const buttons = screen.getAllByRole('button');
      // Like button should be one of them
      fireEvent.click(buttons[0]!);
      expect(onFeedback).toHaveBeenCalledWith(1);
    });

    it('點擊踩按鈕觸發 onFeedback(-1)', () => {
      const onFeedback = vi.fn();
      render(
        <MessageBubble
          message={createMessage({ content: '回答完畢' })}
          onFeedback={onFeedback}
        />,
      );

      const buttons = screen.getAllByRole('button');
      // Dislike button is the second one
      fireEvent.click(buttons[1]!);
      expect(onFeedback).toHaveBeenCalledWith(-1);
    });

    it('已回饋時按鈕應被禁用並顯示「已回饋」', () => {
      const onFeedback = vi.fn();
      render(
        <MessageBubble
          message={createMessage({ content: '回答完畢', feedbackScore: 1 })}
          onFeedback={onFeedback}
        />,
      );

      expect(screen.getByText('已回饋')).toBeInTheDocument();
      const buttons = screen.getAllByRole('button');
      buttons.forEach((btn) => {
        expect(btn).toBeDisabled();
      });
    });

    it('feedbackScore 為 -1 時按鈕也應被禁用', () => {
      const onFeedback = vi.fn();
      render(
        <MessageBubble
          message={createMessage({ content: '回答完畢', feedbackScore: -1 })}
          onFeedback={onFeedback}
        />,
      );

      expect(screen.getByText('已回饋')).toBeInTheDocument();
    });

    it('沒有 onFeedback 回呼時不顯示回饋區域', () => {
      render(
        <MessageBubble message={createMessage({ content: '回答完畢' })} />,
      );
      expect(screen.queryByText('回答有幫助嗎？')).not.toBeInTheDocument();
    });

    it('空內容時不顯示回饋按鈕', () => {
      const onFeedback = vi.fn();
      render(
        <MessageBubble
          message={createMessage({ content: '' })}
          onFeedback={onFeedback}
        />,
      );
      expect(screen.queryByText('回答有幫助嗎？')).not.toBeInTheDocument();
    });
  });

  // =========================================================================
  // 來源引用
  // =========================================================================
  describe('來源引用', () => {
    it('有來源時顯示可摺疊的來源區域', () => {
      const sources = [createSource(), createSource({ doc_number: 'CK-2026-002', subject: '第二篇' })];
      render(
        <MessageBubble message={createMessage({ sources })} />,
      );
      expect(screen.getByText(/查看 2 篇來源公文/)).toBeInTheDocument();
    });

    it('展開後顯示公文號與主旨', () => {
      const sources = [createSource({ doc_number: 'CK-2026-001', subject: '重要公文主旨' })];
      render(
        <MessageBubble message={createMessage({ sources })} />,
      );

      // Click to expand the collapse
      const collapseHeader = screen.getByText(/查看 1 篇來源公文/);
      fireEvent.click(collapseHeader);

      expect(screen.getByText('CK-2026-001')).toBeInTheDocument();
      expect(screen.getByText('重要公文主旨')).toBeInTheDocument();
    });

    it('顯示來源的相似度百分比', () => {
      const sources = [createSource({ similarity: 0.87 })];
      render(
        <MessageBubble message={createMessage({ sources })} />,
      );

      const collapseHeader = screen.getByText(/查看 1 篇來源公文/);
      fireEvent.click(collapseHeader);

      expect(screen.getByText('87%')).toBeInTheDocument();
    });

    it('相似度為 0 時不顯示百分比標籤', () => {
      const sources = [createSource({ similarity: 0 })];
      render(
        <MessageBubble message={createMessage({ sources })} />,
      );

      const collapseHeader = screen.getByText(/查看 1 篇來源公文/);
      fireEvent.click(collapseHeader);

      expect(screen.queryByText('0%')).not.toBeInTheDocument();
    });

    it('顯示發文者與日期', () => {
      const sources = [createSource({ sender: '新北市政府', doc_date: '2026-01-20' })];
      render(
        <MessageBubble message={createMessage({ sources })} />,
      );

      const collapseHeader = screen.getByText(/查看 1 篇來源公文/);
      fireEvent.click(collapseHeader);

      expect(screen.getByText(/新北市政府/)).toBeInTheDocument();
      expect(screen.getByText(/2026-01-20/)).toBeInTheDocument();
    });

    it('顯示公文類別標籤', () => {
      const sources = [createSource({ doc_type: '書函' })];
      render(
        <MessageBubble message={createMessage({ sources })} />,
      );

      const collapseHeader = screen.getByText(/查看 1 篇來源公文/);
      fireEvent.click(collapseHeader);

      expect(screen.getByText('書函')).toBeInTheDocument();
    });

    it('沒有來源時不顯示來源區域', () => {
      render(<MessageBubble message={createMessage({ sources: [] })} />);
      expect(screen.queryByText(/查看.*篇來源公文/)).not.toBeInTheDocument();
    });

    it('sources 為 undefined 時不顯示來源區域', () => {
      render(<MessageBubble message={createMessage()} />);
      expect(screen.queryByText(/查看.*篇來源公文/)).not.toBeInTheDocument();
    });
  });

  // =========================================================================
  // Agent 推理步驟
  // =========================================================================
  describe('Agent 推理步驟', () => {
    const mockSteps: AgentStepInfo[] = [
      { type: 'thinking', step_index: 0, step: '分析問題' },
      { type: 'tool_call', step_index: 1, tool: 'search_documents', params: { query: '測試' } },
      { type: 'tool_result', step_index: 2, tool: 'search_documents', summary: '找到 5 筆', count: 5 },
    ];

    it('有步驟時顯示可摺疊的推理過程', () => {
      render(
        <MessageBubble message={createMessage({ agentSteps: mockSteps })} />,
      );
      expect(screen.getByText(/推理過程 \(3 步\)/)).toBeInTheDocument();
    });

    it('展開後渲染 AgentStepsDisplay', () => {
      render(
        <MessageBubble message={createMessage({ agentSteps: mockSteps })} />,
      );

      // Click to expand
      const header = screen.getByText(/推理過程/);
      fireEvent.click(header);

      expect(screen.getByTestId('agent-steps-display')).toBeInTheDocument();
      expect(screen.getByText('3 steps')).toBeInTheDocument();
    });

    it('streaming 中且無 content 時傳 streaming=true 給 AgentStepsDisplay', () => {
      render(
        <MessageBubble
          message={createMessage({ agentSteps: mockSteps, streaming: true, content: '' })}
        />,
      );

      // When streaming, defaultActiveKey includes 'steps', so it should be visible
      const stepsDisplay = screen.getByTestId('agent-steps-display');
      expect(stepsDisplay).toHaveAttribute('data-streaming', 'true');
    });

    it('streaming 中有 content 時傳 streaming=false 給 AgentStepsDisplay', () => {
      render(
        <MessageBubble
          message={createMessage({ agentSteps: mockSteps, streaming: true, content: '部分回答' })}
        />,
      );

      // Need to expand since defaultActiveKey=['steps'] only when streaming
      const header = screen.getByText(/推理過程/);
      fireEvent.click(header);

      const stepsDisplay = screen.getByTestId('agent-steps-display');
      expect(stepsDisplay).toHaveAttribute('data-streaming', 'false');
    });

    it('沒有步驟時不顯示推理過程區域', () => {
      render(<MessageBubble message={createMessage({ agentSteps: [] })} />);
      expect(screen.queryByText(/推理過程/)).not.toBeInTheDocument();
    });

    it('agentSteps 為 undefined 時不顯示推理過程區域', () => {
      render(<MessageBubble message={createMessage()} />);
      expect(screen.queryByText(/推理過程/)).not.toBeInTheDocument();
    });
  });

  // =========================================================================
  // Mermaid 區塊渲染
  // =========================================================================
  describe('Mermaid 圖表渲染', () => {
    it('assistant 訊息中的 mermaid 區塊渲染為 MermaidBlock', async () => {
      const content = '分析結果如下：\n```mermaid\ngraph TD\nA-->B\n```\n結束';
      render(<MessageBubble message={createMessage({ content })} />);

      const mermaidBlock = await screen.findByTestId('mermaid-block');
      expect(mermaidBlock).toBeInTheDocument();
      expect(mermaidBlock.textContent).toContain('graph TD');
      expect(mermaidBlock.textContent).toContain('A-->B');
    });

    it('使用者訊息不解析 mermaid 區塊', () => {
      const content = '```mermaid\ngraph TD\nA-->B\n```';
      render(<MessageBubble message={createMessage({ role: 'user', content })} />);

      expect(screen.queryByTestId('mermaid-block')).not.toBeInTheDocument();
      // Content should be rendered as plain text (use regex to avoid exact multiline match issues)
      expect(screen.getByText(/```mermaid/)).toBeInTheDocument();
    });

    it('混合文字與 mermaid 區塊同時渲染', async () => {
      const content = '前文\n```mermaid\nflowchart LR\nX-->Y\n```\n後文';
      render(<MessageBubble message={createMessage({ content })} />);

      expect(screen.getByText(/前文/)).toBeInTheDocument();
      expect(await screen.findByTestId('mermaid-block')).toBeInTheDocument();
      expect(screen.getByText(/後文/)).toBeInTheDocument();
    });
  });

  // =========================================================================
  // Embedded 模式
  // =========================================================================
  describe('Embedded 模式', () => {
    it('embedded=true 時容器寬度較大 (95%)', () => {
      const { container } = render(
        <MessageBubble message={createMessage()} embedded={true} />,
      );
      // The inner div should have maxWidth 95%
      const innerDiv = container.firstChild?.firstChild as HTMLElement;
      expect(innerDiv.style.maxWidth).toBe('95%');
    });

    it('embedded=false (預設) 時容器寬度為 85%', () => {
      const { container } = render(
        <MessageBubble message={createMessage()} />,
      );
      const innerDiv = container.firstChild?.firstChild as HTMLElement;
      expect(innerDiv.style.maxWidth).toBe('85%');
    });
  });

  // =========================================================================
  // 佈局方向
  // =========================================================================
  describe('佈局方向', () => {
    it('使用者訊息靠右對齊', () => {
      const { container } = render(
        <MessageBubble message={createMessage({ role: 'user', content: '你好' })} />,
      );
      const outerDiv = container.firstChild as HTMLElement;
      expect(outerDiv.style.justifyContent).toBe('flex-end');
    });

    it('助理訊息靠左對齊', () => {
      const { container } = render(
        <MessageBubble message={createMessage({ role: 'assistant' })} />,
      );
      const outerDiv = container.firstChild as HTMLElement;
      expect(outerDiv.style.justifyContent).toBe('flex-start');
    });
  });

  // =========================================================================
  // 氣泡樣式
  // =========================================================================
  describe('氣泡樣式', () => {
    it('使用者訊息使用藍色背景', () => {
      const { container } = render(
        <MessageBubble message={createMessage({ role: 'user', content: '你好' })} />,
      );
      // The bubble div (second level child with background)
      const bubbleDiv = container.querySelector('[style*="background"]') as HTMLElement;
      expect(bubbleDiv?.style.background).toBe('rgb(230, 247, 255)');
    });

    it('助理訊息使用白色背景', () => {
      const { container } = render(
        <MessageBubble message={createMessage({ role: 'assistant' })} />,
      );
      const bubbleDiv = container.querySelector('[style*="background"]') as HTMLElement;
      expect(bubbleDiv?.style.background).toBe('rgb(255, 255, 255)');
    });
  });

  // =========================================================================
  // 邊界情境
  // =========================================================================
  describe('邊界情境', () => {
    it('空內容的助理訊息正常渲染', () => {
      const { container } = render(
        <MessageBubble message={createMessage({ content: '' })} />,
      );
      expect(container.firstChild).toBeInTheDocument();
    });

    it('同時有所有 metadata 欄位時正確渲染', () => {
      render(
        <MessageBubble
          message={createMessage({
            latency_ms: 3200,
            model: 'mixtral-8x7b',
            retrieval_count: 8,
            iterations: 4,
            toolsUsed: ['search', 'graph_query'],
          })}
        />,
      );

      expect(screen.getByText('3.2s')).toBeInTheDocument();
      expect(screen.getByText('mixtral-8x7b')).toBeInTheDocument();
      expect(screen.getByText('8 篇引用')).toBeInTheDocument();
      expect(screen.getByText('4 輪推理')).toBeInTheDocument();
      expect(screen.getByText('2 工具')).toBeInTheDocument();
    });

    it('有 agentSteps + sources + feedback 同時渲染', () => {
      const steps: AgentStepInfo[] = [
        { type: 'thinking', step_index: 0, step: '分析' },
      ];
      const sources = [createSource()];
      const onFeedback = vi.fn();

      render(
        <MessageBubble
          message={createMessage({
            content: '完整回答',
            agentSteps: steps,
            sources,
            latency_ms: 1000,
          })}
          onFeedback={onFeedback}
        />,
      );

      expect(screen.getByText(/推理過程 \(1 步\)/)).toBeInTheDocument();
      expect(screen.getByText(/查看 1 篇來源公文/)).toBeInTheDocument();
      expect(screen.getByText('回答有幫助嗎？')).toBeInTheDocument();
      expect(screen.getByText('1.0s')).toBeInTheDocument();
    });
  });
});

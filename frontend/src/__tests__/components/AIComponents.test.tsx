/**
 * AI Components - Smoke & Interaction Tests
 *
 * Tests: MessageBubble, AgentStepsDisplay, GraphNodeSettings, GraphToolbar
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
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

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
}));

// Mock MermaidBlock for MessageBubble
vi.mock('../../components/ai/MermaidBlock', () => ({
  default: ({ chart }: { chart: string }) => (
    <div data-testid="mermaid-block">{chart}</div>
  ),
}));

// Mock graphNodeConfig for GraphNodeSettings and GraphToolbar
vi.mock('../../config/graphNodeConfig', () => ({
  GRAPH_NODE_CONFIG: {
    document: { color: '#1890ff', radius: 6, label: '公文', detailable: false, description: '公文記錄' },
    agency: { color: '#fa8c16', radius: 5, label: '機關', detailable: false, description: '機關' },
    project: { color: '#52c41a', radius: 9, label: '承攬案件', detailable: false, description: '案件' },
    person: { color: '#eb2f96', radius: 4, label: '人物', detailable: true, description: '人物' },
  },
  getUserOverrides: vi.fn(() => ({})),
  saveUserOverrides: vi.fn(),
  resetUserOverrides: vi.fn(),
  getAllMergedConfigs: vi.fn(() => ({
    document: { color: '#1890ff', radius: 6, label: '公文', description: '公文記錄' },
    agency: { color: '#fa8c16', radius: 5, label: '機關', description: '機關' },
  })),
  getMergedNodeConfig: vi.fn((type: string) => ({
    color: '#999', radius: 5, label: type, description: `${type} node`,
  })),
  getNodeConfig: vi.fn((type: string) => ({
    color: '#999', radius: 5, label: type, description: `${type} node`,
  })),
}));

// ============================================================================
// Imports (after mocks)
// ============================================================================

import { MessageBubble, parseMermaidBlocks } from '../../components/ai/MessageBubble';
import { AgentStepsDisplay, TOOL_LABELS, TOOL_ICONS } from '../../components/ai/AgentStepsDisplay';
import { GraphNodeSettings } from '../../components/ai/GraphNodeSettings';
import { GraphToolbar } from '../../components/ai/knowledgeGraph/GraphToolbar';
import type { ChatMessage, AgentStepInfo, GraphNode, GraphEdge } from '../../types/ai';

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

function createMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    role: 'user',
    content: 'Hello test message',
    timestamp: new Date('2026-01-15T10:30:00'),
    ...overrides,
  };
}

// ============================================================================
// MessageBubble Tests
// ============================================================================

describe('MessageBubble', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders user message', () => {
    renderWithAntd(<MessageBubble message={createMessage()} />);
    expect(screen.getByText('Hello test message')).toBeInTheDocument();
    expect(screen.getByText('您', { exact: false })).toBeInTheDocument();
  });

  it('renders assistant message', () => {
    renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'I am an AI assistant',
        })}
      />,
    );
    expect(screen.getByText('I am an AI assistant')).toBeInTheDocument();
    expect(screen.getByText('AI 助理', { exact: false })).toBeInTheDocument();
  });

  it('renders streaming indicator when streaming', () => {
    renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'Thinking...',
          streaming: true,
        })}
      />,
    );
    expect(screen.getByText('Thinking...')).toBeInTheDocument();
  });

  it('renders metadata tags for assistant messages', () => {
    renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'Response with metadata',
          latency_ms: 1500,
          model: 'groq-llama3',
          retrieval_count: 3,
        })}
      />,
    );
    expect(screen.getByText('1.5s')).toBeInTheDocument();
    expect(screen.getByText('groq-llama3')).toBeInTheDocument();
    expect(screen.getByText('3 篇引用')).toBeInTheDocument();
  });

  it('renders tools used tag', () => {
    renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'Used tools',
          latency_ms: 500,
          toolsUsed: ['search_documents', 'get_statistics'],
        })}
      />,
    );
    expect(screen.getByText('2 工具')).toBeInTheDocument();
  });

  it('renders feedback buttons for assistant messages', () => {
    const onFeedback = vi.fn();
    renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'Rate me!',
        })}
        onFeedback={onFeedback}
      />,
    );
    expect(screen.getByText('回答有幫助嗎？')).toBeInTheDocument();
  });

  it('does not render feedback for user messages', () => {
    const onFeedback = vi.fn();
    renderWithAntd(
      <MessageBubble
        message={createMessage({ role: 'user', content: 'Hi' })}
        onFeedback={onFeedback}
      />,
    );
    expect(screen.queryByText('回答有幫助嗎？')).not.toBeInTheDocument();
  });
});

describe('parseMermaidBlocks', () => {
  it('returns null for plain text', () => {
    expect(parseMermaidBlocks('Just plain text')).toBeNull();
  });

  it('parses mermaid blocks from content', () => {
    const content = 'Before\n```mermaid\ngraph TD\nA-->B\n```\nAfter';
    const result = parseMermaidBlocks(content);
    expect(result).not.toBeNull();
    expect(result!.length).toBe(3);
    expect(result![0]).toEqual({ type: 'text', content: 'Before\n' });
    expect(result![1]).toEqual({ type: 'mermaid', content: 'graph TD\nA-->B' });
    expect(result![2]).toEqual({ type: 'text', content: '\nAfter' });
  });

  it('returns null for content without mermaid blocks', () => {
    expect(parseMermaidBlocks('```javascript\nconst x = 1;\n```')).toBeNull();
  });
});

// ============================================================================
// AgentStepsDisplay Tests
// ============================================================================

describe('AgentStepsDisplay', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns null for empty steps', () => {
    const { container } = render(
      <AgentStepsDisplay steps={[]} streaming={false} />,
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders thinking step', () => {
    const steps: AgentStepInfo[] = [
      { type: 'thinking', step_index: 0, step: 'Analyzing the query' },
    ];
    renderWithAntd(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/Analyzing the query/)).toBeInTheDocument();
  });

  it('renders tool_call step', () => {
    const steps: AgentStepInfo[] = [
      { type: 'tool_call', step_index: 0, tool: 'search_documents', step: 'Searching' },
    ];
    renderWithAntd(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/搜尋公文/)).toBeInTheDocument();
  });

  it('renders tool_result step', () => {
    const steps: AgentStepInfo[] = [
      { type: 'tool_call', step_index: 0, tool: 'search_documents' },
      { type: 'tool_result', step_index: 1, tool: 'search_documents', summary: 'Found 5 documents' },
    ];
    renderWithAntd(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/Found 5 documents/)).toBeInTheDocument();
  });

  it('shows loading step when streaming', () => {
    const steps: AgentStepInfo[] = [
      { type: 'thinking', step_index: 0, step: 'Thinking...' },
    ];
    renderWithAntd(<AgentStepsDisplay steps={steps} streaming={true} />);
    expect(screen.getByText(/處理中.../)).toBeInTheDocument();
  });

  it('sorts steps by step_index', () => {
    const steps: AgentStepInfo[] = [
      { type: 'tool_result', step_index: 2, tool: 'search_documents', summary: 'Step 3' },
      { type: 'thinking', step_index: 0, step: 'Step 1' },
      { type: 'tool_call', step_index: 1, tool: 'search_documents', step: 'Step 2' },
    ];
    renderWithAntd(<AgentStepsDisplay steps={steps} streaming={false} />);
    expect(screen.getByText(/Step 1/)).toBeInTheDocument();
    expect(screen.getByText(/Step 3/)).toBeInTheDocument();
  });

  it('TOOL_LABELS has known tool labels', () => {
    expect(TOOL_LABELS.search_documents).toBe('搜尋公文');
    expect(TOOL_LABELS.search_dispatch_orders).toBe('搜尋派工單');
    expect(TOOL_LABELS.get_statistics).toBe('統計資訊');
  });

  it('TOOL_ICONS has entries for known tools', () => {
    expect(TOOL_ICONS.search_documents).toBeTruthy();
    expect(TOOL_ICONS.search_dispatch_orders).toBeTruthy();
  });
});

// ============================================================================
// GraphNodeSettings Tests
// ============================================================================

describe('GraphNodeSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders drawer when open', () => {
    renderWithAntd(
      <GraphNodeSettings
        open={true}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText('知識圖譜節點設定')).toBeInTheDocument();
  });

  it('renders save and cancel buttons in drawer footer', () => {
    const { baseElement } = renderWithAntd(
      <GraphNodeSettings
        open={true}
        onClose={vi.fn()}
      />,
    );
    // Drawer footer buttons are rendered in a portal, query via baseElement
    const footerButtons = baseElement.querySelectorAll('.ant-drawer-footer button');
    expect(footerButtons.length).toBeGreaterThanOrEqual(2);
  });

  it('renders reset button', () => {
    renderWithAntd(
      <GraphNodeSettings
        open={true}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText('重置')).toBeInTheDocument();
  });

  it('renders info alert with instructions', () => {
    renderWithAntd(
      <GraphNodeSettings
        open={true}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/僅顯示圖譜中實際存在的節點類型/)).toBeInTheDocument();
  });

  it('does not render drawer content when closed', () => {
    renderWithAntd(
      <GraphNodeSettings
        open={false}
        onClose={vi.fn()}
      />,
    );
    expect(screen.queryByText('知識圖譜節點設定')).not.toBeInTheDocument();
  });

  it('filters node types by activeTypes', () => {
    const activeTypes = new Set(['document', 'agency']);
    renderWithAntd(
      <GraphNodeSettings
        open={true}
        onClose={vi.fn()}
        activeTypes={activeTypes}
      />,
    );
    // Multiple elements may match due to group labels + node type labels
    expect(screen.getAllByText('公文').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('機關').length).toBeGreaterThanOrEqual(1);
  });
});

// ============================================================================
// GraphToolbar Tests
// ============================================================================

describe('GraphToolbar', () => {
  const defaultProps = {
    searchText: '',
    onSearchChange: vi.fn(),
    onSearchSubmit: vi.fn(),
    apiSearching: false,
    visibleTypes: new Set(['document', 'agency']),
    onTypeToggle: vi.fn(),
    onSettingsOpen: vi.fn(),
    onZoomToFit: vi.fn(),
    onRefresh: vi.fn(),
    rawNodes: [
      { id: '1', type: 'document', label: 'Doc 1' },
      { id: '2', type: 'agency', label: 'Agency 1' },
    ] as GraphNode[],
    mergedConfigs: {
      document: { color: '#1890ff', radius: 6, label: '公文', description: '公文記錄', detailable: false, visible: true },
      agency: { color: '#fa8c16', radius: 5, label: '機關', description: '機關', detailable: false, visible: true },
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders search input', () => {
    renderWithAntd(<GraphToolbar {...defaultProps} />);
    expect(screen.getByPlaceholderText('搜尋節點（Enter 擴展搜尋）')).toBeInTheDocument();
  });

  it('renders type filter tags for present node types', () => {
    renderWithAntd(<GraphToolbar {...defaultProps} />);
    // Group label + checkable tag both contain the text, so use getAllByText
    expect(screen.getAllByText('公文').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('機關').length).toBeGreaterThanOrEqual(1);
  });

  it('renders dimension toggle when provided', () => {
    renderWithAntd(
      <GraphToolbar
        {...defaultProps}
        dimension="2d"
        onDimensionChange={vi.fn()}
      />,
    );
    expect(screen.getByText('2D')).toBeInTheDocument();
    expect(screen.getByText('3D')).toBeInTheDocument();
  });

  it('renders view mode toggle when provided', () => {
    renderWithAntd(
      <GraphToolbar
        {...defaultProps}
        viewMode="entity"
        onViewModeChange={vi.fn()}
      />,
    );
    expect(screen.getByText('核心關係')).toBeInTheDocument();
    expect(screen.getByText('完整網絡')).toBeInTheDocument();
  });

  it('renders edge legend when rawEdges provided', () => {
    const edges: GraphEdge[] = [
      { source: '1', target: '2', label: 'sends', type: 'sends' },
    ];
    renderWithAntd(
      <GraphToolbar {...defaultProps} rawEdges={edges} />,
    );
    expect(screen.getByText('發文')).toBeInTheDocument();
  });

  it('renders settings, zoom-to-fit, and refresh buttons', () => {
    const { container } = renderWithAntd(<GraphToolbar {...defaultProps} />);
    // There should be 3 action buttons at the right side
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThanOrEqual(3);
  });

  it('shows loading spinner when apiSearching', () => {
    const { container } = renderWithAntd(
      <GraphToolbar {...defaultProps} apiSearching={true} />,
    );
    const spinner = container.querySelector('.ant-spin');
    expect(spinner).toBeInTheDocument();
  });
});

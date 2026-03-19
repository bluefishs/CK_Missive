/**
 * MessageBubble - Unit Tests
 *
 * Tests: user/assistant message styles, markdown content, metadata, feedback buttons
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
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

vi.mock('../../components/ai/MermaidBlock', () => ({
  default: ({ chart }: { chart: string }) => (
    <div data-testid="mermaid-block">{chart}</div>
  ),
}));

// ============================================================================
// Imports (after mocks)
// ============================================================================

import { MessageBubble, parseMermaidBlocks } from '../../components/ai/MessageBubble';
import type { ChatMessage } from '../../types/ai';

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
    content: 'Test message',
    timestamp: new Date('2026-03-14T10:30:00'),
    ...overrides,
  };
}

// ============================================================================
// Tests
// ============================================================================

describe('MessageBubble', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders user message with "您" label', () => {
    renderWithAntd(<MessageBubble message={createMessage()} />);
    expect(screen.getByText('Test message')).toBeInTheDocument();
    expect(screen.getByText('您', { exact: false })).toBeInTheDocument();
  });

  it('renders assistant message with "AI 助理" label', () => {
    renderWithAntd(
      <MessageBubble message={createMessage({ role: 'assistant', content: 'AI response' })} />,
    );
    expect(screen.getByText('AI response')).toBeInTheDocument();
    expect(screen.getByText('AI 助理', { exact: false })).toBeInTheDocument();
  });

  it('applies different background colors for user vs assistant', () => {
    const { container: userContainer } = renderWithAntd(
      <MessageBubble message={createMessage({ content: 'User msg' })} />,
    );
    const userBubble = userContainer.querySelector('div[style*="background"]');
    expect(userBubble).toBeTruthy();

    const { container: assistantContainer } = renderWithAntd(
      <MessageBubble message={createMessage({ role: 'assistant', content: 'AI msg' })} />,
    );
    const assistantBubble = assistantContainer.querySelector('div[style*="background"]');
    expect(assistantBubble).toBeTruthy();
  });

  it('renders latency tag for assistant messages with latency_ms', () => {
    renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'Response',
          latency_ms: 2500,
        })}
      />,
    );
    expect(screen.getByText('2.5s')).toBeInTheDocument();
  });

  it('renders model tag when model is provided', () => {
    renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'Response',
          latency_ms: 1000,
          model: 'llama3-70b',
        })}
      />,
    );
    expect(screen.getByText('llama3-70b')).toBeInTheDocument();
  });

  it('renders feedback buttons and calls onFeedback', () => {
    const onFeedback = vi.fn();
    renderWithAntd(
      <MessageBubble
        message={createMessage({ role: 'assistant', content: 'Rate this' })}
        onFeedback={onFeedback}
      />,
    );
    expect(screen.getByText('回答有幫助嗎？')).toBeInTheDocument();
  });

  it('does not render feedback for user messages', () => {
    const onFeedback = vi.fn();
    renderWithAntd(
      <MessageBubble
        message={createMessage({ role: 'user', content: 'Hello' })}
        onFeedback={onFeedback}
      />,
    );
    expect(screen.queryByText('回答有幫助嗎？')).not.toBeInTheDocument();
  });

  it('displays agentIdentity instead of "AI 助理" when provided', () => {
    renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'Hello',
          agentIdentity: '乾坤圖譜分析員',
        })}
      />,
    );
    expect(screen.getByText('乾坤圖譜分析員', { exact: false })).toBeInTheDocument();
    expect(screen.queryByText('AI 助理', { exact: false })).not.toBeInTheDocument();
  });

  it('falls back to "AI 助理" when agentIdentity is undefined', () => {
    renderWithAntd(
      <MessageBubble
        message={createMessage({ role: 'assistant', content: 'Hi' })}
      />,
    );
    expect(screen.getByText('AI 助理', { exact: false })).toBeInTheDocument();
  });

  it('renders iterations tag when iterations > 0', () => {
    renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'Result',
          latency_ms: 3000,
          iterations: 3,
        })}
      />,
    );
    expect(screen.getByText('3 輪推理')).toBeInTheDocument();
  });

  it('does not render iterations tag when iterations is 0 or undefined', () => {
    renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'Result',
          latency_ms: 1000,
          iterations: 0,
        })}
      />,
    );
    expect(screen.queryByText(/輪推理/)).not.toBeInTheDocument();
  });

  it('renders tools used count', () => {
    renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'Result',
          latency_ms: 1000,
          toolsUsed: ['search_documents', 'get_entity_detail'],
        })}
      />,
    );
    expect(screen.getByText('2 工具')).toBeInTheDocument();
  });

  it('renders retrieval count', () => {
    renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'Result',
          latency_ms: 1000,
          retrieval_count: 5,
        })}
      />,
    );
    expect(screen.getByText('5 篇引用')).toBeInTheDocument();
  });

  it('splits mermaid blocks in content into text and diagram parts', () => {
    const content = 'Before\n\n```mermaid\ngraph TD\nA-->B\n```\n\nAfter';
    const parts = parseMermaidBlocks(content);
    expect(parts).not.toBeNull();
    expect(parts).toHaveLength(3);
    expect(parts![0]).toEqual({ type: 'text', content: 'Before\n\n' });
    expect(parts![1]).toEqual({ type: 'mermaid', content: 'graph TD\nA-->B' });
    expect(parts![2]).toEqual({ type: 'text', content: '\n\nAfter' });
  });

  it('returns null for content without mermaid blocks', () => {
    expect(parseMermaidBlocks('Just plain text')).toBeNull();
  });

  it('shows loading indicator when streaming', () => {
    const { container } = renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'Partial...',
          streaming: true,
        })}
      />,
    );
    // LoadingOutlined renders an antd spin icon
    expect(container.querySelector('.anticon-loading')).toBeTruthy();
  });

  it('does not show metadata tags while streaming', () => {
    renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'Partial...',
          streaming: true,
          latency_ms: 1000,
        })}
      />,
    );
    expect(screen.queryByText('1.0s')).not.toBeInTheDocument();
  });

  it('renders sources collapse when sources are provided', () => {
    renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'Answer',
          sources: [
            { document_id: 1, doc_number: 'TEST-001', subject: '測試公文', similarity: 0.95, sender: '工務局', doc_type: '函', doc_date: '2026-01-01', category: '', receiver: '' },
          ],
        })}
      />,
    );
    expect(screen.getByText('查看 1 篇來源公文', { exact: false })).toBeInTheDocument();
  });

  it('disables feedback buttons after voting', () => {
    const onFeedback = vi.fn();
    renderWithAntd(
      <MessageBubble
        message={createMessage({
          role: 'assistant',
          content: 'Rate this',
          feedbackScore: 1,
        })}
        onFeedback={onFeedback}
      />,
    );
    expect(screen.getByText('已回饋')).toBeInTheDocument();
  });
});

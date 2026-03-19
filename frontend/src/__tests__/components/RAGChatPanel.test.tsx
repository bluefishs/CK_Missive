/**
 * RAGChatPanel Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

// ============================================================================
// jsdom polyfills
// ============================================================================

// scrollIntoView is not implemented in jsdom
Element.prototype.scrollIntoView = vi.fn();

// ============================================================================
// Mocks
// ============================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/ai/adminManagement', () => ({
  submitAIFeedback: vi.fn(),
}));

vi.mock('../../components/ai/MessageBubble', () => ({
  MessageBubble: ({ message }: { message: { content: string } }) => (
    <div data-testid="message-bubble">{message.content}</div>
  ),
}));

vi.mock('../../components/ai/knowledgeGraph/GraphAgentBridge', () => ({
  useGraphAgentBridgeOptional: vi.fn(() => null),
}));

vi.mock('../../hooks/system/useAgentSSE', () => ({
  useAgentSSE: vi.fn(() => ({
    messages: [],
    loading: false,
    conversationId: 'test-conv-id',
    sendQuestion: vi.fn(),
    clearConversation: vi.fn(),
    setMessages: vi.fn(),
  })),
}));

// ============================================================================
// Helpers
// ============================================================================

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp><MemoryRouter>{ui}</MemoryRouter></AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

// ============================================================================
// Tests
// ============================================================================

describe('RAGChatPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing in default mode', async () => {
    const { RAGChatPanel } = await import('../../components/ai/RAGChatPanel');
    const { container } = renderWithProviders(
      <RAGChatPanel />
    );
    expect(container).toBeTruthy();
  });

  it('renders agent mode title', async () => {
    const { RAGChatPanel } = await import('../../components/ai/RAGChatPanel');
    renderWithProviders(
      <RAGChatPanel agentMode={true} />
    );
    expect(screen.getByText('AI 智能體問答')).toBeInTheDocument();
    expect(screen.getByText('Agent')).toBeInTheDocument();
  });

  it('renders RAG mode title when agentMode is false', async () => {
    const { RAGChatPanel } = await import('../../components/ai/RAGChatPanel');
    renderWithProviders(
      <RAGChatPanel agentMode={false} />
    );
    expect(screen.getByText('RAG 公文問答')).toBeInTheDocument();
    expect(screen.getByText('SSE')).toBeInTheDocument();
  });

  it('renders empty state with suggested questions', async () => {
    const { RAGChatPanel } = await import('../../components/ai/RAGChatPanel');
    renderWithProviders(
      <RAGChatPanel />
    );
    expect(screen.getByText('AI 智能體問答助理')).toBeInTheDocument();
    expect(screen.getByText('桃園市工務局相關公文')).toBeInTheDocument();
  });

  it('renders in embedded mode without card wrapper', async () => {
    const { RAGChatPanel } = await import('../../components/ai/RAGChatPanel');
    const { container } = renderWithProviders(
      <RAGChatPanel embedded={true} />
    );
    // embedded mode should not have the card title
    expect(container.querySelector('.ant-card-head')).toBeNull();
  });
});

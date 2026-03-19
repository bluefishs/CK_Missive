/**
 * AIAssistantButton 元件測試
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../../hooks', () => ({
  useResponsive: () => ({
    isMobile: false,
    responsiveValue: (v: { desktop: unknown }) => v.desktop,
  }),
}));

vi.mock('../../config/aiConfig', () => ({
  syncAIConfigFromServer: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('../RAGChatPanel', () => ({
  default: ({ embedded, agentMode, context }: { embedded: boolean; agentMode: boolean; context: string }) => (
    <div data-testid="rag-chat-panel" data-embedded={embedded} data-agent={agentMode} data-context={context}>
      RAGChatPanel Mock
    </div>
  ),
}));

import { AIAssistantButton } from '../AIAssistantButton';

describe('AIAssistantButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clean up portal container
    const portal = document.getElementById('ai-assistant-portal');
    if (portal) portal.remove();
  });

  it('visible=false 時不渲染', () => {
    render(<AIAssistantButton visible={false} />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('預設渲染浮動按鈕', () => {
    render(<AIAssistantButton />);
    const btn = screen.getByLabelText('AI 智慧助理');
    expect(btn).toBeInTheDocument();
  });

  it('點擊按鈕開啟面板', async () => {
    const user = userEvent.setup();
    render(<AIAssistantButton />);

    await user.click(screen.getByLabelText('AI 智慧助理'));

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('公文助理')).toBeInTheDocument();
    expect(screen.getByText('智能體')).toBeInTheDocument();
  });

  it('開啟後按鈕變為關閉圖示', async () => {
    const user = userEvent.setup();
    render(<AIAssistantButton />);

    await user.click(screen.getByLabelText('AI 智慧助理'));

    // After opening, the button label changes
    expect(screen.getByLabelText('關閉 AI 智慧助理')).toBeInTheDocument();
  });

  it('面板有縮小和關閉按鈕', async () => {
    const user = userEvent.setup();
    render(<AIAssistantButton />);

    await user.click(screen.getByLabelText('AI 智慧助理'));

    expect(screen.getByLabelText('縮小面板')).toBeInTheDocument();
    expect(screen.getByLabelText('關閉 AI 面板')).toBeInTheDocument();
  });

  it('點擊關閉按鈕關閉面板', async () => {
    const user = userEvent.setup();
    render(<AIAssistantButton />);

    await user.click(screen.getByLabelText('AI 智慧助理'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    await user.click(screen.getByLabelText('關閉 AI 面板'));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('建立 portal 容器', () => {
    render(<AIAssistantButton />);
    expect(document.getElementById('ai-assistant-portal')).toBeTruthy();
  });

  it('面板內渲染 RAGChatPanel', async () => {
    const user = userEvent.setup();
    render(<AIAssistantButton />);

    await user.click(screen.getByLabelText('AI 智慧助理'));

    expect(screen.getByTestId('rag-chat-panel')).toBeInTheDocument();
  });
});

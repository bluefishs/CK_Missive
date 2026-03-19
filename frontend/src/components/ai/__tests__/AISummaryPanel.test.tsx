/**
 * AISummaryPanel 元件測試
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { App, ConfigProvider } from 'antd';

const { mockAiApi } = vi.hoisted(() => ({
  mockAiApi: {
    generateSummary: vi.fn(),
    streamSummary: vi.fn(),
  },
}));

vi.mock('../../../api/aiApi', () => ({
  aiApi: mockAiApi,
}));

vi.mock('../../../config/aiConfig', () => ({
  AI_CONFIG: {
    summary: { defaultMaxLength: 200 },
    classify: { confidenceThreshold: 0.7 },
  },
  getAISourceColor: (s: string) => (s === 'ai' ? 'blue' : 'default'),
  getAISourceLabel: (s: string) =>
    s === 'ai' ? 'AI 推論' : s === 'fallback' ? '預設摘要' : s,
}));

vi.mock('../StreamingText', () => ({
  StreamingText: ({ text, isStreaming }: { text: string; isStreaming: boolean }) => (
    <span data-testid="streaming-text" data-streaming={isStreaming}>
      {text}
    </span>
  ),
}));

import { AISummaryPanel } from '../AISummaryPanel';

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <ConfigProvider>
      <App>{children}</App>
    </ConfigProvider>
  );
}

describe('AISummaryPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('渲染卡片標題', () => {
    render(
      <Wrapper>
        <AISummaryPanel subject="測試" />
      </Wrapper>,
    );
    expect(screen.getByText('AI 摘要')).toBeInTheDocument();
  });

  it('showCard=false 不渲染卡片', () => {
    render(
      <Wrapper>
        <AISummaryPanel subject="測試" showCard={false} />
      </Wrapper>,
    );
    expect(screen.queryByText('AI 摘要')).not.toBeInTheDocument();
    expect(screen.getByText('生成摘要')).toBeInTheDocument();
  });

  it('無主旨時按鈕禁用', () => {
    render(
      <Wrapper>
        <AISummaryPanel subject="" />
      </Wrapper>,
    );
    const btn = screen.getByText('生成摘要').closest('button');
    expect(btn).toBeDisabled();
  });

  it('初始顯示提示文字', () => {
    render(
      <Wrapper>
        <AISummaryPanel subject="測試" />
      </Wrapper>,
    );
    expect(screen.getByText(/點擊「生成摘要」按鈕/)).toBeInTheDocument();
  });

  it('串流開關預設為開啟', () => {
    render(
      <Wrapper>
        <AISummaryPanel subject="測試" />
      </Wrapper>,
    );
    expect(document.body.textContent).toContain('串流');
  });

  it('一般模式成功生成摘要', async () => {
    mockAiApi.generateSummary.mockResolvedValue({
      summary: '這是測試摘要',
      confidence: 0.85,
      source: 'ai',
    });
    const user = userEvent.setup();
    render(
      <Wrapper>
        <AISummaryPanel subject="測試主旨" />
      </Wrapper>,
    );

    // Switch to non-streaming mode
    const switchEl = document.querySelector('.ant-switch');
    if (switchEl) await user.click(switchEl);

    await user.click(screen.getByText('生成摘要'));

    await waitFor(() => {
      expect(screen.getByText('這是測試摘要')).toBeInTheDocument();
    });
  });

  it('結果出現後按鈕文字變為「重新生成」', async () => {
    mockAiApi.generateSummary.mockResolvedValue({
      summary: '摘要結果',
      confidence: 0.9,
      source: 'ai',
    });
    const user = userEvent.setup();
    render(
      <Wrapper>
        <AISummaryPanel subject="測試" />
      </Wrapper>,
    );

    // Switch to non-streaming mode
    const switchEl = document.querySelector('.ant-switch');
    if (switchEl) await user.click(switchEl);

    await user.click(screen.getByText('生成摘要'));
    await waitFor(() => {
      expect(screen.getByText('重新生成')).toBeInTheDocument();
    });
  });

  it('API 錯誤時不崩潰', async () => {
    mockAiApi.generateSummary.mockRejectedValue(new Error('fail'));
    const user = userEvent.setup();
    render(
      <Wrapper>
        <AISummaryPanel subject="測試" />
      </Wrapper>,
    );

    const switchEl = document.querySelector('.ant-switch');
    if (switchEl) await user.click(switchEl);

    await user.click(screen.getByText('生成摘要'));
    await waitFor(() => {
      expect(screen.getByText('生成摘要')).toBeInTheDocument();
    });
  });

  it('渲染高信心度標籤', async () => {
    mockAiApi.generateSummary.mockResolvedValue({
      summary: '摘要',
      confidence: 0.9,
      source: 'ai',
    });
    const user = userEvent.setup();
    render(
      <Wrapper>
        <AISummaryPanel subject="測試" />
      </Wrapper>,
    );

    const switchEl = document.querySelector('.ant-switch');
    if (switchEl) await user.click(switchEl);

    await user.click(screen.getByText('生成摘要'));
    await waitFor(() => {
      expect(screen.getByText(/高信心度/)).toBeInTheDocument();
      expect(screen.getByText(/90%/)).toBeInTheDocument();
    });
  });

  it('傳遞正確參數給 API', async () => {
    mockAiApi.generateSummary.mockResolvedValue({
      summary: '摘要',
      confidence: 0.8,
      source: 'ai',
    });
    const user = userEvent.setup();
    render(
      <Wrapper>
        <AISummaryPanel subject="主旨" content="內容" sender="機關" maxLength={100} />
      </Wrapper>,
    );

    const switchEl = document.querySelector('.ant-switch');
    if (switchEl) await user.click(switchEl);

    await user.click(screen.getByText('生成摘要'));
    await waitFor(() => {
      expect(mockAiApi.generateSummary).toHaveBeenCalledWith({
        subject: '主旨',
        content: '內容',
        sender: '機關',
        max_length: 100,
      });
    });
  });

  it('串流模式呼叫 streamSummary', async () => {
    // Mock streamSummary to return an AbortController
    mockAiApi.streamSummary.mockReturnValue(new AbortController());
    const user = userEvent.setup();
    render(
      <Wrapper>
        <AISummaryPanel subject="測試主旨" />
      </Wrapper>,
    );

    await user.click(screen.getByText('生成摘要'));

    await waitFor(() => {
      expect(mockAiApi.streamSummary).toHaveBeenCalled();
    });
  });
});

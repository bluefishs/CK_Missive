/**
 * AIClassifyPanel 元件測試
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
    suggestClassification: vi.fn(),
  },
}));

vi.mock('../../../api/aiApi', () => ({
  aiApi: mockAiApi,
}));

vi.mock('../../../config/aiConfig', () => ({
  AI_CONFIG: {
    classify: { confidenceThreshold: 0.7 },
    summary: { defaultMaxLength: 200 },
  },
  getAISourceColor: (s: string) => (s === 'ai' ? 'blue' : 'default'),
  getAISourceLabel: (s: string) =>
    s === 'ai' ? 'AI 推論' : s === 'fallback' ? '預設分類' : s,
}));

import { AIClassifyPanel } from '../AIClassifyPanel';

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <ConfigProvider>
      <App>{children}</App>
    </ConfigProvider>
  );
}

describe('AIClassifyPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('渲染卡片標題', () => {
    render(
      <Wrapper>
        <AIClassifyPanel subject="測試主旨" />
      </Wrapper>,
    );
    expect(screen.getByText('AI 分類建議')).toBeInTheDocument();
  });

  it('showCard=false 不渲染卡片', () => {
    render(
      <Wrapper>
        <AIClassifyPanel subject="測試" showCard={false} />
      </Wrapper>,
    );
    expect(screen.queryByText('AI 分類建議')).not.toBeInTheDocument();
    expect(screen.getByText('取得建議')).toBeInTheDocument();
  });

  it('無主旨時按鈕禁用', () => {
    render(
      <Wrapper>
        <AIClassifyPanel subject="" />
      </Wrapper>,
    );
    const btn = screen.getByText('取得建議').closest('button');
    expect(btn).toBeDisabled();
  });

  it('初始顯示提示文字', () => {
    render(
      <Wrapper>
        <AIClassifyPanel subject="測試" />
      </Wrapper>,
    );
    expect(screen.getByText(/點擊「取得建議」按鈕/)).toBeInTheDocument();
  });

  it('成功取得分類結果', async () => {
    mockAiApi.suggestClassification.mockResolvedValue({
      doc_type: '函',
      doc_type_confidence: 0.9,
      category: '收文',
      category_confidence: 0.85,
      source: 'ai',
      reasoning: '根據主旨判斷',
    });
    const user = userEvent.setup();
    render(
      <Wrapper>
        <AIClassifyPanel subject="桃園市政府來函" />
      </Wrapper>,
    );

    await user.click(screen.getByText('取得建議'));

    await waitFor(() => {
      expect(screen.getByText('函')).toBeInTheDocument();
      expect(screen.getByText('收文')).toBeInTheDocument();
      expect(screen.getByText('根據主旨判斷')).toBeInTheDocument();
    });
  });

  it('結果出現後按鈕文字變為「重新分析」', async () => {
    mockAiApi.suggestClassification.mockResolvedValue({
      doc_type: '函',
      doc_type_confidence: 0.9,
      category: '收文',
      category_confidence: 0.85,
      source: 'ai',
    });
    const user = userEvent.setup();
    render(
      <Wrapper>
        <AIClassifyPanel subject="測試" />
      </Wrapper>,
    );
    await user.click(screen.getByText('取得建議'));
    await waitFor(() => {
      expect(screen.getByText('重新分析')).toBeInTheDocument();
    });
  });

  it('有 onSelect 時顯示「套用建議」按鈕', async () => {
    const onSelect = vi.fn();
    mockAiApi.suggestClassification.mockResolvedValue({
      doc_type: '函',
      doc_type_confidence: 0.9,
      category: '收文',
      category_confidence: 0.85,
      source: 'ai',
    });
    const user = userEvent.setup();
    render(
      <Wrapper>
        <AIClassifyPanel subject="測試" onSelect={onSelect} />
      </Wrapper>,
    );
    await user.click(screen.getByText('取得建議'));
    await waitFor(() => {
      expect(screen.getByText('套用建議')).toBeInTheDocument();
    });

    await user.click(screen.getByText('套用建議'));
    expect(onSelect).toHaveBeenCalledWith('函', '收文');
  });

  it('API 錯誤時不崩潰', async () => {
    mockAiApi.suggestClassification.mockRejectedValue(new Error('fail'));
    const user = userEvent.setup();
    render(
      <Wrapper>
        <AIClassifyPanel subject="測試" />
      </Wrapper>,
    );
    await user.click(screen.getByText('取得建議'));
    // Should not crash, button should be clickable again
    await waitFor(() => {
      expect(screen.getByText('取得建議')).toBeInTheDocument();
    });
  });

  it('渲染信心度標籤', async () => {
    mockAiApi.suggestClassification.mockResolvedValue({
      doc_type: '函',
      doc_type_confidence: 0.85,
      category: '收文',
      category_confidence: 0.5,
      source: 'ai',
    });
    const user = userEvent.setup();
    render(
      <Wrapper>
        <AIClassifyPanel subject="測試" />
      </Wrapper>,
    );
    await user.click(screen.getByText('取得建議'));
    await waitFor(() => {
      expect(screen.getByText(/85%/)).toBeInTheDocument();
      expect(screen.getByText(/50%/)).toBeInTheDocument();
    });
  });

  it('傳遞正確參數給 API', async () => {
    mockAiApi.suggestClassification.mockResolvedValue({
      doc_type: '函',
      doc_type_confidence: 0.9,
      category: '收文',
      category_confidence: 0.9,
      source: 'ai',
    });
    const user = userEvent.setup();
    render(
      <Wrapper>
        <AIClassifyPanel subject="主旨" content="內容" sender="發文機關" />
      </Wrapper>,
    );
    await user.click(screen.getByText('取得建議'));
    await waitFor(() => {
      expect(mockAiApi.suggestClassification).toHaveBeenCalledWith({
        subject: '主旨',
        content: '內容',
        sender: '發文機關',
      });
    });
  });
});

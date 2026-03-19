/**
 * StreamingText 元件測試
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StreamingText } from '../StreamingText';

describe('StreamingText', () => {
  it('渲染文字內容', () => {
    render(<StreamingText text="Hello World" isStreaming={false} />);
    expect(screen.getByText('Hello World')).toBeInTheDocument();
  });

  it('空字串不會報錯', () => {
    const { container } = render(<StreamingText text="" isStreaming={false} />);
    expect(container.querySelector('span')).toBeInTheDocument();
  });

  it('streaming=true 時顯示閃爍游標', () => {
    const { container } = render(<StreamingText text="串流中" isStreaming={true} />);
    // cursor element has specific styles
    const cursor = container.querySelector('span > span');
    expect(cursor).toBeTruthy();
    expect(cursor?.getAttribute('style')).toContain('animation');
  });

  it('streaming=false 時不顯示游標', () => {
    const { container } = render(<StreamingText text="完成" isStreaming={false} />);
    // Only one span (the wrapper), no cursor span
    const spans = container.querySelectorAll('span');
    expect(spans).toHaveLength(1);
  });

  it('streaming=true 時注入 CSS keyframes', () => {
    const { container } = render(<StreamingText text="test" isStreaming={true} />);
    const styleEl = container.querySelector('style');
    expect(styleEl).toBeTruthy();
    expect(styleEl?.textContent).toContain('streaming-cursor-blink');
  });

  it('streaming=false 時不注入 CSS keyframes', () => {
    const { container } = render(<StreamingText text="test" isStreaming={false} />);
    expect(container.querySelector('style')).toBeNull();
  });

  it('接受自訂 style prop', () => {
    const { container } = render(
      <StreamingText text="styled" isStreaming={false} style={{ color: 'red', fontSize: 16 }} />,
    );
    const wrapper = container.querySelector('span');
    expect(wrapper?.getAttribute('style')).toContain('color: red');
  });

  it('中文內容正常顯示', () => {
    render(<StreamingText text="公文摘要分析中..." isStreaming={true} />);
    expect(screen.getByText(/公文摘要分析中/)).toBeInTheDocument();
  });

  it('長文字正常渲染', () => {
    const longText = '這是一段很長的文字'.repeat(100);
    render(<StreamingText text={longText} isStreaming={false} />);
    expect(screen.getByText(longText)).toBeInTheDocument();
  });
});

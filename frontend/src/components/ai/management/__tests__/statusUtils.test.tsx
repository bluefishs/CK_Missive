/**
 * statusUtils 元件測試
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatusIcon } from '../statusUtils';

describe('StatusIcon', () => {
  it('ok=true 渲染綠色勾勾圖示', () => {
    const { container } = render(<StatusIcon ok={true} />);
    const icon = container.querySelector('[aria-label="check-circle"]');
    expect(icon).toBeTruthy();
    // Color is rendered as rgb by jsdom
    expect(container.querySelector('span')?.getAttribute('style')).toContain('color');
    expect(container.querySelector('span')?.getAttribute('style')).toContain('82, 196, 26');
  });

  it('ok=false 渲染紅色叉叉圖示', () => {
    const { container } = render(<StatusIcon ok={false} />);
    const icon = container.querySelector('[aria-label="close-circle"]');
    expect(icon).toBeTruthy();
    expect(container.querySelector('span')?.getAttribute('style')).toContain('255, 77, 79');
  });
});

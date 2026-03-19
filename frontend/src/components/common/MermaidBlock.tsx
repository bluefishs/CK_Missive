/**
 * MermaidBlock - 通用 Mermaid 圖表渲染元件
 *
 * 接收 Mermaid 語法字串，lazy-load mermaid 函式庫並渲染為 SVG。
 * 渲染失敗時顯示原始語法（graceful degradation）。
 *
 * 適用場景：Markdown 渲染器、知識庫文件、任何需要嵌入 Mermaid 圖表的地方。
 * 若需要進階功能（縮放/平移/下載），請使用 `components/ai/MermaidBlock`。
 *
 * @version 1.0.0
 */
import React, { useEffect, useRef, useState } from 'react';

interface MermaidBlockProps {
  /** Mermaid 圖表定義語法 */
  code: string;
  /** 額外 CSS class */
  className?: string;
}

/**
 * 通用 Mermaid 圖表渲染元件。
 *
 * - Lazy-load mermaid 函式庫（不影響初始 bundle 大小）
 * - 渲染失敗時回退顯示原始程式碼
 * - 支援 OS dark mode 自動偵測
 *
 * @example
 * ```tsx
 * <MermaidBlock code="graph TD; A-->B;" />
 * ```
 */
const MermaidBlock: React.FC<MermaidBlockProps> = ({ code, className }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [svg, setSvg] = useState<string>('');
  const idRef = useRef(`mermaid-${Math.random().toString(36).slice(2, 9)}`);
  const mermaidRef = useRef<typeof import('mermaid')['default'] | null>(null);

  // OS dark mode detection
  const [prefersDark, setPrefersDark] = useState(
    () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches,
  );

  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)');
    if (!mq) return;
    const handler = (e: MediaQueryListEvent) => setPrefersDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  useEffect(() => {
    if (!code) return;
    let cancelled = false;

    const renderDiagram = async () => {
      try {
        if (!mermaidRef.current) {
          mermaidRef.current = (await import('mermaid')).default;
        }
        const mermaid = mermaidRef.current;
        mermaid.initialize({
          startOnLoad: false,
          theme: prefersDark ? 'dark' : 'default',
          securityLevel: 'strict',
        });

        const { svg: rendered } = await mermaid.render(idRef.current, code);
        if (!cancelled) {
          setSvg(rendered);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    };

    renderDiagram();
    return () => { cancelled = true; };
  }, [code, prefersDark]);

  if (error) {
    return (
      <pre className={className} style={{ fontSize: 12, color: '#cf1322', background: '#fff2f0', padding: 12, borderRadius: 6, overflow: 'auto' }}>
        {code}
      </pre>
    );
  }

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ textAlign: 'center', margin: '8px 0' }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
};

export default MermaidBlock;

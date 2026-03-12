/**
 * Mermaid 圖表渲染元件
 *
 * 接收 Mermaid 語法字串，自動渲染為 SVG 圖表。
 * 支援 erDiagram, flowchart, classDiagram, graph 等類型。
 * 含主題適配（OS dark mode）、滾輪縮放、拖曳平移。
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Card, Typography, Button, Space, message } from 'antd';
import {
  FullscreenOutlined,
  CopyOutlined,
  DownloadOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  ReloadOutlined,
} from '@ant-design/icons';

type MermaidTheme = 'default' | 'dark' | 'forest' | 'neutral';

interface MermaidBlockProps {
  chart: string;
  title?: string;
  description?: string;
  theme?: MermaidTheme;
}

const ZOOM_MIN = 0.3;
const ZOOM_MAX = 5.0;
const ZOOM_STEP = 0.15;

const MermaidBlock: React.FC<MermaidBlockProps> = ({ chart, title, description, theme: themeProp }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgWrapRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [svgContent, setSvgContent] = useState<string>('');
  const idRef = useRef(`mermaid-${Math.random().toString(36).slice(2, 9)}`);

  // A2: OS dark mode detection
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

  const effectiveTheme: MermaidTheme = themeProp ?? (prefersDark ? 'dark' : 'default');

  // A3: Zoom & Pan state
  const [scale, setScale] = useState(1);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const isPanning = useRef(false);
  const panStart = useRef({ x: 0, y: 0 });
  const translateStart = useRef({ x: 0, y: 0 });

  // D2: 模組層級快取 mermaid 實例（避免每次渲染重複 dynamic import）
  const mermaidRef = useRef<typeof import('mermaid')['default'] | null>(null);

  // Render Mermaid SVG
  useEffect(() => {
    if (!chart) return;
    let cancelled = false;

    const renderChart = async () => {
      try {
        if (!mermaidRef.current) {
          mermaidRef.current = (await import('mermaid')).default;
        }
        const mermaid = mermaidRef.current;
        mermaid.initialize({
          startOnLoad: false,
          theme: effectiveTheme,
          securityLevel: 'strict',
          er: { useMaxWidth: true },
          flowchart: { useMaxWidth: true, curve: 'basis' },
        });

        const { svg } = await mermaid.render(idRef.current, chart);
        if (!cancelled) {
          setSvgContent(svg);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    };

    renderChart();
    return () => { cancelled = true; };
  }, [chart, effectiveTheme]);

  // A3: Wheel zoom (passive: false to allow preventDefault)
  useEffect(() => {
    const el = svgWrapRef.current;
    if (!el) return;

    const handleWheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
      setScale((prev) => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, prev + delta)));
    };

    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => el.removeEventListener('wheel', handleWheel);
  }, []);

  // A3: Mouse drag to pan
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return; // left button only
    isPanning.current = true;
    panStart.current = { x: e.clientX, y: e.clientY };
    translateStart.current = { ...translate };
    e.preventDefault();
  }, [translate]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isPanning.current) return;
    setTranslate({
      x: translateStart.current.x + (e.clientX - panStart.current.x),
      y: translateStart.current.y + (e.clientY - panStart.current.y),
    });
  }, []);

  const handleMouseUp = useCallback(() => {
    isPanning.current = false;
  }, []);

  const handleZoomIn = () => setScale((s) => Math.min(ZOOM_MAX, s + ZOOM_STEP * 2));
  const handleZoomOut = () => setScale((s) => Math.max(ZOOM_MIN, s - ZOOM_STEP * 2));
  const handleResetView = () => { setScale(1); setTranslate({ x: 0, y: 0 }); };

  const handleCopy = () => {
    navigator.clipboard.writeText(chart).then(() => {
      message.success('Mermaid 語法已複製');
    });
  };

  const handleDownloadSVG = () => {
    if (!svgContent) return;
    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title || 'diagram'}.svg`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleFullscreen = () => {
    containerRef.current?.requestFullscreen?.();
  };

  if (error) {
    return (
      <Card size="small" style={{ margin: '8px 0', borderColor: '#ff4d4f' }}>
        <Typography.Text type="danger">Mermaid 渲染失敗: {error}</Typography.Text>
        <pre style={{ fontSize: 11, marginTop: 8, maxHeight: 120, overflow: 'auto' }}>{chart}</pre>
      </Card>
    );
  }

  const zoomPercent = Math.round(scale * 100);

  return (
    <Card
      size="small"
      style={{ margin: '8px 0' }}
      title={title && <Typography.Text strong style={{ fontSize: 13 }}>{title}</Typography.Text>}
      extra={
        <Space size="small">
          <Button size="small" icon={<ZoomOutOutlined />} onClick={handleZoomOut} title="縮小" />
          <Typography.Text style={{ fontSize: 11, minWidth: 36, textAlign: 'center' }}>{zoomPercent}%</Typography.Text>
          <Button size="small" icon={<ZoomInOutlined />} onClick={handleZoomIn} title="放大" />
          <Button size="small" icon={<ReloadOutlined />} onClick={handleResetView} title="重置視圖" />
          <Button size="small" icon={<CopyOutlined />} onClick={handleCopy} title="複製 Mermaid 語法" />
          <Button size="small" icon={<DownloadOutlined />} onClick={handleDownloadSVG} title="下載 SVG" />
          <Button size="small" icon={<FullscreenOutlined />} onClick={handleFullscreen} title="全螢幕" />
        </Space>
      }
    >
      {description && (
        <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>
          {description}
        </Typography.Text>
      )}
      <div
        ref={containerRef}
        style={{ overflow: 'hidden', maxHeight: 600, cursor: isPanning.current ? 'grabbing' : 'grab', userSelect: 'none' }}
      >
        <div
          ref={svgWrapRef}
          style={{
            transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
            transformOrigin: 'center center',
            textAlign: 'center',
            transition: isPanning.current ? 'none' : 'transform 0.15s ease',
          }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          dangerouslySetInnerHTML={{ __html: svgContent }}
        />
      </div>
      <Typography.Text type="secondary" style={{ fontSize: 10, display: 'block', marginTop: 4 }}>
        Ctrl+滾輪縮放 · 拖曳平移
      </Typography.Text>
    </Card>
  );
};

export default MermaidBlock;

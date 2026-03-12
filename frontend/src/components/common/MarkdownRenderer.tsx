/**
 * MarkdownRenderer - 通用 Markdown 渲染器
 *
 * 支援 GFM 表格、程式碼區塊、標題、連結，
 * 以及 ```mermaid 區塊代理至 MermaidBlock 元件
 *
 * @version 1.0.0
 */
import React, { Suspense } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Typography, Spin } from 'antd';

const MermaidBlock = React.lazy(() => import('../ai/MermaidBlock'));

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className }) => {
  return (
    <div className={className} style={{ lineHeight: 1.8 }}>
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Mermaid code blocks
          code({ className: codeClassName, children, ...props }) {
            const match = /language-(\w+)/.exec(codeClassName || '');
            const lang = match?.[1];
            const codeStr = String(children).replace(/\n$/, '');

            if (lang === 'mermaid') {
              return (
                <Suspense fallback={<Spin tip="載入圖表..."><div style={{ padding: 40 }} /></Spin>}>
                  <MermaidBlock chart={codeStr} />
                </Suspense>
              );
            }

            // Regular code blocks
            if (lang) {
              return (
                <pre style={{
                  background: '#f6f8fa',
                  borderRadius: 6,
                  padding: '12px 16px',
                  overflow: 'auto',
                  fontSize: 13,
                  lineHeight: 1.5,
                }}>
                  <code className={codeClassName} {...props}>{children}</code>
                </pre>
              );
            }

            // Inline code
            return (
              <Typography.Text code style={{ fontSize: 13 }}>{children}</Typography.Text>
            );
          },
          // Tables
          table({ children }) {
            return (
              <div style={{ overflowX: 'auto', marginBottom: 16 }}>
                <table style={{
                  borderCollapse: 'collapse',
                  width: '100%',
                  fontSize: 13,
                }}>
                  {children}
                </table>
              </div>
            );
          },
          th({ children }) {
            return (
              <th style={{
                borderBottom: '2px solid #d9d9d9',
                padding: '8px 12px',
                textAlign: 'left',
                fontWeight: 600,
                background: '#fafafa',
              }}>
                {children}
              </th>
            );
          },
          td({ children }) {
            return (
              <td style={{
                borderBottom: '1px solid #f0f0f0',
                padding: '6px 12px',
              }}>
                {children}
              </td>
            );
          },
          // Headings
          h1({ children }) { return <Typography.Title level={2} style={{ marginTop: 24 }}>{children}</Typography.Title>; },
          h2({ children }) { return <Typography.Title level={3} style={{ marginTop: 20 }}>{children}</Typography.Title>; },
          h3({ children }) { return <Typography.Title level={4} style={{ marginTop: 16 }}>{children}</Typography.Title>; },
          h4({ children }) { return <Typography.Title level={5} style={{ marginTop: 12 }}>{children}</Typography.Title>; },
          // Links
          a({ href, children }) {
            return <Typography.Link href={href} target="_blank" rel="noopener noreferrer">{children}</Typography.Link>;
          },
          // Blockquotes
          blockquote({ children }) {
            return (
              <blockquote style={{
                borderLeft: '4px solid #1890ff',
                paddingLeft: 16,
                margin: '12px 0',
                color: '#595959',
                background: '#f6f8fa',
                padding: '8px 16px',
                borderRadius: '0 4px 4px 0',
              }}>
                {children}
              </blockquote>
            );
          },
        }}
      >
        {content}
      </Markdown>
    </div>
  );
};

export default MarkdownRenderer;

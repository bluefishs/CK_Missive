/**
 * 串流文字顯示元件
 *
 * 顯示逐步增長的 AI 回應文字，
 * 串流中顯示閃爍游標，完成後移除。
 *
 * @version 1.0.0
 * @created 2026-02-08
 */

import React from 'react';

interface StreamingTextProps {
  /** 目前累積的文字內容 */
  text: string;
  /** 是否正在串流中 */
  isStreaming: boolean;
  /** 自訂樣式 */
  style?: React.CSSProperties;
}

/**
 * 串流文字顯示元件
 *
 * 在串流進行時顯示閃爍的方塊游標，
 * 串流完成後自動移除游標。
 */
export const StreamingText: React.FC<StreamingTextProps> = ({
  text,
  isStreaming,
  style,
}) => {
  return (
    <span style={style}>
      {text}
      {isStreaming && (
        <span
          style={{
            display: 'inline-block',
            width: '0.6em',
            height: '1.1em',
            backgroundColor: '#1890ff',
            marginLeft: '2px',
            verticalAlign: 'text-bottom',
            animation: 'streaming-cursor-blink 0.8s step-end infinite',
          }}
        />
      )}
      {isStreaming && (
        <style>{`
          @keyframes streaming-cursor-blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
          }
        `}</style>
      )}
    </span>
  );
};

export default StreamingText;

/**
 * StarrySky — 深藍星空背景裝飾元件
 *
 * 從 EntryPage.tsx 拆分（v1.0 2026-04-18）
 * 包含：
 *   - 隨機星點 (small/medium/large)
 *   - 角落星形裝飾
 *   - 幾何弧線 + 星座點
 *
 * 純 presentation，無狀態依賴。手機端自動降星數。
 */
import React, { useMemo } from 'react';

interface StarProps {
  className: string;
  style: React.CSSProperties;
}

const Star: React.FC<StarProps> = ({ className, style }) => (
  <div className={`star ${className}`} style={style} />
);

const generateStars = (count: number, className: string): StarProps[] =>
  Array.from({ length: count }, () => ({
    className,
    style: {
      left: `${Math.random() * 100}%`,
      top: `${Math.random() * 100}%`,
      animationDelay: `${Math.random() * 3}s`,
      animationDuration: `${2 + Math.random() * 2}s`,
    },
  }));

const isMobileDevice = () =>
  typeof window !== 'undefined' && window.innerWidth < 768;

const StarrySky: React.FC = () => {
  const mobile = isMobileDevice();
  const stars = useMemo(
    () => ({
      small: generateStars(mobile ? 30 : 60, 'star-small'),
      medium: generateStars(mobile ? 15 : 35, 'star-medium'),
      large: generateStars(mobile ? 8 : 20, 'star-large'),
    }),
    [mobile],
  );

  return (
    <div className="stars-container">
      {stars.small.map((star, i) => <Star key={`small-${i}`} {...star} />)}
      {stars.medium.map((star, i) => <Star key={`medium-${i}`} {...star} />)}
      {stars.large.map((star, i) => <Star key={`large-${i}`} {...star} />)}

      {/* 四角星裝飾 */}
      <div className="star-decoration star-decoration-1" />
      <div className="star-decoration star-decoration-2" />
      <div className="star-decoration star-decoration-3" />

      {/* 幾何弧線裝飾 */}
      <svg className="arc-decoration" viewBox="0 0 800 400" preserveAspectRatio="xMidYMid meet">
        <path className="arc-line" d="M 50 350 Q 400 50 750 350" fill="none" />
        <path className="arc-line arc-line-2" d="M 100 320 Q 400 100 700 320" fill="none" />
      </svg>

      {/* 星座點裝飾 */}
      <svg className="constellation-dots" viewBox="0 0 1000 600">
        {/* 左上星座 */}
        <circle cx="150" cy="120" r="2" className="dot" />
        <circle cx="180" cy="100" r="3" className="dot" />
        <circle cx="220" cy="130" r="2" className="dot" />
        <circle cx="200" cy="160" r="2" className="dot" />
        <line x1="150" y1="120" x2="180" y2="100" className="constellation-line" />
        <line x1="180" y1="100" x2="220" y2="130" className="constellation-line" />
        <line x1="220" y1="130" x2="200" y2="160" className="constellation-line" />

        {/* 右上星座 */}
        <circle cx="750" cy="80" r="2" className="dot" />
        <circle cx="800" cy="120" r="3" className="dot" />
        <circle cx="850" cy="90" r="2" className="dot" />
        <circle cx="820" cy="150" r="2" className="dot" />
        <line x1="750" y1="80" x2="800" y2="120" className="constellation-line" />
        <line x1="800" y1="120" x2="850" y2="90" className="constellation-line" />
        <line x1="800" y1="120" x2="820" y2="150" className="constellation-line" />

        {/* 右下星座 */}
        <circle cx="880" cy="450" r="2" className="dot" />
        <circle cx="920" cy="480" r="3" className="dot" />
        <circle cx="900" cy="520" r="2" className="dot" />
        <line x1="880" y1="450" x2="920" y2="480" className="constellation-line" />
        <line x1="920" y1="480" x2="900" y2="520" className="constellation-line" />
      </svg>
    </div>
  );
};

export default StarrySky;

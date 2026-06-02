/**
 * 閒置登出倒數徽章
 *
 * 在 Header 右上角使用者名稱後顯示「無操作情境下」距自動登出的剩餘時間。
 * 自包含活動偵測 + 每秒 tick（隔離 re-render，僅本徽章每秒更新，不觸發整個 Layout）。
 * 共用 useIdleTimeout 的 DEFAULT_IDLE_TIMEOUT_MS（SSOT），確保顯示與實際登出一致。
 *
 * @version 1.0.0
 * @date 2026-06-02
 */

import React, { useState, useEffect, useRef } from 'react';
import { Tooltip, Tag } from 'antd';
import { ClockCircleOutlined } from '@ant-design/icons';
import { DEFAULT_IDLE_TIMEOUT_MS } from '../../hooks/utility/useIdleTimeout';
import { isAuthDisabled } from '../../config/env';

const WARNING_MS = 5 * 60 * 1000; // 剩 5 分鐘內以警示色提示

export const IdleCountdownBadge: React.FC = () => {
  const lastActivityRef = useRef<number>(Date.now());
  const [remainingMs, setRemainingMs] = useState<number>(DEFAULT_IDLE_TIMEOUT_MS);

  useEffect(() => {
    // 開發/免認證模式不顯示（無閒置登出）
    if (isAuthDisabled()) return;

    const onActivity = () => {
      lastActivityRef.current = Date.now();
    };
    const events: (keyof WindowEventMap)[] = [
      'mousemove', 'keydown', 'mousedown', 'touchstart', 'scroll',
    ];
    for (const e of events) {
      window.addEventListener(e, onActivity, { passive: true });
    }

    const tick = setInterval(() => {
      const left = DEFAULT_IDLE_TIMEOUT_MS - (Date.now() - lastActivityRef.current);
      setRemainingMs(left > 0 ? left : 0);
    }, 1000);

    return () => {
      clearInterval(tick);
      for (const e of events) {
        window.removeEventListener(e, onActivity);
      }
    };
  }, []);

  if (isAuthDisabled()) return null;

  const totalSec = Math.max(0, Math.floor(remainingMs / 1000));
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  const warning = remainingMs <= WARNING_MS;

  return (
    <Tooltip title={`您將於 ${min} 分 ${sec} 秒後登出（無操作達 30 分鐘自動登出；任何操作即重置）`}>
      <Tag
        icon={<ClockCircleOutlined />}
        color={warning ? 'warning' : 'default'}
        style={{ marginInlineEnd: 0 }}
      >
        {min} 分 {String(sec).padStart(2, '0')} 秒
      </Tag>
    </Tooltip>
  );
};

export default IdleCountdownBadge;

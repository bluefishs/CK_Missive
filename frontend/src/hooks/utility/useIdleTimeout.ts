/**
 * 閒置超時 Hook
 *
 * 監聽使用者活動（滑鼠、鍵盤、觸控、滾動），
 * 閒置超過指定時間後自動登出。
 *
 * @version 1.0.0
 * @date 2026-02-07
 */

import { useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../../services/authService';
import { isAuthDisabled } from '../../config/env';
import { ROUTES } from '../../router/types';
import { logger } from '../../utils/logger';

/** 預設閒置超時：30 分鐘 */
const DEFAULT_IDLE_TIMEOUT_MS = 30 * 60 * 1000;

/** 活動事件節流間隔：1 分鐘 */
const ACTIVITY_THROTTLE_MS = 60 * 1000;

interface UseIdleTimeoutOptions {
  /** 超時毫秒數（預設 30 分鐘） */
  timeoutMs?: number;
  /** 是否啟用（預設 true） */
  enabled?: boolean;
}

/**
 * 使用者閒置超時 Hook
 *
 * 在受保護頁面中使用，自動偵測閒置並登出。
 */
export function useIdleTimeout(options: UseIdleTimeoutOptions = {}) {
  const {
    timeoutMs = DEFAULT_IDLE_TIMEOUT_MS,
    enabled = true,
  } = options;

  const navigate = useNavigate();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastActivityRef = useRef<number>(Date.now());

  const handleTimeout = useCallback(() => {
    logger.warn(`[IdleTimeout] 閒置 ${timeoutMs / 60000} 分鐘，自動登出`);
    authService.logout().then(() => {
      navigate(ROUTES.LOGIN, { replace: true });
    });
  }, [timeoutMs, navigate]);

  const resetTimer = useCallback(() => {
    const now = Date.now();
    // 節流：避免頻繁重設 timer
    if (now - lastActivityRef.current < ACTIVITY_THROTTLE_MS) return;
    lastActivityRef.current = now;

    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    timerRef.current = setTimeout(handleTimeout, timeoutMs);
  }, [handleTimeout, timeoutMs]);

  useEffect(() => {
    // 開發模式或未啟用時不啟動
    if (!enabled || isAuthDisabled()) return;
    if (!authService.isAuthenticated()) return;

    const events: (keyof WindowEventMap)[] = [
      'mousemove', 'keydown', 'mousedown', 'touchstart', 'scroll',
    ];

    // 初始化 timer
    timerRef.current = setTimeout(handleTimeout, timeoutMs);

    // 監聽活動事件
    for (const event of events) {
      window.addEventListener(event, resetTimer, { passive: true });
    }

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      for (const event of events) {
        window.removeEventListener(event, resetTimer);
      }
    };
  }, [enabled, handleTimeout, resetTimer, timeoutMs]);
}

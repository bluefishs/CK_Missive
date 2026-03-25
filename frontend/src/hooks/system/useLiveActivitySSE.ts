/**
 * useLiveActivitySSE — 即時 Swarm 轉播 Hook (V-2.2)
 *
 * 透過 EventSource 訂閱 Missive 後端代理的 OpenClaw EventRelay SSE 串流，
 * 即時接收 Agent 任務生命週期事件 (created/running/approved/rejected/completed/failed)。
 *
 * @version 1.1.0
 * @created 2026-03-23
 * @updated 2026-03-23 — v1.1 reconnection + max-retry + readyState 修復
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { DIGITAL_TWIN_ENDPOINTS } from '../../api/endpoints';

export interface LiveJobEvent {
  type: string;
  payload: {
    job_id?: string;
    agent_id?: string;
    source?: string;
    approved_by?: string;
    rejected_by?: string;
    reason?: string;
    error?: string;
    answer_length?: number;
    [key: string]: unknown;
  };
  correlation_id?: string;
  timestamp: string;
}

interface UseLiveActivityReturn {
  events: LiveJobEvent[];
  isConnected: boolean;
  clearEvents: () => void;
}

const MAX_EVENTS = 100;
const MAX_RETRIES = 5;
const RETRY_BASE_MS = 2000;

export function useLiveActivitySSE(
  channel: string = 'jobs',
  enabled: boolean = true,
): UseLiveActivityReturn {
  const [events, setEvents] = useState<LiveJobEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const retryRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearEvents = useCallback(() => setEvents([]), []);

  useEffect(() => {
    if (!enabled) {
      esRef.current?.close();
      esRef.current = null;
      setIsConnected(false);
      retryRef.current = 0;
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      return;
    }

    let cancelled = false;

    function connect() {
      if (cancelled) return;

      const url = `/api${DIGITAL_TWIN_ENDPOINTS.LIVE_ACTIVITY_STREAM}?channel=${encodeURIComponent(channel)}`;
      const es = new EventSource(url);
      esRef.current = es;

      es.onopen = () => {
        setIsConnected(true);
        retryRef.current = 0; // reset on successful connection
      };

      es.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data) as LiveJobEvent;
          if (event.type === 'error') {
            console.warn('[LiveActivity] SSE error event:', event);
            return;
          }
          setEvents((prev) => [event, ...prev].slice(0, MAX_EVENTS));
        } catch {
          // heartbeat or malformed — ignore
        }
      };

      es.onerror = () => {
        setIsConnected(false);

        // If browser gave up (CLOSED), manually reconnect with backoff
        if (es.readyState === EventSource.CLOSED) {
          es.close();
          esRef.current = null;
          retryRef.current += 1;

          if (retryRef.current <= MAX_RETRIES && !cancelled) {
            const delay = RETRY_BASE_MS * Math.pow(2, retryRef.current - 1);
            retryTimerRef.current = setTimeout(connect, delay);
          }
          // After MAX_RETRIES, stop trying — UI shows "offline" permanently
        }
        // If CONNECTING, browser is auto-retrying — let it
      };
    }

    connect();

    return () => {
      cancelled = true;
      esRef.current?.close();
      esRef.current = null;
      setIsConnected(false);
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    };
  }, [channel, enabled]);

  return { events, isConnected, clearEvents };
}

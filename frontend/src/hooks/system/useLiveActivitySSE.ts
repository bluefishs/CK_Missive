/**
 * useLiveActivitySSE — 即時 Swarm 轉播 Hook (V-2.2)
 *
 * 透過 EventSource 訂閱 Missive 後端代理的 OpenClaw EventRelay SSE 串流，
 * 即時接收 Agent 任務生命週期事件 (created/running/approved/rejected/completed/failed)。
 *
 * @version 1.0.0
 * @created 2026-03-23
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

export function useLiveActivitySSE(
  channel: string = 'jobs',
  enabled: boolean = true,
): UseLiveActivityReturn {
  const [events, setEvents] = useState<LiveJobEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  const clearEvents = useCallback(() => setEvents([]), []);

  useEffect(() => {
    if (!enabled) {
      esRef.current?.close();
      esRef.current = null;
      setIsConnected(false);
      return;
    }

    const url = `/api${DIGITAL_TWIN_ENDPOINTS.LIVE_ACTIVITY_STREAM}?channel=${channel}`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => setIsConnected(true);

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
      // EventSource auto-reconnects
    };

    return () => {
      es.close();
      esRef.current = null;
      setIsConnected(false);
    };
  }, [channel, enabled]);

  return { events, isConnected, clearEvents };
}

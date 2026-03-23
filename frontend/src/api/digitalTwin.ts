/**
 * Digital Twin API — 透過 Missive 後端代理至 NemoClaw Gateway
 *
 * 前端不直接呼叫 NemoClaw Gateway (CORS + X-Service-Token 認證限制)，
 * 改為呼叫 Missive 後端 /ai/digital-twin/query/stream 代理端點。
 *
 * 流程: POST /ai/digital-twin/query/stream → 後端 FederationClient
 *       → NemoClaw Gateway → SSE 串流回傳
 *
 * @version 2.0.0
 * @created 2026-03-22
 * @updated 2026-03-22 — v2.0 改為後端代理模式 (修復 CORS + Auth)
 */

import { DIGITAL_TWIN_ENDPOINTS } from './endpoints';
import { logger } from '../services/logger';

// ---------------------------------------------------------------------------
// Types — SSOT 在 types/ai.ts，此處 re-export
// ---------------------------------------------------------------------------

export type { DelegateRequest, DigitalTwinStreamCallbacks } from '../types/ai';
import type { DelegateRequest, DigitalTwinStreamCallbacks } from '../types/ai';

// ---------------------------------------------------------------------------
// Core: SSE via Missive backend proxy
// ---------------------------------------------------------------------------

const SSE_TIMEOUT_MS = 120_000;

/**
 * 透過 Missive 後端代理向 NemoClaw Gateway 發送查詢，SSE 串流接收回應。
 *
 * @returns AbortController 供呼叫端取消
 */
export function streamDigitalTwin(
  request: DelegateRequest,
  callbacks: DigitalTwinStreamCallbacks,
): AbortController {
  const controller = new AbortController();
  const startTime = Date.now();

  (async () => {
    try {
      callbacks.onStatus?.('connecting', '正在連接數位分身...');

      // 透過 Missive 後端代理 — apiClient 的 baseURL 是 /api/v1，
      // 但 AI 端點掛在 /api/ai 前綴，需用完整路徑
      const streamUrl = `/api${DIGITAL_TWIN_ENDPOINTS.QUERY_STREAM}`;
      const timeoutId = setTimeout(() => controller.abort(), SSE_TIMEOUT_MS);

      const res = await fetch(streamUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        credentials: 'include', // 帶上 auth cookie
        body: JSON.stringify({
          question: request.question,
          session_id: request.session_id,
          context: request.context,
        }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        clearTimeout(timeoutId);
        const errText = await res.text().catch(() => '');
        callbacks.onError(
          `後端代理回應異常 (HTTP ${res.status}): ${errText.slice(0, 200)}`,
        );
        callbacks.onDone(Date.now() - startTime);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let fullAnswer = '';
      let answered = false;

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          const lines = part.split('\n');
          let dataStr = '';

          for (const line of lines) {
            if (line.startsWith('data: ')) dataStr += line.slice(6);
          }

          if (!dataStr || part.startsWith(':')) continue;

          try {
            const event = JSON.parse(dataStr) as {
              type?: string;
              token?: string;
              message?: string;
              error?: string;
              latency_ms?: number;
              model?: string;
              [key: string]: unknown;
            };

            switch (event.type) {
              case 'status':
                callbacks.onStatus?.('running', event.message || '');
                break;

              case 'token':
                if (event.token) {
                  fullAnswer += event.token;
                  callbacks.onToken(event.token);
                }
                break;

              case 'done':
                clearTimeout(timeoutId);
                answered = true;
                callbacks.onDone(
                  event.latency_ms || Date.now() - startTime,
                  fullAnswer,
                );
                return;

              case 'error':
                callbacks.onError(event.error || '數位分身處理失敗');
                break;

              default:
                logger.log('[DigitalTwin] Unknown event type:', event.type);
            }
          } catch {
            logger.warn(
              '[DigitalTwin] SSE parse error:',
              dataStr.slice(0, 100),
            );
          }
        }
      }

      clearTimeout(timeoutId);
      if (!answered) {
        callbacks.onDone(Date.now() - startTime, fullAnswer || undefined);
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      logger.error('[DigitalTwin] Stream error:', err);
      callbacks.onError('數位分身連線失敗');
      callbacks.onDone(Date.now() - startTime);
    }
  })();

  return controller;
}

// ---------------------------------------------------------------------------
// Human Approval Gate (V-2.1) — TaskJobRecord SSOT 在 types/ai.ts
// ---------------------------------------------------------------------------

export type { TaskJobRecord } from '../types/ai';
import type { TaskJobRecord } from '../types/ai';

export async function getTaskStatus(jobId: string): Promise<{
  success: boolean;
  job?: TaskJobRecord;
  error?: string;
}> {
  const res = await fetch(`/api${DIGITAL_TWIN_ENDPOINTS.TASK_STATUS(jobId)}`, {
    credentials: 'include',
  });
  return res.json();
}

export async function approveTask(
  jobId: string,
  approvedBy?: string,
): Promise<{ success: boolean; error?: string }> {
  const res = await fetch(`/api${DIGITAL_TWIN_ENDPOINTS.TASK_APPROVE(jobId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ approved_by: approvedBy || '' }),
  });
  return res.json();
}

export async function rejectTask(
  jobId: string,
  rejectedBy?: string,
  reason?: string,
): Promise<{ success: boolean; error?: string }> {
  const res = await fetch(`/api${DIGITAL_TWIN_ENDPOINTS.TASK_REJECT(jobId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ rejected_by: rejectedBy || '', reason: reason || '' }),
  });
  return res.json();
}

// ---------------------------------------------------------------------------
// Health check (via backend proxy)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Agent Topology (V-3.1) — SSOT 在 types/ai.ts
// ---------------------------------------------------------------------------

export type { AgentNode, AgentEdge, AgentTopologyResponse } from '../types/ai';
import type { AgentTopologyResponse } from '../types/ai';

export async function getAgentTopology(): Promise<AgentTopologyResponse> {
  const res = await fetch(`/api${DIGITAL_TWIN_ENDPOINTS.AGENT_TOPOLOGY}`, {
    credentials: 'include',
  });
  return res.json();
}

export async function checkGatewayHealth(): Promise<{
  available: boolean;
  latencyMs: number;
  message?: string;
}> {
  const start = Date.now();
  try {
    const res = await fetch(`/api${DIGITAL_TWIN_ENDPOINTS.HEALTH}`, {
      credentials: 'include',
      signal: AbortSignal.timeout(10_000),
    });
    const latencyMs = Date.now() - start;
    if (res.ok) {
      const data = await res.json();
      return {
        available: data.available ?? false,
        latencyMs,
        message: data.available ? undefined : 'Gateway 不可用',
      };
    }
    return { available: false, latencyMs, message: `HTTP ${res.status}` };
  } catch {
    return {
      available: false,
      latencyMs: Date.now() - start,
      message: 'Gateway 無回應',
    };
  }
}

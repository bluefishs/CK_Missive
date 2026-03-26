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
const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 1500;

/**
 * 透過 Missive 後端代理向本地 Agent 發送查詢，SSE 串流接收回應。
 * 支援自動重連（最多 MAX_RETRIES 次）。
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
    let lastError = '';
    for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
      if (controller.signal.aborted) return;

      // 重試延遲
      if (attempt > 0) {
        callbacks.onStatus?.('connecting', `重新連線中 (第 ${attempt} 次)...`);
        await new Promise(r => setTimeout(r, RETRY_DELAY_MS * attempt));
        if (controller.signal.aborted) return;
      }

      const result = await _attemptStream(request, callbacks, controller, startTime);
      if (result === 'success' || result === 'aborted') return;
      lastError = result;
    }

    // 所有重試失敗
    callbacks.onError(lastError || '數位分身連線失敗');
    callbacks.onDone(Date.now() - startTime);
  })();

  return controller;
}

async function _attemptStream(
  request: DelegateRequest,
  callbacks: DigitalTwinStreamCallbacks,
  controller: AbortController,
  startTime: number,
): Promise<'success' | 'aborted' | string> {
  try {
    callbacks.onStatus?.('connecting', '正在連接數位分身...');

    const streamUrl = `/api${DIGITAL_TWIN_ENDPOINTS.QUERY_STREAM}`;
    const timeoutId = setTimeout(() => controller.abort(), SSE_TIMEOUT_MS);

    const res = await fetch(streamUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      credentials: 'include',
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
      return `後端回應異常 (HTTP ${res.status}): ${errText.slice(0, 200)}`;
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
                return 'success';

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
      return 'success';
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return 'aborted';
      logger.error('[DigitalTwin] Stream error (will retry):', err);
      return `連線失敗: ${err instanceof Error ? err.message : String(err)}`;
    }
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
  if (!res.ok) {
    return { success: false, error: `HTTP ${res.status}` };
  }
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
  if (!res.ok) {
    return { success: false, error: `HTTP ${res.status}` };
  }
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
  if (!res.ok) {
    return { success: false, error: `HTTP ${res.status}` };
  }
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
    method: 'POST',
    credentials: 'include',
  });
  if (!res.ok) {
    return { nodes: [], edges: [], meta: { total_nodes: 0, total_edges: 0, timestamp: new Date().toISOString() } };
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// QA Impact Analysis (V-3.3) — SSOT 在 types/ai.ts
// ---------------------------------------------------------------------------

export type { QaAffectedModule, QaImpactResponse } from '../types/ai';
import type { QaImpactResponse } from '../types/ai';

export async function getQaImpact(baseBranch = 'main'): Promise<QaImpactResponse> {
  const res = await fetch(
    `/api${DIGITAL_TWIN_ENDPOINTS.QA_IMPACT}?base_branch=${encodeURIComponent(baseBranch)}`,
    { method: 'POST', credentials: 'include' },
  );
  if (!res.ok) {
    return { success: false, changed_files_count: 0, affected: [], recommendation: 'no_changes', message: `HTTP ${res.status}` };
  }
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
      method: 'POST',
      credentials: 'include',
      signal: AbortSignal.timeout(10_000),
    });
    const latencyMs = Date.now() - start;
    if (res.ok) {
      const data = await res.json();
      // v2.0: health 回傳 local_agent + gateway_available
      const available = data.local_agent ?? data.gateway_available ?? data.available ?? false;
      return {
        available,
        latencyMs,
        message: available ? undefined : (data.gateway_error ?? 'Agent 不可用'),
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

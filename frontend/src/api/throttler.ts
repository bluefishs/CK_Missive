/**
 * 請求節流與重試模組
 *
 * 包含 RequestThrottler（防止請求風暴）和網路錯誤重試邏輯。
 * 從 client.ts 拆分以提升可維護性。
 *
 * @version 1.0.0
 * @date 2026-02-11
 */

import axios, { AxiosError } from 'axios';
import { logger } from '../services/logger';

// ============================================================================
// Request Circuit Breaker（請求熔斷器）
// ============================================================================

/**
 * 請求節流配置
 *
 * 防止前端程式錯誤（如 useEffect 無限迴圈）造成請求風暴，
 * 導致後端 OOM 和全系統連鎖崩潰。
 *
 * @see DEVELOPMENT_GUIDELINES.md 常見錯誤 #10
 */
/** @internal 導出供測試使用 */
export const THROTTLE_CONFIG = {
  /** 同 URL 最小請求間隔 (ms) */
  MIN_INTERVAL_MS: 1000,
  /** 單 URL 滑動窗口內最大請求數 */
  MAX_PER_URL: 20,
  /** 滑動窗口時長 (ms) */
  WINDOW_MS: 10_000,
  /** 全域熔斷器閾值（窗口內總請求數） */
  GLOBAL_MAX: 50,
  /** 熔斷器冷卻時間 (ms) */
  COOLDOWN_MS: 5_000,
};

interface ThrottleRecord {
  timestamps: number[];
  lastData: unknown;
  lastTime: number;
}

/** @internal 導出供測試使用 */
export class RequestThrottler {
  private records = new Map<string, ThrottleRecord>();
  private globalTimestamps: number[] = [];
  private circuitOpenUntil = 0;

  private getKey(method: string | undefined, url: string | undefined): string {
    return `${(method || 'get').toUpperCase()}:${url || ''}`;
  }

  private pruneOld(arr: number[], windowMs: number): number[] {
    const cutoff = Date.now() - windowMs;
    return arr.filter(t => t > cutoff);
  }

  /**
   * 檢查請求是否應被節流
   * @returns null 表示放行，否則返回快取資料或 'reject'
   */
  check(method: string | undefined, url: string | undefined): { action: 'allow' } | { action: 'cache'; data: unknown } | { action: 'reject'; reason: string } {
    const now = Date.now();
    const key = this.getKey(method, url);

    // 全域熔斷器
    if (now < this.circuitOpenUntil) {
      const remaining = Math.ceil((this.circuitOpenUntil - now) / 1000);
      logger.error(`[CircuitBreaker] 熔斷中，剩餘 ${remaining}s - 請檢查是否有 useEffect 無限迴圈`);
      return { action: 'reject', reason: `全域熔斷中 (${remaining}s)` };
    }

    let record = this.records.get(key);
    if (!record) {
      record = { timestamps: [], lastData: null, lastTime: 0 };
      this.records.set(key, record);
    }

    // 清理過期時間戳
    record.timestamps = this.pruneOld(record.timestamps, THROTTLE_CONFIG.WINDOW_MS);
    this.globalTimestamps = this.pruneOld(this.globalTimestamps, THROTTLE_CONFIG.WINDOW_MS);

    // 檢查 1：同 URL 最小間隔
    if (record.lastData && (now - record.lastTime) < THROTTLE_CONFIG.MIN_INTERVAL_MS) {
      return { action: 'cache', data: record.lastData };
    }

    // 檢查 2：單 URL 頻率上限
    if (record.timestamps.length >= THROTTLE_CONFIG.MAX_PER_URL) {
      logger.error(`[Throttle] ${key} 超頻 (${record.timestamps.length}/${THROTTLE_CONFIG.WINDOW_MS}ms) - 疑似無限迴圈`);
      if (record.lastData) {
        return { action: 'cache', data: record.lastData };
      }
      return { action: 'reject', reason: '單 URL 請求過於頻繁' };
    }

    // 檢查 3：全域熔斷
    if (this.globalTimestamps.length >= THROTTLE_CONFIG.GLOBAL_MAX) {
      logger.error(`[CircuitBreaker] 全域請求超限 (${this.globalTimestamps.length}/${THROTTLE_CONFIG.WINDOW_MS}ms) - 啟動熔斷`);
      this.circuitOpenUntil = now + THROTTLE_CONFIG.COOLDOWN_MS;
      return { action: 'reject', reason: '全域熔斷器觸發' };
    }

    // 放行：記錄時間戳
    record.timestamps.push(now);
    this.globalTimestamps.push(now);
    return { action: 'allow' };
  }

  /** 記錄成功回應（供快取使用） */
  recordResponse(method: string | undefined, url: string | undefined, data: unknown): void {
    const key = this.getKey(method, url);
    const record = this.records.get(key);
    if (record) {
      record.lastData = data;
      record.lastTime = Date.now();
    }
  }
}

// ============================================================================
// 網路錯誤重試配置
// ============================================================================

/**
 * 網路錯誤自動重試配置
 *
 * 針對後端重啟期間的 ERR_CONNECTION_REFUSED 等網路錯誤，
 * 使用指數退避策略自動重試，避免使用者看到瞬間的連線失敗。
 *
 * 僅重試網路層錯誤（無回應），不重試伺服器回傳的錯誤（4xx/5xx）。
 */
export const RETRY_CONFIG = {
  /** 最大重試次數 */
  MAX_RETRIES: 3,
  /** 初始延遲 (ms) */
  BASE_DELAY_MS: 1000,
  /** 延遲倍數（指數退避） */
  BACKOFF_MULTIPLIER: 2,
  /** 最大延遲 (ms) */
  MAX_DELAY_MS: 5000,
};

/**
 * 判斷錯誤是否為可重試的網路錯誤
 * 僅在完全無回應時重試（連線被拒、DNS 失敗等）
 */
export function isRetryableNetworkError(error: AxiosError): boolean {
  // 有回應 = 伺服器已回覆，不重試
  if (error.response) return false;
  // 請求超時也不重試（已等待足夠時間）
  if (error.code === 'ECONNABORTED') return false;
  // 用戶主動取消不重試
  if (axios.isCancel(error)) return false;
  // 其他網路錯誤（ERR_CONNECTION_REFUSED 等）可重試
  return true;
}

/**
 * Logger 服務 - 統一日誌管理
 *
 * 功能：
 * - 依據環境自動切換日誌等級
 * - 生產環境自動禁用 debug/log 輸出
 * - 支援分組日誌和效能計時
 * - 統一格式化輸出
 *
 * @version 1.0.0
 * @date 2026-01-11
 */

type LogLevel = 'debug' | 'log' | 'info' | 'warn' | 'error';

interface LoggerConfig {
  enabled: boolean;
  level: LogLevel;
  prefix: string;
  showTimestamp: boolean;
}

// 日誌等級優先順序
const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  log: 1,
  info: 2,
  warn: 3,
  error: 4,
};

// 判斷是否為開發環境
const isDevelopment = (): boolean => {
  return import.meta.env.DEV || import.meta.env.MODE === 'development';
};

// 預設配置
const defaultConfig: LoggerConfig = {
  enabled: true,
  level: isDevelopment() ? 'debug' : 'warn', // 生產環境只顯示 warn 和 error
  prefix: '[CK_Missive]',
  showTimestamp: isDevelopment(),
};

class Logger {
  private config: LoggerConfig;
  private timers: Map<string, number> = new Map();

  constructor(config: Partial<LoggerConfig> = {}) {
    this.config = { ...defaultConfig, ...config };
  }

  /**
   * 更新配置
   */
  setConfig(config: Partial<LoggerConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * 檢查是否應該輸出此等級的日誌
   */
  private shouldLog(level: LogLevel): boolean {
    if (!this.config.enabled) return false;
    return LOG_LEVELS[level] >= LOG_LEVELS[this.config.level];
  }

  /**
   * 格式化日誌訊息
   */
  private formatMessage(level: LogLevel, message: string): string {
    const parts: string[] = [];

    if (this.config.showTimestamp) {
      parts.push(`[${new Date().toISOString()}]`);
    }

    parts.push(this.config.prefix);
    parts.push(`[${level.toUpperCase()}]`);
    parts.push(message);

    return parts.join(' ');
  }

  /**
   * Debug 等級日誌 (僅開發環境)
   */
  debug(message: string, ...args: unknown[]): void {
    if (this.shouldLog('debug')) {
      console.debug(this.formatMessage('debug', message), ...args);
    }
  }

  /**
   * Log 等級日誌 (一般記錄)
   */
  log(message: string, ...args: unknown[]): void {
    if (this.shouldLog('log')) {
      console.log(this.formatMessage('log', message), ...args);
    }
  }

  /**
   * Info 等級日誌 (資訊性訊息)
   */
  info(message: string, ...args: unknown[]): void {
    if (this.shouldLog('info')) {
      console.info(this.formatMessage('info', message), ...args);
    }
  }

  /**
   * Warn 等級日誌 (警告)
   */
  warn(message: string, ...args: unknown[]): void {
    if (this.shouldLog('warn')) {
      console.warn(this.formatMessage('warn', message), ...args);
    }
  }

  /**
   * Error 等級日誌 (錯誤)
   */
  error(message: string, ...args: unknown[]): void {
    if (this.shouldLog('error')) {
      console.error(this.formatMessage('error', message), ...args);
    }
  }

  /**
   * 分組日誌開始
   */
  group(label: string): void {
    if (this.shouldLog('debug')) {
      console.group(this.formatMessage('debug', label));
    }
  }

  /**
   * 分組日誌結束
   */
  groupEnd(): void {
    if (this.shouldLog('debug')) {
      console.groupEnd();
    }
  }

  /**
   * 開始計時
   */
  time(label: string): void {
    if (this.shouldLog('debug')) {
      this.timers.set(label, performance.now());
    }
  }

  /**
   * 結束計時並輸出
   */
  timeEnd(label: string): void {
    if (this.shouldLog('debug')) {
      const startTime = this.timers.get(label);
      if (startTime !== undefined) {
        const duration = performance.now() - startTime;
        this.debug(`${label}: ${duration.toFixed(2)}ms`);
        this.timers.delete(label);
      }
    }
  }

  /**
   * 表格輸出
   */
  table(data: unknown): void {
    if (this.shouldLog('debug')) {
      console.table(data);
    }
  }

  /**
   * 建立帶有自訂前綴的子日誌器
   */
  createChild(prefix: string): Logger {
    return new Logger({
      ...this.config,
      prefix: `${this.config.prefix}[${prefix}]`,
    });
  }
}

// 匯出單例實例
export const logger = new Logger();

// 匯出類別供需要自訂配置時使用
export { Logger };
export type { LoggerConfig, LogLevel };

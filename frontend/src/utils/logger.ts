/* eslint-disable no-console */
/**
 * 日誌工具
 * @description 提供統一的日誌記錄功能
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface Logger {
  debug: (...args: unknown[]) => void;
  info: (...args: unknown[]) => void;
  warn: (...args: unknown[]) => void;
  error: (...args: unknown[]) => void;
  log: (...args: unknown[]) => void;
}

const isDevelopment = import.meta.env.DEV;

const createLogger = (): Logger => {
  const formatMessage = (level: LogLevel): string => {
    const timestamp = new Date().toISOString();
    return `[${timestamp}] [${level.toUpperCase()}]`;
  };

  return {
    debug: (...args: unknown[]) => {
      if (isDevelopment) {
        console.debug(formatMessage('debug'), ...args);
      }
    },
    info: (...args: unknown[]) => {
      if (isDevelopment) {
        console.info(formatMessage('info'), ...args);
      }
    },
    warn: (...args: unknown[]) => {
      console.warn(formatMessage('warn'), ...args);
    },
    error: (...args: unknown[]) => {
      console.error(formatMessage('error'), ...args);
    },
    log: (...args: unknown[]) => {
      if (isDevelopment) {
        console.log(...args);
      }
    },
  };
};

export const logger = createLogger();
export default logger;

/* eslint-disable no-console */
/**
 * 日誌工具
 * @description 提供統一的日誌記錄功能
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface Logger {
  debug: (...args: any[]) => void;
  info: (...args: any[]) => void;
  warn: (...args: any[]) => void;
  error: (...args: any[]) => void;
  log: (...args: any[]) => void;
}

const isDevelopment = import.meta.env.DEV;

const createLogger = (): Logger => {
  const formatMessage = (level: LogLevel, ...args: any[]): string => {
    const timestamp = new Date().toISOString();
    return `[${timestamp}] [${level.toUpperCase()}]`;
  };

  return {
    debug: (...args: any[]) => {
      if (isDevelopment) {
        console.debug(formatMessage('debug'), ...args);
      }
    },
    info: (...args: any[]) => {
      if (isDevelopment) {
        console.info(formatMessage('info'), ...args);
      }
    },
    warn: (...args: any[]) => {
      console.warn(formatMessage('warn'), ...args);
    },
    error: (...args: any[]) => {
      console.error(formatMessage('error'), ...args);
    },
    log: (...args: any[]) => {
      if (isDevelopment) {
        console.log(...args);
      }
    },
  };
};

export const logger = createLogger();
export default logger;

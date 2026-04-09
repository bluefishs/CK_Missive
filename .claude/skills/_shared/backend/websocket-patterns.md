# WebSocket Patterns Skill

**技能名稱**：WebSocket 模式
**用途**：正確處理 WebSocket 連線、StrictMode 相容性
**適用場景**：即時通訊、AI 對話串流、即時資料推送

---

## 一、React StrictMode 問題

### 1.1 問題描述

React 18+ 的 StrictMode 會在開發環境中雙重渲染元件，導致：
- WebSocket 連線建立後立即關閉
- Console 警告：`WebSocket closed before established`
- 連線狀態不穩定

### 1.2 解決方案架構

```typescript
// frontend/src/hooks/useWebSocket.ts

import { useRef, useEffect, useCallback } from 'react';

export const useWebSocket = (url: string, options?: WebSocketOptions) => {
  const wsRef = useRef<WebSocket | null>(null);

  // ✅ 關鍵：追蹤元件掛載狀態
  const isMountedRef = useRef(true);

  // ✅ 關鍵：追蹤是否為有意斷開
  const isIntentionalDisconnectRef = useRef(false);

  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttemptRef = useRef(0);

  // ... 其他實作
};
```

---

## 二、完整實作模式

### 2.1 Hook 核心結構

```typescript
export const useWebSocket = (url: string) => {
  const wsRef = useRef<WebSocket | null>(null);
  const isMountedRef = useRef(true);
  const isIntentionalDisconnectRef = useRef(false);
  const reconnectAttemptRef = useRef(0);

  const [connectionState, setConnectionState] = useState<ConnectionState>({
    isConnected: false,
    isConnecting: false,
    error: null,
  });

  // 連線函數
  const connect = useCallback(() => {
    // 防止未掛載時連線
    if (!isMountedRef.current) {
      console.debug('[WebSocket] 元件已卸載，跳過連線');
      return;
    }

    // 防止重複連線
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionState(prev => ({ ...prev, isConnecting: true }));

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        if (!isMountedRef.current) {
          ws.close();
          return;
        }
        setConnectionState({
          isConnected: true,
          isConnecting: false,
          error: null,
        });
        reconnectAttemptRef.current = 0;
      };

      ws.onclose = (event) => {
        // ✅ 關鍵：判斷是否應該重連
        const shouldSkipReconnect =
          !isMountedRef.current ||
          isIntentionalDisconnectRef.current ||
          event.wasClean;

        if (shouldSkipReconnect) {
          console.debug('[WebSocket] 跳過重連', {
            mounted: isMountedRef.current,
            intentional: isIntentionalDisconnectRef.current,
            wasClean: event.wasClean,
          });
          return;
        }

        // 執行重連邏輯
        scheduleReconnect();
      };

      ws.onerror = (error) => {
        if (!isMountedRef.current) return;
        setConnectionState(prev => ({
          ...prev,
          error: error,
          isConnecting: false,
        }));
      };

      wsRef.current = ws;
    } catch (error) {
      setConnectionState(prev => ({
        ...prev,
        error: error as Error,
        isConnecting: false,
      }));
    }
  }, [url]);

  // 斷開函數
  const disconnect = useCallback(() => {
    isIntentionalDisconnectRef.current = true;

    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }

    setConnectionState({
      isConnected: false,
      isConnecting: false,
      error: null,
    });
  }, []);

  // 元件生命週期
  useEffect(() => {
    isMountedRef.current = true;
    isIntentionalDisconnectRef.current = false;

    connect();

    return () => {
      // ✅ 關鍵：清理時標記狀態
      isMountedRef.current = false;
      isIntentionalDisconnectRef.current = true;

      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
        wsRef.current = null;
      }
    };
  }, [connect]);

  return {
    connectionState,
    connect,
    disconnect,
    send: (data: string) => wsRef.current?.send(data),
  };
};
```

### 2.2 重連策略

```typescript
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000]; // 指數退避

const scheduleReconnect = useCallback(() => {
  if (reconnectAttemptRef.current >= MAX_RECONNECT_ATTEMPTS) {
    console.warn('[WebSocket] 達到最大重連次數');
    setConnectionState(prev => ({
      ...prev,
      error: new Error('達到最大重連次數'),
    }));
    return;
  }

  const delay = RECONNECT_DELAYS[reconnectAttemptRef.current] || 16000;
  reconnectAttemptRef.current += 1;

  console.debug(`[WebSocket] ${delay}ms 後重連 (第 ${reconnectAttemptRef.current} 次)`);

  reconnectTimeoutRef.current = setTimeout(() => {
    if (isMountedRef.current && !isIntentionalDisconnectRef.current) {
      connect();
    }
  }, delay);
}, [connect]);
```

---

## 三、錯誤碼處理

### 3.1 錯誤碼定義

```typescript
// frontend/src/constants/errorCodes.ts

// WebSocket 相關 (9xxx)
ERR_9101: 'WebSocket 連線中斷'
ERR_9102: 'WebSocket 認證失敗'
ERR_9103: 'WebSocket 連線逾時'
```

### 3.2 錯誤處理整合

```typescript
import { ERROR_CODES } from '@/constants/errorCodes';

ws.onclose = (event) => {
  if (event.code === 1006) {
    // 異常關閉
    handleError({
      code: 'ERR_9101',
      message: ERROR_CODES.ERR_9101,
    });
  } else if (event.code === 4001) {
    // 認證失敗
    handleError({
      code: 'ERR_9102',
      message: ERROR_CODES.ERR_9102,
    });
  }
};
```

---

## 四、AI 對話串流模式

### 4.1 串流訊息處理

```typescript
interface StreamMessage {
  type: 'start' | 'chunk' | 'end' | 'error';
  content?: string;
  messageId?: string;
}

const useAIStream = () => {
  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);

  const handleMessage = useCallback((event: MessageEvent) => {
    const message: StreamMessage = JSON.parse(event.data);

    switch (message.type) {
      case 'start':
        setIsStreaming(true);
        setStreamingContent('');
        break;

      case 'chunk':
        setStreamingContent(prev => prev + message.content);
        break;

      case 'end':
        setIsStreaming(false);
        break;

      case 'error':
        setIsStreaming(false);
        handleError(message);
        break;
    }
  }, []);

  return { streamingContent, isStreaming };
};
```

---

## 五、除錯技巧

### 5.1 開發環境除錯

```typescript
// 啟用詳細日誌
const DEBUG = process.env.NODE_ENV === 'development';

const log = (message: string, data?: unknown) => {
  if (DEBUG) {
    console.debug(`[WebSocket] ${message}`, data);
  }
};

// 在關鍵點加入日誌
ws.onopen = () => log('連線建立');
ws.onclose = (e) => log('連線關閉', { code: e.code, reason: e.reason });
ws.onerror = (e) => log('連線錯誤', e);
```

### 5.2 StrictMode 檢測

```typescript
// 檢測是否在 StrictMode 下
const isStrictMode = useRef(false);

useEffect(() => {
  if (isStrictMode.current) {
    console.debug('[WebSocket] StrictMode 重新渲染');
  }
  isStrictMode.current = true;
}, []);
```

### 5.3 常見問題診斷

| 症狀 | 可能原因 | 解決方案 |
|------|----------|----------|
| 連線建立後立即關閉 | StrictMode 雙重渲染 | 使用 `isMountedRef` |
| 無限重連 | 未檢查 `wasClean` | 加入 `shouldSkipReconnect` |
| 記憶體洩漏 | 未清理 timeout | 在 cleanup 中 `clearTimeout` |
| 狀態不同步 | 未檢查 mounted | 更新狀態前檢查 `isMountedRef` |

---

## 六、驗證清單

### 實作完成檢查

```
[ ] isMountedRef 正確初始化和清理
[ ] isIntentionalDisconnectRef 在有意斷開時設為 true
[ ] onclose 中正確判斷 shouldSkipReconnect
[ ] cleanup 函數清理所有 ref 和 timeout
[ ] 開發環境下無 console 警告
[ ] 生產環境下連線穩定
```

---

**建立日期**：2025-12-24
**最後更新**：2025-12-24

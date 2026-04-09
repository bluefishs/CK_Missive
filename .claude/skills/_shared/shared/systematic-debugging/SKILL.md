# 系統化除錯技能

## 概述
CK_GPS 專案的系統化除錯方法和工具。

## 除錯策略

### 1. 問題定位流程

```
1. 重現問題
   ↓
2. 縮小範圍
   ↓
3. 形成假設
   ↓
4. 驗證假設
   ↓
5. 修復並測試
```

### 2. 常見問題類型

#### 前端問題
- **渲染問題**: React DevTools 檢查
- **狀態問題**: Console.log 或 React DevTools
- **網路問題**: Network Tab 檢查
- **效能問題**: Performance Tab 分析

#### 後端問題
- **API 錯誤**: 檢查 request/response
- **資料庫問題**: 檢查 SQL 查詢
- **認證問題**: 檢查 JWT/Session
- **效能問題**: 檢查查詢計劃

## 除錯工具

### VS Code 除錯

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "node",
      "request": "attach",
      "name": "Attach to Backend",
      "port": 9229,
      "restart": true
    }
  ]
}
```

### Node.js Inspector

```bash
# 啟動帶除錯器的後端
node --inspect=0.0.0.0:9229 SimpleApiServer.js
```

### PostgreSQL 查詢分析

```sql
-- 檢查查詢計劃
EXPLAIN ANALYZE SELECT * FROM control_points WHERE city = '基隆市';

-- 檢查索引使用
SELECT * FROM pg_stat_user_indexes WHERE relname = 'control_points';
```

## 日誌策略

### 前端日誌
```typescript
// 使用結構化日誌
const logger = {
  info: (msg: string, data?: object) => {
    if (import.meta.env.DEV) {
      console.log(`[INFO] ${msg}`, data);
    }
  },
  error: (msg: string, error: Error) => {
    console.error(`[ERROR] ${msg}`, error);
    // 生產環境發送到監控系統
  }
};
```

### 後端日誌
```typescript
// 使用 Winston
import winston from 'winston';

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' })
  ]
});
```

## 常見問題速查

| 症狀 | 可能原因 | 檢查方式 |
|------|---------|---------|
| API 返回 500 | 資料庫連接失敗 | 檢查 DB_HOST 配置 |
| 頁面空白 | JS 錯誤 | Console 檢查 |
| 資料不更新 | 快取問題 | 清除 Redis |
| 地圖不顯示 | API Key 問題 | 檢查 Leaflet 配置 |

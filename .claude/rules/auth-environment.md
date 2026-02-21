# 認證與環境檢測規範

## 環境類型定義

| 環境類型 | 判斷條件 | 認證要求 |
|----------|----------|----------|
| `localhost` | hostname = localhost / 127.0.0.1 | Google OAuth |
| `internal` | 內網 IP (10.x / 172.16-31.x / 192.168.x) | **免認證** |
| `ngrok` | *.ngrok.io / *.ngrok-free.app | Google OAuth |
| `public` | 其他 | Google OAuth |

## 集中式認證檢測 (必須遵守)

**所有認證相關判斷必須使用 `config/env.ts` 的共用函數：**

```typescript
// ✅ 正確 - 使用共用函數
import { isAuthDisabled, isInternalIP, detectEnvironment } from '../config/env';

const authDisabled = isAuthDisabled();  // 自動判斷是否停用認證
const envType = detectEnvironment();    // 取得環境類型

// ❌ 禁止 - 自行定義檢測邏輯
const isInternal = () => { /* 重複的 IP 檢測邏輯 */ };
const authDisabled = import.meta.env.VITE_AUTH_DISABLED === 'true';
```

## 內網 IP 規則

```typescript
// config/env.ts 中的標準定義
const internalIPPatterns = [
  /^10\./,                           // 10.0.0.0 - 10.255.255.255 (Class A)
  /^172\.(1[6-9]|2[0-9]|3[0-1])\./,  // 172.16.0.0 - 172.31.255.255 (Class B)
  /^192\.168\./                       // 192.168.0.0 - 192.168.255.255 (Class C)
];
```

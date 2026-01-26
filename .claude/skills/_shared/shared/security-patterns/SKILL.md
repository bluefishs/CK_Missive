---
name: security-patterns
description: 安全最佳實踐和常見漏洞防護
version: 1.0.0
category: shared
triggers:
  - 安全模式
  - security patterns
  - JWT
  - 認證
  - 授權
  - authentication
updated: 2026-01-22
---

# 安全模式技能

> **用途**: 安全最佳實踐和常見漏洞防護
> **觸發**: 安全模式, security patterns, JWT, 認證
> **版本**: 1.0.0
> **分類**: shared

## 概述
專案的安全最佳實踐和常見漏洞防護。

## 認證與授權

### JWT 實作

```typescript
// services/auth.service.ts
import jwt from 'jsonwebtoken';

const JWT_SECRET = process.env.JWT_SECRET;
const JWT_EXPIRES_IN = '24h';

// 確保 JWT_SECRET 已配置
if (!JWT_SECRET || JWT_SECRET.length < 32) {
  throw new Error('JWT_SECRET must be at least 32 characters');
}

export function generateToken(payload: TokenPayload): string {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });
}

export function verifyToken(token: string): TokenPayload {
  return jwt.verify(token, JWT_SECRET) as TokenPayload;
}
```

### 認證中間件

```typescript
// middleware/auth.middleware.ts
import { Request, Response, NextFunction } from 'express';
import { verifyToken } from '../services/auth.service';

export const authenticate = (req: Request, res: Response, next: NextFunction) => {
  const authHeader = req.headers.authorization;

  if (!authHeader?.startsWith('Bearer ')) {
    return res.status(401).json({
      success: false,
      error: { code: 'UNAUTHORIZED', message: '未提供認證令牌' }
    });
  }

  try {
    const token = authHeader.slice(7);
    const payload = verifyToken(token);
    req.user = payload;
    next();
  } catch (error) {
    return res.status(401).json({
      success: false,
      error: { code: 'INVALID_TOKEN', message: '無效的認證令牌' }
    });
  }
};
```

## 輸入驗證

### 請求參數驗證

```typescript
// 使用 Joi 驗證
import Joi from 'joi';

const querySchema = Joi.object({
  city: Joi.string().max(50).pattern(/^[\u4e00-\u9fa5]+$/),
  page: Joi.number().integer().min(1).max(1000).default(1),
  limit: Joi.number().integer().min(1).max(100).default(20)
});

// 防止 NoSQL 注入
const sanitize = (input: string): string => {
  return input.replace(/[<>'"&]/g, '');
};
```

### SQL 注入防護

```typescript
// ✅ 使用參數化查詢
await pool.query(
  'SELECT * FROM users WHERE username = $1',
  [username]
);

// ❌ 避免字串拼接
await pool.query(`SELECT * FROM users WHERE username = '${username}'`);
```

## XSS 防護

### 前端輸出編碼

```typescript
// React 自動處理大部分 XSS
// 但使用 dangerouslySetInnerHTML 時需特別注意

import DOMPurify from 'dompurify';

// 清理 HTML 內容
const sanitizedHtml = DOMPurify.sanitize(userInput);

<div dangerouslySetInnerHTML={{ __html: sanitizedHtml }} />
```

### 後端響應頭

```typescript
// 設定安全響應頭
app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Content-Security-Policy', "default-src 'self'");
  next();
});
```

## 敏感資料處理

### 環境變數管理

```typescript
// ✅ 從環境變數讀取
const dbPassword = process.env.DB_PASSWORD;

// ❌ 避免硬編碼
const dbPassword = '123456';

// 啟動時驗證必要配置
const requiredEnvVars = ['DB_PASSWORD', 'JWT_SECRET', 'REDIS_PASSWORD'];
requiredEnvVars.forEach(varName => {
  if (!process.env[varName]) {
    throw new Error(`Missing required environment variable: ${varName}`);
  }
});
```

### 密碼處理

```typescript
import bcrypt from 'bcrypt';

const SALT_ROUNDS = 12;

// 加密密碼
export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, SALT_ROUNDS);
}

// 驗證密碼
export async function verifyPassword(
  password: string,
  hash: string
): Promise<boolean> {
  return bcrypt.compare(password, hash);
}
```

## 安全檢查清單

### 必須項目
- [ ] 無硬編碼密碼
- [ ] JWT 使用強密鑰 (≥32 字元)
- [ ] SQL 使用參數化查詢
- [ ] 輸入驗證完整
- [ ] HTTPS 強制啟用（生產環境）

### 建議項目
- [ ] Rate limiting 實作
- [ ] 安全響應頭配置
- [ ] 錯誤訊息不洩漏敏感資訊
- [ ] 日誌脫敏處理
- [ ] 定期依賴安全掃描

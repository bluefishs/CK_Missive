# Express API 模式技能

## 概述
CK_GPS 後端的 Express.js API 開發最佳實踐。

## API 架構

### 分層結構
```
routes/       → 路由定義和請求驗證
controllers/  → 業務邏輯協調
services/     → 核心業務邏輯
config/       → 資料庫和配置管理
```

## 路由模式

### 1. RESTful 路由定義

```typescript
// routes/v1/controlPoints.routes.ts
import { Router } from 'express';
import { ControlPointsController } from '../controllers';
import { validateRequest } from '../middleware';

const router = Router();

router.get('/', ControlPointsController.list);
router.get('/:id', ControlPointsController.getById);
router.post('/', validateRequest(createSchema), ControlPointsController.create);
router.put('/:id', validateRequest(updateSchema), ControlPointsController.update);
router.delete('/:id', ControlPointsController.delete);

export default router;
```

### 2. 請求驗證

```typescript
// middleware/validateRequest.ts
import { Request, Response, NextFunction } from 'express';
import Joi from 'joi';

export const validateRequest = (schema: Joi.Schema) => {
  return (req: Request, res: Response, next: NextFunction) => {
    const { error } = schema.validate(req.body);
    if (error) {
      return res.status(400).json({
        success: false,
        error: {
          code: 'VALIDATION_ERROR',
          message: error.details[0].message
        }
      });
    }
    next();
  };
};

// 驗證 Schema 定義
export const createControlPointSchema = Joi.object({
  point_no: Joi.string().pattern(/^[A-Z]\d{4}$/).required(),
  city: Joi.string().max(50).required(),
  lat: Joi.number().min(-90).max(90).required(),
  lng: Joi.number().min(-180).max(180).required()
});
```

## 控制器模式

```typescript
// controllers/controlPoints.controller.ts
import { Request, Response } from 'express';
import { ControlPointService } from '../services';

export class ControlPointsController {
  static async list(req: Request, res: Response) {
    try {
      const { city, page = 1, limit = 20 } = req.query;

      // 參數驗證
      const pageNum = Math.max(1, parseInt(page as string) || 1);
      const limitNum = Math.min(100, Math.max(1, parseInt(limit as string) || 20));

      const result = await ControlPointService.findAll({
        city: city as string,
        page: pageNum,
        limit: limitNum
      });

      res.json({
        success: true,
        data: result.data,
        pagination: {
          page: pageNum,
          limit: limitNum,
          total: result.total
        }
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: {
          code: 'INTERNAL_ERROR',
          message: '伺服器錯誤'
        }
      });
    }
  }
}
```

## 錯誤處理

### 統一錯誤格式

```typescript
// middleware/errorHandler.ts
import { Request, Response, NextFunction } from 'express';

export class AppError extends Error {
  constructor(
    public statusCode: number,
    public code: string,
    message: string
  ) {
    super(message);
  }
}

export const errorHandler = (
  err: Error,
  req: Request,
  res: Response,
  next: NextFunction
) => {
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      success: false,
      error: {
        code: err.code,
        message: err.message
      }
    });
  }

  console.error('Unhandled error:', err);
  res.status(500).json({
    success: false,
    error: {
      code: 'INTERNAL_ERROR',
      message: '伺服器錯誤'
    }
  });
};
```

## 回應格式標準

### 成功回應
```json
{
  "success": true,
  "data": { ... },
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100
  }
}
```

### 錯誤回應
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "點號格式錯誤"
  }
}
```

## 常用 HTTP 狀態碼

| 狀態碼 | 使用情境 |
|--------|---------|
| 200 | 成功 |
| 201 | 創建成功 |
| 400 | 請求參數錯誤 |
| 401 | 未認證 |
| 403 | 無權限 |
| 404 | 資源不存在 |
| 500 | 伺服器錯誤 |

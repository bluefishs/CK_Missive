# PostgreSQL 模式技能

## 概述
CK_GPS 專案的 PostgreSQL 資料庫最佳實踐。

## 連接配置

### 連接池設定

```typescript
// config/database.ts
import { Pool } from 'pg';

const pool = new Pool({
  user: process.env.DB_USER || 'postgres',
  host: process.env.DB_HOST || 'localhost',
  database: process.env.DB_NAME || 'MOI_GPS',
  password: process.env.DB_PASSWORD,
  port: parseInt(process.env.DB_PORT || '5432'),

  // 連接池配置
  max: 20,                    // 最大連接數
  idleTimeoutMillis: 30000,   // 閒置超時
  connectionTimeoutMillis: 5000,

  // 編碼設定
  client_encoding: 'UTF8'
});

export default pool;
```

## 查詢模式

### 1. 參數化查詢（防止 SQL 注入）

```typescript
// ✅ 正確方式
const result = await pool.query(
  'SELECT * FROM control_points WHERE city = $1 AND status = $2',
  [city, status]
);

// ❌ 錯誤方式（SQL 注入風險）
const result = await pool.query(
  `SELECT * FROM control_points WHERE city = '${city}'`
);
```

### 2. 分頁查詢

```typescript
async function findWithPagination(page: number, limit: number, filters: object) {
  const offset = (page - 1) * limit;

  // 動態建構 WHERE 子句
  const conditions: string[] = [];
  const values: any[] = [];
  let paramIndex = 1;

  if (filters.city) {
    conditions.push(`city = $${paramIndex++}`);
    values.push(filters.city);
  }

  const whereClause = conditions.length
    ? `WHERE ${conditions.join(' AND ')}`
    : '';

  // 計算總數
  const countResult = await pool.query(
    `SELECT COUNT(*) FROM control_points ${whereClause}`,
    values
  );

  // 查詢資料
  const dataResult = await pool.query(
    `SELECT * FROM control_points ${whereClause}
     ORDER BY created_at DESC
     LIMIT $${paramIndex++} OFFSET $${paramIndex}`,
    [...values, limit, offset]
  );

  return {
    data: dataResult.rows,
    total: parseInt(countResult.rows[0].count)
  };
}
```

### 3. 交易處理

```typescript
async function createWithRelations(pointData: object, coordData: object) {
  const client = await pool.connect();

  try {
    await client.query('BEGIN');

    // 插入主表
    const pointResult = await client.query(
      'INSERT INTO control_points (point_no, city) VALUES ($1, $2) RETURNING id',
      [pointData.point_no, pointData.city]
    );

    const pointId = pointResult.rows[0].id;

    // 插入關聯表
    await client.query(
      'INSERT INTO coordinates (point_id, lat, lng) VALUES ($1, $2, $3)',
      [pointId, coordData.lat, coordData.lng]
    );

    await client.query('COMMIT');
    return pointId;
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
}
```

## 效能優化

### 索引策略

```sql
-- 常用查詢欄位建立索引
CREATE INDEX idx_control_points_city ON control_points(city);
CREATE INDEX idx_control_points_status ON control_points(status);

-- 複合索引（多條件查詢）
CREATE INDEX idx_control_points_city_status ON control_points(city, status);

-- 部分索引（只索引活躍資料）
CREATE INDEX idx_control_points_active ON control_points(city)
WHERE status = 'active';
```

### 查詢分析

```sql
-- 檢查查詢計劃
EXPLAIN ANALYZE
SELECT * FROM control_points
WHERE city = '基隆市' AND status = 'active';

-- 檢查索引使用情況
SELECT
  schemaname, tablename, indexname,
  idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'control_points';
```

## CK_GPS 資料庫結構

### 主要表格

| 表格 | 說明 | 主鍵 |
|------|------|------|
| control_points | 控制點主表 | id |
| control_point_details | 詳細資訊 | id |
| coordinates | 座標資料 | id |
| images | 控制點照片 | id |
| measurement_plans | 測量計劃 | id |

### 常用查詢

```sql
-- 查詢控制點及其座標
SELECT
  cp.point_no, cp.city, cp.status,
  c.lat, c.lng, c.elevation
FROM control_points cp
LEFT JOIN coordinates c ON cp.id = c.point_id
WHERE cp.city = $1;

-- 統計各城市控制點數量
SELECT city, COUNT(*) as count
FROM control_points
GROUP BY city
ORDER BY count DESC;
```

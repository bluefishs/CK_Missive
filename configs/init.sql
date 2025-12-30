-- 初始化 PostgreSQL 資料庫
-- 設定編碼和語言環境

-- 創建擴展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 設定時區
SET timezone = 'Asia/Taipei';

-- 創建索引以提升性能
-- 這些索引會在 SQLAlchemy 創建表格後自動建立

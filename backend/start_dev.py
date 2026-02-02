#!/usr/bin/env python3
"""
後端開發伺服器啟動腳本
設定正確的環境變數和數據庫連接

@version 2.0.0 - 安全性修正：移除硬編碼密碼 (2026-02-02)
"""
import os
import sys
import logging
from dotenv import load_dotenv
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv('../.env')

# 從 .env 讀取資料庫設定（不硬編碼）
db_user = os.environ.get('POSTGRES_USER', '')
db_password = os.environ.get('POSTGRES_PASSWORD', '')
db_host = os.environ.get('POSTGRES_HOST', 'localhost')
db_port = os.environ.get('POSTGRES_PORT', '5434')
db_name = os.environ.get('POSTGRES_DB', '')

# 驗證必要的環境變數
if not db_user or not db_password or not db_name:
    logger.error("❌ 缺少必要的資料庫設定，請確認 .env 檔案包含:")
    logger.error("   - POSTGRES_USER")
    logger.error("   - POSTGRES_PASSWORD")
    logger.error("   - POSTGRES_DB")
    sys.exit(1)

# 設定開發模式的數據庫連接
os.environ['DATABASE_URL'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
os.environ['DEBUG'] = 'True'
os.environ['AUTH_DISABLED'] = os.environ.get('AUTH_DISABLED', 'false')

logger.info("Starting backend server with:")
logger.info(f"  DATABASE_URL: postgresql://{db_user}:****@{db_host}:{db_port}/{db_name}")
logger.info(f"  DEBUG: {os.environ.get('DEBUG')}")
logger.info(f"  AUTH_DISABLED: {os.environ.get('AUTH_DISABLED')}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
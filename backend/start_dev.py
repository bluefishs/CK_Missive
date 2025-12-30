#!/usr/bin/env python3
"""
後端開發伺服器啟動腳本
設定正確的環境變數和數據庫連接
"""
import os
import sys
from dotenv import load_dotenv
import uvicorn

# 載入環境變數
load_dotenv('../.env')

# 設定開發模式的數據庫連接
os.environ['DATABASE_URL'] = 'postgresql://ck_user:ck_password@localhost:5434/ck_documents'
os.environ['DEBUG'] = 'True'
os.environ['AUTH_DISABLED'] = 'true'

print("Starting backend server with:")
print(f"DATABASE_URL: {os.environ.get('DATABASE_URL')}")
print(f"DEBUG: {os.environ.get('DEBUG')}")
print(f"AUTH_DISABLED: {os.environ.get('AUTH_DISABLED')}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
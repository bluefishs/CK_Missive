#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系統配置檢查工具 - 簡化版本
"""

import os
import sys
import json
from pathlib import Path

def check_file_exists(file_path, description=""):
    """檢查檔案是否存在"""
    exists = Path(file_path).exists()
    status = "OK" if exists else "MISSING"
    print(f"[{status}] {file_path} - {description}")
    return exists

def parse_env_file(file_path):
    """解析環境變數檔案"""
    env_vars = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except Exception as e:
        print(f"[ERROR] 無法讀取 {file_path}: {e}")
    return env_vars

def main():
    print("=== 乾坤測繪系統配置檢查 ===")

    # 1. 檢查必要檔案
    print("\n1. 檢查必要檔案:")
    required_files = {
        ".env": "主環境配置",
        ".env.master": "配置範本",
        "docker-compose.unified.yml": "統一Docker配置",
        "docker-compose.dev.yml": "開發環境配置",
        "port-config.json": "端口配置",
        "backend/Dockerfile.unified": "後端映像",
        "frontend/Dockerfile.unified": "前端映像"
    }

    missing_files = []
    for file_path, desc in required_files.items():
        if not check_file_exists(file_path, desc):
            missing_files.append(file_path)

    # 2. 檢查環境變數
    print("\n2. 檢查環境變數:")
    if Path(".env").exists():
        env_vars = parse_env_file(".env")
        critical_vars = [
            "COMPOSE_PROJECT_NAME", "FRONTEND_HOST_PORT",
            "BACKEND_HOST_PORT", "POSTGRES_HOST_PORT",
            "DATABASE_URL", "VITE_API_BASE_URL"
        ]

        for var in critical_vars:
            if var in env_vars:
                print(f"[OK] {var} = {env_vars[var]}")
            else:
                print(f"[MISSING] {var}")
    else:
        print("[ERROR] .env 檔案不存在")

    # 3. 檢查端口配置
    print("\n3. 檢查端口配置:")
    if Path("port-config.json").exists():
        try:
            with open("port-config.json", 'r', encoding='utf-8') as f:
                port_config = json.load(f)

            services = port_config.get("services", {})
            for service, config in services.items():
                port = config.get("port", "未定義")
                print(f"[OK] {service}: {port}")
        except Exception as e:
            print(f"[ERROR] 無法讀取端口配置: {e}")
    else:
        print("[ERROR] port-config.json 不存在")

    # 4. 總結
    print("\n=== 檢查總結 ===")
    if missing_files:
        print(f"缺少檔案: {len(missing_files)} 個")
        for file in missing_files:
            print(f"  - {file}")
    else:
        print("所有必要檔案都存在")

    # 5. 建議
    print("\n=== 建議 ===")
    if missing_files:
        print("1. 請確認缺少的檔案是否需要創建")
        print("2. 檢查是否在正確的專案目錄中執行")

    if not Path(".env").exists() and Path(".env.master").exists():
        print("3. 建議執行: copy .env.master .env")

    print("4. 可執行完整測試: python system-config-test.py")
    print("5. 可執行服務監控: python dev-monitor.py")

if __name__ == "__main__":
    main()
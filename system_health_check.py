#!/usr/bin/env python3
"""
乾坤測繪公文管理系統 - 系統健康檢查腳本
檢查所有服務狀態，確保系統正常運行
"""

import requests
import json
import subprocess
import time
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class HealthCheck:
    name: str
    url: str
    expected_status: int = 200
    timeout: int = 10

def check_docker_services() -> Dict[str, bool]:
    """檢查Docker服務狀態"""
    print("\n🔍 檢查 Docker 服務狀態...")

    services = {
        "ck_missive_postgres": False,
        "ck_missive_redis": False,
        "ck_missive_backend": False,
        "ck_missive_frontend": False,
        "ck_missive_adminer": False
    }

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "json"],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line:
                    container = json.loads(line)
                    name = container.get('Names', '')
                    state = container.get('State', '')

                    if name in services:
                        services[name] = (state == 'running')
                        status = "✅ 運行中" if services[name] else "❌ 停止"
                        print(f"  {name}: {status}")

    except Exception as e:
        print(f"❌ Docker 檢查失敗: {e}")

    return services

def check_api_endpoints() -> Dict[str, bool]:
    """檢查API端點狀態"""
    print("\n🔍 檢查 API 端點...")

    endpoints = [
        HealthCheck("健康檢查", "http://localhost:8001/health"),
        HealthCheck("CSRF Token", "http://localhost:8001/api/secure-site-management/csrf-token", timeout=5),
        HealthCheck("用戶認證", "http://localhost:8001/api/auth/me"),
        HealthCheck("前端服務", "http://localhost:3000", timeout=5),
    ]

    results = {}

    for check in endpoints:
        try:
            if "csrf-token" in check.url:
                # POST 請求
                response = requests.post(
                    check.url,
                    json={},
                    timeout=check.timeout
                )
            else:
                # GET 請求
                response = requests.get(check.url, timeout=check.timeout)

            success = response.status_code == check.expected_status
            results[check.name] = success

            status = "✅ 正常" if success else f"❌ 失敗 ({response.status_code})"
            print(f"  {check.name}: {status}")

            if not success:
                print(f"    詳細: {response.text[:100]}...")

        except requests.exceptions.RequestException as e:
            results[check.name] = False
            print(f"  {check.name}: ❌ 連接失敗 - {str(e)[:50]}...")

    return results

def check_frontend_build() -> bool:
    """檢查前端建置狀態"""
    print("\n🔍 檢查前端建置...")

    try:
        # 檢查dist目錄是否存在
        import os
        dist_path = "frontend/dist"

        if os.path.exists(dist_path):
            files = os.listdir(dist_path)
            if "index.html" in files:
                print("  ✅ 前端建置完成")
                return True
            else:
                print("  ❌ 缺少 index.html")
                return False
        else:
            print("  ❌ dist 目錄不存在")
            return False

    except Exception as e:
        print(f"  ❌ 檢查失敗: {e}")
        return False

def check_configuration() -> Dict[str, bool]:
    """檢查配置檔案"""
    print("\n🔍 檢查配置檔案...")

    import os

    configs = {
        ".env": os.path.exists(".env"),
        ".env.master": os.path.exists(".env.master"),
        "docker-compose.unified.yml": os.path.exists("docker-compose.unified.yml"),
        "backend/Dockerfile.unified": os.path.exists("backend/Dockerfile.unified"),
        "frontend/Dockerfile.unified": os.path.exists("frontend/Dockerfile.unified"),
    }

    for name, exists in configs.items():
        status = "✅ 存在" if exists else "❌ 缺失"
        print(f"  {name}: {status}")

    return configs

def generate_report(docker_services: Dict, api_results: Dict, frontend_build: bool, configs: Dict):
    """生成系統報告"""
    print("\n" + "="*60)
    print("🎯 系統健康檢查報告")
    print("="*60)

    # Docker 服務統計
    docker_healthy = sum(docker_services.values())
    docker_total = len(docker_services)
    print(f"\n📦 Docker 服務: {docker_healthy}/{docker_total} 正常運行")

    # API 端點統計
    api_healthy = sum(api_results.values())
    api_total = len(api_results)
    print(f"🌐 API 端點: {api_healthy}/{api_total} 正常回應")

    # 前端建置
    frontend_status = "✅ 正常" if frontend_build else "❌ 異常"
    print(f"⚛️  前端建置: {frontend_status}")

    # 配置檔案
    config_healthy = sum(configs.values())
    config_total = len(configs)
    print(f"⚙️  配置檔案: {config_healthy}/{config_total} 正確配置")

    # 整體健康度
    total_checks = docker_total + api_total + 1 + config_total
    total_healthy = docker_healthy + api_healthy + (1 if frontend_build else 0) + config_healthy

    health_percentage = (total_healthy / total_checks) * 100

    print(f"\n🎯 整體系統健康度: {health_percentage:.1f}%")

    if health_percentage >= 90:
        print("🎉 系統運行狀態良好！")
    elif health_percentage >= 70:
        print("⚠️  系統有部分問題，建議檢查")
    else:
        print("🚨 系統存在嚴重問題，需要立即修復")

    # 建議修復步驟
    if health_percentage < 100:
        print("\n🔧 建議修復步驟:")

        if not all(docker_services.values()):
            print("  1. 重啟 Docker 服務: docker-compose -f docker-compose.unified.yml up -d")

        if not all(api_results.values()):
            print("  2. 檢查後端API配置和資料庫連接")

        if not frontend_build:
            print("  3. 重新建置前端: cd frontend && npm run build")

        if not all(configs.values()):
            print("  4. 檢查並補充缺失的配置檔案")

def main():
    """主要執行函數"""
    print("🚀 乾坤測繪公文管理系統 - 健康檢查開始")
    print("="*60)

    # 執行各項檢查
    docker_services = check_docker_services()
    api_results = check_api_endpoints()
    frontend_build = check_frontend_build()
    configs = check_configuration()

    # 生成報告
    generate_report(docker_services, api_results, frontend_build, configs)

    print("\n🏁 健康檢查完成")

if __name__ == "__main__":
    main()
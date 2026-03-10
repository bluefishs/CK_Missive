#!/usr/bin/env python3
"""
乾坤測繪公文管理系統 - 開發環境監控工具
===========================================
🎯 目標：監控開發環境狀態，提供即時反饋
🔧 功能：服務狀態監控、日誌追踪、性能監控
"""

import requests
import subprocess
import time
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional

class DevMonitor:
    def __init__(self):
        self.services = {
            "frontend": {"url": "http://localhost:3000", "name": "前端服務"},
            "backend": {"url": "http://localhost:8001/health", "name": "後端API"},
            "backend_docs": {"url": "http://localhost:8001/api/docs", "name": "API文檔"},
            "adminer": {"url": "http://localhost:8080", "name": "資料庫管理"}
        }

    def check_docker_services(self) -> Dict:
        """檢查 Docker 服務狀態"""
        try:
            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose.dev.yml", "ps", "--format", "json"],
                capture_output=True, text=True, check=True
            )

            services = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    service_info = json.loads(line)
                    services.append({
                        "name": service_info.get("Service", "Unknown"),
                        "state": service_info.get("State", "Unknown"),
                        "status": service_info.get("Status", "Unknown")
                    })

            return {"status": "success", "services": services}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": f"Docker 命令執行失敗: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"檢查 Docker 服務時出錯: {e}"}

    def check_http_services(self) -> Dict:
        """檢查 HTTP 服務可用性"""
        results = {}

        for service_id, service_info in self.services.items():
            try:
                response = requests.get(service_info["url"], timeout=5)
                results[service_id] = {
                    "name": service_info["name"],
                    "url": service_info["url"],
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }
            except requests.exceptions.RequestException as e:
                results[service_id] = {
                    "name": service_info["name"],
                    "url": service_info["url"],
                    "status": "unreachable",
                    "error": str(e)
                }

        return results

    def get_container_stats(self) -> Dict:
        """獲取容器資源使用統計"""
        try:
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format",
                 "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"],
                capture_output=True, text=True, check=True
            )

            lines = result.stdout.strip().split('\n')[1:]  # 跳過標題行
            stats = []

            for line in lines:
                if 'ck_missive' in line:  # 只顯示我們的容器
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        stats.append({
                            "container": parts[0],
                            "cpu_percent": parts[1],
                            "memory_usage": parts[2],
                            "memory_percent": parts[3]
                        })

            return {"status": "success", "stats": stats}
        except Exception as e:
            return {"status": "error", "message": f"獲取容器統計失敗: {e}"}

    def check_file_sync(self) -> Dict:
        """檢查文件同步狀態（通過檢查時間戳）"""
        sync_status = {}

        # 檢查後端文件同步
        try:
            backend_main = "backend/main.py"
            import os
            if os.path.exists(backend_main):
                mtime = os.path.getmtime(backend_main)
                sync_status["backend"] = {
                    "file": backend_main,
                    "last_modified": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "synced"
                }
        except Exception as e:
            sync_status["backend"] = {"status": "error", "message": str(e)}

        # 檢查前端文件同步
        try:
            frontend_main = "frontend/src/main.tsx"
            if os.path.exists(frontend_main):
                mtime = os.path.getmtime(frontend_main)
                sync_status["frontend"] = {
                    "file": frontend_main,
                    "last_modified": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "synced"
                }
        except Exception as e:
            sync_status["frontend"] = {"status": "error", "message": str(e)}

        return sync_status

    def display_status(self):
        """顯示完整的開發環境狀態"""
        print("\n" + "="*70)
        print("🔧 乾坤測繪開發環境監控報告")
        print(f"📅 時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)

        # Docker 服務狀態
        print("\n📦 Docker 容器狀態:")
        docker_status = self.check_docker_services()
        if docker_status["status"] == "success":
            for service in docker_status["services"]:
                status_icon = "✅" if "Up" in service["state"] else "❌"
                print(f"  {status_icon} {service['name']:15} | {service['state']:10} | {service['status']}")
        else:
            print(f"  ❌ {docker_status['message']}")

        # HTTP 服務狀態
        print("\n🌐 HTTP 服務狀態:")
        http_status = self.check_http_services()
        for service_id, info in http_status.items():
            if info["status"] == "healthy":
                icon = "✅"
                detail = f"{info['status_code']} | {info['response_time']:.2f}s"
            elif info["status"] == "unhealthy":
                icon = "⚠️"
                detail = f"{info['status_code']}"
            else:
                icon = "❌"
                detail = "無法連接"

            print(f"  {icon} {info['name']:15} | {detail}")

        # 容器資源使用
        print("\n📊 容器資源使用:")
        stats = self.get_container_stats()
        if stats["status"] == "success":
            for stat in stats["stats"]:
                container_name = stat["container"].split('_')[-1] if '_' in stat["container"] else stat["container"]
                print(f"  📈 {container_name:15} | CPU: {stat['cpu_percent']:6} | 記憶體: {stat['memory_usage']:15} ({stat['memory_percent']:6})")
        else:
            print(f"  ❌ {stats['message']}")

        # 文件同步狀態
        print("\n📂 文件同步狀態:")
        sync_status = self.check_file_sync()
        for component, info in sync_status.items():
            if info["status"] == "synced":
                print(f"  ✅ {component:15} | 最後修改: {info['last_modified']}")
            else:
                print(f"  ❌ {component:15} | 錯誤: {info.get('message', '未知錯誤')}")

        print("\n" + "="*70)

    def watch_mode(self, interval: int = 30):
        """監控模式：定期刷新狀態"""
        print("🔍 開始監控模式 (Ctrl+C 停止)")
        print(f"📱 每 {interval} 秒刷新一次")

        try:
            while True:
                # 清屏（跨平台）
                import os
                os.system('cls' if os.name == 'nt' else 'clear')

                self.display_status()
                print(f"\n⏰ 下次刷新：{interval} 秒後 (Ctrl+C 停止監控)")

                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n👋 監控已停止")

def main():
    monitor = DevMonitor()

    if len(sys.argv) > 1:
        if sys.argv[1] == "watch":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            monitor.watch_mode(interval)
        elif sys.argv[1] == "docker":
            result = monitor.check_docker_services()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif sys.argv[1] == "http":
            result = monitor.check_http_services()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("用法:")
            print("  python dev-monitor.py           # 單次檢查")
            print("  python dev-monitor.py watch     # 監控模式")
            print("  python dev-monitor.py watch 10  # 10秒間隔監控")
            print("  python dev-monitor.py docker    # 只檢查Docker")
            print("  python dev-monitor.py http      # 只檢查HTTP")
    else:
        monitor.display_status()

if __name__ == "__main__":
    main()
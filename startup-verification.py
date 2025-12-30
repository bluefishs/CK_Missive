#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系統重啟後自動驗證腳本
確保所有服務和配置按預期運行
"""

import os
import sys
import time
import json
import requests
import subprocess
from pathlib import Path
from datetime import datetime

class StartupVerifier:
    def __init__(self):
        self.project_root = Path.cwd()
        self.verification_log = self.project_root / "startup-verification.log"
        self.critical_services = {
            "postgres": "localhost:5434",
            "redis": "localhost:6380",
            "backend": "http://localhost:8001",
            "frontend": "http://localhost:3000",
            "adminer": "http://localhost:8080"
        }

    def log_message(self, message, level="INFO"):
        """記錄驗證日誌"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)

        with open(self.verification_log, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")

    def wait_for_docker_services(self, timeout=120):
        """等待 Docker 服務啟動"""
        self.log_message("等待 Docker 服務啟動...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["docker", "ps", "--filter", "name=ck_missive", "--format", "table {{.Names}}\t{{.Status}}"],
                    capture_output=True, text=True, check=True
                )

                if "ck_missive_" in result.stdout:
                    running_services = []
                    for line in result.stdout.split('\n'):
                        if "ck_missive_" in line and "Up" in line:
                            service_name = line.split()[0].replace("ck_missive_", "")
                            running_services.append(service_name)

                    if len(running_services) >= 4:  # postgres, redis, backend, frontend (adminer 可選)
                        self.log_message(f"Docker 服務已啟動: {', '.join(running_services)}")
                        return True

                self.log_message("等待更多服務啟動...", "DEBUG")
                time.sleep(5)

            except subprocess.CalledProcessError as e:
                self.log_message(f"Docker 命令執行失敗: {e}", "ERROR")
                time.sleep(5)

        self.log_message("Docker 服務啟動逾時", "ERROR")
        return False

    def verify_service_health(self, service_name, endpoint, timeout=30):
        """驗證單一服務健康狀態"""
        self.log_message(f"檢查 {service_name} 服務健康狀態...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if endpoint.startswith("http"):
                    # HTTP 服務檢查
                    response = requests.get(endpoint, timeout=5)
                    if response.status_code == 200:
                        self.log_message(f"{service_name} 服務正常運行")
                        return True
                    else:
                        self.log_message(f"{service_name} 回應狀態碼: {response.status_code}", "WARN")
                else:
                    # TCP 端口檢查
                    import socket
                    host, port = endpoint.split(":")
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((host, int(port)))
                    sock.close()

                    if result == 0:
                        self.log_message(f"{service_name} 端口連接正常")
                        return True
                    else:
                        self.log_message(f"{service_name} 端口連接失敗", "WARN")

                time.sleep(2)

            except Exception as e:
                self.log_message(f"{service_name} 健康檢查異常: {e}", "WARN")
                time.sleep(2)

        self.log_message(f"{service_name} 健康檢查逾時", "ERROR")
        return False

    def verify_api_endpoints(self):
        """驗證 API 端點功能"""
        self.log_message("驗證 API 端點功能...")

        api_tests = [
            ("健康檢查", "GET", "http://localhost:8001/health"),
            ("CSRF Token", "GET", "http://localhost:8001/api/csrf"),
            ("用戶認證", "GET", "http://localhost:8001/api/auth/me")
        ]

        passed_tests = 0
        for test_name, method, url in api_tests:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code in [200, 401]:  # 401 表示認證端點正常但未登入
                    self.log_message(f"✅ {test_name} - 通過")
                    passed_tests += 1
                else:
                    self.log_message(f"❌ {test_name} - 失敗 (狀態碼: {response.status_code})", "ERROR")
            except Exception as e:
                self.log_message(f"❌ {test_name} - 異常: {e}", "ERROR")

        success_rate = (passed_tests / len(api_tests)) * 100
        self.log_message(f"API 測試通過率: {success_rate:.1f}% ({passed_tests}/{len(api_tests)})")

        return success_rate >= 70  # 70% 通過率視為成功

    def verify_configuration_integrity(self):
        """驗證配置檔案完整性"""
        self.log_message("驗證配置檔案完整性...")

        try:
            result = subprocess.run(
                ["python", "config-persistence-check.py", "--verify"],
                capture_output=True, text=True, cwd=self.project_root
            )

            if result.returncode == 0:
                self.log_message("✅ 配置檔案完整性驗證通過")
                return True
            else:
                self.log_message("❌ 配置檔案完整性驗證失敗", "ERROR")
                self.log_message(result.stdout, "DEBUG")
                return False

        except Exception as e:
            self.log_message(f"配置檔案檢查異常: {e}", "ERROR")
            return False

    def verify_database_connection(self):
        """驗證資料庫連接"""
        self.log_message("驗證資料庫連接...")

        try:
            # 嘗試通過 backend API 測試資料庫連接
            response = requests.get("http://localhost:8001/health", timeout=10)

            if response.status_code == 200:
                health_data = response.json()
                if "database" in health_data and health_data["database"] == "connected":
                    self.log_message("✅ 資料庫連接正常")
                    return True
                else:
                    self.log_message("❌ 資料庫連接狀態異常", "ERROR")
                    return False
            else:
                self.log_message("❌ 無法取得資料庫狀態", "ERROR")
                return False

        except Exception as e:
            self.log_message(f"資料庫連接檢查異常: {e}", "ERROR")
            return False

    def create_startup_report(self, results):
        """創建啟動驗證報告"""
        report_file = self.project_root / "startup-report.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "SUCCESS" if all(results.values()) else "FAILED",
            "results": results,
            "recommendations": []
        }

        # 根據結果提供建議
        if not results.get("docker_services", False):
            report["recommendations"].append("檢查 Docker 服務是否正確啟動")

        if not results.get("configuration", False):
            report["recommendations"].append("檢查配置檔案是否被意外修改")

        if not results.get("api_endpoints", False):
            report["recommendations"].append("檢查後端服務配置和日誌")

        if not results.get("database", False):
            report["recommendations"].append("檢查資料庫服務和連接配置")

        # 保存報告
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.log_message(f"啟動驗證報告已保存: {report_file}")
        return report

    def run_full_verification(self):
        """執行完整的啟動驗證"""
        self.log_message("=== 開始系統重啟後驗證 ===")

        results = {}

        # 1. 等待 Docker 服務
        results["docker_services"] = self.wait_for_docker_services()

        # 2. 驗證各服務健康狀態
        service_health = []
        for service_name, endpoint in self.critical_services.items():
            health_ok = self.verify_service_health(service_name, endpoint)
            service_health.append(health_ok)

        results["service_health"] = all(service_health)

        # 3. 驗證配置完整性
        results["configuration"] = self.verify_configuration_integrity()

        # 4. 驗證 API 端點
        results["api_endpoints"] = self.verify_api_endpoints()

        # 5. 驗證資料庫連接
        results["database"] = self.verify_database_connection()

        # 生成報告
        report = self.create_startup_report(results)

        # 顯示最終結果
        if report["overall_status"] == "SUCCESS":
            self.log_message("🎉 系統重啟後驗證完全成功！")
            return True
        else:
            self.log_message("⚠️ 系統重啟後驗證發現問題", "ERROR")
            self.log_message("建議檢查項目：")
            for rec in report["recommendations"]:
                self.log_message(f"  - {rec}")
            return False

    def quick_fix_attempt(self):
        """嘗試快速修復常見問題"""
        self.log_message("嘗試快速修復...")

        try:
            # 重新同步配置
            if os.path.exists(".env.master"):
                import shutil
                shutil.copy2(".env.master", ".env")
                self.log_message("已重新同步 .env 配置")

            # 重啟 Docker 服務
            subprocess.run(
                ["docker-compose", "-f", "docker-compose.unified.yml", "restart"],
                cwd=self.project_root, timeout=60
            )
            self.log_message("已重啟 Docker 服務")

            return True

        except Exception as e:
            self.log_message(f"快速修復失敗: {e}", "ERROR")
            return False

def main():
    verifier = StartupVerifier()

    if len(sys.argv) > 1 and sys.argv[1] == "--fix":
        verifier.quick_fix_attempt()
        return

    # 執行完整驗證
    success = verifier.run_full_verification()

    if not success:
        # 如果驗證失敗，詢問是否嘗試修復
        print("\n是否嘗試自動修復? (y/N): ", end="")
        try:
            response = input().strip().lower()
            if response == 'y':
                if verifier.quick_fix_attempt():
                    print("修復完成，請重新執行驗證")
                else:
                    print("自動修復失敗，請手動檢查")
        except:
            pass

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乾坤測繪公文管理系統 - 系統配置全面測試工具
==============================================
目標：全面檢視系統設定與測試配置一致性
功能：配置檢查、服務測試、環境驗證、連通性測試
"""

import os
import sys
import io

# 設定標準輸出編碼
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import json
import subprocess
import requests
import time
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class SystemConfigTester:
    def __init__(self):
        self.project_root = Path.cwd()
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }

    def log_result(self, test_name: str, status: str, message: str, details: Optional[Dict] = None):
        """記錄測試結果"""
        self.test_results["tests"][test_name] = {
            "status": status,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }

        self.test_results["summary"]["total"] += 1
        if status == "PASS":
            self.test_results["summary"]["passed"] += 1
            icon = "[PASS]"
        elif status == "FAIL":
            self.test_results["summary"]["failed"] += 1
            icon = "[FAIL]"
        else:  # WARNING
            self.test_results["summary"]["warnings"] += 1
            icon = "[WARN]"

        print(f"{icon} {test_name}: {message}")
        if details:
            for key, value in details.items():
                print(f"   └─ {key}: {value}")

    def test_config_files_existence(self):
        """測試 1: 檢查配置檔案存在性"""
        print("\n[檢查] 測試 1: 配置檔案存在性檢查")

        required_files = {
            ".env": "主環境配置檔案",
            ".env.master": "主配置範本檔案",
            "docker-compose.unified.yml": "統一Docker配置",
            "docker-compose.dev.yml": "開發環境配置",
            "port-config.json": "端口配置檔案",
            "backend/Dockerfile.unified": "後端統一映像",
            "frontend/Dockerfile.unified": "前端統一映像",
            "setup.sh": "部署腳本",
            "setup-config.ps1": "Windows配置腳本"
        }

        missing_files = []
        existing_files = []

        for file_path, description in required_files.items():
            full_path = self.project_root / file_path
            if full_path.exists():
                existing_files.append(f"{file_path} ({description})")
            else:
                missing_files.append(f"{file_path} ({description})")

        if not missing_files:
            self.log_result(
                "配置檔案存在性", "PASS",
                f"所有 {len(required_files)} 個必要檔案都存在",
                {"existing_files": len(existing_files)}
            )
        else:
            self.log_result(
                "配置檔案存在性", "FAIL",
                f"缺少 {len(missing_files)} 個必要檔案",
                {"missing_files": missing_files}
            )

    def test_env_variables_consistency(self):
        """測試 2: 環境變數一致性檢查"""
        print("\n[檢查] 測試 2: 環境變數一致性檢查")

        try:
            # 讀取主配置檔案
            env_master = self.project_root / ".env.master"
            env_current = self.project_root / ".env"

            if not env_master.exists():
                self.log_result(
                    "環境變數一致性", "FAIL",
                    ".env.master 檔案不存在"
                )
                return

            if not env_current.exists():
                self.log_result(
                    "環境變數一致性", "WARNING",
                    ".env 檔案不存在，建議從 .env.master 複製"
                )
                return

            # 解析環境變數
            master_vars = self.parse_env_file(env_master)
            current_vars = self.parse_env_file(env_current)

            # 檢查關鍵變數
            critical_vars = [
                "COMPOSE_PROJECT_NAME", "FRONTEND_HOST_PORT", "BACKEND_HOST_PORT",
                "POSTGRES_HOST_PORT", "DATABASE_URL", "VITE_API_BASE_URL"
            ]

            missing_vars = []
            inconsistent_vars = []

            for var in critical_vars:
                if var not in current_vars:
                    missing_vars.append(var)
                elif var in master_vars and current_vars[var] != master_vars[var]:
                    inconsistent_vars.append(f"{var}: {current_vars[var]} ≠ {master_vars[var]}")

            if not missing_vars and not inconsistent_vars:
                self.log_result(
                    "環境變數一致性", "PASS",
                    "所有關鍵環境變數都存在且一致",
                    {"checked_variables": len(critical_vars)}
                )
            else:
                details = {}
                if missing_vars:
                    details["missing_variables"] = missing_vars
                if inconsistent_vars:
                    details["inconsistent_variables"] = inconsistent_vars

                self.log_result(
                    "環境變數一致性", "FAIL",
                    f"發現 {len(missing_vars + inconsistent_vars)} 個問題",
                    details
                )

        except Exception as e:
            self.log_result(
                "環境變數一致性", "FAIL",
                f"檢查過程中發生錯誤: {str(e)}"
            )

    def parse_env_file(self, file_path: Path) -> Dict[str, str]:
        """解析環境變數檔案"""
        env_vars = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        return env_vars

    def test_docker_compose_syntax(self):
        """測試 3: Docker Compose 檔案語法檢查"""
        print("\n[檢查] 測試 3: Docker Compose 語法檢查")

        compose_files = [
            "docker-compose.unified.yml",
            "docker-compose.dev.yml",
            "configs/docker-compose.yml"
        ]

        results = {}

        for compose_file in compose_files:
            file_path = self.project_root / compose_file
            if not file_path.exists():
                results[compose_file] = "檔案不存在"
                continue

            try:
                # 使用 docker-compose config 檢查語法
                result = subprocess.run(
                    ["docker-compose", "-f", str(file_path), "config"],
                    capture_output=True, text=True, cwd=self.project_root
                )

                if result.returncode == 0:
                    results[compose_file] = "語法正確"
                else:
                    results[compose_file] = f"語法錯誤: {result.stderr}"

            except FileNotFoundError:
                results[compose_file] = "docker-compose 未安裝"
            except Exception as e:
                results[compose_file] = f"檢查失敗: {str(e)}"

        failed_files = [f for f, status in results.items() if "錯誤" in status or "失敗" in status]

        if not failed_files:
            self.log_result(
                "Docker Compose 語法", "PASS",
                f"所有 {len(compose_files)} 個檔案語法正確",
                {"results": results}
            )
        else:
            self.log_result(
                "Docker Compose 語法", "FAIL",
                f"{len(failed_files)} 個檔案有語法問題",
                {"failed_files": {f: results[f] for f in failed_files}}
            )

    def test_port_configuration(self):
        """測試 4: 端口配置檢查"""
        print("\n🔍 測試 4: 端口配置檢查")

        try:
            # 檢查端口配置檔案
            port_config_file = self.project_root / "port-config.json"
            if not port_config_file.exists():
                self.log_result(
                    "端口配置", "WARNING",
                    "port-config.json 檔案不存在"
                )
                return

            with open(port_config_file, 'r', encoding='utf-8') as f:
                port_config = json.load(f)

            # 檢查環境變數中的端口設定
            env_file = self.project_root / ".env"
            if env_file.exists():
                env_vars = self.parse_env_file(env_file)

                # 比較端口設定
                port_mapping = {
                    "FRONTEND_HOST_PORT": port_config["services"]["frontend"]["port"],
                    "BACKEND_HOST_PORT": port_config["services"]["backend"]["port"],
                    "POSTGRES_HOST_PORT": port_config["services"]["database"]["port"],
                    "ADMINER_HOST_PORT": port_config["services"]["adminer"]["port"]
                }

                inconsistencies = []
                for env_key, config_port in port_mapping.items():
                    if env_key in env_vars:
                        env_port = int(env_vars[env_key])
                        if env_port != config_port:
                            inconsistencies.append(f"{env_key}: env={env_port} ≠ config={config_port}")

                if not inconsistencies:
                    self.log_result(
                        "端口配置", "PASS",
                        "環境變數與 port-config.json 端口設定一致",
                        {"checked_ports": len(port_mapping)}
                    )
                else:
                    self.log_result(
                        "端口配置", "FAIL",
                        f"發現 {len(inconsistencies)} 個端口不一致",
                        {"inconsistencies": inconsistencies}
                    )
            else:
                self.log_result(
                    "端口配置", "WARNING",
                    "無法比較端口設定，.env 檔案不存在"
                )

        except Exception as e:
            self.log_result(
                "端口配置", "FAIL",
                f"端口配置檢查失敗: {str(e)}"
            )

    def test_docker_services_status(self):
        """測試 5: Docker 服務狀態檢查"""
        print("\n🔍 測試 5: Docker 服務狀態檢查")

        try:
            # 檢查 Docker 是否運行
            result = subprocess.run(
                ["docker", "version", "--format", "json"],
                capture_output=True, text=True
            )

            if result.returncode != 0:
                self.log_result(
                    "Docker 服務狀態", "FAIL",
                    "Docker 未運行或未安裝"
                )
                return

            # 檢查正在運行的容器
            result = subprocess.run(
                ["docker", "ps", "--format", "json"],
                capture_output=True, text=True
            )

            if result.returncode == 0:
                containers = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        container = json.loads(line)
                        if 'ck_missive' in container.get('Names', ''):
                            containers.append({
                                "name": container.get('Names'),
                                "status": container.get('Status'),
                                "ports": container.get('Ports', '')
                            })

                if containers:
                    self.log_result(
                        "Docker 服務狀態", "PASS",
                        f"發現 {len(containers)} 個運行中的專案容器",
                        {"containers": containers}
                    )
                else:
                    self.log_result(
                        "Docker 服務狀態", "WARNING",
                        "沒有發現運行中的專案容器"
                    )
            else:
                self.log_result(
                    "Docker 服務狀態", "FAIL",
                    "無法獲取 Docker 容器狀態"
                )

        except FileNotFoundError:
            self.log_result(
                "Docker 服務狀態", "FAIL",
                "Docker 未安裝"
            )
        except Exception as e:
            self.log_result(
                "Docker 服務狀態", "FAIL",
                f"Docker 狀態檢查失敗: {str(e)}"
            )

    def test_service_connectivity(self):
        """測試 6: 服務連通性檢查"""
        print("\n🔍 測試 6: 服務連通性檢查")

        # 從環境變數或預設值獲取端口
        env_file = self.project_root / ".env"
        if env_file.exists():
            env_vars = self.parse_env_file(env_file)
            frontend_port = env_vars.get("FRONTEND_HOST_PORT", "3000")
            backend_port = env_vars.get("BACKEND_HOST_PORT", "8001")
            adminer_port = env_vars.get("ADMINER_HOST_PORT", "8080")
        else:
            frontend_port = "3000"
            backend_port = "8001"
            adminer_port = "8080"

        services = {
            "前端服務": f"http://localhost:{frontend_port}",
            "後端API": f"http://localhost:{backend_port}/health",
            "API文檔": f"http://localhost:{backend_port}/api/docs",
            "資料庫管理": f"http://localhost:{adminer_port}"
        }

        connectivity_results = {}

        for service_name, url in services.items():
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    connectivity_results[service_name] = {
                        "status": "可連接",
                        "response_time": f"{response.elapsed.total_seconds():.2f}s"
                    }
                else:
                    connectivity_results[service_name] = {
                        "status": f"HTTP {response.status_code}",
                        "response_time": f"{response.elapsed.total_seconds():.2f}s"
                    }
            except requests.exceptions.ConnectionError:
                connectivity_results[service_name] = {"status": "連接失敗", "error": "無法連接"}
            except requests.exceptions.Timeout:
                connectivity_results[service_name] = {"status": "超時", "error": "請求超時"}
            except Exception as e:
                connectivity_results[service_name] = {"status": "錯誤", "error": str(e)}

        successful_connections = sum(1 for result in connectivity_results.values() if result["status"] == "可連接")

        if successful_connections == len(services):
            self.log_result(
                "服務連通性", "PASS",
                f"所有 {len(services)} 個服務都可正常連接",
                {"connectivity_results": connectivity_results}
            )
        elif successful_connections > 0:
            self.log_result(
                "服務連通性", "WARNING",
                f"{successful_connections}/{len(services)} 個服務可連接",
                {"connectivity_results": connectivity_results}
            )
        else:
            self.log_result(
                "服務連通性", "FAIL",
                "所有服務都無法連接",
                {"connectivity_results": connectivity_results}
            )

    def test_configuration_consistency(self):
        """測試 7: 配置一致性檢查"""
        print("\n🔍 測試 7: 跨檔案配置一致性檢查")

        try:
            inconsistencies = []

            # 檢查 .env 和 docker-compose.unified.yml 的一致性
            env_file = self.project_root / ".env"
            compose_file = self.project_root / "docker-compose.unified.yml"

            if env_file.exists() and compose_file.exists():
                env_vars = self.parse_env_file(env_file)

                # 讀取 docker-compose.yml
                with open(compose_file, 'r', encoding='utf-8') as f:
                    compose_content = f.read()

                # 檢查端口映射是否一致
                port_checks = [
                    ("FRONTEND_HOST_PORT", "3000"),
                    ("BACKEND_HOST_PORT", "8001"),
                    ("POSTGRES_HOST_PORT", "5434"),
                    ("ADMINER_HOST_PORT", "8080")
                ]

                for env_key, expected_in_compose in port_checks:
                    if env_key in env_vars:
                        env_port = env_vars[env_key]
                        if f"{env_port}:" not in compose_content:
                            inconsistencies.append(f"{env_key}={env_port} 在 docker-compose.yml 中未找到對應端口映射")

            # 檢查前端環境變數
            frontend_env = self.project_root / "frontend" / ".env.development"
            if frontend_env.exists() and env_file.exists():
                frontend_vars = self.parse_env_file(frontend_env)
                env_vars = self.parse_env_file(env_file)

                if "VITE_API_BASE_URL" in frontend_vars and "VITE_API_BASE_URL" in env_vars:
                    if frontend_vars["VITE_API_BASE_URL"] != env_vars["VITE_API_BASE_URL"]:
                        inconsistencies.append("前端 VITE_API_BASE_URL 與主配置不一致")

            if not inconsistencies:
                self.log_result(
                    "配置一致性", "PASS",
                    "跨檔案配置檢查通過"
                )
            else:
                self.log_result(
                    "配置一致性", "WARNING",
                    f"發現 {len(inconsistencies)} 個配置不一致",
                    {"inconsistencies": inconsistencies}
                )

        except Exception as e:
            self.log_result(
                "配置一致性", "FAIL",
                f"配置一致性檢查失敗: {str(e)}"
            )

    def test_security_configuration(self):
        """測試 8: 安全配置檢查"""
        print("\n🔍 測試 8: 安全配置檢查")

        try:
            security_issues = []

            env_file = self.project_root / ".env"
            if env_file.exists():
                env_vars = self.parse_env_file(env_file)

                # 檢查預設密碼
                if env_vars.get("POSTGRES_PASSWORD") == "ck_password_2024":
                    security_issues.append("使用預設資料庫密碼")

                if env_vars.get("SECRET_KEY") == "your_super_secret_key_here_change_in_production":
                    security_issues.append("使用預設 SECRET_KEY")

                # 檢查除錯模式
                if env_vars.get("DEBUG", "").lower() == "true":
                    security_issues.append("除錯模式已啟用")

                # 檢查認證設定
                if env_vars.get("AUTH_DISABLED", "").lower() == "true":
                    security_issues.append("認證已停用")

                # 檢查 Google Client Secret
                if env_vars.get("GOOGLE_CLIENT_SECRET") == "your_google_client_secret":
                    security_issues.append("使用預設 Google Client Secret")

            if not security_issues:
                self.log_result(
                    "安全配置", "PASS",
                    "未發現明顯的安全配置問題"
                )
            else:
                # 判斷是否為生產環境問題
                is_dev_environment = env_vars.get("ENVIRONMENT", "").lower() == "development"
                status = "WARNING" if is_dev_environment else "FAIL"

                self.log_result(
                    "安全配置", status,
                    f"發現 {len(security_issues)} 個安全配置問題",
                    {"security_issues": security_issues, "environment": env_vars.get("ENVIRONMENT", "unknown")}
                )

        except Exception as e:
            self.log_result(
                "安全配置", "FAIL",
                f"安全配置檢查失敗: {str(e)}"
            )

    def generate_report(self):
        """生成測試報告"""
        print("\n" + "="*80)
        print("📊 系統配置測試報告")
        print("="*80)

        summary = self.test_results["summary"]
        total = summary["total"]
        passed = summary["passed"]
        failed = summary["failed"]
        warnings = summary["warnings"]

        print(f"📈 測試統計：")
        print(f"   總測試數: {total}")
        print(f"   通過: {passed} ✅")
        print(f"   警告: {warnings} ⚠️")
        print(f"   失敗: {failed} ❌")
        print(f"   成功率: {(passed/total*100):.1f}%")

        # 生成建議
        print(f"\n💡 建議：")
        if failed > 0:
            print("   🔥 發現關鍵問題，建議立即修復失敗項目")
        if warnings > 0:
            print("   ⚠️ 注意警告項目，建議檢查並修復")
        if passed == total:
            print("   🎉 所有測試都通過！系統配置正常")

        # 保存詳細報告
        report_file = self.project_root / f"system-config-test-report-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)

        print(f"\n📄 詳細報告已保存至: {report_file}")

    def run_all_tests(self):
        """執行所有測試"""
        print("🚀 開始系統配置全面測試...")
        print(f"📂 專案目錄: {self.project_root}")
        print(f"🕐 測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 執行所有測試
        self.test_config_files_existence()
        self.test_env_variables_consistency()
        self.test_docker_compose_syntax()
        self.test_port_configuration()
        self.test_docker_services_status()
        self.test_service_connectivity()
        self.test_configuration_consistency()
        self.test_security_configuration()

        # 生成報告
        self.generate_report()

def main():
    if len(sys.argv) > 1:
        command = sys.argv[1]
        tester = SystemConfigTester()

        if command == "config":
            tester.test_config_files_existence()
            tester.test_env_variables_consistency()
            tester.test_configuration_consistency()
        elif command == "docker":
            tester.test_docker_compose_syntax()
            tester.test_docker_services_status()
        elif command == "network":
            tester.test_service_connectivity()
            tester.test_port_configuration()
        elif command == "security":
            tester.test_security_configuration()
        else:
            print("用法:")
            print("  python system-config-test.py           # 運行所有測試")
            print("  python system-config-test.py config    # 只測試配置")
            print("  python system-config-test.py docker    # 只測試Docker")
            print("  python system-config-test.py network   # 只測試網路")
            print("  python system-config-test.py security  # 只測試安全")
    else:
        tester = SystemConfigTester()
        tester.run_all_tests()

if __name__ == "__main__":
    main()
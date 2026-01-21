#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
環境切換測試工具
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

class EnvironmentSwitcher:
    def __init__(self):
        self.project_root = Path.cwd()
        self.backup_dir = self.project_root / "config_backups"

    def backup_current_config(self):
        """備份當前配置"""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir()

        # 備份 .env
        if (self.project_root / ".env").exists():
            shutil.copy2(
                self.project_root / ".env",
                self.backup_dir / f".env.backup"
            )
            print("[OK] 已備份當前 .env 配置")
        else:
            print("[WARN] 當前沒有 .env 檔案")

    def switch_to_development(self):
        """切換到開發環境"""
        print("\n=== 切換到開發環境 ===")

        # 從 .env.master 複製
        if (self.project_root / ".env.master").exists():
            shutil.copy2(
                self.project_root / ".env.master",
                self.project_root / ".env"
            )
            print("[OK] 已從 .env.master 創建開發環境配置")
        else:
            print("[ERROR] .env.master 不存在")
            return False

        # 確認開發環境設定
        self.verify_environment("development")
        return True

    def switch_to_production(self):
        """切換到生產環境"""
        print("\n=== 切換到生產環境 ===")

        if (self.project_root / ".env.production").exists():
            shutil.copy2(
                self.project_root / ".env.production",
                self.project_root / ".env"
            )
            print("[OK] 已切換到生產環境配置")
        else:
            # 從 master 創建並修改為生產設定
            if (self.project_root / ".env.master").exists():
                shutil.copy2(
                    self.project_root / ".env.master",
                    self.project_root / ".env"
                )

                # 修改為生產環境設定
                self.modify_for_production()
                print("[OK] 已創建生產環境配置")
            else:
                print("[ERROR] 沒有可用的配置範本")
                return False

        self.verify_environment("production")
        return True

    def modify_for_production(self):
        """修改配置為生產環境"""
        env_file = self.project_root / ".env"

        # 讀取配置
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 修改關鍵設定
        modifications = {
            'ENVIRONMENT=development': 'ENVIRONMENT=production',
            'DEBUG=true': 'DEBUG=false',
            'AUTH_DISABLED=true': 'AUTH_DISABLED=false',
            'LOG_LEVEL=DEBUG': 'LOG_LEVEL=INFO',
            'NODE_ENV=development': 'NODE_ENV=production'
        }

        for old, new in modifications.items():
            content = content.replace(old, new)

        # 寫回檔案
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print("[OK] 已修改生產環境安全設定")

    def verify_environment(self, expected_env):
        """驗證環境設定"""
        print(f"\n--- 驗證 {expected_env} 環境設定 ---")

        env_file = self.project_root / ".env"
        if not env_file.exists():
            print("[ERROR] .env 檔案不存在")
            return

        # 解析環境變數
        env_vars = {}
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()

        # 檢查關鍵設定
        checks = [
            ("ENVIRONMENT", expected_env),
            ("DEBUG", "false" if expected_env == "production" else "true"),
            ("AUTH_DISABLED", "false" if expected_env == "production" else "true"),
            ("NODE_ENV", expected_env)
        ]

        all_correct = True
        for key, expected_value in checks:
            actual_value = env_vars.get(key, "未設定")
            if actual_value == expected_value:
                print(f"[OK] {key} = {actual_value}")
            else:
                print(f"[WARN] {key} = {actual_value} (預期: {expected_value})")
                all_correct = False

        # 安全檢查（僅生產環境）
        if expected_env == "production":
            security_checks = [
                ("SECRET_KEY", "your_super_secret_key_here_change_in_production"),
                ("POSTGRES_PASSWORD", "ck_password_2024")
            ]

            for key, default_value in security_checks:
                actual_value = env_vars.get(key, "")
                if actual_value == default_value:
                    print(f"[SECURITY WARN] {key} 仍使用預設值，建議修改")
                    all_correct = False
                else:
                    print(f"[OK] {key} 已自定義")

        return all_correct

    def test_docker_compose_configs(self):
        """測試不同的 Docker Compose 配置"""
        print("\n=== 測試 Docker Compose 配置 ===")

        configs = [
            ("docker-compose.dev.yml", "開發環境"),
            ("docker-compose.unified.yml", "統一/生產環境"),
            ("configs/docker-compose.yml", "替代配置")
        ]

        for config_file, description in configs:
            config_path = self.project_root / config_file
            if config_path.exists():
                try:
                    # 測試配置語法
                    result = subprocess.run(
                        ["docker-compose", "-f", str(config_path), "config", "--quiet"],
                        capture_output=True, text=True, cwd=self.project_root
                    )

                    if result.returncode == 0:
                        print(f"[OK] {config_file} ({description}) - 語法正確")
                    else:
                        print(f"[ERROR] {config_file} ({description}) - 語法錯誤")
                        print(f"       {result.stderr}")

                except FileNotFoundError:
                    print(f"[WARN] Docker Compose 未安裝，無法測試 {config_file}")
                except Exception as e:
                    print(f"[ERROR] 測試 {config_file} 時出錯: {e}")
            else:
                print(f"[MISSING] {config_file} ({description}) - 檔案不存在")

    def simulate_deployment_scenarios(self):
        """模擬部署情境"""
        print("\n=== 模擬部署情境測試 ===")

        scenarios = [
            {
                "name": "開發環境啟動",
                "compose_file": "docker-compose.dev.yml",
                "environment": "development"
            },
            {
                "name": "生產環境部署",
                "compose_file": "docker-compose.unified.yml",
                "environment": "production"
            }
        ]

        for scenario in scenarios:
            print(f"\n--- {scenario['name']} ---")

            # 切換環境
            if scenario['environment'] == 'development':
                self.switch_to_development()
            else:
                self.switch_to_production()

            # 檢查 Docker Compose 檔案
            compose_path = self.project_root / scenario['compose_file']
            if compose_path.exists():
                print(f"[OK] 找到 {scenario['compose_file']}")

                # 模擬啟動命令（不實際執行）
                command = f"docker-compose -f {scenario['compose_file']} up --build -d"
                print(f"[SIMULATE] 執行命令: {command}")

                # 這裡可以加入更多檢查...
            else:
                print(f"[ERROR] 缺少 {scenario['compose_file']}")

def main():
    switcher = EnvironmentSwitcher()

    print("=== 環境切換與配置測試 ===")

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "dev":
            switcher.backup_current_config()
            switcher.switch_to_development()
        elif command == "prod":
            switcher.backup_current_config()
            switcher.switch_to_production()
        elif command == "test":
            switcher.test_docker_compose_configs()
        elif command == "scenario":
            switcher.simulate_deployment_scenarios()
        else:
            print("用法:")
            print("  python env-switch-test.py dev       # 切換到開發環境")
            print("  python env-switch-test.py prod      # 切換到生產環境")
            print("  python env-switch-test.py test      # 測試Docker配置")
            print("  python env-switch-test.py scenario  # 模擬部署情境")
    else:
        # 執行完整測試
        switcher.backup_current_config()
        switcher.test_docker_compose_configs()
        switcher.simulate_deployment_scenarios()

if __name__ == "__main__":
    main()
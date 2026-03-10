#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生產環境安全配置檢查工具
"""

import os
import sys
import secrets
import string
from pathlib import Path

class SecurityConfigChecker:
    def __init__(self):
        self.project_root = Path.cwd()
        self.security_issues = []
        self.recommendations = []

    def log_issue(self, severity, component, issue, recommendation=""):
        """記錄安全問題"""
        self.security_issues.append({
            "severity": severity,
            "component": component,
            "issue": issue,
            "recommendation": recommendation
        })

    def log_recommendation(self, recommendation):
        """記錄建議"""
        self.recommendations.append(recommendation)

    def parse_env_file(self, file_path):
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

    def check_default_secrets(self, env_vars):
        """檢查預設密鑰和密碼"""
        print("\n1. 檢查預設密鑰和密碼:")

        default_secrets = {
            "SECRET_KEY": "your_super_secret_key_here_change_in_production",
            "POSTGRES_PASSWORD": "ck_password_2024",
            "GOOGLE_CLIENT_SECRET": "your_google_client_secret"
        }

        for key, default_value in default_secrets.items():
            if key in env_vars:
                if env_vars[key] == default_value:
                    print(f"[CRITICAL] {key} 仍使用預設值")
                    self.log_issue("CRITICAL", key, f"使用預設值: {default_value}",
                                 f"請產生強密鑰替換預設值")
                else:
                    print(f"[OK] {key} 已自定義")
            else:
                print(f"[MISSING] {key} 未設定")
                self.log_issue("HIGH", key, "未設定", "請設定此安全參數")

    def check_debug_settings(self, env_vars):
        """檢查除錯設定"""
        print("\n2. 檢查除錯設定:")

        debug_settings = {
            "DEBUG": "false",
            "AUTH_DISABLED": "false",
            "DATABASE_ECHO": "false"
        }

        for key, production_value in debug_settings.items():
            if key in env_vars:
                current_value = env_vars[key].lower()
                if current_value != production_value:
                    severity = "HIGH" if key in ["DEBUG", "AUTH_DISABLED"] else "MEDIUM"
                    print(f"[{severity}] {key} = {env_vars[key]} (建議: {production_value})")
                    self.log_issue(severity, key, f"不安全的設定值: {env_vars[key]}",
                                 f"生產環境應設為: {production_value}")
                else:
                    print(f"[OK] {key} = {env_vars[key]}")
            else:
                print(f"[MISSING] {key} 未設定")

    def check_environment_setting(self, env_vars):
        """檢查環境設定"""
        print("\n3. 檢查環境設定:")

        if "ENVIRONMENT" in env_vars:
            env_value = env_vars["ENVIRONMENT"].lower()
            if env_value == "production":
                print(f"[OK] ENVIRONMENT = {env_vars['ENVIRONMENT']}")
            else:
                print(f"[WARN] ENVIRONMENT = {env_vars['ENVIRONMENT']} (不是 production)")
                self.log_issue("MEDIUM", "ENVIRONMENT",
                             f"環境設定為: {env_vars['ENVIRONMENT']}",
                             "生產環境應設為: production")
        else:
            print("[MISSING] ENVIRONMENT 未設定")

        if "NODE_ENV" in env_vars:
            node_env = env_vars["NODE_ENV"].lower()
            if node_env == "production":
                print(f"[OK] NODE_ENV = {env_vars['NODE_ENV']}")
            else:
                print(f"[WARN] NODE_ENV = {env_vars['NODE_ENV']} (不是 production)")
        else:
            print("[MISSING] NODE_ENV 未設定")

    def check_cors_settings(self, env_vars):
        """檢查 CORS 設定"""
        print("\n4. 檢查 CORS 設定:")

        if "CORS_ORIGINS" in env_vars:
            cors_origins = env_vars["CORS_ORIGINS"]
            if "localhost" in cors_origins or "127.0.0.1" in cors_origins:
                print(f"[WARN] CORS_ORIGINS 包含本地開發地址: {cors_origins}")
                self.log_issue("MEDIUM", "CORS_ORIGINS",
                             "包含開發環境地址",
                             "生產環境應只包含實際域名")
            else:
                print(f"[OK] CORS_ORIGINS = {cors_origins}")
        else:
            print("[MISSING] CORS_ORIGINS 未設定")

    def check_database_security(self, env_vars):
        """檢查資料庫安全設定"""
        print("\n5. 檢查資料庫安全:")

        if "DATABASE_URL" in env_vars:
            db_url = env_vars["DATABASE_URL"]
            if "localhost" in db_url:
                print(f"[WARN] DATABASE_URL 使用 localhost: {db_url}")
                self.log_issue("MEDIUM", "DATABASE_URL",
                             "使用 localhost",
                             "生產環境應使用實際資料庫主機")
            elif "ck_password_2024" in db_url:
                print(f"[CRITICAL] DATABASE_URL 包含預設密碼")
                self.log_issue("CRITICAL", "DATABASE_URL",
                             "包含預設密碼",
                             "請使用強密碼")
            else:
                print(f"[OK] DATABASE_URL 已配置")

        # 檢查 PostgreSQL 設定
        if "POSTGRES_PASSWORD" in env_vars:
            password = env_vars["POSTGRES_PASSWORD"]
            if len(password) < 12:
                print(f"[WARN] PostgreSQL 密碼長度不足 ({len(password)} 字符)")
                self.log_issue("MEDIUM", "POSTGRES_PASSWORD",
                             f"密碼長度只有 {len(password)} 字符",
                             "建議使用至少 12 字符的強密碼")

    def check_docker_security(self):
        """檢查 Docker 安全配置"""
        print("\n6. 檢查 Docker 安全配置:")

        # 檢查 Dockerfile 安全
        dockerfiles = [
            "backend/Dockerfile.unified",
            "frontend/Dockerfile.unified"
        ]

        for dockerfile in dockerfiles:
            dockerfile_path = self.project_root / dockerfile
            if dockerfile_path.exists():
                with open(dockerfile_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 檢查非 root 使用者
                if "USER " in content and "USER root" not in content:
                    print(f"[OK] {dockerfile} 使用非 root 使用者")
                else:
                    print(f"[WARN] {dockerfile} 可能使用 root 使用者")
                    self.log_issue("MEDIUM", dockerfile,
                                 "可能使用 root 使用者",
                                 "建議使用非 root 使用者執行容器")

                # 檢查健康檢查
                if "HEALTHCHECK" in content:
                    print(f"[OK] {dockerfile} 包含健康檢查")
                else:
                    print(f"[INFO] {dockerfile} 未包含健康檢查")

    def generate_secure_secrets(self):
        """產生安全的密鑰"""
        print("\n7. 安全密鑰產生器:")

        # 產生 Django-style secret key
        secret_key = ''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%^&*(-_=+)')
                           for _ in range(50))

        # 產生資料庫密碼
        db_password = ''.join(secrets.choice(string.ascii_letters + string.digits)
                            for _ in range(16))

        print(f"建議的 SECRET_KEY:")
        print(f"SECRET_KEY={secret_key}")
        print(f"\n建議的資料庫密碼:")
        print(f"POSTGRES_PASSWORD={db_password}")

        self.log_recommendation("請將上述產生的密鑰複製到生產環境配置中")

    def create_production_env(self, env_vars):
        """創建生產環境配置檔案"""
        print("\n8. 創建生產環境配置:")

        production_env = env_vars.copy()

        # 修改為生產環境設定
        production_env["ENVIRONMENT"] = "production"
        production_env["NODE_ENV"] = "production"
        production_env["DEBUG"] = "false"
        production_env["AUTH_DISABLED"] = "false"
        production_env["DATABASE_ECHO"] = "false"
        production_env["LOG_LEVEL"] = "WARNING"

        # 生成新密鑰
        production_env["SECRET_KEY"] = ''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%^&*(-_=+)')
                                             for _ in range(50))
        production_env["POSTGRES_PASSWORD"] = ''.join(secrets.choice(string.ascii_letters + string.digits)
                                                    for _ in range(16))

        # 寫入 .env.production.secure
        production_file = self.project_root / ".env.production.secure"
        with open(production_file, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# 生產環境安全配置 - 自動生成\n")
            f.write("# =============================================================================\n")
            f.write("# ⚠️ 警告：此檔案包含機密資訊，請勿提交到版本控制\n")
            f.write("# 🔒 使用：複製為 .env 並根據實際環境調整\n")
            f.write("# =============================================================================\n\n")

            for key, value in production_env.items():
                f.write(f"{key}={value}\n")

        print(f"[OK] 已創建安全的生產環境配置: {production_file}")
        self.log_recommendation(f"請檢查並使用 {production_file} 作為生產環境配置")

    def generate_security_report(self):
        """生成安全檢查報告"""
        print("\n" + "="*80)
        print("安全檢查報告")
        print("="*80)

        # 統計問題
        critical_count = sum(1 for issue in self.security_issues if issue["severity"] == "CRITICAL")
        high_count = sum(1 for issue in self.security_issues if issue["severity"] == "HIGH")
        medium_count = sum(1 for issue in self.security_issues if issue["severity"] == "MEDIUM")

        print(f"發現的安全問題:")
        print(f"  嚴重 (CRITICAL): {critical_count}")
        print(f"  高風險 (HIGH): {high_count}")
        print(f"  中風險 (MEDIUM): {medium_count}")
        print(f"  總計: {len(self.security_issues)}")

        if self.security_issues:
            print(f"\n詳細問題:")
            for i, issue in enumerate(self.security_issues, 1):
                print(f"{i}. [{issue['severity']}] {issue['component']}")
                print(f"   問題: {issue['issue']}")
                if issue['recommendation']:
                    print(f"   建議: {issue['recommendation']}")
                print()

        if self.recommendations:
            print(f"建議事項:")
            for i, rec in enumerate(self.recommendations, 1):
                print(f"{i}. {rec}")

        # 安全等級評估
        if critical_count > 0:
            security_level = "不安全 - 存在嚴重安全風險"
        elif high_count > 0:
            security_level = "風險較高 - 需要立即處理"
        elif medium_count > 0:
            security_level = "中等風險 - 建議改善"
        else:
            security_level = "安全 - 符合基本安全要求"

        print(f"\n整體安全等級: {security_level}")

def main():
    checker = SecurityConfigChecker()

    print("=== 生產環境安全配置檢查 ===")

    # 檢查 .env 檔案
    env_file = checker.project_root / ".env"
    if not env_file.exists():
        print("[ERROR] .env 檔案不存在")
        return

    env_vars = checker.parse_env_file(env_file)

    # 執行各項安全檢查
    checker.check_default_secrets(env_vars)
    checker.check_debug_settings(env_vars)
    checker.check_environment_setting(env_vars)
    checker.check_cors_settings(env_vars)
    checker.check_database_security(env_vars)
    checker.check_docker_security()

    # 產生安全密鑰
    checker.generate_secure_secrets()

    # 創建生產環境配置
    if len(sys.argv) > 1 and sys.argv[1] == "--create-production":
        checker.create_production_env(env_vars)

    # 生成報告
    checker.generate_security_report()

    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("\n用法:")
        print("  python security-config-check.py                    # 執行安全檢查")
        print("  python security-config-check.py --create-production # 創建生產環境配置")

if __name__ == "__main__":
    main()
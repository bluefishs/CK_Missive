#!/usr/bin/env python3
"""
設置管理員用戶腳本

@version 2.0.0 - 安全性修正：移除硬編碼密碼 (2026-02-02)

使用方式:
    python setup_admin.py --admin-password <password> --test-password <password>

環境變數:
    ADMIN_PASSWORD: 管理員密碼 (可選，預設需要輸入)
    TEST_PASSWORD: 測試用戶密碼 (可選，預設需要輸入)
"""
import asyncio
import asyncpg
import bcrypt
import json
import os
import sys
import argparse
import getpass
import logging
from datetime import datetime
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv('../.env')
load_dotenv('.env')


def get_password(prompt: str, env_var: str, arg_value: str = None) -> str:
    """安全地取得密碼"""
    # 優先使用命令列參數
    if arg_value:
        return arg_value
    # 其次使用環境變數
    env_password = os.environ.get(env_var)
    if env_password:
        return env_password
    # 最後互動式輸入
    return getpass.getpass(prompt)


async def setup_admin_user(admin_password: str, test_password: str):
    """設置管理員用戶"""
    # 從環境變數讀取資料庫連線資訊
    db_host = os.environ.get('POSTGRES_HOST', 'localhost')
    db_port = int(os.environ.get('POSTGRES_PORT', '5434'))
    db_user = os.environ.get('POSTGRES_USER', '')
    db_password = os.environ.get('POSTGRES_PASSWORD', '')
    db_name = os.environ.get('POSTGRES_DB', '')

    # 驗證資料庫設定
    if not all([db_user, db_password, db_name]):
        logger.error("❌ 缺少必要的資料庫設定，請確認 .env 檔案包含:")
        logger.error("   - POSTGRES_USER")
        logger.error("   - POSTGRES_PASSWORD")
        logger.error("   - POSTGRES_DB")
        return False

    try:
        # 連接資料庫
        conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
        )

        logger.info("Database connected successfully")

        # 生成管理員密碼的hash
        password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # 管理員權限列表
        admin_permissions = [
            "documents:read", "documents:create", "documents:edit", "documents:delete",
            "projects:read", "projects:create", "projects:edit", "projects:delete",
            "agencies:read", "agencies:create", "agencies:edit", "agencies:delete",
            "vendors:read", "vendors:create", "vendors:edit", "vendors:delete",
            "admin:users", "admin:settings", "admin:site_management",
            "reports:view", "reports:export",
            "calendar:read", "calendar:edit"
        ]
        permissions_json = json.dumps(admin_permissions)

        # 檢查管理員用戶是否存在
        admin_user = await conn.fetchrow(
            "SELECT id, email, username FROM users WHERE email = $1 OR username = $2",
            "admin@ck-missive.com", "admin"
        )

        if admin_user:
            # 更新現有管理員用戶
            await conn.execute("""
                UPDATE users SET
                    password_hash = $1,
                    is_admin = true,
                    is_active = true,
                    role = 'admin',
                    permissions = $2,
                    updated_at = $3
                WHERE id = $4
            """, password_hash, permissions_json, datetime.now(), admin_user['id'])
            logger.info(f"✅ 更新管理員用戶: {admin_user['username']} ({admin_user['email']})")
        else:
            # 創建新的管理員用戶
            await conn.execute("""
                INSERT INTO users (
                    email, username, full_name, password_hash,
                    is_active, is_admin, is_superuser,
                    auth_provider, role, permissions,
                    email_verified, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4,
                    true, true, false,
                    'email', 'admin', $5,
                    true, $6, $6
                )
            """,
                "admin@ck-missive.com", "admin", "系統管理員", password_hash,
                permissions_json, datetime.now()
            )
            logger.info("✅ 創建新管理員用戶: admin@ck-missive.com")

        # 創建測試用戶
        test_password_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        test_permissions = ["documents:read", "projects:read", "agencies:read", "vendors:read", "calendar:read", "reports:view"]
        test_permissions_json = json.dumps(test_permissions)

        test_user = await conn.fetchrow("SELECT id FROM users WHERE username = $1", "testuser")
        if not test_user:
            await conn.execute("""
                INSERT INTO users (
                    email, username, full_name, password_hash,
                    is_active, is_admin, is_superuser,
                    auth_provider, role, permissions,
                    email_verified, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4,
                    true, false, false,
                    'email', 'user', $5,
                    true, $6, $6
                )
            """,
                "user@ck-missive.com", "testuser", "測試用戶", test_password_hash,
                test_permissions_json, datetime.now()
            )
            logger.info("✅ 創建測試用戶: testuser@ck-missive.com")

        # 驗證管理員用戶
        admin_check = await conn.fetchrow(
            "SELECT id, username, email, is_admin, role FROM users WHERE is_admin = true LIMIT 1"
        )
        if admin_check:
            logger.info(f"✅ 驗證成功 - 管理員用戶: {admin_check['username']} (ID: {admin_check['id']})")

        await conn.close()
        logger.info("✅ 管理員用戶設置完成")
        logger.info("🔑 管理員登入資訊:")
        logger.info("   - 用戶名: admin")
        logger.info("   - 密碼: ******** (您設定的密碼)")
        logger.info("🔑 測試用戶登入資訊:")
        logger.info("   - 用戶名: testuser")
        logger.info("   - 密碼: ******** (您設定的密碼)")

    except Exception as e:
        logger.error(f"❌ 錯誤: {e}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description='設置管理員用戶')
    parser.add_argument('--admin-password', '-a', help='管理員密碼')
    parser.add_argument('--test-password', '-t', help='測試用戶密碼')
    parser.add_argument('--non-interactive', '-n', action='store_true',
                        help='非互動模式，密碼必須透過參數或環境變數提供')
    args = parser.parse_args()

    # 取得密碼
    if args.non_interactive:
        admin_password = args.admin_password or os.environ.get('ADMIN_PASSWORD')
        test_password = args.test_password or os.environ.get('TEST_PASSWORD')
        if not admin_password or not test_password:
            logger.error("非互動模式下必須提供密碼 (--admin-password, --test-password 或環境變數)")
            sys.exit(1)
    else:
        admin_password = get_password("請輸入管理員密碼: ", "ADMIN_PASSWORD", args.admin_password)
        test_password = get_password("請輸入測試用戶密碼: ", "TEST_PASSWORD", args.test_password)

    # 密碼強度驗證
    if len(admin_password) < 8:
        logger.warning("⚠️ 警告: 管理員密碼長度少於 8 字元，建議使用更強的密碼")

    success = asyncio.run(setup_admin_user(admin_password, test_password))
    if success:
        logger.info("✅ 設置完成！現在可以使用管理員帳號登入並訪問用戶管理功能。")
    else:
        logger.error("❌ 設置失敗！請檢查錯誤訊息。")
        sys.exit(1)


if __name__ == "__main__":
    main()

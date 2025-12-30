#!/usr/bin/env python3
"""
設置管理員用戶腳本
修復用戶權限和密碼問題
"""
import asyncio
import asyncpg
import bcrypt
import json
from datetime import datetime

async def setup_admin_user():
    """設置管理員用戶"""
    try:
        # 連接資料庫
        conn = await asyncpg.connect(
            host="localhost",
            port=5434,
            user="ck_user", 
            password="ck_password",
            database="ck_documents"
        )
        
        print("Database connected successfully")
        
        # 生成管理員密碼的hash
        admin_password = "admin123"
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
            print(f"✅ 更新管理員用戶: {admin_user['username']} ({admin_user['email']})")
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
            print("✅ 創建新管理員用戶: admin@ck-missive.com")
        
        # 創建測試用戶
        test_password_hash = bcrypt.hashpw("test123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
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
            print("✅ 創建測試用戶: testuser@ck-missive.com")
        
        # 驗證管理員用戶
        admin_check = await conn.fetchrow(
            "SELECT id, username, email, is_admin, role FROM users WHERE is_admin = true LIMIT 1"
        )
        if admin_check:
            print(f"✅ 驗證成功 - 管理員用戶: {admin_check['username']} (ID: {admin_check['id']})")
        
        await conn.close()
        print("✅ 管理員用戶設置完成")
        print("🔑 管理員登入資訊:")
        print("   - 用戶名: admin")
        print("   - 密碼: admin123")
        print("🔑 測試用戶登入資訊:")
        print("   - 用戶名: testuser") 
        print("   - 密碼: test123")
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(setup_admin_user())
    if success:
        print("✅ 設置完成！現在可以使用管理員帳號登入並訪問用戶管理功能。")
    else:
        print("❌ 設置失敗！請檢查錯誤訊息。")
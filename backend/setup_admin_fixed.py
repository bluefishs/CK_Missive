#!/usr/bin/env python3
"""
Fixed admin user setup script
"""
import asyncio
import asyncpg
import bcrypt
import json
from datetime import datetime

async def setup_admin_user():
    """Setup admin user with correct password hash"""
    try:
        # Connect to database
        conn = await asyncpg.connect(
            host="localhost",
            port=5434,
            user="ck_user", 
            password="ck_password",
            database="ck_documents"
        )
        
        print("Database connected successfully")
        
        # Generate admin password hash using bcrypt
        admin_password = "admin123"
        password_hash = bcrypt.hashpw(admin_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        
        # Admin permissions list
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
        
        # Update existing admin user
        await conn.execute("""
            UPDATE users SET 
                password_hash = $1,
                is_admin = true,
                is_active = true,
                role = 'admin',
                permissions = $2,
                updated_at = $3
            WHERE email = 'admin@ck-missive.com' OR username = 'admin'
        """, password_hash, permissions_json, datetime.now())
        
        print("Updated admin user: admin@ck-missive.com")
        
        # Update test user password
        test_password_hash = bcrypt.hashpw("test123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        test_permissions = ["documents:read", "projects:read", "agencies:read", "vendors:read", "calendar:read", "reports:view"]
        test_permissions_json = json.dumps(test_permissions)
        
        await conn.execute("""
            UPDATE users SET 
                password_hash = $1,
                permissions = $2,
                updated_at = $3
            WHERE username = 'testuser'
        """, test_password_hash, test_permissions_json, datetime.now())
        
        print("Updated test user: testuser")
        
        # Test password verification
        test_verify = bcrypt.checkpw("admin123".encode("utf-8"), password_hash.encode("utf-8"))
        print(f"Password verification test: {test_verify}")
        
        await conn.close()
        print("Password hash fix completed")
        print("Admin login info:")
        print("   - Username: admin")
        print("   - Password: admin123")
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(setup_admin_user())
    if success:
        print("Setup completed! Admin password hash is now compatible with AuthService.")
    else:
        print("Setup failed! Please check error messages.")
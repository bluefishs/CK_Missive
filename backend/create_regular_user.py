#!/usr/bin/env python3
"""
Create regular user script
"""
import asyncio
import asyncpg
import bcrypt
import json
from datetime import datetime

async def create_regular_user():
    """Create regular user with correct password hash"""
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
        
        # Generate user password hash using bcrypt
        user_email = "user@ck-missive.com"
        user_password = "user123"
        password_hash = bcrypt.hashpw(user_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        
        # Regular user permissions list
        user_permissions = [
            "documents:read", 
            "projects:read", 
            "agencies:read", 
            "vendors:read", 
            "calendar:read", 
            "reports:view"
        ]
        permissions_json = json.dumps(user_permissions)
        
        # Check if user already exists
        existing_user = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1",
            user_email
        )
        
        if existing_user:
            # Update existing user
            await conn.execute("""
                UPDATE users SET 
                    password_hash = $1,
                    is_admin = false,
                    is_active = true,
                    role = 'user',
                    permissions = $2,
                    updated_at = $3
                WHERE email = $4
            """, password_hash, permissions_json, datetime.now(), user_email)
            
            print(f"Updated existing user: {user_email}")
        else:
            # Create new regular user
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
                user_email, "user", "一般使用者", password_hash,
                permissions_json, datetime.now()
            )
            
            print(f"Created new regular user: {user_email}")
        
        # Test password verification
        test_verify = bcrypt.checkpw(user_password.encode("utf-8"), password_hash.encode("utf-8"))
        print(f"Password verification test: {test_verify}")
        
        await conn.close()
        print("Regular user creation completed")
        print("Regular user login info:")
        print(f"   - Email: {user_email}")
        print(f"   - Password: {user_password}")
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(create_regular_user())
    if success:
        print("Setup completed! Regular user is ready for login.")
    else:
        print("Setup failed! Please check error messages.")
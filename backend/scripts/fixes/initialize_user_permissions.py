#!/usr/bin/env python3
"""
使用者權限初始化腳本
為現有使用者分配對應角色權限
"""
import json
from sqlalchemy.orm import sessionmaker
from app.db.database import sync_engine
from app.extended.models import User

def get_role_permissions():
    """定義各角色的權限"""
    return {
        'superuser': [
            # 公文管理
            'documents:read', 'documents:create', 'documents:edit', 'documents:delete',
            # 專案管理
            'projects:read', 'projects:create', 'projects:edit', 'projects:delete',
            # 機關管理
            'agencies:read', 'agencies:create', 'agencies:edit', 'agencies:delete',
            # 廠商管理
            'vendors:read', 'vendors:create', 'vendors:edit', 'vendors:delete',
            # 行事曆管理
            'calendar:read', 'calendar:edit',
            # 報表管理
            'reports:view', 'reports:export',
            # 系統文件
            'system_docs:read', 'system_docs:create', 'system_docs:edit', 'system_docs:delete',
            # 系統管理
            'admin:users', 'admin:settings', 'admin:site_management'
        ],
        'admin': [
            # 公文管理 (無刪除)
            'documents:read', 'documents:create', 'documents:edit',
            # 專案管理 (無刪除)
            'projects:read', 'projects:create', 'projects:edit',
            # 機關管理 (無刪除)
            'agencies:read', 'agencies:create', 'agencies:edit',
            # 廠商管理 (無刪除)
            'vendors:read', 'vendors:create', 'vendors:edit',
            # 行事曆管理
            'calendar:read', 'calendar:edit',
            # 報表管理
            'reports:view', 'reports:export',
            # 使用者管理
            'admin:users'
        ],
        'user': [
            # 基本檢視權限
            'documents:read',
            'projects:read',
            'agencies:read',
            'vendors:read',
            'calendar:read',
            'reports:view'
        ],
        'unverified': []  # 無任何權限
    }

def get_role_navigation_items():
    """定義各角色可見的導覽項目"""
    return {
        'superuser': 'all',  # 顯示全部25個項目
        'admin': [
            # 22個項目 (隱藏系統級診斷功能)
            'document-browse', 'documents', 'document-import', 'document-export', 'document-workflow',
            'projects', 'agencies', 'vendors', 'calendar', 'pure-calendar', 'document-calendar',
            'reports', 'reports-stats', 'cases', 'api-docs', 'settings',
            'user-management', 'permission-management', 'site-management', 'database-management',
            'admin-dashboard', 'unified-form-demo'
        ],
        'user': [
            # 12個項目 (僅基本檢視功能)
            'document-browse', 'documents', 'projects', 'agencies', 'vendors',
            'calendar', 'pure-calendar', 'document-calendar', 'reports', 'cases',
            'api-docs', 'settings'
        ],
        'unverified': [
            # 2個項目 (僅登入和說明)
            'api-docs', 'settings'
        ]
    }

def initialize_permissions():
    """初始化使用者權限"""
    Session = sessionmaker(bind=sync_engine)
    db = Session()

    try:
        role_permissions = get_role_permissions()
        users = db.query(User).all()

        print(f"Starting permission initialization for {len(users)} users...")

        updated_count = 0
        for user in users:
            # 取得使用者角色
            user_role = user.role or 'user'

            # 取得對應權限
            permissions = role_permissions.get(user_role, [])

            # 更新使用者權限
            user.permissions = json.dumps(permissions) if permissions else json.dumps([])

            print(f"  OK {user.email} ({user_role}): {len(permissions)} permissions")
            updated_count += 1

        # 提交變更
        db.commit()
        print(f"\nSuccessfully updated {updated_count} users permissions!")

        # 顯示結果
        print("\nPermission assignment results:")
        for user in users:
            permissions = json.loads(user.permissions) if user.permissions else []
            print(f"  {user.email}: {user.role} - {len(permissions)} permissions")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

def verify_permissions():
    """驗證權限設定"""
    Session = sessionmaker(bind=sync_engine)
    db = Session()

    try:
        users = db.query(User).all()
        role_permissions = get_role_permissions()

        print("\nVerifying permission settings:")
        all_valid = True

        for user in users:
            expected_permissions = role_permissions.get(user.role, [])
            actual_permissions = json.loads(user.permissions) if user.permissions else []

            if set(expected_permissions) == set(actual_permissions):
                print(f"  OK {user.email}: permissions correct")
            else:
                print(f"  ERROR {user.email}: permissions mismatch")
                print(f"    Expected: {len(expected_permissions)}")
                print(f"    Actual: {len(actual_permissions)}")
                all_valid = False

        return all_valid

    except Exception as e:
        print(f"Verification error: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("CK_Missive User Permission Initialization")
    print("=" * 50)

    # 執行權限初始化
    initialize_permissions()

    # 驗證結果
    if verify_permissions():
        print("\nPermission initialization completed and verified!")
    else:
        print("\nPermission initialization completed but verification found issues!")
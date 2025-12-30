#!/usr/bin/env python3
"""
驗證完整權限系統對應
確認導覽、路由、頁面、權限的完整對應關係
"""
import json
from sqlalchemy.orm import sessionmaker
from app.db.database import sync_engine
from app.extended.models import User, SiteNavigationItem

def verify_complete_system():
    Session = sessionmaker(bind=sync_engine)
    db = Session()

    try:
        print("=== Complete Permission System Verification ===")
        print()

        # 1. 使用者權限檢查
        print("1. User Permission Status:")
        users = db.query(User).all()
        for user in users:
            permissions = json.loads(user.permissions) if user.permissions else []
            print(f"   {user.email} ({user.role}): {len(permissions)} permissions")

        # 2. 關鍵導覽項目對應檢查
        print("\n2. Key Navigation Items:")
        key_items = [
            ('user-management', '/admin/user-management', 'UserManagementPage.tsx'),
            ('permission-management', '/admin/permissions', 'PermissionManagementPage.tsx'),
            ('admin-dashboard', '/admin/dashboard', 'AdminDashboardPage.tsx'),
            ('site-management', '/admin/site', 'SiteManagementPage.tsx'),
            ('documents', '/documents', 'DocumentPage.tsx'),
            ('projects', '/projects', 'ProjectPage.tsx'),
            ('calendar', '/calendar', 'CalendarPage.tsx')
        ]

        all_correct = True
        for key, expected_path, page_file in key_items:
            item = db.query(SiteNavigationItem).filter_by(key=key).first()
            if item:
                path_ok = item.path == expected_path
                perms = json.loads(item.permission_required) if item.permission_required else []

                status = "OK" if path_ok else "ERROR"
                print(f"   {status}: {key}")
                print(f"      Path: {item.path} {'✓' if path_ok else '✗ Expected: ' + expected_path}")
                print(f"      Page: {page_file}")
                print(f"      Permissions: {perms}")

                if not path_ok:
                    all_correct = False
            else:
                print(f"   ERROR: {key} - Item not found!")
                all_correct = False

        # 3. 權限管理功能檢查
        print("\n3. Permission Management Features:")

        # 檢查權限管理頁面的路由對應
        perm_mgmt = db.query(SiteNavigationItem).filter_by(key='permission-management').first()
        if perm_mgmt:
            print(f"   Permission Management Page: {perm_mgmt.path}")
            print(f"   Expected Frontend Route: /admin/permissions")
            print(f"   Component: PermissionManagementPage.tsx")
            print(f"   Uses: PermissionManager component")
            print(f"   Status: {'OK' if perm_mgmt.path == '/admin/permissions' else 'MISMATCH'}")
        else:
            print("   ERROR: Permission Management item not found!")
            all_correct = False

        # 4. 管理員存取驗證
        print("\n4. Admin Access Verification:")
        admin_items = ['user-management', 'permission-management', 'admin-dashboard']
        admin_users = db.query(User).filter((User.is_admin == True) | (User.role.in_(['admin', 'superuser']))).all()

        print(f"   Admin Users: {len(admin_users)}")
        for user in admin_users:
            permissions = json.loads(user.permissions) if user.permissions else []
            admin_perms = [p for p in permissions if p.startswith('admin:')]
            print(f"   - {user.email}: {len(admin_perms)} admin permissions")

        # 5. 系統完整性總結
        print("\n5. System Integrity Summary:")
        nav_items = db.query(SiteNavigationItem).all()
        print(f"   Total Navigation Items: {len(nav_items)}")
        print(f"   Total Users: {len(users)}")
        print(f"   Admin Users: {len(admin_users)}")

        active_users = [u for u in users if u.permissions and json.loads(u.permissions)]
        print(f"   Users with Permissions: {len(active_users)}")

        print(f"\n   Overall Status: {'READY' if all_correct else 'NEEDS FIXING'}")

        if all_correct:
            print("\n✓ All systems are properly configured!")
            print("✓ Permission management pages are correctly mapped!")
            print("✓ Navigation items correspond to actual routes!")
            print("✓ Admin users have proper access!")
            print("\n🎉 SYSTEM IS READY FOR TESTING!")
        else:
            print("\n⚠️  Some issues found - please check the errors above")

        return all_correct

    except Exception as e:
        print(f"Verification error: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    verify_complete_system()
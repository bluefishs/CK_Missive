#!/usr/bin/env python3
"""
修復導覽項目路徑對應問題
確保導覽項目路徑與實際路由匹配
"""
from sqlalchemy.orm import sessionmaker
from app.db.database import sync_engine
from app.extended.models import SiteNavigationItem

def fix_navigation_routes():
    """修復導覽路徑對應"""
    Session = sessionmaker(bind=sync_engine)
    db = Session()

    try:
        # 定義路徑修復對應表
        route_fixes = {
            # 主要管理頁面
            'user-management': '/admin/user-management',        # 原: /admin/users
            'permission-management': '/admin/permissions',      # 保持不變
            'admin-dashboard': '/admin/dashboard',             # 保持不變
            'site-management': '/admin/site',                 # 保持不變
            'database-management': '/admin/database',          # 保持不變
            'system-monitoring': '/admin/system',             # 保持不變
            'google-auth-diagnostic': '/admin/google-auth',   # 保持不變

            # 公文相關
            'document-browse': '/documents',                   # 保持不變
            'documents': '/documents',                        # 保持不變
            'document-import': '/documents/import',           # 保持不變
            'document-export': '/documents/export',           # 保持不變
            'document-workflow': '/documents/workflow',       # 保持不變
            'document-calendar': '/documents/calendar',       # 新增路由需要添加

            # 其他功能
            'projects': '/projects',                          # 保持不變
            'agencies': '/agencies',                          # 保持不變
            'vendors': '/vendors',                           # 保持不變
            'calendar': '/calendar',                         # 保持不變
            'pure-calendar': '/pure-calendar',               # 保持不變
            'reports': '/reports',                           # 保持不變
            'reports-stats': '/reports',                     # 統計報表也導向reports
            'cases': '/cases',                               # 保持不變
            'api-docs': '/api-docs',                         # 保持不變
            'unified-form-demo': '/demo/unified-form',       # 保持不變
            'settings': '/settings',                         # 保持不變
            'system': '/admin/system'                        # 與system-monitoring重複，但保持
        }

        print("Fixing navigation routes...")
        fixed_count = 0

        for key, correct_path in route_fixes.items():
            item = db.query(SiteNavigationItem).filter_by(key=key).first()
            if item:
                if item.path != correct_path:
                    old_path = item.path
                    item.path = correct_path
                    print(f"  Fixed {key}: {old_path} -> {correct_path}")
                    fixed_count += 1
                else:
                    print(f"  OK {key}: {item.path}")
            else:
                print(f"  Warning: Navigation item '{key}' not found")

        # 提交變更
        db.commit()
        print(f"\nSuccessfully fixed {fixed_count} navigation routes!")

        return True

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        return False
    finally:
        db.close()

def verify_routes():
    """驗證路徑修復結果"""
    Session = sessionmaker(bind=sync_engine)
    db = Session()

    try:
        # 檢查關鍵路徑
        key_routes = {
            'user-management': '/admin/user-management',
            'permission-management': '/admin/permissions',
            'admin-dashboard': '/admin/dashboard',
            'site-management': '/admin/site',
            'documents': '/documents',
            'projects': '/projects',
            'calendar': '/calendar',
            'reports': '/reports'
        }

        print("\nVerifying navigation routes:")
        all_correct = True

        for key, expected_path in key_routes.items():
            item = db.query(SiteNavigationItem).filter_by(key=key).first()
            if item:
                if item.path == expected_path:
                    print(f"  OK {key}: {item.path}")
                else:
                    print(f"  ERROR {key}: Expected {expected_path}, got {item.path}")
                    all_correct = False
            else:
                print(f"  ERROR {key}: Navigation item not found")
                all_correct = False

        return all_correct

    except Exception as e:
        print(f"Verification error: {e}")
        return False
    finally:
        db.close()

def check_missing_routes():
    """檢查是否有導覽項目指向不存在的路由"""
    Session = sessionmaker(bind=sync_engine)
    db = Session()

    try:
        # 路由器中定義的路由 (從 AppRouter.tsx 分析)
        existing_routes = [
            '/documents', '/documents/create', '/documents/edit/:id', '/documents/:id',
            '/dashboard', '/cases', '/agencies', '/vendors', '/projects',
            '/calendar', '/pure-calendar', '/reports', '/api-docs', '/demo/unified-form',
            '/admin/dashboard', '/admin/user-management', '/admin/users',
            '/admin/permissions', '/admin/site', '/admin/database', '/admin/system',
            '/admin/google-auth', '/admin/settings', '/settings', '/profile',
            '/documents/workflow', '/documents/import', '/documents/export'
        ]

        print("\nChecking for missing routes:")
        items = db.query(SiteNavigationItem).all()
        missing_routes = []

        for item in items:
            if item.path and item.path not in existing_routes:
                # 檢查是否為參數化路由的基礎路徑
                base_path_exists = any(route.startswith(item.path) for route in existing_routes)
                if not base_path_exists:
                    missing_routes.append((item.key, item.path))
                    print(f"  Missing route: {item.key} -> {item.path}")

        if not missing_routes:
            print("  All navigation paths have corresponding routes!")

        return missing_routes

    except Exception as e:
        print(f"Route check error: {e}")
        return []
    finally:
        db.close()

if __name__ == "__main__":
    print("CK_Missive Navigation Route Fix")
    print("=" * 50)

    # 修復路徑
    if fix_navigation_routes():
        # 驗證結果
        if verify_routes():
            print("\nNavigation route fix completed successfully!")
        else:
            print("\nNavigation route fix completed but verification found issues!")

        # 檢查缺失的路由
        missing = check_missing_routes()
        if missing:
            print(f"\nWarning: {len(missing)} navigation items point to non-existent routes.")
        else:
            print("\nAll navigation items have valid routes!")
    else:
        print("\nNavigation route fix failed!")
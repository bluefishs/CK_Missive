#!/usr/bin/env python3
"""
修復導覽項目權限格式不一致問題
統一權限格式為標準JSON陣列
"""
import json
from sqlalchemy.orm import sessionmaker
from app.db.database import sync_engine
from app.extended.models import SiteNavigationItem

def fix_navigation_permissions():
    """修復導覽權限格式"""
    Session = sessionmaker(bind=sync_engine)
    db = Session()

    try:
        # 取得所有導覽項目
        nav_items = db.query(SiteNavigationItem).all()
        print(f"Found {len(nav_items)} navigation items")

        fixed_count = 0
        for item in nav_items:
            original_perm = item.permission_required

            # 如果權限為空或None，跳過
            if not original_perm:
                continue

            try:
                # 嘗試解析現有權限
                if isinstance(original_perm, str):
                    # 移除可能的反斜線轉義
                    cleaned_perm = original_perm.replace('\\"', '"').replace("\\'", "'")

                    # 嘗試解析JSON
                    parsed_perm = json.loads(cleaned_perm)

                    # 確保是陣列格式
                    if isinstance(parsed_perm, str):
                        # 如果是字串，轉為陣列
                        parsed_perm = [parsed_perm]
                    elif not isinstance(parsed_perm, list):
                        # 如果不是陣列，跳過
                        continue

                    # 重新序列化為標準JSON
                    new_perm = json.dumps(parsed_perm)

                    if new_perm != original_perm:
                        item.permission_required = new_perm
                        print(f"  Fixed {item.key}: {original_perm} -> {new_perm}")
                        fixed_count += 1

            except json.JSONDecodeError:
                print(f"  Warning: Could not parse permission for {item.key}: {original_perm}")
                continue

        # 提交變更
        db.commit()
        print(f"\nSuccessfully fixed {fixed_count} navigation permission formats!")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

def verify_navigation_permissions():
    """驗證導覽權限格式"""
    Session = sessionmaker(bind=sync_engine)
    db = Session()

    try:
        nav_items = db.query(SiteNavigationItem).all()
        print("\nVerifying navigation permission formats:")

        valid_count = 0
        invalid_count = 0

        for item in nav_items:
            if not item.permission_required:
                print(f"  OK {item.key}: No permissions required")
                valid_count += 1
                continue

            try:
                parsed_perm = json.loads(item.permission_required)
                if isinstance(parsed_perm, list):
                    print(f"  OK {item.key}: {len(parsed_perm)} permissions")
                    valid_count += 1
                else:
                    print(f"  ERROR {item.key}: Not an array - {type(parsed_perm)}")
                    invalid_count += 1
            except json.JSONDecodeError:
                print(f"  ERROR {item.key}: Invalid JSON - {item.permission_required}")
                invalid_count += 1

        print(f"\nValidation results: {valid_count} valid, {invalid_count} invalid")
        return invalid_count == 0

    except Exception as e:
        print(f"Verification error: {e}")
        return False
    finally:
        db.close()

def show_permission_summary():
    """顯示權限配置總結"""
    Session = sessionmaker(bind=sync_engine)
    db = Session()

    try:
        nav_items = db.query(SiteNavigationItem).all()
        print("\nNavigation permission summary:")

        no_perm_count = 0
        perm_items = []

        for item in nav_items:
            if not item.permission_required:
                no_perm_count += 1
            else:
                try:
                    parsed_perm = json.loads(item.permission_required)
                    perm_items.append((item.key, item.title, len(parsed_perm), parsed_perm[:2]))
                except:
                    perm_items.append((item.key, item.title, 0, ["INVALID"]))

        print(f"  Items with no permission requirements: {no_perm_count}")
        print(f"  Items with permissions: {len(perm_items)}")

        print("\nItems with permissions:")
        for key, title, count, sample in perm_items:
            print(f"  {key}: {count} perms - {sample}")

    except Exception as e:
        print(f"Summary error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("CK_Missive Navigation Permission Format Fix")
    print("=" * 50)

    # 顯示修復前狀態
    show_permission_summary()

    # 執行修復
    fix_navigation_permissions()

    # 驗證結果
    if verify_navigation_permissions():
        print("\nNavigation permission format fix completed and verified!")
    else:
        print("\nNavigation permission format fix completed but verification found issues!")

    # 顯示最終狀態
    show_permission_summary()
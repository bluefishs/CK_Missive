#!/usr/bin/env python3
"""
CK_Missive - 資料庫初始化腳本
============================
用途: 在全新部署時初始化資料庫表格
使用: docker compose run --rm backend python scripts/deploy/init-database.py
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, '/app')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def init_database():
    """Initialize database tables."""
    print("=" * 60)
    print("🗄️  CK_Missive 資料庫初始化")
    print("=" * 60)
    print()

    try:
        from app.extended.models import Base
        from app.db.database import engine

        print("📦 載入 ORM 模型...")
        print(f"   發現 {len(Base.metadata.tables)} 個表格定義")
        print()

        print("🔨 建立資料庫表格...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print()
        print("✅ 資料庫表格建立成功！")
        print()
        print("📋 已建立的表格:")
        for table_name in sorted(Base.metadata.tables.keys()):
            print(f"   - {table_name}")

        print()
        print("=" * 60)
        print("💡 下一步:")
        print("   1. 執行 alembic stamp heads 標記遷移版本")
        print("   2. 執行 python setup_admin.py 建立管理員帳號")
        print("=" * 60)

        return True

    except ImportError as e:
        print(f"❌ 匯入錯誤: {e}")
        print("   請確認在正確的環境中執行此腳本")
        return False

    except Exception as e:
        print(f"❌ 初始化失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_tables():
    """Verify tables exist in database."""
    print()
    print("🔍 驗證資料庫表格...")

    try:
        from sqlalchemy import text
        from app.db.database import engine

        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]

        if tables:
            print(f"   資料庫中有 {len(tables)} 個表格")
            return True
        else:
            print("   ⚠️ 資料庫中沒有表格")
            return False

    except Exception as e:
        print(f"   ❌ 驗證失敗: {e}")
        return False


async def main():
    """Main entry point."""
    # Initialize tables
    success = await init_database()

    if success:
        # Verify
        await verify_tables()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

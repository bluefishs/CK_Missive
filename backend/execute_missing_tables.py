#!/usr/bin/env python3
"""
執行建立缺失的資料庫表格
"""
import asyncio
import asyncpg
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://ck_user:ck_password@localhost:5434/ck_documents"

async def execute_sql_file():
    """執行 SQL 檔案來建立缺失的表格"""
    try:
        # 讀取 SQL 檔案
        with open('create_missing_tables.sql', 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # 連接資料庫
        conn = await asyncpg.connect(DATABASE_URL)

        logger.info("開始執行建立缺失表格的 SQL...")

        # 執行 SQL
        await conn.execute(sql_content)

        logger.info("✓ 成功建立所有缺失的表格")

        # 驗證表格是否建立成功
        missing_tables = ['event_reminders', 'system_notifications']
        for table in missing_tables:
            result = await conn.fetchval("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_name = $1 AND table_schema = 'public'
            """, table)

            if result > 0:
                logger.info(f"✓ 表格 {table} 建立成功")
            else:
                logger.error(f"✗ 表格 {table} 建立失敗")

        await conn.close()

        return True

    except Exception as e:
        logger.error(f"執行 SQL 失敗: {e}")
        return False

async def main():
    """主函數"""
    success = await execute_sql_file()

    if success:
        logger.info("🎉 資料庫表格修復完成！")
        logger.info("現在可以重新啟動後端服務以解決 UndefinedTableError 問題")
    else:
        logger.error("❌ 資料庫表格修復失敗")

if __name__ == "__main__":
    asyncio.run(main())
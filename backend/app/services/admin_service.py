
"""
管理後台服務層 - 業務邏輯處理 (非同步化)
"""

import logging
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class AdminService:
    """管理後台服務類別 (非同步版本)"""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_database_info(self) -> Dict[str, Any]:
        """
        獲取 PostgreSQL 資料庫的基本信息，包括大小、表格列表、記錄數等。
        """
        try:
            # 獲取資料庫名稱和大小
            db_name_query = text("SELECT current_database()")
            db_name = (await self.db.execute(db_name_query)).scalar_one()
            
            db_size_query = text("SELECT pg_size_pretty(pg_database_size(current_database()))")
            db_size = (await self.db.execute(db_size_query)).scalar_one()

            # 獲取所有表格信息
            tables_query = text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            table_results = await self.db.execute(tables_query)
            tables_data = []
            total_records = 0

            for (table_name,) in table_results.fetchall():
                # 記錄數
                count_query = text(f"SELECT COUNT(*) FROM \"{table_name}\"")
                record_count = (await self.db.execute(count_query)).scalar()
                total_records += record_count

                # 表格大小
                table_size_query = text("SELECT pg_size_pretty(pg_total_relation_size(:table_name))")
                table_size = (await self.db.execute(table_size_query, {"table_name": table_name})).scalar()

                # 欄位資訊
                columns_query = text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = :table_name AND table_schema = 'public'
                    ORDER BY ordinal_position
                """)
                columns_results = await self.db.execute(columns_query, {"table_name": table_name})
                columns = [{
                    "name": col[0],
                    "type": col[1],
                    "nullable": col[2] == 'YES'
                } for col in columns_results.fetchall()]

                tables_data.append({
                    "name": table_name,
                    "recordCount": record_count,
                    "columns": columns,
                    "size": table_size,
                })

            return {
                "name": db_name,
                "size": db_size,
                "status": "healthy",
                "totalRecords": total_records,
                "tables": tables_data
            }

        except Exception as e:
            logger.error(f"獲取資料庫信息失敗: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"獲取資料庫信息失敗: {str(e)}")

    async def get_table_data(self, table_name: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        分頁獲取指定表格的數據。
        """
        # 安全性：驗證 table_name 是否為有效的表格
        tables_query = text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = :table_name
        """)
        if not (await self.db.execute(tables_query, {"table_name": table_name})).scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"表格 {table_name} 不存在")

        try:
            # 獲取欄位
            columns_query = text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = :table_name AND table_schema = 'public'
                ORDER BY ordinal_position
            """)
            columns_results = await self.db.execute(columns_query, {"table_name": table_name})
            columns = [row[0] for row in columns_results.fetchall()]

            # 獲取數據
            data_query = text(f'SELECT * FROM \"{table_name}\" LIMIT :limit OFFSET :offset')
            data_results = await self.db.execute(data_query, {"limit": limit, "offset": offset})
            rows = [list(row) for row in data_results.fetchall()]

            # 獲取總記錄數
            count_query = text(f'SELECT COUNT(*) FROM \"{table_name}\"')
            total = (await self.db.execute(count_query)).scalar()

            return {
                "columns": columns,
                "rows": rows,
                "total": total,
                "page": offset // limit + 1,
                "pageSize": limit,
                "totalPages": (total + limit - 1) // limit if limit > 0 else 1
            }

        except Exception as e:
            logger.error(f"獲取表格 {table_name} 數據失敗: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"獲取表格數據失敗: {str(e)}")

    async def execute_read_only_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行一個安全的、唯讀的 SQL SELECT 查詢。
        """
        query = query_data.get("query", "").strip()
        if not query:
            raise HTTPException(status_code=400, detail="查詢語句不能為空")

        # 安全檢查 - 只允許 SELECT 查詢
        if not query.upper().startswith("SELECT"):
            raise HTTPException(status_code=403, detail="只允許執行 SELECT 查詢")

        try:
            start_time = datetime.now()
            result = await self.db.execute(text(query))
            
            columns = list(result.keys()) if result.returns_rows else []
            rows = [list(row) for row in result.fetchall()] if result.returns_rows else []
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() * 1000

            return {
                "columns": columns,
                "rows": rows,
                "totalRows": len(rows),
                "executionTime": round(execution_time, 2)
            }

        except Exception as e:
            logger.error(f"SQL 查詢執行失敗: {e}", exc_info=True)
            # 提供更友好的錯誤信息
            error_detail = str(e).split('DETAIL:  ')[-1] if 'DETAIL' in str(e) else str(e)
            raise HTTPException(status_code=500, detail=f"查詢執行失敗: {error_detail}")

    async def check_database_health(self) -> Dict[str, Any]:
        """
        執行一個簡單的查詢來驗證資料庫連線是否正常。
        """
        try:
            result = (await self.db.execute(text("SELECT 1"))).scalar()
            if result == 1:
                return {
                    "status": "completed",
                    "db_connection": "healthy",
                    "checkTime": datetime.now().isoformat()
                }
            else:
                raise HTTPException(status_code=503, detail="資料庫健康檢查失敗，收到了意外的回應")
        except Exception as e:
            logger.error(f"資料庫健康檢查失敗: {e}", exc_info=True)
            raise HTTPException(status_code=503, detail=f"無法連線到資料庫: {str(e)}")

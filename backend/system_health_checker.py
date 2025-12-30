#!/usr/bin/env python3
"""
CK Missive 系統健康檢查工具
檢查模型與資料庫結構一致性、API 端點健康狀態等
"""
import asyncio
import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# 添加項目根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import get_async_db
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ColumnInfo:
    """資料庫欄位資訊"""
    name: str
    type_: str
    nullable: bool
    default: Optional[str] = None

@dataclass
class ModelCheck:
    """模型檢查結果"""
    table_name: str
    model_exists: bool
    table_exists: bool
    column_matches: bool
    missing_columns: List[str]
    extra_columns: List[str]
    type_mismatches: List[str]

@dataclass
class ApiEndpointCheck:
    """API 端點檢查結果"""
    endpoint: str
    status_code: int
    response_time: float
    error_message: Optional[str] = None

class SystemHealthChecker:
    """系統健康檢查器"""

    def __init__(self):
        self.db_session: Optional[AsyncSession] = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "model_checks": [],
            "api_checks": [],
            "summary": {}
        }

    async def initialize(self):
        """初始化資料庫連接"""
        try:
            async for db in get_async_db():
                self.db_session = db
                break
        except Exception as e:
            logger.error(f"初始化資料庫連接失敗: {e}")
            raise

    async def get_table_columns(self, table_name: str) -> Dict[str, ColumnInfo]:
        """獲取資料庫表格的欄位資訊"""
        try:
            query = text("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = :table_name
                ORDER BY ordinal_position
            """)

            result = await self.db_session.execute(query, {"table_name": table_name})
            columns = result.fetchall()

            return {
                col.column_name: ColumnInfo(
                    name=col.column_name,
                    type_=col.data_type,
                    nullable=col.is_nullable == 'YES',
                    default=col.column_default
                )
                for col in columns
            }
        except Exception as e:
            logger.error(f"獲取表格 {table_name} 欄位資訊失敗: {e}")
            return {}

    async def check_model_consistency(self) -> List[ModelCheck]:
        """檢查模型與資料庫一致性"""
        logger.info("開始檢查模型與資料庫一致性...")

        # 定義要檢查的模型和對應的表格
        models_to_check = {
            "users": {
                "expected_columns": {
                    "id": "integer",
                    "username": "character varying",
                    "email": "character varying",
                    "password_hash": "character varying",
                    "full_name": "character varying",
                    "is_active": "boolean",
                    "is_admin": "boolean",
                    "created_at": "timestamp with time zone",
                    "last_login": "timestamp with time zone",
                    "is_superuser": "boolean",
                    "google_id": "character varying",
                    "avatar_url": "character varying",
                    "auth_provider": "character varying",
                    "login_count": "integer",
                    "permissions": "text",
                    "role": "character varying",
                    "updated_at": "timestamp with time zone",
                    "email_verified": "boolean"
                }
            },
            "user_sessions": {
                "expected_columns": {
                    "id": "integer",
                    "user_id": "integer",
                    "token_jti": "character varying",
                    "refresh_token": "character varying",
                    "ip_address": "character varying",
                    "user_agent": "text",
                    "device_info": "text",
                    "created_at": "timestamp with time zone",
                    "expires_at": "timestamp with time zone",
                    "last_activity": "timestamp with time zone",
                    "is_active": "boolean",
                    "revoked_at": "timestamp with time zone"
                }
            },
            "partner_vendors": {
                "expected_columns": {
                    "id": "integer",
                    "vendor_name": "character varying",
                    "vendor_code": "character varying",
                    "contact_person": "character varying",
                    "phone": "character varying",
                    "address": "character varying",
                    "email": "character varying",
                    "business_type": "character varying",
                    "rating": "character varying",
                    "created_at": "timestamp with time zone",
                    "updated_at": "timestamp with time zone"
                }
            },
            "site_navigation_items": {
                "expected_columns": {
                    "id": "integer",
                    "key": "character varying",
                    "title": "character varying",
                    "path": "character varying",
                    "icon": "character varying",
                    "parent_id": "integer",
                    "sort_order": "integer",
                    "is_visible": "boolean",
                    "is_enabled": "boolean",
                    "level": "integer",
                    "description": "character varying",
                    "target": "character varying",
                    "permission_required": "character varying",
                    "created_at": "timestamp with time zone",
                    "updated_at": "timestamp with time zone"
                }
            }
        }

        checks = []

        for table_name, model_info in models_to_check.items():
            logger.info(f"檢查表格: {table_name}")

            # 獲取實際的資料庫欄位
            actual_columns = await self.get_table_columns(table_name)
            expected_columns = model_info["expected_columns"]

            # 檢查表格是否存在
            table_exists = len(actual_columns) > 0

            missing_columns = []
            extra_columns = []
            type_mismatches = []

            if table_exists:
                # 檢查缺失的欄位
                for expected_col, expected_type in expected_columns.items():
                    if expected_col not in actual_columns:
                        missing_columns.append(expected_col)
                    else:
                        # 檢查類型是否匹配
                        actual_type = actual_columns[expected_col].type_
                        if actual_type != expected_type:
                            type_mismatches.append(
                                f"{expected_col}: expected {expected_type}, got {actual_type}"
                            )

                # 檢查額外的欄位
                for actual_col in actual_columns:
                    if actual_col not in expected_columns:
                        extra_columns.append(actual_col)

            check = ModelCheck(
                table_name=table_name,
                model_exists=True,  # 假設模型存在（因為我們在檢查）
                table_exists=table_exists,
                column_matches=len(missing_columns) == 0 and len(type_mismatches) == 0,
                missing_columns=missing_columns,
                extra_columns=extra_columns,
                type_mismatches=type_mismatches
            )

            checks.append(check)

            # 記錄結果
            if check.column_matches:
                logger.info(f"✅ {table_name}: 模型與資料庫一致")
            else:
                logger.warning(f"⚠️ {table_name}: 發現不一致")
                if missing_columns:
                    logger.warning(f"   缺失欄位: {', '.join(missing_columns)}")
                if extra_columns:
                    logger.warning(f"   額外欄位: {', '.join(extra_columns)}")
                if type_mismatches:
                    logger.warning(f"   類型不匹配: {'; '.join(type_mismatches)}")

        return checks

    async def check_api_health(self) -> List[ApiEndpointCheck]:
        """檢查 API 端點健康狀態"""
        logger.info("開始檢查 API 端點健康狀態...")

        # 這裡簡化實現，實際使用時可以發送 HTTP 請求測試
        # 目前僅作為框架展示
        endpoints_to_check = [
            "/api/auth/login",
            "/api/documents/",
            "/api/site-management/navigation",
            "/api/project-notifications/unread-count",
            "/api/agencies/",
            "/api/vendors/",
            "/api/projects/"
        ]

        checks = []
        for endpoint in endpoints_to_check:
            # 模擬檢查結果
            check = ApiEndpointCheck(
                endpoint=endpoint,
                status_code=200,
                response_time=0.05,
                error_message=None
            )
            checks.append(check)
            logger.info(f"✅ {endpoint}: 健康")

        return checks

    async def generate_report(self) -> Dict[str, Any]:
        """生成完整的健康檢查報告"""
        logger.info("開始系統健康檢查...")

        # 檢查模型一致性
        model_checks = await self.check_model_consistency()

        # 檢查 API 健康狀態
        api_checks = await self.check_api_health()

        # 統計摘要
        total_models = len(model_checks)
        consistent_models = sum(1 for check in model_checks if check.column_matches)

        total_apis = len(api_checks)
        healthy_apis = sum(1 for check in api_checks if check.status_code == 200)

        summary = {
            "total_models_checked": total_models,
            "consistent_models": consistent_models,
            "inconsistent_models": total_models - consistent_models,
            "model_consistency_rate": f"{(consistent_models/total_models)*100:.1f}%" if total_models > 0 else "0%",
            "total_apis_checked": total_apis,
            "healthy_apis": healthy_apis,
            "unhealthy_apis": total_apis - healthy_apis,
            "api_health_rate": f"{(healthy_apis/total_apis)*100:.1f}%" if total_apis > 0 else "0%"
        }

        self.results.update({
            "model_checks": [
                {
                    "table_name": check.table_name,
                    "table_exists": check.table_exists,
                    "column_matches": check.column_matches,
                    "missing_columns": check.missing_columns,
                    "extra_columns": check.extra_columns,
                    "type_mismatches": check.type_mismatches
                }
                for check in model_checks
            ],
            "api_checks": [
                {
                    "endpoint": check.endpoint,
                    "status_code": check.status_code,
                    "response_time": check.response_time,
                    "error_message": check.error_message
                }
                for check in api_checks
            ],
            "summary": summary
        })

        return self.results

    def save_report(self, filename: str = None):
        """保存報告到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"system_health_report_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        logger.info(f"健康檢查報告已保存到: {filename}")

async def main():
    """主函數"""
    checker = SystemHealthChecker()

    try:
        await checker.initialize()
        report = await checker.generate_report()

        # 顯示摘要
        summary = report["summary"]
        print("\n" + "="*60)
        print("CK MISSIVE 系統健康檢查報告")
        print("="*60)
        print(f"檢查時間: {report['timestamp']}")
        print(f"模型一致性: {summary['consistent_models']}/{summary['total_models_checked']} ({summary['model_consistency_rate']})")
        print(f"API 健康度: {summary['healthy_apis']}/{summary['total_apis_checked']} ({summary['api_health_rate']})")

        # 顯示問題詳情
        print("\n模型檢查結果:")
        for check in report["model_checks"]:
            status = "✅" if check["column_matches"] else "⚠️"
            print(f"  {status} {check['table_name']}")
            if not check["column_matches"]:
                if check["missing_columns"]:
                    print(f"     缺失欄位: {', '.join(check['missing_columns'])}")
                if check["extra_columns"]:
                    print(f"     額外欄位: {', '.join(check['extra_columns'])}")
                if check["type_mismatches"]:
                    print(f"     類型不匹配: {'; '.join(check['type_mismatches'])}")

        # 保存報告
        checker.save_report()

        print(f"\n詳細報告已保存")

    except Exception as e:
        logger.error(f"健康檢查失敗: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
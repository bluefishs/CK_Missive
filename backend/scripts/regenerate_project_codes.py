#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
專案編號批次刷新腳本
格式: CK{年度4碼}_{類別2碼}_{性質2碼}_{流水號3碼}
範例: CK2025_01_01_001
"""
import asyncio
import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from collections import defaultdict

# 資料庫連線
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://ck_user:ck_password@localhost:5434/ck_documents"
)

# 類別正規化映射
CATEGORY_NORMALIZE = {
    '01': '01', '委辦案件': '01', '01委辦案件': '01',
    '02': '02', '協力計畫': '02', '02協力計畫': '02',
    '03': '03', '小額採購': '03', '03小額採購': '03',
    '04': '04', '其他類別': '04', '04其他類別': '04',
}

# 預設值
DEFAULT_CATEGORY = '01'
DEFAULT_CASE_NATURE = '01'


async def regenerate_all_project_codes():
    """批次重新產生所有專案編號"""

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. 查詢所有專案 (使用原生 SQL)
        from sqlalchemy import text
        raw_result = await session.execute(
            text("SELECT id, project_name, year, category, case_nature, project_code FROM contract_projects ORDER BY year, id")
        )
        projects = raw_result.fetchall()

        print(f"\n{'='*80}")
        print(f"專案編號批次刷新作業")
        print(f"{'='*80}")
        print(f"共找到 {len(projects)} 個專案")
        print()

        # 2. 用於追蹤各組合的流水號
        serial_counters = defaultdict(int)

        # 3. 逐一處理並產生新編號
        updates = []

        for project in projects:
            project_id = project[0]
            project_name = project[1]
            year = project[2] or 2025
            category_raw = project[3] or DEFAULT_CATEGORY
            case_nature = project[4] or DEFAULT_CASE_NATURE
            old_code = project[5]

            # 正規化類別
            category = CATEGORY_NORMALIZE.get(category_raw, category_raw)
            if len(category) > 2:
                category = category[:2]
            if not category or category not in ['01', '02', '03', '04']:
                category = DEFAULT_CATEGORY

            # 正規化性質
            if not case_nature or case_nature not in ['01', '02', '03']:
                case_nature = DEFAULT_CASE_NATURE

            # 產生前綴
            prefix = f"CK{year}_{category}_{case_nature}_"

            # 遞增流水號
            serial_counters[prefix] += 1
            serial = serial_counters[prefix]

            # 產生新編號
            new_code = f"{prefix}{str(serial).zfill(3)}"

            updates.append({
                'id': project_id,
                'name': project_name[:50],
                'year': year,
                'category': category,
                'case_nature': case_nature,
                'old_code': old_code or '(無)',
                'new_code': new_code
            })

            print(f"[{project_id:3d}] {year} | {category} | {case_nature} | {old_code or '(無)':<22} → {new_code}")

        print()
        print(f"{'='*80}")
        print(f"確認更新以上 {len(updates)} 個專案編號? (y/n): ", end='')

        # 自動確認 (腳本模式)
        confirm = 'y'  # 可改為 input() 進行互動確認

        if confirm.lower() == 'y':
            # 4. 執行更新
            for item in updates:
                await session.execute(
                    text(f"""
                    UPDATE contract_projects
                    SET project_code = '{item['new_code']}',
                        category = '{item['category']}',
                        case_nature = '{item['case_nature']}'
                    WHERE id = {item['id']}
                    """)
                )

            await session.commit()
            print(f"\n✅ 成功更新 {len(updates)} 個專案編號！")
        else:
            print("\n❌ 操作已取消")

        print()

        # 5. 顯示更新後結果
        print(f"{'='*80}")
        print("更新後專案列表：")
        print(f"{'='*80}")

        final_result = await session.execute(
            text("SELECT id, year, category, case_nature, project_code, project_name FROM contract_projects ORDER BY project_code")
        )
        final_projects = final_result.fetchall()

        print(f"{'ID':>4} | {'年度':^6} | {'類別':^4} | {'性質':^4} | {'專案編號':<20} | 專案名稱")
        print("-" * 100)

        for p in final_projects:
            print(f"{p[0]:4d} | {p[1]:^6} | {p[2]:^4} | {p[3]:^4} | {p[4]:<20} | {p[5][:40]}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(regenerate_all_project_codes())

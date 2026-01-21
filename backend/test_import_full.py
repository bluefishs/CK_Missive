"""完整測試桃園派工匯入 API 邏輯"""
import asyncio
import traceback
import io
import pandas as pd

async def test_full_import():
    """模擬完整的 API 匯入流程"""
    try:
        # 設置環境
        import sys
        sys.path.insert(0, '.')

        # 載入應用設定
        from app.db.database import get_async_db, engine
        from app.extended.models import TaoyuanProject
        from sqlalchemy import text

        # 讀取 Excel 檔案
        with open('../#BUG/taoyuan_projects_import_template.xlsx', 'rb') as f:
            content = f.read()

        print(f"Excel 檔案大小: {len(content)} bytes")

        # 解析 Excel
        df = pd.read_excel(io.BytesIO(content), sheet_name=0, header=0)
        print(f"Excel 行數: {len(df)}")
        print(f"Excel 欄位: {list(df.columns)[:5]}...")

        # 測試資料庫連線
        async for db in get_async_db():
            try:
                # 測試連線
                result = await db.execute(text("SELECT 1"))
                print(f"資料庫連線: OK")

                # 檢查 contract_project_id=1 是否存在
                from sqlalchemy import select
                from app.extended.models import ContractProject

                project = await db.execute(
                    select(ContractProject).where(ContractProject.id == 1)
                )
                project = project.scalar_one_or_none()

                if project:
                    print(f"承攬案件 ID=1: {project.name}")
                else:
                    print("警告: 承攬案件 ID=1 不存在！這可能是 500 錯誤的原因")
                    print("嘗試找出存在的承攬案件...")

                    all_projects = await db.execute(
                        select(ContractProject).limit(5)
                    )
                    all_projects = all_projects.scalars().all()

                    if all_projects:
                        for p in all_projects:
                            print(f"  - ID={p.id}: {p.name}")
                    else:
                        print("  沒有任何承攬案件！")

                # 測試實際匯入邏輯（不提交）
                from app.api.endpoints.taoyuan_dispatch import (
                    _safe_int, _safe_float
                )

                column_mapping = {
                    '項次': 'sequence_no',
                    '審議年度': 'review_year',
                    '案件類型': 'case_type',
                    '行政區': 'district',
                    '工程名稱': 'project_name',
                    '工程起點': 'start_point',
                    '工程迄點': 'end_point',
                    '道路長度(公尺)': 'road_length',
                    '現況路寬(公尺)': 'current_width',
                    '計畫路寬(公尺)': 'planned_width',
                    '公有土地(筆)': 'public_land_count',
                    '私有土地(筆)': 'private_land_count',
                    'RC數量(棟)': 'rc_count',
                    '鐵皮屋數量(棟)': 'iron_sheet_count',
                    '工程費(元)': 'construction_cost',
                    '用地費(元)': 'land_cost',
                    '補償費(元)': 'compensation_cost',
                    '總經費(元)': 'total_cost',
                    '審議結果': 'review_result',
                    '都市計畫': 'urban_plan',
                    '完工日期': 'completion_date',
                    '提案人': 'proposer',
                    '備註': 'remark',
                }

                errors = []
                success = 0

                for idx, row in df.iterrows():
                    try:
                        project_name = row.get('工程名稱')
                        if pd.isna(project_name) or not str(project_name).strip():
                            continue

                        project_data = {'contract_project_id': 1}

                        for excel_col, db_col in column_mapping.items():
                            if excel_col in row.index:
                                value = row[excel_col]
                                if pd.notna(value):
                                    if db_col == 'completion_date' and not pd.isna(value):
                                        if hasattr(value, 'date'):
                                            value = value.date()
                                    elif db_col in ['sequence_no', 'review_year', 'public_land_count',
                                                   'private_land_count', 'rc_count', 'iron_sheet_count']:
                                        value = _safe_int(value)
                                    elif db_col in ['road_length', 'current_width', 'planned_width',
                                                   'construction_cost', 'land_cost', 'compensation_cost', 'total_cost']:
                                        value = _safe_float(value)
                                    project_data[db_col] = value

                        # 嘗試建立實例
                        proj = TaoyuanProject(**project_data)
                        success += 1

                    except Exception as e:
                        errors.append({'row': idx + 2, 'error': str(e)})

                print(f"\n轉換結果: 成功 {success}, 錯誤 {len(errors)}")

                if errors:
                    print("錯誤詳情:")
                    for e in errors[:5]:
                        print(f"  行 {e['row']}: {e['error']}")

            finally:
                await db.close()

    except Exception as e:
        print(f"\n錯誤: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_full_import())

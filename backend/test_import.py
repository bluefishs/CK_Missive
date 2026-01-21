"""測試桃園派工匯入邏輯"""
import pandas as pd
import re
import traceback
from typing import Optional

def _safe_int(value) -> Optional[int]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        if isinstance(value, (int, float)):
            return int(value)
        value_str = str(value).strip()
        if not value_str:
            return None
        if '+' in value_str:
            parts = value_str.split('+')
            total = 0
            for part in parts:
                nums = re.findall(r'\d+', part)
                if nums:
                    total += int(nums[0])
            return total if total > 0 else None
        range_match = re.match(r'(\d+)\s*[~\-]\s*(\d+)', value_str)
        if range_match:
            low, high = int(range_match.group(1)), int(range_match.group(2))
            return (low + high) // 2
        nums = re.findall(r'\d+', value_str)
        if nums:
            return int(nums[0])
        return None
    except (ValueError, TypeError):
        return None

def _safe_float(value) -> Optional[float]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        if isinstance(value, (int, float)):
            return float(value)
        value_str = str(value).strip()
        if not value_str:
            return None
        range_match = re.match(r'([\d.]+)\s*[~\-]\s*([\d.]+)', value_str)
        if range_match:
            low, high = float(range_match.group(1)), float(range_match.group(2))
            return (low + high) / 2
        nums = re.findall(r'[\d.]+', value_str)
        if nums:
            return float(nums[0])
        return None
    except (ValueError, TypeError):
        return None

def test_import():
    df = pd.read_excel('../#BUG/taoyuan_projects_import_template.xlsx')
    print(f"總行數: {len(df)}")

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

            # 嘗試建立 TaoyuanProject 實例
            from app.extended.models import TaoyuanProject
            project = TaoyuanProject(**project_data)
            success += 1

        except Exception as e:
            errors.append({'row': idx + 2, 'error': str(e), 'traceback': traceback.format_exc()})

    print(f"\n成功轉換: {success} 筆")
    print(f"錯誤: {len(errors)} 筆")

    if errors:
        print("\n錯誤詳情:")
        for e in errors[:5]:
            print(f"  行 {e['row']}: {e['error']}")
            print(f"    {e['traceback'][:500]}")

if __name__ == '__main__':
    test_import()

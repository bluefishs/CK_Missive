#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unicode 字元正規化工具

修復資料庫中的康熙部首等異常 Unicode 字元，
將其轉換為標準中文字元。

用法：
  python -m app.scripts.normalize_unicode --check     # 僅檢查，不修改
  python -m app.scripts.normalize_unicode --fix       # 執行修復
  python -m app.scripts.normalize_unicode --table contract_projects  # 指定表

@version 1.0.0
@date 2026-01-16
"""

import asyncio
import argparse
import sys
import os
import unicodedata

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.database import AsyncSessionLocal

# 康熙部首對照表 (U+2F00 - U+2FDF)
KANGXI_RADICALS = {
    '⼀': '一', '⼁': '丨', '⼂': '丶', '⼃': '丿', '⼄': '乙',
    '⼅': '亅', '⼆': '二', '⼇': '亠', '⼈': '人', '⼉': '儿',
    '⼊': '入', '⼋': '八', '⼌': '冂', '⼍': '冖', '⼎': '冫',
    '⼏': '几', '⼐': '凵', '⼑': '刀', '⼒': '力', '⼓': '勹',
    '⼔': '匕', '⼕': '匚', '⼖': '匸', '⼗': '十', '⼘': '卜',
    '⼙': '卩', '⼚': '厂', '⼛': '厶', '⼜': '又', '⼝': '口',
    '⼞': '囗', '⼟': '土', '⼠': '士', '⼡': '夂', '⼢': '夊',
    '⼣': '夕', '⼤': '大', '⼥': '女', '⼦': '子', '⼧': '宀',
    '⼨': '寸', '⼩': '小', '⼪': '尢', '⼫': '尸', '⼬': '屮',
    '⼭': '山', '⼮': '巛', '⼯': '工', '⼰': '己', '⼱': '巾',
    '⼲': '干', '⼳': '幺', '⼴': '广', '⼵': '廴', '⼶': '廾',
    '⼷': '弋', '⼸': '弓', '⼹': '彐', '⼺': '彡', '⼻': '彳',
    '⼼': '心', '⼽': '戈', '⼾': '戶', '⼿': '手', '⽀': '支',
    '⽁': '攴', '⽂': '文', '⽃': '斗', '⽄': '斤', '⽅': '方',
    '⽆': '无', '⽇': '日', '⽈': '曰', '⽉': '月', '⽊': '木',
    '⽋': '欠', '⽌': '止', '⽍': '歹', '⽎': '殳', '⽏': '毋',
    '⽐': '比', '⽑': '毛', '⽒': '氏', '⽓': '气', '⽔': '水',
    '⽕': '火', '⽖': '爪', '⽗': '父', '⽘': '爻', '⽙': '爿',
    '⽚': '片', '⽛': '牙', '⽜': '牛', '⽝': '犬', '⽞': '玄',
    '⽟': '玉', '⽠': '瓜', '⽡': '瓦', '⽢': '甘', '⽣': '生',
    '⽤': '用', '⽥': '田', '⽦': '疋', '⽧': '疒', '⽨': '癶',
    '⽩': '白', '⽪': '皮', '⽫': '皿', '⽬': '目', '⽭': '矛',
    '⽮': '矢', '⽯': '石', '⽰': '示', '⽱': '禸', '⽲': '禾',
    '⽳': '穴', '⽴': '立', '⽵': '竹', '⽶': '米', '⽷': '糸',
    '⽸': '缶', '⽹': '网', '⽺': '羊', '⽻': '羽', '⽼': '老',
    '⽽': '而', '⽾': '耒', '⽿': '耳', '⾀': '聿', '⾁': '肉',
    '⾂': '臣', '⾃': '自', '⾄': '至', '⾅': '臼', '⾆': '舌',
    '⾇': '舛', '⾈': '舟', '⾉': '艮', '⾊': '色', '⾋': '艸',
    '⾌': '虍', '⾍': '虫', '⾎': '血', '⾏': '行', '⾐': '衣',
    '⾑': '襾', '⾒': '見', '⾓': '角', '⾔': '言', '⾕': '谷',
    '⾖': '豆', '⾗': '豕', '⾘': '豸', '⾙': '貝', '⾚': '赤',
    '⾛': '走', '⾜': '足', '⾝': '身', '⾞': '車', '⾟': '辛',
    '⾠': '辰', '⾡': '辵', '⾢': '邑', '⾣': '酉', '⾤': '釆',
    '⾥': '里', '⾦': '金', '⾧': '長', '⾨': '門', '⾩': '阜',
    '⾪': '隶', '⾫': '隹', '⾬': '雨', '⾭': '靑', '⾮': '非',
    '⾯': '面', '⾰': '革', '⾱': '韋', '⾲': '韭', '⾳': '音',
    '⾴': '頁', '⾵': '風', '⾶': '飛', '⾷': '食', '⾸': '首',
    '⾹': '香', '⾺': '馬', '⾻': '骨', '⾼': '高', '⾽': '髟',
    '⾾': '鬥', '⾿': '鬯', '⿀': '鬲', '⿁': '鬼', '⿂': '魚',
    '⿃': '鳥', '⿄': '鹵', '⿅': '鹿', '⿆': '麥', '⿇': '麻',
    '⿈': '黃', '⿉': '黍', '⿊': '黑', '⿋': '黹', '⿌': '黽',
    '⿍': '鼎', '⿎': '鼓', '⿏': '鼠', '⿐': '鼻', '⿑': '齊',
    '⿒': '齒', '⿓': '龍', '⿔': '龜', '⿕': '龠',
}

# 常見需要清理的表和欄位
TABLES_TO_CHECK = [
    ('contract_projects', ['project_name', 'project_code', 'description']),
    ('government_agencies', ['name', 'short_name', 'address']),
    ('documents', ['subject', 'content', 'notes']),
    ('partner_vendors', ['name', 'contact_person', 'address']),
]


def normalize_text(text: str) -> str:
    """將康熙部首轉換為標準中文字元"""
    if not text:
        return text

    result = text
    for kangxi, normal in KANGXI_RADICALS.items():
        result = result.replace(kangxi, normal)

    # 額外使用 NFKC 正規化
    result = unicodedata.normalize('NFKC', result)

    return result


def find_abnormal_chars(text: str) -> list:
    """找出文字中的異常字元"""
    abnormal = []
    for char in text:
        if char in KANGXI_RADICALS:
            abnormal.append((char, KANGXI_RADICALS[char], hex(ord(char))))
    return abnormal


async def check_table(db, table: str, columns: list) -> list:
    """檢查指定表的異常字元"""
    issues = []

    for column in columns:
        try:
            query = text(f"SELECT id, {column} FROM {table} WHERE {column} IS NOT NULL")
            result = await db.execute(query)
            rows = result.fetchall()

            for row in rows:
                row_id, value = row
                if value:
                    abnormal = find_abnormal_chars(str(value))
                    if abnormal:
                        issues.append({
                            'table': table,
                            'column': column,
                            'id': row_id,
                            'abnormal_chars': abnormal,
                            'original': value[:100] + '...' if len(value) > 100 else value
                        })
        except Exception as e:
            print(f"  警告: 檢查 {table}.{column} 時發生錯誤: {e}")

    return issues


async def fix_table(db, table: str, columns: list) -> int:
    """修復指定表的異常字元"""
    fixed_count = 0

    for column in columns:
        try:
            # 構建 REPLACE 鏈
            replace_sql = column
            for kangxi, normal in KANGXI_RADICALS.items():
                replace_sql = f"REPLACE({replace_sql}, '{kangxi}', '{normal}')"

            # 只更新包含異常字元的記錄
            conditions = " OR ".join([f"{column} LIKE '%{k}%'" for k in KANGXI_RADICALS.keys()])

            update_query = text(f"""
                UPDATE {table}
                SET {column} = {replace_sql}
                WHERE {conditions}
            """)

            result = await db.execute(update_query)
            if result.rowcount > 0:
                print(f"  ✓ {table}.{column}: 修復 {result.rowcount} 筆")
                fixed_count += result.rowcount

        except Exception as e:
            print(f"  警告: 修復 {table}.{column} 時發生錯誤: {e}")

    return fixed_count


async def main(args):
    """主函數"""
    print("=" * 60)
    print("Unicode 字元正規化工具")
    print("=" * 60)

    tables = TABLES_TO_CHECK
    if args.table:
        tables = [(args.table, [col for t, cols in TABLES_TO_CHECK if t == args.table for col in cols])]
        if not tables[0][1]:
            print(f"錯誤: 未找到表 '{args.table}' 的欄位配置")
            return 1

    async with AsyncSessionLocal() as db:
        if args.check:
            print("\n[檢查模式] 掃描異常字元...\n")
            all_issues = []

            for table, columns in tables:
                print(f"檢查表: {table}")
                issues = await check_table(db, table, columns)
                all_issues.extend(issues)

            if all_issues:
                print(f"\n發現 {len(all_issues)} 筆異常記錄:\n")
                for issue in all_issues:
                    print(f"  [{issue['table']}.{issue['column']}] ID={issue['id']}")
                    print(f"    異常字元: {issue['abnormal_chars']}")
                    print(f"    原始內容: {issue['original']}")
                    print()
            else:
                print("\n✓ 未發現異常字元")

        elif args.fix:
            print("\n[修復模式] 正規化異常字元...\n")
            total_fixed = 0

            for table, columns in tables:
                print(f"修復表: {table}")
                fixed = await fix_table(db, table, columns)
                total_fixed += fixed

            await db.commit()
            print(f"\n✓ 共修復 {total_fixed} 筆記錄")

        else:
            print("請指定 --check 或 --fix 參數")
            return 1

    print("\n" + "=" * 60)
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description="Unicode 字元正規化工具")
    parser.add_argument('--check', action='store_true', help='檢查異常字元（不修改）')
    parser.add_argument('--fix', action='store_true', help='修復異常字元')
    parser.add_argument('--table', type=str, help='指定要處理的表名')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    exit_code = asyncio.run(main(args))
    sys.exit(exit_code)

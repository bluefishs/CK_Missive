#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unicode 字元正規化工具

修復資料庫中的異常 Unicode 字元，包括：
- 康熙部首 (U+2F00 - U+2FDF) → 標準 CJK 統一漢字
- CJK 相容漢字 (U+F900 - U+FAFF) → 標準 CJK 統一漢字
- 全形英數 (U+FF01 - U+FF5E) → ASCII 半形
- 其他 NFKC 可轉換字元

用法：
  python -m app.scripts.normalize_unicode --check     # 僅檢查，不修改
  python -m app.scripts.normalize_unicode --fix       # 執行修復
  python -m app.scripts.normalize_unicode --table documents  # 指定表
  python -m app.scripts.normalize_unicode --check --verbose  # 顯示異常字元細節

@version 3.0.0
@date 2026-03-04
@security SQL 注入防護：白名單驗證 + 識別符引號
"""

import asyncio
import argparse
import sys
import os
import unicodedata
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

from sqlalchemy import text
from app.db.database import AsyncSessionLocal

# 常見需要清理的表和欄位 (白名單，欄位名需與實際 DB 一致)
TABLES_TO_CHECK = [
    ('contract_projects', ['project_name', 'project_code', 'description']),
    ('government_agencies', ['agency_name', 'agency_short_name', 'address']),
    ('documents', ['subject', 'content', 'notes', 'ck_note', 'doc_number']),
    ('partner_vendors', ['vendor_name', 'contact_person', 'address']),
    ('taoyuan_dispatch_orders', ['project_name', 'dispatch_no', 'sub_case_name', 'contact_note']),
    ('canonical_entities', ['canonical_name']),
    ('entity_aliases', ['alias_name']),
    ('document_entity_mentions', ['mention_text']),
]

# 安全性：建立允許的表名和列名白名單
ALLOWED_TABLES = {t[0] for t in TABLES_TO_CHECK}
ALLOWED_COLUMNS = {col for _, cols in TABLES_TO_CHECK for col in cols}


def validate_identifier(name: str, allowed_set: set, identifier_type: str) -> str:
    """
    驗證並返回安全的 SQL 識別符

    Args:
        name: 識別符名稱
        allowed_set: 允許的名稱集合
        identifier_type: 識別符類型 (用於錯誤訊息)

    Returns:
        安全的識別符 (使用雙引號包裹)

    Raises:
        ValueError: 如果識別符不在白名單中
    """
    if name not in allowed_set:
        raise ValueError(f"不允許的{identifier_type}: {name}")
    # 使用雙引號包裹識別符，防止 SQL 注入
    return f'"{name}"'


def is_abnormal_char(char: str, include_fullwidth: bool = False) -> bool:
    """
    判斷字元是否為異常 Unicode（NFKC 正規化後會改變的字元）

    涵蓋範圍：
    - U+2F00-U+2FDF: 康熙部首
    - U+F900-U+FAFF: CJK 相容漢字
    - U+FF01-U+FF5E: 全形英數符號（預設不檢查，因中文語境常用全形標點）

    Args:
        include_fullwidth: 是否包含全形英數（預設 False，僅 --fullwidth 模式啟用）
    """
    cp = ord(char)
    # 快速路徑：康熙部首 + CJK 相容漢字（永遠視為異常）
    if 0x2F00 <= cp <= 0x2FDF:  # 康熙部首
        return True
    if 0xF900 <= cp <= 0xFAFF:  # CJK 相容漢字
        return True
    # 全形英數：僅在明確要求時才視為異常
    if include_fullwidth and 0xFF01 <= cp <= 0xFF5E:
        return True
    return False


def normalize_text(value: str) -> str:
    """
    將異常 Unicode 字元正規化為標準形式

    針對性處理（保留全形標點）：
    - 康熙部首 (U+2F00-U+2FDF) → 標準漢字
    - CJK 相容漢字 (U+F900-U+FAFF) → 標準漢字

    NOTE: 不使用全域 NFKC，因為會把全形逗號（，）轉成半形（,），
    但中文語境中全形標點是正常的。改為逐字元判斷只轉換異常範圍。
    """
    if not value or not isinstance(value, str):
        return value

    result = []
    for char in value:
        cp = ord(char)
        if 0x2F00 <= cp <= 0x2FDF or 0xF900 <= cp <= 0xFAFF:
            # 康熙部首 + CJK 相容漢字 → NFKC 正規化
            result.append(unicodedata.normalize('NFKC', char))
        else:
            result.append(char)
    return ''.join(result)


def find_abnormal_chars(value: str, include_fullwidth: bool = False) -> list:
    """找出文字中的異常字元，返回 [(原字元, 正規化後, hex碼位, 類別)] 清單"""
    abnormal = []
    for char in value:
        if is_abnormal_char(char, include_fullwidth):
            cp = ord(char)
            normalized = unicodedata.normalize('NFKC', char)
            if 0x2F00 <= cp <= 0x2FDF:
                category = 'Kangxi Radical'
            elif 0xF900 <= cp <= 0xFAFF:
                category = 'CJK Compat'
            elif 0xFF01 <= cp <= 0xFF5E:
                category = 'Fullwidth'
            else:
                category = 'Other'
            abnormal.append((char, normalized, hex(cp), category))
    return abnormal


async def check_table(db, table: str, columns: list, verbose: bool = False, include_fullwidth: bool = False) -> list:
    """檢查指定表的異常字元"""
    issues = []

    safe_table = validate_identifier(table, ALLOWED_TABLES, "表名")

    for column in columns:
        try:
            safe_column = validate_identifier(column, ALLOWED_COLUMNS, "列名")
            query = text(f"SELECT id, {safe_column} FROM {safe_table} WHERE {safe_column} IS NOT NULL")
            result = await db.execute(query)
            rows = result.fetchall()

            for row in rows:
                row_id, value = row
                if value:
                    abnormal = find_abnormal_chars(str(value), include_fullwidth)
                    if abnormal:
                        issues.append({
                            'table': table,
                            'column': column,
                            'id': row_id,
                            'abnormal_chars': abnormal,
                            'original': value[:100] + '...' if len(value) > 100 else value
                        })
        except Exception as e:
            logger.warning(f"檢查 {table}.{column} 時發生錯誤: {e}")

    return issues


async def fix_table(db, table: str, columns: list) -> int:
    """
    修復指定表的異常字元

    策略：逐筆讀取 → Python NFKC 正規化 → 逐筆回寫
    （比 SQL REPLACE 鏈更可靠，涵蓋所有 NFKC 可轉換字元）
    """
    fixed_count = 0

    safe_table = validate_identifier(table, ALLOWED_TABLES, "表名")

    for column in columns:
        try:
            safe_column = validate_identifier(column, ALLOWED_COLUMNS, "列名")

            # 讀取所有非空紀錄
            query = text(f"SELECT id, {safe_column} FROM {safe_table} WHERE {safe_column} IS NOT NULL")
            result = await db.execute(query)
            rows = result.fetchall()

            batch_updates = []
            for row in rows:
                row_id, value = row
                if not value:
                    continue
                normalized = normalize_text(str(value))
                if normalized != str(value):
                    batch_updates.append((row_id, normalized))

            # 批次更新
            if batch_updates:
                for row_id, normalized_value in batch_updates:
                    update_query = text(
                        f"UPDATE {safe_table} SET {safe_column} = :val WHERE id = :id"
                    )
                    await db.execute(update_query, {"val": normalized_value, "id": row_id})

                logger.info(f"{table}.{column}: 修復 {len(batch_updates)} 筆")
                fixed_count += len(batch_updates)

        except Exception as e:
            logger.warning(f"修復 {table}.{column} 時發生錯誤: {e}")

    return fixed_count


async def main(args):
    """主函數"""
    # 配置日誌等級
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    logger.info("=" * 60)
    logger.info("Unicode 字元正規化工具 v3.0")
    logger.info("涵蓋：康熙部首 + CJK 相容漢字 + 全形英數")
    logger.info("=" * 60)

    tables = TABLES_TO_CHECK
    if args.table:
        tables = [(args.table, [col for t, cols in TABLES_TO_CHECK if t == args.table for col in cols])]
        if not tables[0][1]:
            logger.error(f"未找到表 '{args.table}' 的欄位配置")
            return 1

    if args.check:
        logger.info("[檢查模式] 掃描異常字元...")
        all_issues = []
        category_stats: dict[str, int] = {}

        for table, columns in tables:
            # 每個表獨立 session，避免單表錯誤中斷全部
            async with AsyncSessionLocal() as db:
                try:
                    logger.info(f"檢查表: {table}")
                    issues = await check_table(db, table, columns, args.verbose, getattr(args, 'fullwidth', False))
                    all_issues.extend(issues)
                except Exception as e:
                    logger.warning(f"跳過表 {table}: {e}")

        if all_issues:
            logger.info(f"\n發現 {len(all_issues)} 筆含異常字元的記錄:")
            for issue in all_issues:
                logger.info(f"  [{issue['table']}.{issue['column']}] ID={issue['id']} ({len(issue['abnormal_chars'])} 個異常字元)")
                for char, norm, hexval, cat in issue['abnormal_chars']:
                    category_stats[cat] = category_stats.get(cat, 0) + 1
                    if args.verbose:
                        logger.info(f"    '{char}' → '{norm}' ({hexval}, {cat})")

            logger.info(f"\n異常字元統計:")
            for cat, count in sorted(category_stats.items(), key=lambda x: -x[1]):
                logger.info(f"  {cat}: {count} 個")
        else:
            logger.info("未發現異常字元")

    elif args.fix:
        logger.info("[修復模式] 正規化異常字元...")
        total_fixed = 0

        for table, columns in tables:
            async with AsyncSessionLocal() as db:
                try:
                    logger.info(f"修復表: {table}")
                    fixed = await fix_table(db, table, columns)
                    total_fixed += fixed
                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    logger.warning(f"修復表 {table} 失敗: {e}")

        logger.info(f"\n共修復 {total_fixed} 筆記錄")

    else:
        logger.warning("請指定 --check 或 --fix 參數")
        return 1

    logger.info("=" * 60)
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description="Unicode 字元正規化工具 v3.0")
    parser.add_argument('--check', action='store_true', help='檢查異常字元（不修改）')
    parser.add_argument('--fix', action='store_true', help='修復異常字元')
    parser.add_argument('--table', type=str, help='指定要處理的表名')
    parser.add_argument('--verbose', '-v', action='store_true', help='顯示異常字元細節')
    parser.add_argument('--fullwidth', action='store_true', help='同時檢查全形英數符號 (預設不檢查)')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    exit_code = asyncio.run(main(args))
    sys.exit(exit_code)

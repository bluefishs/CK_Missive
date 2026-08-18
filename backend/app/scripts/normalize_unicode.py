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
    # `client_agency` 2026-08-18 補入（見檔尾說明）—— 併進既有這一筆，
    # 不另開第二個 contract_projects 條目：同一張表兩處宣告，
    # 下次改的人只會看到其中一處。
    ('contract_projects', ['project_name', 'project_code', 'description', 'client_agency']),
    ('government_agencies', ['agency_name', 'agency_short_name', 'address']),
    ('documents', ['subject', 'content', 'notes', 'ck_note', 'doc_number']),
    ('partner_vendors', ['vendor_name', 'contact_person', 'address']),
    ('taoyuan_dispatch_orders', ['project_name', 'dispatch_no', 'sub_case_name', 'contact_note']),
    ('canonical_entities', ['canonical_name']),
    ('entity_aliases', ['alias_name']),
    ('document_entity_mentions', ['mention_text']),
    # 2026-08-16 補入：這兩張表正是 case_code 橋樑比對的兩端，
    # 名稱帶相容字會讓「同名」比對靜默失效（含承攬案件防重）。
    ('erp_quotations', ['case_name']),
    ('pm_cases', ['case_name']),
    # 2026-08-18 補入：owner 開 `/contract-cases/21/agency-contacts/26/edit`
    # 時順手查到 —— 那筆的 `department` 是「桃園市政府⼯務局⼯程⽤地科」，
    # 用的是**康熙部首** `⼯`(U+2F27)／`⽤`(U+2F65) 而不是 `工`／`用`。
    #
    # 字形一模一樣、長度一樣，肉眼與畫面都看不出來，
    # 但 `contract_projects.client_agency` 的「桃園市政府⼯務局」
    # **永遠比對不到** `government_agencies.agency_name` 的「桃園市政府工務局」。
    #
    # 這兩欄原本不在白名單裡 —— 而它們正是機關關聯比對的兩端。
    # 實測 5 筆：承辦 department 3、機關名 1、承攬 client_agency 1
    #（機關那筆是「南投縣埔⾥地政事務所」的 `里` U+F9E9，
    # 前後看起來完全相同 —— 本專案在 wiki 連結那次踩過同一個字）。
    ('project_agency_contacts', ['contact_name', 'department', 'position']),
    # 2026-08-18 同日稍後：**全庫掃描**（477 個文字欄位）而不是只看白名單 ——
    # 白名單本身就是「拿看得見的東西當分母」，它只涵蓋 27 欄。
    #
    # 掃出 **29 個欄位 / 約 1,500 筆**帶康熙部首或相容漢字，
    # 而實害已經在三個層級發生：
    #
    #   機關      `南投縣埔里地政事務所` 兩筆並存（id 42 正常字／146 U+2FA5）
    #   KG        canonical 兩組重複：`115年度`(52/42477)、
    #             `國強一街至文中路道路開闢工程`(286/14908)
    #   實體解析  `document_entities` **28 個不重複名稱**永遠併不進 canonical
    #
    # KG 的整個價值就建立在名稱比對上，而這幾欄原本不在白名單裡。
    ('document_entities', ['entity_name']),
    ('entity_relations', ['source_entity_name', 'target_entity_name']),
    ('documents', ['receiver']),
]

# ---------------------------------------------------------------------------
# 刻意**不**正規化的欄位（2026-08-18 全庫掃描後的判斷）
#
# 全庫 29 個受污染欄位裡，只有上面那些該修。其餘分兩類，改了反而是錯的：
#
# ① **原文快照** —— 改了就與來源不一致，日後對不回去
#      tender_records.raw_data(365) / .title(365)   外部爬來的原始資料
#      document_entities.context(31)                抽取當下的上下文片段
#      document_entity_mentions.context(20)         同上
#      document_chunks.chunk_text(7)                文件切片，改了與原文不符
#      tender_match_review.pcc_title(28)            外部來源的原始標題
#
# ② **歷史事實** —— 那是「當時發生了什麼」，不是可以整理的資料
#      audit_logs.changes(109)                      稽核紀錄
#      system_notifications.message(245)            已經送出去的訊息
#      agent_query_traces.*(5)                      當時的問答紀錄
#      event_reminders.title/message(6)             已送出的提醒
#
# ③ 純顯示、不參與比對 —— 修了沒有壞處也沒有好處，不值得動生產資料
#      document_calendar_events.title(63)/.description(14)
#      taoyuan_work_records.description(18)
#      canonical_entities.description(2) / entity_relations.relation_label(2)
#      erp_invoices/erp_vendor_payables/finance_ledgers.description(各 1)
#      contract_projects.project_path(1)
#
# 判準：**這個欄位有沒有人拿去和別的東西比對？** 有 → 正規化；
# 沒有 → 不動（動生產資料要有理由，「看起來不整齊」不是理由）。
NOT_NORMALIZED_REASON = "見上方註解：原文快照／歷史事實／純顯示欄位刻意不動"

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
    failed: list[str] = []

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
            # ⚠️ 2026-08-18：這裡原本只 log warning **而不 rollback**。
            #
            # PostgreSQL 的交易一旦有敘述失敗就進入 aborted 狀態，
            # 後續每一個查詢都直接回 `InFailedSQLTransactionError` ——
            # 於是**第一個欄位失敗之後，這張表剩下的欄位全部被跳過**，
            # 每個都只留一行 warning，最後印「共修復 0 筆」。
            #
            # 實際踩到：`government_agencies.agency_name` 正規化後撞唯一鍵
            #（因為表裡已經有一筆正常字的同名機關），
            # 導致 agency_short_name / address 兩欄根本沒被檢查過，
            # 而輸出看起來像「這張表沒事」。
            #
            # 同本專案反覆記錄的 `idle in transaction (aborted)` 家族。
            failed.append(f"{table}.{column}: {type(e).__name__}")
            logger.warning(f"修復 {table}.{column} 時發生錯誤: {e}")
            try:
                await db.rollback()   # 讓後續欄位還能繼續
            except Exception:
                pass

    if failed:
        # **不能只留 warning** —— 呼叫端只看 fixed_count 會以為沒事可做。
        logger.error(
            "%s：%d 個欄位修復失敗（未修復不等於沒問題）：%s",
            table, len(failed), "; ".join(failed),
        )

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

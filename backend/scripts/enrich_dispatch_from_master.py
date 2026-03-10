# -*- coding: utf-8 -*-
"""
一次性腳本：從「分派案件紀錄表」主表 Excel 增強匯入價金 + 公文原始值。

用法：
  cd backend
  python scripts/enrich_dispatch_from_master.py
"""
import sys
import os
import asyncio
import json

# 加入 backend 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXCEL_PATH = str(
    _PROJECT_ROOT / "#BUG" / "8.112至113年度桃園查估案-分派案件紀錄表_雅惠姊協助填寫-1150303.xlsx"
)


async def main():
    from app.db.database import AsyncSessionLocal
    from app.services.taoyuan.dispatch_enrichment_service import DispatchEnrichmentService

    # 讀取 Excel
    with open(EXCEL_PATH, 'rb') as f:
        content = f.read()
    print(f"讀取 Excel: {EXCEL_PATH} ({len(content):,} bytes)")

    async with AsyncSessionLocal() as db:
        service = DispatchEnrichmentService(db)
        result = await service.enrich_from_master_excel(
            file_content=content,
            dispatch_no_prefix="112年_派工單號",
            data_start_row=4,
            sheet_name="派工單",
        )

    print("\n=== 匯入結果 ===")
    print(f"  訊息: {result['message']}")
    print(f"  掃描行數: {result['total_rows']}")
    print(f"  匹配派工單: {result['matched']}")
    print(f"  更新公文原始值: {result['doc_updated']}")
    print(f"  價金新增: {result['payment_created']}")
    print(f"  價金更新: {result['payment_updated']}")
    print(f"  跳過 (未找到): {result['skipped']}")

    if result['errors']:
        print(f"\n=== 未匹配項目 ({len(result['errors'])}) ===")
        for err in result['errors'][:20]:
            print(f"  項次 {err['seq']}: {err['dispatch_no']} - {err['reason']}")


if __name__ == '__main__':
    asyncio.run(main())

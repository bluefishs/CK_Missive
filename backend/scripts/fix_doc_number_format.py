# -*- coding: utf-8 -*-
"""
修正公文字號格式
從 "乾坤測1140000145" 修正為 "乾坤測字第1140000145號"
"""
import sys
import os
import re

# 添加 backend 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 資料庫連接
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ck_user:ck_password@localhost:5434/ck_documents")


def fix_doc_number_format():
    """修正所有文號格式"""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 查詢所有不符合格式的文號（不包含「字第」和「號」）
        result = session.execute(text("""
            SELECT id, document_number, prefix_code, number_code
            FROM documents
            WHERE document_number IS NOT NULL
              AND document_number != ''
              AND document_number NOT LIKE '%字第%號'
        """))

        rows = result.fetchall()
        print(f"找到 {len(rows)} 筆需要修正的記錄")

        updated_count = 0
        for row in rows:
            doc_id, doc_number, prefix_code, number_code = row

            # 嘗試解析現有格式
            # 例如: "乾坤測1140000145" -> prefix="乾坤測", number="1140000145"
            if doc_number:
                # 使用正則表達式分離字和號
                match = re.match(r'^([^\d]+)(\d+)$', doc_number)
                if match:
                    prefix = match.group(1)
                    number = match.group(2)
                    new_doc_number = f"{prefix}字第{number}號"

                    # 更新記錄
                    session.execute(text("""
                        UPDATE documents
                        SET document_number = :new_doc_number,
                            prefix_code = :prefix,
                            number_code = :number
                        WHERE id = :id
                    """), {
                        'new_doc_number': new_doc_number,
                        'prefix': prefix,
                        'number': number,
                        'id': doc_id
                    })

                    print(f"  ID {doc_id}: '{doc_number}' -> '{new_doc_number}'")
                    updated_count += 1

        session.commit()
        print(f"\n成功更新 {updated_count} 筆記錄")

    except Exception as e:
        session.rollback()
        print(f"錯誤: {e}")
        raise
    finally:
        session.close()


def preview_changes():
    """預覽將要修正的記錄（不實際修改）"""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        result = session.execute(text("""
            SELECT id, document_number, prefix_code, number_code
            FROM documents
            WHERE document_number IS NOT NULL
              AND document_number != ''
            ORDER BY id
            LIMIT 20
        """))

        rows = result.fetchall()
        print(f"現有記錄預覽（前 20 筆）:")
        print("-" * 60)

        for row in rows:
            doc_id, doc_number, prefix_code, number_code = row
            needs_fix = doc_number and '字第' not in doc_number and '號' not in doc_number
            status = "需修正" if needs_fix else "正確"
            print(f"  ID {doc_id}: {doc_number} [{status}]")

    finally:
        session.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='修正公文字號格式')
    parser.add_argument('--preview', action='store_true', help='預覽模式，不實際修改')
    parser.add_argument('--fix', action='store_true', help='執行修正')

    args = parser.parse_args()

    if args.preview:
        preview_changes()
    elif args.fix:
        fix_doc_number_format()
    else:
        print("使用方式:")
        print("  python fix_doc_number_format.py --preview  # 預覽")
        print("  python fix_doc_number_format.py --fix      # 執行修正")

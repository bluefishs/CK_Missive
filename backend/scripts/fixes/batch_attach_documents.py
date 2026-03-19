"""
批次附件上傳腳本 — 從 Excel 讀取檔案路徑，將 PDF 附加到對應公文

用法:
    python scripts/fixes/batch_attach_documents.py --dry-run
    python scripts/fixes/batch_attach_documents.py

資料來源:
    Excel: D:\\CKProject\\CK_Missive\\#BUG\\112收發文整理匯入範本.xlsx
    Sheet: 公文系統匯入樣版
    Column 6 (F): 公文字號 (doc_number)
    Column 24 (X): 公文檔路徑(NEW) — 完整檔案路徑
"""

import argparse
import hashlib
import os
import shutil
import sys
import uuid
from datetime import datetime

# ── 確保 backend/ 在 sys.path ────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.insert(0, BACKEND_DIR)

import openpyxl
from sqlalchemy import create_engine, text

# ── 設定常數 ─────────────────────────────────────────────────────────────

EXCEL_PATH = r"D:\CKProject\CK_Missive\#BUG\112收發文整理匯入範本.xlsx"
SHEET_NAME = "公文系統匯入樣版"
COL_DOC_NUMBER = 5   # 0-indexed, column F
COL_FILE_PATH = 23   # 0-indexed, column X

# 附件儲存根目錄 (與 files/common.py 一致)
UPLOAD_BASE_DIR = os.path.join(BACKEND_DIR, "uploads")

# 從 .env 讀取資料庫連線
def get_database_url() -> str:
    """從 .env 讀取 DATABASE_URL"""
    env_path = os.path.join(BACKEND_DIR, "..", ".env")
    db_url = None
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DATABASE_URL="):
                    db_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not db_url:
        # fallback
        db_url = "postgresql://ck_user:ck_password@localhost:5434/ck_documents"
    # sqlalchemy 2.x 需要 postgresql:// 而非 postgres://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return db_url


def calculate_checksum(filepath: str) -> str:
    """計算檔案 SHA256"""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def get_structured_path(document_id: int, original_filename: str) -> tuple[str, str]:
    """
    生成結構化儲存路徑 (與 files/common.py 一致)

    格式: uploads/{year}/{month}/doc_{document_id}/{uuid8}_{safe_name}
    Returns: (full_path, relative_path_for_db)
    """
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    file_uuid = str(uuid.uuid4())[:8]

    # 安全化檔案名 — 保留中文字元
    safe_chars = []
    for c in original_filename:
        if c.isalnum() or c in "._-" or "\u4e00" <= c <= "\u9fff":
            safe_chars.append(c)
    safe_filename = "".join(safe_chars).strip()
    if not safe_filename:
        safe_filename = "unnamed.pdf"

    unique_filename = f"{file_uuid}_{safe_filename}"
    relative_dir = os.path.join(year, month, f"doc_{document_id}")
    full_dir = os.path.join(UPLOAD_BASE_DIR, relative_dir)

    relative_path = os.path.join(relative_dir, unique_filename)
    full_path = os.path.join(UPLOAD_BASE_DIR, relative_path)

    return full_path, full_dir, relative_path


def main():
    parser = argparse.ArgumentParser(description="批次附件上傳腳本")
    parser.add_argument("--dry-run", action="store_true", help="僅預覽，不實際寫入")
    args = parser.parse_args()

    dry_run = args.dry_run
    print(f"{'[DRY-RUN] ' if dry_run else ''}批次附件上傳腳本")
    print(f"Excel: {EXCEL_PATH}")
    print(f"儲存目錄: {UPLOAD_BASE_DIR}")
    print()

    # ── 1. 讀取 Excel ────────────────────────────────────────────────────
    if not os.path.exists(EXCEL_PATH):
        print(f"[ERROR] Excel 檔案不存在: {EXCEL_PATH}")
        sys.exit(1)

    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True)
    ws = wb[SHEET_NAME]

    rows_data = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        doc_number = row[COL_DOC_NUMBER]
        file_path = row[COL_FILE_PATH]
        if doc_number and file_path and str(file_path).strip():
            rows_data.append((str(doc_number).strip(), str(file_path).strip()))
    wb.close()

    print(f"Excel 中有檔案路徑的列數: {len(rows_data)}")

    # ── 2. 連接資料庫，查詢公文 ──────────────────────────────────────────
    db_url = get_database_url()
    engine = create_engine(db_url, echo=False)

    with engine.connect() as conn:
        # 建立 doc_number → id 映射
        result = conn.execute(text("SELECT id, doc_number FROM documents WHERE doc_number IS NOT NULL"))
        doc_map: dict[str, int] = {}
        for row in result:
            if row.doc_number:
                doc_map[row.doc_number.strip()] = row.id

        print(f"資料庫公文數 (有文號): {len(doc_map)}")

        # 查詢現有附件 (document_id → set of original_name)
        result = conn.execute(text(
            "SELECT document_id, original_name, file_name FROM document_attachments"
        ))
        existing_attachments: dict[int, set[str]] = {}
        for row in result:
            doc_id = row.document_id
            names = existing_attachments.setdefault(doc_id, set())
            if row.original_name:
                names.add(row.original_name)
            if row.file_name:
                names.add(row.file_name)

        print(f"現有附件數: {sum(len(v) for v in existing_attachments.values())}")
        print()

        # ── 3. 逐行處理 ─────────────────────────────────────────────────
        stats = {
            "matched": 0,
            "attached": 0,
            "doc_not_found": 0,
            "file_not_found": 0,
            "already_attached": 0,
            "errors": 0,
        }
        doc_not_found_samples: list[str] = []
        file_not_found_samples: list[str] = []
        error_samples: list[str] = []

        for doc_number, file_path in rows_data:
            # 3a. 查找公文
            doc_id = doc_map.get(doc_number)
            if doc_id is None:
                stats["doc_not_found"] += 1
                if len(doc_not_found_samples) < 5:
                    doc_not_found_samples.append(doc_number)
                continue

            # 3b. 檢查檔案是否存在
            if not os.path.isfile(file_path):
                stats["file_not_found"] += 1
                if len(file_not_found_samples) < 5:
                    file_not_found_samples.append(file_path)
                continue

            stats["matched"] += 1

            # 3c. 檢查是否已附加 (以 original_name 比對)
            original_name = os.path.basename(file_path)
            if doc_id in existing_attachments and original_name in existing_attachments[doc_id]:
                stats["already_attached"] += 1
                continue

            # 3d. 複製檔案並建立記錄
            try:
                file_size = os.path.getsize(file_path)
                full_dest, dest_dir, relative_path = get_structured_path(doc_id, original_name)

                if not dry_run:
                    os.makedirs(dest_dir, exist_ok=True)
                    shutil.copy2(file_path, full_dest)
                    checksum = calculate_checksum(full_dest)

                    # file_path 存入 DB 時帶 uploads/ 前綴 (與現有記錄一致)
                    db_file_path = os.path.join("uploads", relative_path).replace("\\", "/")

                    conn.execute(text("""
                        INSERT INTO document_attachments
                            (document_id, file_name, file_path, file_size, mime_type,
                             storage_type, original_name, checksum)
                        VALUES
                            (:doc_id, :file_name, :file_path, :file_size, :mime_type,
                             :storage_type, :original_name, :checksum)
                    """), {
                        "doc_id": doc_id,
                        "file_name": original_name,
                        "file_path": db_file_path,
                        "file_size": file_size,
                        "mime_type": "application/pdf",
                        "storage_type": "local",
                        "original_name": original_name,
                        "checksum": checksum,
                    })

                    # 同時更新 documents.has_attachment = true
                    conn.execute(text(
                        "UPDATE documents SET has_attachment = true WHERE id = :doc_id"
                    ), {"doc_id": doc_id})

                stats["attached"] += 1

            except Exception as e:
                stats["errors"] += 1
                if len(error_samples) < 5:
                    error_samples.append(f"doc_id={doc_id}, file={file_path}: {e}")

        if not dry_run:
            conn.commit()

    engine.dispose()

    # ── 4. 報告 ──────────────────────────────────────────────────────────
    print("=" * 60)
    print(f"{'[DRY-RUN] ' if dry_run else ''}批次附件上傳結果")
    print("=" * 60)
    print(f"  Excel 資料列:       {len(rows_data)}")
    print(f"  公文+檔案都找到:    {stats['matched']}")
    print(f"  成功附加:           {stats['attached']}")
    print(f"  已有相同附件(跳過): {stats['already_attached']}")
    print(f"  公文未找到:         {stats['doc_not_found']}")
    print(f"  檔案不存在:         {stats['file_not_found']}")
    print(f"  錯誤:               {stats['errors']}")
    print()

    if doc_not_found_samples:
        print("公文未找到範例:")
        for s in doc_not_found_samples:
            print(f"  - {s}")
        print()

    if file_not_found_samples:
        print("檔案不存在範例:")
        for s in file_not_found_samples:
            print(f"  - {s}")
        print()

    if error_samples:
        print("錯誤範例:")
        for s in error_samples:
            print(f"  - {s}")
        print()


if __name__ == "__main__":
    main()

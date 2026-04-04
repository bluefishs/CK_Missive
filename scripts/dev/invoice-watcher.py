#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
發票影像 Watchdog 監控服務

同時監控多個雲端同步資料夾 (OneDrive / Google Drive / Dropbox)，
偵測到新影像檔後自動執行：
  1. QR Code 掃描 — 含左側 Head + 右側 Detail (品項明細)
  2. OCR 文字辨識 — QR 失敗時由 Tesseract 補充
  3. 自動建立費用報銷記錄 → PostgreSQL
  4. 歸檔至各目錄下「已處理」子資料夾

使用方式:
  python scripts/dev/invoice-watcher.py
  pm2 start scripts/dev/invoice-watcher.py --name invoice-watcher --interpreter python

環境變數:
  INVOICE_WATCH_DIR  — 監控資料夾 (分號分隔多路徑)
                       預設: ~/OneDrive/發票掃描;~/Google Drive/發票掃描;~/Dropbox/發票掃描
  DATABASE_URL       — PostgreSQL 連線字串 (從 .env 自動載入)

Version: 1.0.0
"""
import os
import sys
import time
import shutil
import logging
import asyncio
from pathlib import Path
from datetime import datetime

# 確保 backend 目錄在 path 中
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# 載入 .env
from dotenv import load_dotenv
load_dotenv(BACKEND_DIR.parent / ".env")

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# 監控資料夾 — 不限定雲端平台，統一放到同一個資料夾
# 使用者只需將任何雲端 App (OneDrive/Google Drive/Dropbox/iCloud) 的
# 「掃描文件」存到此資料夾即可，Watchdog 不需知道來源是哪個平台。
# 多資料夾用分號分隔。
_DEFAULT_DIR = str(Path.home() / "Documents" / "發票掃描")
WATCH_DIRS = [
    Path(d.strip())
    for d in os.getenv("INVOICE_WATCH_DIR", _DEFAULT_DIR).split(os.pathsep)
    if d.strip()
]
DONE_SUBDIR = "已處理"
FAILED_SUBDIR = "辨識失敗"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp", ".tiff", ".pdf"}
SETTLE_SECONDS = 3  # 等候雲端同步寫入完成

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("invoice-watcher")

# ---------------------------------------------------------------------------
# DB 寫入
# ---------------------------------------------------------------------------

async def create_expense_record(
    inv_num: str,
    date_val,
    amount,
    buyer_ban: str | None = None,
    seller_ban: str | None = None,
    source: str = "watchdog",
    receipt_path: str | None = None,
) -> dict:
    """建立費用報銷記錄到 PostgreSQL"""
    from app.core.database import AsyncSessionLocal
    from app.services.expense_invoice_service import ExpenseInvoiceService
    from app.schemas.erp.expense import ExpenseInvoiceCreate
    from decimal import Decimal

    async with AsyncSessionLocal() as db:
        svc = ExpenseInvoiceService(db)

        # 重複檢查
        existing = await svc.check_duplicate(inv_num)
        if existing:
            return {"status": "duplicate", "inv_num": inv_num}

        data = ExpenseInvoiceCreate(
            inv_num=inv_num,
            date=date_val,
            amount=Decimal(str(amount)) if amount else Decimal("0"),
            buyer_ban=buyer_ban,
            seller_ban=seller_ban,
            source=source,
        )
        invoice = await svc.create(data, receipt_image_path=receipt_path)
        await db.commit()
        return {"status": "created", "id": invoice.id, "inv_num": inv_num}

# ---------------------------------------------------------------------------
# 檔案處理
# ---------------------------------------------------------------------------

def process_file(file_path: Path):
    """處理單一影像檔 — 使用統一辨識服務"""
    logger.info(f"處理: {file_path.name}")

    from app.services.invoice_recognizer import recognize_invoice
    import uuid

    recognition = recognize_invoice(str(file_path))
    result_info = {"file": file_path.name, "method": recognition.method, "status": "failed"}

    if recognition.success:
        try:
            # 複製到 uploads 作為收據
            receipt_dir = BACKEND_DIR / "uploads" / "receipts"
            receipt_dir.mkdir(parents=True, exist_ok=True)
            receipt_name = f"watch_{uuid.uuid4().hex[:8]}{file_path.suffix}"
            shutil.copy2(file_path, receipt_dir / receipt_name)

            db_result = asyncio.run(create_expense_record(
                inv_num=recognition.inv_num,
                date_val=recognition.date,
                amount=recognition.amount or 0,
                buyer_ban=recognition.buyer_ban,
                seller_ban=recognition.seller_ban,
                source=f"watchdog_{recognition.method}",
                receipt_path=f"uploads/receipts/{receipt_name}",
            ))
            result_info.update(db_result)
            logger.info(f"  {recognition.method}→DB: {db_result['status']} ({recognition.inv_num})")
        except Exception as e:
            logger.error(f"  建檔失敗: {e}")
            result_info["error"] = str(e)

    # 歸檔
    parent = file_path.parent
    if result_info.get("status") in ("created", "duplicate"):
        done_dir = parent / DONE_SUBDIR
        done_dir.mkdir(parents=True, exist_ok=True)
        dest = done_dir / f"{datetime.now():%Y%m%d}_{file_path.name}"
        shutil.move(str(file_path), str(dest))
        logger.info(f"  歸檔: {dest.name}")
    else:
        fail_dir = parent / FAILED_SUBDIR
        fail_dir.mkdir(parents=True, exist_ok=True)
        dest = fail_dir / f"{datetime.now():%Y%m%d}_{file_path.name}"
        shutil.move(str(file_path), str(dest))
        logger.warning(f"  辨識失敗，移至: {dest.name}")

    return result_info

# ---------------------------------------------------------------------------
# Watchdog Handler
# ---------------------------------------------------------------------------

class InvoiceHandler(FileSystemEventHandler):
    """監控新增影像檔"""

    def __init__(self):
        self._processing = set()

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in IMAGE_EXTS:
            return
        if path.name.startswith(".") or path.name.startswith("~"):
            return
        # 避免重複處理
        if str(path) in self._processing:
            return
        self._processing.add(str(path))

        # 等候檔案寫入完成 (雲端同步可能分段寫入)
        time.sleep(SETTLE_SECONDS)

        try:
            if path.exists() and path.stat().st_size > 0:
                process_file(path)
        except Exception as e:
            logger.error(f"處理異常: {path.name}: {e}")
        finally:
            self._processing.discard(str(path))

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # 篩選實際存在的監控目錄 (自動建立)
    active_dirs = []
    for d in WATCH_DIRS:
        try:
            d.mkdir(parents=True, exist_ok=True)
            (d / DONE_SUBDIR).mkdir(exist_ok=True)
            active_dirs.append(d)
        except OSError as e:
            logger.warning(f"無法建立目錄 {d}: {e}")

    if not active_dirs:
        logger.error("沒有可監控的資料夾，請設定 INVOICE_WATCH_DIR 環境變數")
        return

    logger.info("=" * 60)
    logger.info("發票影像 Watchdog 監控服務啟動")
    for d in active_dirs:
        logger.info(f"  監控: {d}")
    logger.info(f"  支援: {', '.join(sorted(IMAGE_EXTS))}")
    logger.info("=" * 60)

    # 啟動前處理各目錄已有檔案
    for watch_dir in active_dirs:
        existing = [f for f in watch_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in IMAGE_EXTS]
        if existing:
            logger.info(f"[{watch_dir.name}] 發現 {len(existing)} 個待處理檔案")
            for f in sorted(existing):
                try:
                    process_file(f)
                except Exception as e:
                    logger.error(f"處理失敗: {f.name}: {e}")

    # 啟動 Watchdog — 監控所有目錄
    handler = InvoiceHandler()
    observer = Observer()
    for watch_dir in active_dirs:
        observer.schedule(handler, str(watch_dir), recursive=False)
        logger.info(f"  → 已掛載監控: {watch_dir}")
    observer.start()

    logger.info(f"監控 {len(active_dirs)} 個資料夾中... (Ctrl+C 停止)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("監控已停止")
    observer.join()


if __name__ == "__main__":
    main()
